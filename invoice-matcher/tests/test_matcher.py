import tempfile
from pathlib import Path
from invoice_matcher.matcher import generate_rename_plan, execute_renames


class TestGenerateRenamePlan:
    def test_basic_rename_plan(self):
        matches = {
            "document1.pdf": ["INV-001"],
            "scan_page3.pdf": ["INV-002"],
        }
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {
            "document1.pdf": "INV-001.pdf",
            "scan_page3.pdf": "INV-002.pdf",
        }

    def test_preserves_original_extension(self):
        matches = {"scan.PDF": ["INV-100"]}
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {"scan.PDF": "INV-100.PDF"}

    def test_pattern_with_original_name(self):
        matches = {"doc.pdf": ["INV-100"]}
        plan = generate_rename_plan(matches, pattern="{invoice}_{original}")
        assert plan == {"doc.pdf": "INV-100_doc.pdf"}

    def test_multiple_invoices_default_separator(self):
        matches = {"multi.pdf": ["INV-001", "INV-002"]}
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {"multi.pdf": "INV-001_INV-002.pdf"}

    def test_multiple_invoices_custom_separator(self):
        """User wants invoices separated by - instead of _."""
        matches = {"multi.pdf": ["123", "456", "789"]}
        plan = generate_rename_plan(matches, pattern="{invoice}", separator="-")
        assert plan == {"multi.pdf": "123-456-789.pdf"}

    def test_multiple_invoices_plus_separator(self):
        matches = {"multi.pdf": ["123", "456"]}
        plan = generate_rename_plan(matches, pattern="{invoice}", separator="+")
        assert plan == {"multi.pdf": "123+456.pdf"}

    def test_no_matches_excluded_from_plan(self):
        matches = {
            "matched.pdf": ["INV-001"],
            "unmatched.pdf": [],
        }
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {"matched.pdf": "INV-001.pdf"}

    def test_default_pattern(self):
        matches = {"file.pdf": ["INV-999"]}
        plan = generate_rename_plan(matches)
        assert plan == {"file.pdf": "INV-999.pdf"}

    def test_master_version_used_for_rename(self):
        """Master has "56", fuzzy matched — rename uses "56" not "000056"."""
        matches = {"scan.pdf": ["56"]}
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {"scan.pdf": "56.pdf"}


class TestExecuteRenames:
    def test_renames_files_in_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "doc1.pdf").write_bytes(b"fake")
            (Path(tmpdir) / "doc2.pdf").write_bytes(b"fake")

            plan = {"doc1.pdf": "INV-001.pdf", "doc2.pdf": "INV-002.pdf"}
            results = execute_renames(Path(tmpdir), plan)

            assert (Path(tmpdir) / "INV-001.pdf").exists()
            assert (Path(tmpdir) / "INV-002.pdf").exists()
            assert not (Path(tmpdir) / "doc1.pdf").exists()
            assert len(results["renamed"]) == 2

    def test_skips_if_target_already_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "doc.pdf").write_bytes(b"original")
            (Path(tmpdir) / "INV-001.pdf").write_bytes(b"existing")

            plan = {"doc.pdf": "INV-001.pdf"}
            results = execute_renames(Path(tmpdir), plan)

            assert len(results["skipped"]) == 1
            assert (Path(tmpdir) / "doc.pdf").exists()  # not renamed
