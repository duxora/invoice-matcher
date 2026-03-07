# Invoice Matcher

Match and rename invoice PDFs using Gemini AI.

## What it does

You have a folder full of scanned PDFs — invoices, receipts, purchase orders. One file is a master list with all your invoice numbers. Invoice Matcher reads every PDF using Google's Gemini AI, finds which invoice number each file belongs to, and renames the file for you.

**Handles fuzzy matching:** If the master list has "56" but the document shows "000056", it still matches and renames to "56".

**Multiple invoices per file:** If one PDF contains multiple invoices, all numbers are included in the filename (e.g., `123-456-789.pdf`).

**Non-destructive:** Original files are never modified — renamed copies are saved to a separate output folder.

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

## Setup Guide (for non-technical users)

### Step 1: Install Python

You need Python 3.10 or newer on your computer.

**On macOS:**
1. Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter)
2. Type this and press Enter:
   ```
   python3 --version
   ```
3. If you see `Python 3.10` or higher, skip to Step 2
4. If not, download Python from https://www.python.org/downloads/ and run the installer

**On Windows:**
1. Open **Command Prompt** (press `Win` key, type "cmd", press Enter)
2. Type this and press Enter:
   ```
   python --version
   ```
3. If you see `Python 3.10` or higher, skip to Step 2
4. If not:
   - Download Python from https://www.python.org/downloads/
   - **IMPORTANT:** During installation, check the box **"Add Python to PATH"**
   - Run the installer

### Step 2: Get a Gemini API Key (Free)

1. Open your browser and go to: https://aistudio.google.com/apikey
2. Sign in with your Google account
3. Click **"Create API Key"**
4. Select any project (or create a new one)
5. Copy the key — it looks like `AIzaSy...` (about 40 characters)
6. Save it somewhere safe — you'll paste it into the app once (it's saved locally)

> **Cost:** The free tier gives you 15 requests/minute and 1,500 requests/day.
> That's enough for ~1,500 PDF files per day at no cost.

### Step 3: Install Invoice Matcher

Open Terminal (Mac) or Command Prompt (Windows), navigate to the invoice-matcher folder:
```
cd path/to/invoice-matcher
```
**Tip (Mac):** Type `cd ` then drag the folder from Finder into Terminal to auto-fill the path.

Then run:

```
pip install -e .
```

On macOS, if that doesn't work, try:
```
pip3 install -e .
```

You should see "Successfully installed invoice-matcher" at the end.

### Step 4: Start the App

Run this command:

```
invoice-matcher
```

Then open your browser and go to: **http://127.0.0.1:8000**

You should see the Invoice Matcher web page.

> **To stop the app:** Go back to Terminal and press `Ctrl + C`.

---

## How to Use

### 1. Configure API Key (first time only)

Click **Settings** in the top right, paste your Gemini API key, and click **Save**. The key is stored locally on your computer.

### 2. Select Invoice Files

You have three options:

| Method | How |
|--------|-----|
| **Select Folder** | Click "Select Folder" — a native folder picker opens. Select the folder containing your PDFs. |
| **Upload ZIP** | Click "Upload ZIP" — select a .zip file containing your PDFs. The app extracts them automatically. |
| **Paste path** | Type or paste the full folder path directly into the text field. |

### 3. Select Master File

The master file is the PDF that lists all your invoice numbers.

- **From directory:** If you selected a folder, a dropdown appears with all PDFs in that folder — pick the master file.
- **Browse:** Click "Browse" to select any PDF file from your computer.

### 4. Set Output Folder (optional)

Where renamed files will be saved.

- **Default:** An `outputs` subfolder is created inside the source folder.
- **Custom:** Click "Browse" or paste a path to choose a different location.
- **Required** when using ZIP upload.

> **Note:** Original files are never modified — copies are saved to the output folder.

### 5. Fill in the Form

| Field | What to enter |
|-------|--------------|
| **Filename Pattern** | How you want files renamed (see below) |
| **Multi-Invoice Separator** | Character between multiple invoice numbers (default: `/`) |

### 6. Filename Patterns

The pattern controls how matched files get renamed. File extension (.pdf) is always kept automatically.

| Pattern | Example Result | When to use |
|---------|---------------|-------------|
| `{invoice}` | `56.pdf` | Simple — just the invoice number (default) |
| `{invoice}_{original}` | `56_scan_001.pdf` | Keep the original name too |
| `HD_{invoice}` | `HD_56.pdf` | Add a custom prefix |
| `MuaBan_{invoice}` | `MuaBan_56.pdf` | Vietnamese prefix example |

> **Note:** Numbers use the master list version (e.g., master has "56", even if the document shows "000056").

### 7. Multi-Invoice Separator

When a PDF contains multiple invoices, they are joined with the separator. Default is `/`, but since `/` is invalid in filenames, it's automatically replaced with `-`.

| Separator | Example Result |
|-----------|---------------|
| `/` (default) | `123-456-789.pdf` (replaced with `-`) |
| `_` | `123_456_789.pdf` |
| `-` | `123-456-789.pdf` |

### 8. Scan & Review

1. Click **"Scan & Match"** — wait while Gemini reads each PDF (a few seconds per file)
2. Review the results table:
   - **Green** = matched (will be renamed)
   - **Red** = unmatched (will be left alone)
3. If everything looks correct, click **"Rename Files"**

> **Safe to use:** The app shows you a preview before renaming anything.
> Original files are preserved — renamed copies go to the output folder.
> Files that already exist in the output folder are skipped (no overwriting).

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `command not found: invoice-matcher` | Run `pip install -e .` again in the invoice-matcher folder |
| `command not found: pip` | Try `pip3` instead, or reinstall Python with "Add to PATH" checked |
| "Not a valid directory" | Make sure you typed the full folder path. On Mac, drag the folder into Terminal to get the path. |
| "No invoice numbers found" | The master file might not be a readable PDF, or Gemini couldn't extract numbers. Try a different master file. |
| "Failed to read master file" | Check your Gemini API key is correct and you have internet. |
| Scan is slow | Each PDF takes 2-5 seconds. For 100 files, expect ~5-8 minutes. |
| Some files not matched | Gemini may not read poorly scanned or handwritten PDFs well. |
| Port 8000 already in use | Another app is using that port. Stop it or wait a moment and try again. |

---

## Requirements

- Python 3.10+
- Gemini API key (free tier — 1,500 requests/day)
- Internet connection (for Gemini API calls)
- Works on macOS, Windows, and Linux
