# Getting Started — Invoice Matcher

## Step 1: Install Python

You need Python 3.10 or newer.

**On macOS:**
1. Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter)
2. Type `python3 --version` and press Enter
3. If you see `Python 3.10` or higher, skip to Step 2
4. If not, download Python from https://www.python.org/downloads/ and run the installer

**On Windows:**
1. Open **Command Prompt** (press `Win` key, type "cmd", press Enter)
2. Type `python --version` and press Enter
3. If you see `Python 3.10` or higher, skip to Step 2
4. If not:
   - Download Python from https://www.python.org/downloads/
   - **IMPORTANT:** During installation, check the box **"Add Python to PATH"**
   - Run the installer

## Step 2: Get a Gemini API Key (Free)

1. Go to https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Select any project (or create a new one)
5. Copy the key — it looks like `AIzaSy...` (about 40 characters)

> **Cost:** The free tier gives you 15 requests/minute and 1,500 requests/day — enough for ~1,500 files per day at no cost.

## Step 3: Install Invoice Matcher

### Option A: Clone the repository

```bash
git clone https://github.com/duxora/invoice-matcher.git
cd invoice-matcher
```

### Option B: From a received folder

Open Terminal (Mac) or Command Prompt (Windows), navigate to the invoice-matcher folder:
```bash
cd path/to/invoice-matcher
```
**Tip (Mac):** Type `cd ` then drag the folder from Finder into Terminal to auto-fill the path.

### Install

```bash
pip install -e .
```

On macOS, if `pip` is not found:
```bash
pip3 install -e .
```

You should see "Successfully installed invoice-matcher" at the end.

## Step 4: Start the App

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
