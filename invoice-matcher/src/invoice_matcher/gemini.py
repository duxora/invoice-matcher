"""Gemini AI integration for PDF invoice extraction."""
import json
import re
from google import genai
from google.genai import types

MODEL_NAME = "gemini-2.0-flash"

MASTER_LIST_PROMPT = """You are an invoice number extractor.
This PDF is a master list of invoice numbers (buying and selling).
Extract ALL invoice numbers from this document.
Return ONLY a JSON array of invoice number strings. Example: ["INV-001", "INV-002"]
No explanation, no markdown, just the JSON array."""

MATCH_PROMPT_TEMPLATE = """You are an invoice number matcher.
This PDF is a business document (invoice, receipt, purchase order, etc).
Here is a list of known invoice numbers from the master list: {invoices}

Find which of these invoice numbers appear in this document.
IMPORTANT: Numbers may have leading zeros or different formatting.
For example, master number "56" matches "000056" or "0056" in the document.
Similarly, "HD-123" matches "HD-00123".

When you find a match, return the MASTER LIST version of the number (not the document version).
For example, if master has "56" and document has "000056", return "56".

Return ONLY a JSON array of matched master invoice numbers. If none match, return [].
No explanation, no markdown, just the JSON array."""


def _get_client(api_key: str):
    return genai.Client(api_key=api_key)


def _parse_invoice_list(text: str) -> list[str]:
    """Parse Gemini response into a list of invoice numbers."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    # Try JSON first
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except json.JSONDecodeError:
        pass
    # Fallback: one per line
    return [line.strip() for line in text.splitlines() if line.strip()]


def _normalize_number(s: str) -> str:
    """Strip leading zeros from numeric parts for fuzzy comparison."""
    return re.sub(r'0*(\d+)', lambda m: m.group(1), s)


def fuzzy_match_invoices(
    gemini_found: list[str], known_invoices: list[str]
) -> list[str]:
    """Match Gemini results back to master list, handling leading zeros.

    Returns the master list version of matched invoice numbers.
    Example: gemini found "000056", master has "56" → returns "56"
    """
    matched = []
    for found in gemini_found:
        norm_found = _normalize_number(found)
        for known in known_invoices:
            norm_known = _normalize_number(known)
            if norm_found == norm_known:
                if known not in matched:
                    matched.append(known)
                break
    return matched


def extract_invoice_list(pdf_bytes: bytes, api_key: str) -> list[str]:
    """Extract all invoice numbers from a master list PDF."""
    client = _get_client(api_key)
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            MASTER_LIST_PROMPT,
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        ],
    )
    return _parse_invoice_list(response.text)


def extract_invoices_from_pdf(
    pdf_bytes: bytes, known_invoices: list[str], api_key: str
) -> list[str]:
    """Find which known invoice numbers appear in a PDF document.

    Returns the master list version of matched numbers.
    Handles leading zeros: master "56" matches document "000056".
    """
    client = _get_client(api_key)
    prompt = MATCH_PROMPT_TEMPLATE.format(invoices=json.dumps(known_invoices))
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=[
            prompt,
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        ],
    )
    gemini_found = _parse_invoice_list(response.text)
    return fuzzy_match_invoices(gemini_found, known_invoices)
