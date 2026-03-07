"""Generate minimal test PDF fixtures for live Gemini tests.
Run once: python tests/create_test_fixtures.py
"""
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)


def create_minimal_pdf(text: str) -> bytes:
    """Create a minimal valid PDF with embedded text."""
    content_stream = f"BT /F1 12 Tf 100 700 Td ({text}) Tj ET"
    stream_bytes = content_stream.encode("latin-1")
    stream_len = len(stream_bytes)

    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj
4 0 obj << /Length {stream_len} >>
stream
{content_stream}
endstream
endobj
5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj
xref
0 6
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000266 00000 n
trailer << /Size 6 /Root 1 0 R >>
startxref
0
%%EOF"""
    return pdf.encode("latin-1")


master_text = "Invoice List: INV-2024-001, INV-2024-002, INV-2024-003"
(FIXTURES_DIR / "master.pdf").write_bytes(create_minimal_pdf(master_text))

doc1_text = "Purchase Order - Invoice Number: INV-2024-001 - Total: $500.00"
(FIXTURES_DIR / "doc_scan_001.pdf").write_bytes(create_minimal_pdf(doc1_text))

doc2_text = "Receipt for payment of invoice INV-2024-002 dated 2024-01-15"
(FIXTURES_DIR / "doc_scan_002.pdf").write_bytes(create_minimal_pdf(doc2_text))

doc3_text = "Company memo - quarterly review meeting notes"
(FIXTURES_DIR / "doc_scan_003.pdf").write_bytes(create_minimal_pdf(doc3_text))

print(f"Created test fixtures in {FIXTURES_DIR}")
