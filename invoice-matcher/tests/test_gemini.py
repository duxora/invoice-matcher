# tests/test_gemini.py
from unittest.mock import patch, MagicMock
from invoice_matcher.gemini import (
    extract_invoices_from_pdf,
    extract_invoice_list,
    fuzzy_match_invoices,
    _normalize_number,
)


def _mock_gemini_response(text: str):
    """Create a mock Gemini response object."""
    resp = MagicMock()
    resp.text = text
    return resp


class TestExtractInvoiceList:
    """Extract invoice numbers from the master file."""

    def test_parses_invoice_numbers_from_gemini_response(self):
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_gemini_response(
            '["INV-001", "INV-002", "INV-003"]'
        )
        with patch("invoice_matcher.gemini._get_model", return_value=mock_model):
            result = extract_invoice_list(b"fake pdf bytes", api_key="fake-key")
        assert result == ["INV-001", "INV-002", "INV-003"]

    def test_handles_gemini_returning_plain_list(self):
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_gemini_response(
            "INV-001\nINV-002\nINV-003"
        )
        with patch("invoice_matcher.gemini._get_model", return_value=mock_model):
            result = extract_invoice_list(b"fake pdf bytes", api_key="fake-key")
        assert result == ["INV-001", "INV-002", "INV-003"]


class TestNormalizeNumber:
    """Strip leading zeros from numeric parts for fuzzy comparison."""

    def test_strips_leading_zeros(self):
        assert _normalize_number("000056") == "56"

    def test_preserves_non_numeric_prefix(self):
        assert _normalize_number("HD-00123") == "HD-123"

    def test_no_change_needed(self):
        assert _normalize_number("56") == "56"

    def test_multiple_numeric_parts(self):
        assert _normalize_number("INV-001-002") == "INV-1-2"

    def test_pure_zeros_becomes_zero(self):
        assert _normalize_number("000") == "0"


class TestFuzzyMatchInvoices:
    """Match Gemini results back to master list handling leading zeros."""

    def test_exact_match(self):
        result = fuzzy_match_invoices(["INV-001"], ["INV-001", "INV-002"])
        assert result == ["INV-001"]

    def test_leading_zeros_match(self):
        """Master has "56", document has "000056" — returns "56"."""
        result = fuzzy_match_invoices(["000056"], ["56", "78", "99"])
        assert result == ["56"]

    def test_leading_zeros_with_prefix(self):
        """Master has "HD-123", document has "HD-00123" — returns "HD-123"."""
        result = fuzzy_match_invoices(["HD-00123"], ["HD-123", "HD-456"])
        assert result == ["HD-123"]

    def test_no_match(self):
        result = fuzzy_match_invoices(["999"], ["56", "78"])
        assert result == []

    def test_multiple_matches(self):
        result = fuzzy_match_invoices(["000056", "000078"], ["56", "78", "99"])
        assert result == ["56", "78"]

    def test_no_duplicates(self):
        result = fuzzy_match_invoices(["56", "0056", "00056"], ["56"])
        assert result == ["56"]

    def test_gemini_returns_master_version_directly(self):
        """If Gemini already returns master version, still works."""
        result = fuzzy_match_invoices(["56"], ["56", "78"])
        assert result == ["56"]


class TestExtractInvoicesFromPdf:
    """Find which invoice numbers from the master list appear in a document."""

    def test_finds_matching_invoice(self):
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_gemini_response(
            '["INV-002"]'
        )
        with patch("invoice_matcher.gemini._get_model", return_value=mock_model):
            result = extract_invoices_from_pdf(
                b"fake pdf bytes",
                known_invoices=["INV-001", "INV-002", "INV-003"],
                api_key="fake-key",
            )
        assert result == ["INV-002"]

    def test_returns_empty_when_no_match(self):
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_gemini_response("[]")
        with patch("invoice_matcher.gemini._get_model", return_value=mock_model):
            result = extract_invoices_from_pdf(
                b"fake pdf bytes",
                known_invoices=["INV-001"],
                api_key="fake-key",
            )
        assert result == []

    def test_fuzzy_match_leading_zeros(self):
        """Gemini finds "000056" in doc, master has "56" — returns "56"."""
        mock_model = MagicMock()
        mock_model.generate_content.return_value = _mock_gemini_response(
            '["000056"]'
        )
        with patch("invoice_matcher.gemini._get_model", return_value=mock_model):
            result = extract_invoices_from_pdf(
                b"fake pdf bytes",
                known_invoices=["56", "78", "99"],
                api_key="fake-key",
            )
        assert result == ["56"]
