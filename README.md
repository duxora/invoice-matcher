# Invoice Matcher

Match and rename invoice documents using Gemini AI.

## What it does

You have a folder full of scanned documents — invoices, receipts, purchase orders. One file is a master list with all your invoice numbers. Invoice Matcher reads every document using Google's Gemini AI, finds which invoice number each file belongs to, and creates a renamed copy for you.

**Handles fuzzy matching:** If the master list has "56" but the document shows "000056", it still matches and renames to "56".

**Multiple invoices per file:** If one document contains multiple invoices, all numbers are included in the filename (e.g., `123-456-789.pdf`).

**Non-destructive:** Original files are never modified — renamed copies are saved to a separate output folder.

**Supported file types:** PDF, PNG, JPG, TIFF, Word (.doc/.docx), Excel (.xls/.xlsx), PowerPoint (.ppt/.pptx)

**Before:**
```
scan_001.pdf    <- contains invoice HD-2024-0042
scan_002.pdf    <- contains invoice HD-2024-0107
scan_003.pdf    <- no invoice found
master_list.pdf <- lists all invoice numbers
```

**After (in outputs folder):**
```
outputs/
  HD-2024-0042.pdf
  HD-2024-0107.pdf
```

---

## Quick Start

```bash
pip install -e .
invoice-matcher
```

Open **http://127.0.0.1:8000** in your browser.

See **[docs/getting-started.md](docs/getting-started.md)** for the full setup guide (Python install, Gemini API key, usage instructions, troubleshooting).

---

## Requirements

- Python 3.10+
- Gemini API key (free tier — 1,500 requests/day)
- Internet connection (for Gemini API calls)
- Works on macOS, Windows, and Linux
