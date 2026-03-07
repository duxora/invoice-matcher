"""Live integration tests using real Gemini API.

These tests are SKIPPED unless GEMINI_API_KEY env var is set.
Run: GEMINI_API_KEY=your-key pytest tests/test_gemini_live.py -v
"""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from invoice_matcher.gemini import extract_invoice_list, extract_invoices_from_pdf
from invoice_matcher.matcher import generate_rename_plan, execute_renames

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
FIXTURES_DIR = Path(__file__).parent / "fixtures"

skip_no_key = pytest.mark.skipif(
    not GEMINI_API_KEY,
    reason="GEMINI_API_KEY env var not set"
)

skip_no_fixtures = pytest.mark.skipif(
    not (FIXTURES_DIR / "master.pdf").exists(),
    reason="Test fixtures not found — run: python tests/create_test_fixtures.py"
)


@skip_no_key
@skip_no_fixtures
class TestLiveExtractInvoiceList:
    def test_extracts_invoices_from_master_pdf(self):
        pdf_bytes = (FIXTURES_DIR / "master.pdf").read_bytes()
        invoices = extract_invoice_list(pdf_bytes, api_key=GEMINI_API_KEY)

        assert len(invoices) >= 3
        invoice_text = " ".join(invoices).upper()
        assert "001" in invoice_text
        assert "002" in invoice_text
        assert "003" in invoice_text


@skip_no_key
@skip_no_fixtures
class TestLiveExtractInvoicesFromPdf:
    def test_finds_matching_invoice_in_document(self):
        pdf_bytes = (FIXTURES_DIR / "doc_scan_001.pdf").read_bytes()
        known = ["INV-2024-001", "INV-2024-002", "INV-2024-003"]
        found = extract_invoices_from_pdf(pdf_bytes, known_invoices=known, api_key=GEMINI_API_KEY)

        assert len(found) >= 1
        assert any("001" in inv for inv in found)

    def test_no_match_in_unrelated_document(self):
        pdf_bytes = (FIXTURES_DIR / "doc_scan_003.pdf").read_bytes()
        known = ["INV-2024-001", "INV-2024-002", "INV-2024-003"]
        found = extract_invoices_from_pdf(pdf_bytes, known_invoices=known, api_key=GEMINI_API_KEY)

        assert found == []


@skip_no_key
@skip_no_fixtures
class TestLiveEndToEnd:
    def test_full_scan_and_rename_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in FIXTURES_DIR.iterdir():
                if f.suffix == ".pdf":
                    shutil.copy2(f, tmpdir)

            tmpdir_path = Path(tmpdir)

            master_bytes = (tmpdir_path / "master.pdf").read_bytes()
            master_invoices = extract_invoice_list(master_bytes, api_key=GEMINI_API_KEY)
            assert len(master_invoices) >= 3

            doc_files = [f for f in tmpdir_path.iterdir() if f.name != "master.pdf"]
            matches = {}
            for doc in sorted(doc_files):
                found = extract_invoices_from_pdf(
                    doc.read_bytes(),
                    known_invoices=master_invoices,
                    api_key=GEMINI_API_KEY,
                )
                matches[doc.name] = found

            matched_files = {k: v for k, v in matches.items() if v}
            assert len(matched_files) >= 2, f"Expected at least 2 matches, got: {matches}"

            plan = generate_rename_plan(matches, pattern="{invoice}")
            assert len(plan) >= 2

            results = execute_renames(tmpdir_path, plan)
            assert len(results["renamed"]) >= 2

            for item in results["renamed"]:
                assert (tmpdir_path / item["new"]).exists()
