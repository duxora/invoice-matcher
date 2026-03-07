"""Edge case and error handling tests."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from invoice_matcher.app import app
from invoice_matcher.gemini import _parse_invoice_list
from invoice_matcher.matcher import generate_rename_plan, execute_renames

client = TestClient(app)


def _mock_gemini_response(text):
    r = MagicMock()
    r.text = text
    return r


# --- Parser edge cases ---

class TestParseInvoiceList:
    def test_json_array(self):
        assert _parse_invoice_list('["A", "B"]') == ["A", "B"]

    def test_newline_separated(self):
        assert _parse_invoice_list("A\nB\nC") == ["A", "B", "C"]

    def test_strips_whitespace(self):
        assert _parse_invoice_list("  A  \n  B  ") == ["A", "B"]

    def test_empty_string(self):
        assert _parse_invoice_list("") == []

    def test_json_with_markdown_fences(self):
        text = '```json\n["INV-1", "INV-2"]\n```'
        result = _parse_invoice_list(text)
        assert result == ["INV-1", "INV-2"]

    def test_skips_empty_lines(self):
        assert _parse_invoice_list("A\n\n\nB") == ["A", "B"]

    def test_numeric_invoices(self):
        assert _parse_invoice_list('[12345, 67890]') == ["12345", "67890"]


# --- Matcher edge cases ---

class TestMatcherEdgeCases:
    def test_empty_matches(self):
        assert generate_rename_plan({}) == {}

    def test_all_unmatched(self):
        matches = {"a.pdf": [], "b.pdf": []}
        assert generate_rename_plan(matches) == {}

    def test_pattern_without_invoice_placeholder(self):
        matches = {"a.pdf": ["INV-1"]}
        plan = generate_rename_plan(matches, pattern="renamed")
        assert plan == {"a.pdf": "renamed.pdf"}

    def test_special_characters_in_invoice(self):
        matches = {"a.pdf": ["INV-2024-001"]}
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {"a.pdf": "INV-2024-001.pdf"}

    def test_custom_prefix_pattern(self):
        matches = {"a.pdf": ["HD-2024-01"]}
        plan = generate_rename_plan(matches, pattern="HoaDon_{invoice}")
        assert plan == {"a.pdf": "HoaDon_HD-2024-01.pdf"}

    def test_preserves_uppercase_extension(self):
        matches = {"SCAN.PDF": ["56"]}
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {"SCAN.PDF": "56.PDF"}


class TestExecuteRenamesEdgeCases:
    def test_empty_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results = execute_renames(Path(tmpdir), {})
            assert results == {"renamed": [], "skipped": []}

    def test_source_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = {"nonexistent.pdf": "INV-001.pdf"}
            results = execute_renames(Path(tmpdir), plan)
            assert len(results["skipped"]) == 1
            assert results["skipped"][0]["reason"] == "source not found"

    def test_preserves_file_content_after_rename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = b"important invoice content"
            (Path(tmpdir) / "doc.pdf").write_bytes(content)
            execute_renames(Path(tmpdir), {"doc.pdf": "INV-001.pdf"})
            assert (Path(tmpdir) / "INV-001.pdf").read_bytes() == content

    def test_multiple_renames_in_one_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(5):
                (Path(tmpdir) / f"doc{i}.pdf").write_bytes(b"x")
            plan = {f"doc{i}.pdf": f"INV-{i:03d}.pdf" for i in range(5)}
            results = execute_renames(Path(tmpdir), plan)
            assert len(results["renamed"]) == 5
            assert len(results["skipped"]) == 0


# --- API edge cases ---

class TestApiEdgeCases:
    def test_scan_with_missing_master_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resp = client.post("/api/scan", json={
                "api_key": "fake",
                "directory": tmpdir,
                "master_file": "nonexistent.pdf",
                "pattern": "{invoice}",
            })
            assert resp.status_code == 400

    def test_scan_with_invalid_directory(self):
        resp = client.post("/api/scan", json={
            "api_key": "fake",
            "directory": "/this/does/not/exist",
            "master_file": "master.pdf",
            "pattern": "{invoice}",
        })
        assert resp.status_code == 400

    def test_scan_empty_master(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "master.pdf").write_bytes(b"empty")
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _mock_gemini_response("[]")

            with patch("invoice_matcher.gemini._get_client", return_value=mock_client):
                resp = client.post("/api/scan", json={
                    "api_key": "fake",
                    "directory": tmpdir,
                    "master_file": "master.pdf",
                })
            assert resp.status_code == 400
            assert "No invoice numbers" in resp.json()["detail"]

    def test_scan_with_only_master_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "master.pdf").write_bytes(b"master")
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = _mock_gemini_response('["INV-001"]')

            with patch("invoice_matcher.gemini._get_client", return_value=mock_client):
                resp = client.post("/api/scan", json={
                    "api_key": "fake",
                    "directory": tmpdir,
                    "master_file": "master.pdf",
                })
            assert resp.status_code == 200
            assert resp.json()["matches"] == {}
            assert resp.json()["plan"] == {}

    def test_scan_gemini_error_on_one_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "master.pdf").write_bytes(b"master")
            (Path(tmpdir) / "bad.pdf").write_bytes(b"bad")
            (Path(tmpdir) / "good.pdf").write_bytes(b"good")

            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = [
                _mock_gemini_response('["INV-001"]'),
                Exception("Gemini quota exceeded"),
                _mock_gemini_response('["INV-001"]'),
            ]

            with patch("invoice_matcher.gemini._get_client", return_value=mock_client):
                resp = client.post("/api/scan", json={
                    "api_key": "fake",
                    "directory": tmpdir,
                    "master_file": "master.pdf",
                })
            assert resp.status_code == 200
            data = resp.json()
            assert data["matches"]["good.pdf"]["invoices"] == ["INV-001"]
            assert data["matches"]["bad.pdf"]["invoices"] == []
            assert "error" in data["matches"]["bad.pdf"]

    def test_rename_invalid_directory(self):
        resp = client.post("/api/rename", json={
            "directory": "/nonexistent",
            "plan": {"a.pdf": "b.pdf"},
        })
        assert resp.status_code == 400

    def test_list_files_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resp = client.get(f"/api/list-files?directory={tmpdir}")
            assert resp.status_code == 200
            assert resp.json() == []

    def test_list_files_ignores_non_pdf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.pdf").write_bytes(b"x")
            (Path(tmpdir) / "b.xlsx").write_bytes(b"x")
            (Path(tmpdir) / "c.docx").write_bytes(b"x")
            (Path(tmpdir) / "d.jpg").write_bytes(b"x")
            resp = client.get(f"/api/list-files?directory={tmpdir}")
            assert resp.json() == ["a.pdf"]

    def test_health_endpoint(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
