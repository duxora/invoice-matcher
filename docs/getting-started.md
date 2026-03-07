# Getting Started — Invoice Matcher

## Prerequisites

- **Python 3.10+** installed on your machine
- **Gemini API key** (free) — get one at https://aistudio.google.com/apikey
- Internet connection (for Gemini API calls)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/duxora/invoice-matcher.git
cd invoice-matcher
```

### 2. Install dependencies

```bash
pip install -e .
```

On macOS, if `pip` is not found:
```bash
pip3 install -e .
```

### 3. Start the app

```bash
invoice-matcher
```

Open your browser at **http://127.0.0.1:8000**

> To stop: press `Ctrl + C` in the terminal.

---

## First-time Setup

1. Click **Settings** (top right)
2. Paste your Gemini API key and click **Save**
3. The key is stored locally at `~/.config/invoice-matcher/settings.json`

---

## Usage

### Select invoice files

| Method | How |
|--------|-----|
| **Select Folder** | Opens a native folder picker — select the folder with your documents |
| **Upload ZIP** | Upload a .zip file — the app extracts documents automatically |
| **Paste path** | Type or paste the full folder path into the text field |

### Supported file types

PDF, PNG, JPG, TIFF, Word (.doc/.docx), Excel (.xls/.xlsx), PowerPoint (.ppt/.pptx)

### Select master file

The master file lists all your invoice numbers. You can:
- **Browse** — click Browse to pick any file from your computer
- **Pick from directory** — a dropdown appears with files from the selected folder

### Output folder

- **Default:** creates an `outputs` subfolder in the source folder
- **Custom:** click Browse or paste a path
- **Required** when using ZIP upload
- Original files are never modified — copies are saved to the output folder

### Filename pattern

| Pattern | Example | Description |
|---------|---------|-------------|
| `{invoice}` | `56.pdf` | Invoice number only (default) |
| `{invoice}_{original}` | `56_scan_001.pdf` | Invoice + original name |
| `HD_{invoice}` | `HD_56.pdf` | Custom prefix |

### Multi-invoice separator

When a file contains multiple invoices, they are joined with the separator (default `/`).
Since `/` is invalid in filenames, it's automatically replaced with `-`.

| Separator | Result |
|-----------|--------|
| `/` (default) | `123-456-789.pdf` |
| `_` | `123_456_789.pdf` |

### Scan & rename

1. Click **Scan & Match** — Gemini reads each document (a few seconds per file)
2. Review the results table (green = matched, red = unmatched)
3. Click **Rename Files** to save renamed copies to the output folder

---

## Updating

```bash
cd invoice-matcher
git pull
pip install -e .
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `command not found: invoice-matcher` | Run `pip install -e .` again |
| `command not found: pip` | Try `pip3`, or reinstall Python with "Add to PATH" |
| "No invoice numbers found" | Master file may not be readable. Try a different format. |
| "Failed to read master file" | Check your API key and internet connection |
| Port 8000 in use | Another app is using it. Stop it or wait and retry. |
