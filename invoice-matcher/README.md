# Invoice Matcher

Match and rename invoice PDFs using Gemini AI.

## What it does

You have a folder full of scanned PDFs — invoices, receipts, purchase orders. One file is a master list with all your invoice numbers. Invoice Matcher reads every PDF using Google's Gemini AI, finds which invoice number each file belongs to, and renames the file for you.

**Handles fuzzy matching:** If the master list has "56" but the document shows "000056", it still matches and renames to "56".

**Multiple invoices per file:** If one PDF contains multiple invoices, all numbers are included in the filename (e.g., `123_456_789.pdf`).

**Before:**
```
scan_001.pdf    <- contains invoice HD-2024-0042
scan_002.pdf    <- contains invoice HD-2024-0107
scan_003.pdf    <- no invoice found
master_list.pdf <- lists all invoice numbers
```

**After:**
```
HD-2024-0042.pdf
HD-2024-0107.pdf
scan_003.pdf        <- unchanged (no match)
master_list.pdf     <- unchanged (master file)
```

---

## Setup Guide (Step-by-step for non-technical users)

### Step 1: Install Python

You need Python 3.10 or newer on your computer.

**macOS:**
1. Open **Terminal** (search "Terminal" in Spotlight)
2. Type: `python3 --version`
3. If you see `Python 3.10` or higher, you're good. If not:
   - Go to https://www.python.org/downloads/
   - Download the latest Python for macOS
   - Run the installer, click through all steps

**Windows:**
1. Open **Command Prompt** (search "cmd" in Start menu)
2. Type: `python --version`
3. If you see `Python 3.10` or higher, you're good. If not:
   - Go to https://www.python.org/downloads/
   - Download the latest Python for Windows
   - **IMPORTANT:** Check the box "Add Python to PATH" during installation
   - Run the installer

### Step 2: Get a Gemini API Key (Free)

1. Go to https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Select any project (or create a new one)
5. Copy the key — it looks like `AIzaSy...` (about 40 characters)
6. Save it somewhere safe (you'll paste it into the app each time)

> **Cost:** The free tier gives you 15 requests/minute and 1,500 requests/day.
> That's enough for ~1,500 PDF files per day at no cost.

### Step 3: Install Invoice Matcher

1. Open Terminal (macOS) or Command Prompt (Windows)
2. Navigate to the invoice-matcher folder:
   ```bash
   cd path/to/invoice-matcher
   ```
3. Install:
   ```bash
   pip install -e .
   ```
   (On macOS you may need `pip3 install -e .`)

### Step 4: Run the App

```bash
invoice-matcher
```

Then open your browser and go to: **http://127.0.0.1:8000**

---

## How to Use

### 1. Prepare Your Files

Put all your PDFs in **one folder**:
- The master invoice list (a PDF that contains all your invoice numbers)
- All the document PDFs you want to match and rename

### 2. Fill in the Form

| Field | What to enter |
|-------|--------------|
| **Gemini API Key** | Paste the key from Step 2 above |
| **Directory Path** | The full path to your PDF folder. Examples: `/Users/you/Desktop/invoices` (Mac) or `C:\Users\you\Desktop\invoices` (Windows) |
| **Master Invoice File** | Select the file that lists all invoice numbers |
| **Filename Pattern** | How you want files renamed (see below) |
| **Multi-Invoice Separator** | Character between multiple invoice numbers (default: `_`) |

### 3. Filename Patterns

The pattern controls how matched files get renamed:

| Pattern | Example Result | When to use |
|---------|---------------|-------------|
| `{invoice}` | `56.pdf` | Simple — just the invoice number (default) |
| `{invoice}_{original}` | `56_scan_001.pdf` | Keep the original name too |
| `HD_{invoice}` | `HD_56.pdf` | Add a custom prefix |
| `MuaBan_{invoice}` | `MuaBan_56.pdf` | Vietnamese prefix example |

> **Note:** The file extension (.pdf, .PDF) is always preserved automatically from the original file. Numbers use the master list version (e.g., master has "56", even if the document shows "000056").

### 4. Multi-Invoice Separator

When a PDF contains multiple invoices, they are joined with the separator:

| Separator | Example Result |
|-----------|---------------|
| `_` (default) | `123_456_789.pdf` |
| `-` | `123-456-789.pdf` |
| `+` | `123+456+789.pdf` |
| ` ` (space) | `123 456 789.pdf` |

### 5. Scan & Review

1. Click **"Scan & Match"** — wait while Gemini reads each PDF (a few seconds per file)
2. Review the results table:
   - Green = matched (will be renamed)
   - Red = unmatched (will be left alone)
3. If everything looks correct, click **"Rename Files"**

> **Safe to use:** The app shows you a preview before renaming anything.
> Files that already have the target name are skipped (no overwriting).

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Not a valid directory" | Make sure you typed the full folder path correctly. On Mac, you can drag a folder into Terminal to get its path. |
| "No invoice numbers found" | The master file might not be a readable PDF, or Gemini couldn't extract numbers from it. Try a different master file. |
| "Failed to read master file" | Check your Gemini API key is correct and you have internet access. |
| Scan is slow | Each PDF takes 2-5 seconds. For 100 files, expect ~5-8 minutes. |
| Some files not matched | Gemini may not be able to read poorly scanned or handwritten PDFs. |

## Requirements

- Python 3.10+
- Gemini API key (free tier works — 1,500 requests/day)
- Internet connection (for Gemini API calls)
