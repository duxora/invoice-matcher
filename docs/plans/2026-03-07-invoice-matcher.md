# Invoice Matcher Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** A standalone web app that uses Gemini AI to read PDF documents, match invoice numbers against a master list, and rename files accordingly.

**Architecture:** FastAPI backend serves a simple web UI. User points to a local directory of PDFs — one is the "master" invoice list, the rest are documents to match. Gemini API reads each PDF's content to extract invoice numbers, matches them against the master list (fuzzy — handles leading zeros like master "56" matching document "000056"), then renames files using the master's version of the invoice number with a user-defined pattern. Original file extension is always preserved. Preview step before any renames.

**Tech Stack:** Python 3.10+, FastAPI, Jinja2, google-generativeai (Gemini SDK), uvicorn

---

## Flow

```
1. User opens web UI at localhost:8000
2. User enters: directory path, selects master file, enters Gemini API key, optional filename pattern
3. Backend reads master PDF via Gemini → extracts list of invoice numbers
4. Backend reads each remaining PDF via Gemini → asks "what invoice number(s) appear in this document?"
5. Matches are displayed in a preview table: [original filename] → [new filename]
6. User confirms → files get renamed
```

## Project Structure

```
invoice-matcher/
├── pyproject.toml
├── README.md
├── src/
│   └── invoice_matcher/
│       ├── __init__.py
│       ├── app.py              # FastAPI app, routes, static/template config
│       ├── gemini.py           # Gemini API wrapper: extract invoices from PDF
│       ├── matcher.py          # Core logic: match invoices, generate rename plan
│       └── templates/
│           └── index.html      # Single-page UI: form + results table
└── tests/
    ├── test_gemini.py
    └── test_matcher.py
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `invoice-matcher/pyproject.toml`
- Create: `invoice-matcher/src/invoice_matcher/__init__.py`
- Create: `invoice-matcher/src/invoice_matcher/app.py`

**Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "invoice-matcher"
version = "0.1.0"
description = "Match and rename invoice PDFs using Gemini AI"
requires-python = ">=3.10"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "jinja2>=3.1.0",
    "google-generativeai>=0.8.0",
    "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "httpx>=0.27.0"]

[project.scripts]
invoice-matcher = "invoice_matcher.app:main"

[tool.hatch.build.targets.wheel]
packages = ["src/invoice_matcher"]
```

**Step 2: Create __init__.py**

```python
"""Invoice Matcher — match and rename invoice PDFs using Gemini AI."""
```

**Step 3: Create minimal app.py**

```python
"""Invoice Matcher — FastAPI web application."""
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Invoice Matcher", version="0.1.0")


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    uvicorn.run("invoice_matcher.app:app", host="127.0.0.1", port=8000, reload=True)
```

**Step 4: Install and verify**

Run:
```bash
cd invoice-matcher && pip install -e ".[dev]" && invoice-matcher &
sleep 2 && curl http://127.0.0.1:8000/health && kill %1
```
Expected: `{"status":"ok"}`

**Step 5: Commit**

```bash
git add invoice-matcher/
git commit -m "feat: scaffold invoice-matcher project"
```

---

### Task 2: Gemini PDF Extraction Module

**Files:**
- Create: `invoice-matcher/src/invoice_matcher/gemini.py`
- Create: `invoice-matcher/tests/test_gemini.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `cd invoice-matcher && python -m pytest tests/test_gemini.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/invoice_matcher/gemini.py
"""Gemini AI integration for PDF invoice extraction."""
import json
import google.generativeai as genai

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


def _get_model(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


def _parse_invoice_list(text: str) -> list[str]:
    """Parse Gemini response into a list of invoice numbers."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove first and last lines (``` markers)
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
    import re
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
    model = _get_model(api_key)
    response = model.generate_content([
        MASTER_LIST_PROMPT,
        {"mime_type": "application/pdf", "data": pdf_bytes},
    ])
    return _parse_invoice_list(response.text)


def extract_invoices_from_pdf(
    pdf_bytes: bytes, known_invoices: list[str], api_key: str
) -> list[str]:
    """Find which known invoice numbers appear in a PDF document.

    Returns the master list version of matched numbers.
    Handles leading zeros: master "56" matches document "000056".
    """
    model = _get_model(api_key)
    prompt = MATCH_PROMPT_TEMPLATE.format(invoices=json.dumps(known_invoices))
    response = model.generate_content([
        prompt,
        {"mime_type": "application/pdf", "data": pdf_bytes},
    ])
    gemini_found = _parse_invoice_list(response.text)
    # Normalize back to master list versions
    return fuzzy_match_invoices(gemini_found, known_invoices)
```

**Step 4: Run tests to verify they pass**

Run: `cd invoice-matcher && python -m pytest tests/test_gemini.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
cd invoice-matcher && git add -A && git commit -m "feat: gemini PDF invoice extraction module"
```

---

### Task 3: Matcher Module (Core Logic)

**Files:**
- Create: `invoice-matcher/src/invoice_matcher/matcher.py`
- Create: `invoice-matcher/tests/test_matcher.py`

**Step 1: Write the failing test**

```python
# tests/test_matcher.py
import os
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

    def test_multiple_invoices_in_one_file(self):
        matches = {"multi.pdf": ["INV-001", "INV-002"]}
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {"multi.pdf": "INV-001_INV-002.pdf"}

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
            # Create source files
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
```

**Step 2: Run tests to verify they fail**

Run: `cd invoice-matcher && python -m pytest tests/test_matcher.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: Write implementation**

```python
# src/invoice_matcher/matcher.py
"""Core matching logic: rename plan generation and execution."""
from pathlib import Path

DEFAULT_PATTERN = "{invoice}"


def generate_rename_plan(
    matches: dict[str, list[str]],
    pattern: str = DEFAULT_PATTERN,
) -> dict[str, str]:
    """Generate a mapping of old_filename -> new_filename.

    Pattern placeholders:
      {invoice}  — matched invoice number(s), joined by underscore if multiple
      {original} — original filename without extension

    The original file extension is always preserved automatically.
    Uses the master list version of invoice numbers (from fuzzy matching).
    """
    plan = {}
    for filename, invoices in matches.items():
        if not invoices:
            continue
        invoice_str = "_".join(invoices)
        original_path = Path(filename)
        original_stem = original_path.stem
        extension = original_path.suffix  # preserves case: .pdf, .PDF
        new_stem = pattern.format(invoice=invoice_str, original=original_stem)
        plan[filename] = new_stem + extension
    return plan


def execute_renames(
    directory: Path, plan: dict[str, str]
) -> dict[str, list[dict]]:
    """Rename files according to plan. Returns results with renamed/skipped lists."""
    results: dict[str, list[dict]] = {"renamed": [], "skipped": []}
    for old_name, new_name in plan.items():
        old_path = directory / old_name
        new_path = directory / new_name
        if new_path.exists():
            results["skipped"].append({
                "old": old_name, "new": new_name, "reason": "target already exists"
            })
            continue
        if not old_path.exists():
            results["skipped"].append({
                "old": old_name, "new": new_name, "reason": "source not found"
            })
            continue
        old_path.rename(new_path)
        results["renamed"].append({"old": old_name, "new": new_name})
    return results
```

**Step 4: Run tests to verify they pass**

Run: `cd invoice-matcher && python -m pytest tests/test_matcher.py -v`
Expected: All 7 tests PASS

**Step 5: Commit**

```bash
cd invoice-matcher && git add -A && git commit -m "feat: matcher module with rename plan and execution"
```

---

### Task 4: Web UI and Routes

**Files:**
- Create: `invoice-matcher/src/invoice_matcher/templates/index.html`
- Modify: `invoice-matcher/src/invoice_matcher/app.py`

**Step 1: Create the HTML template**

```html
<!-- src/invoice_matcher/templates/index.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Invoice Matcher</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; background: #f8f9fa; color: #212529; }
        h1 { margin-bottom: 0.5rem; }
        .subtitle { color: #6c757d; margin-bottom: 2rem; }
        .card { background: #fff; border-radius: 8px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
        label { display: block; font-weight: 600; margin-bottom: 0.3rem; }
        .help { font-size: 0.85rem; color: #6c757d; margin-bottom: 0.8rem; }
        input[type="text"], input[type="password"], select {
            width: 100%; padding: 0.6rem; border: 1px solid #ced4da; border-radius: 4px; font-size: 1rem; margin-bottom: 1rem;
        }
        button { padding: 0.7rem 1.5rem; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; }
        .btn-primary { background: #0d6efd; color: #fff; }
        .btn-primary:hover { background: #0b5ed7; }
        .btn-primary:disabled { background: #6c757d; cursor: not-allowed; }
        .btn-success { background: #198754; color: #fff; }
        .btn-success:hover { background: #157347; }
        table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
        th, td { padding: 0.6rem; text-align: left; border-bottom: 1px solid #dee2e6; }
        th { background: #f1f3f5; font-weight: 600; }
        .arrow { color: #0d6efd; font-weight: bold; }
        .no-match { color: #adb5bd; font-style: italic; }
        .status { padding: 0.2rem 0.5rem; border-radius: 3px; font-size: 0.85rem; }
        .status-matched { background: #d1e7dd; color: #0f5132; }
        .status-unmatched { background: #f8d7da; color: #842029; }
        .status-renamed { background: #d1e7dd; color: #0f5132; }
        .status-skipped { background: #fff3cd; color: #664d03; }
        #loading { display: none; margin-top: 1rem; }
        .spinner { display: inline-block; width: 1rem; height: 1rem; border: 2px solid #0d6efd; border-top-color: transparent; border-radius: 50%; animation: spin 0.6s linear infinite; }
        @keyframes spin { to { transform: rotate(360deg); } }
        .progress-text { margin-left: 0.5rem; }
        #results, #rename-section { display: none; }
        .error { background: #f8d7da; color: #842029; padding: 1rem; border-radius: 4px; margin-top: 1rem; }
    </style>
</head>
<body>
    <h1>Invoice Matcher</h1>
    <p class="subtitle">Match invoice PDFs against a master list using Gemini AI</p>

    <div class="card">
        <form id="scan-form">
            <label for="api_key">Gemini API Key</label>
            <input type="password" id="api_key" name="api_key" placeholder="AIza..." required>

            <label for="directory">Directory Path</label>
            <p class="help">Full path to the folder containing your PDF files</p>
            <input type="text" id="directory" name="directory" placeholder="/Users/you/invoices" required>

            <label for="master_file">Master Invoice File</label>
            <p class="help">Filename of the master list within that directory</p>
            <select id="master_file" name="master_file" disabled>
                <option value="">-- Enter directory first --</option>
            </select>

            <label for="pattern">Filename Pattern</label>
            <p class="help">Use <code>{invoice}</code> for the invoice number, <code>{original}</code> for original filename. File extension is kept automatically. Default: <code>{invoice}</code></p>
            <input type="text" id="pattern" name="pattern" value="{invoice}" placeholder="{invoice}">

            <button type="submit" class="btn-primary" id="scan-btn">Scan & Match</button>
        </form>

        <div id="loading">
            <span class="spinner"></span>
            <span class="progress-text" id="progress-text">Starting scan...</span>
        </div>
        <div id="error-box" class="error" style="display:none;"></div>
    </div>

    <div id="results" class="card">
        <h2>Match Results</h2>
        <p id="summary"></p>
        <table>
            <thead>
                <tr><th>Original File</th><th></th><th>New Name</th><th>Status</th></tr>
            </thead>
            <tbody id="results-body"></tbody>
        </table>
    </div>

    <div id="rename-section" class="card">
        <h2>Confirm Rename</h2>
        <p>This will rename matched files. Unmatched files are left unchanged.</p>
        <button class="btn-success" id="rename-btn">Rename Files</button>
        <div id="rename-result" style="margin-top: 1rem;"></div>
    </div>

    <script>
        const dirInput = document.getElementById('directory');
        const masterSelect = document.getElementById('master_file');
        let debounceTimer;

        dirInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(loadFiles, 500);
        });

        async function loadFiles() {
            const dir = dirInput.value.trim();
            if (!dir) return;
            try {
                const resp = await fetch(`/api/list-files?directory=${encodeURIComponent(dir)}`);
                if (!resp.ok) return;
                const files = await resp.json();
                masterSelect.innerHTML = files.map(f => `<option value="${f}">${f}</option>`).join('');
                masterSelect.disabled = false;
            } catch (e) { /* ignore */ }
        }

        document.getElementById('scan-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('scan-btn');
            const loading = document.getElementById('loading');
            const errorBox = document.getElementById('error-box');
            btn.disabled = true;
            loading.style.display = 'block';
            errorBox.style.display = 'none';
            document.getElementById('results').style.display = 'none';
            document.getElementById('rename-section').style.display = 'none';

            try {
                const body = {
                    api_key: document.getElementById('api_key').value,
                    directory: document.getElementById('directory').value,
                    master_file: masterSelect.value,
                    pattern: document.getElementById('pattern').value || '{invoice}',
                };

                // SSE for progress
                const resp = await fetch('/api/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body),
                });

                if (!resp.ok) {
                    const err = await resp.json();
                    throw new Error(err.detail || 'Scan failed');
                }

                const data = await resp.json();
                showResults(data);
            } catch (err) {
                errorBox.textContent = err.message;
                errorBox.style.display = 'block';
            } finally {
                btn.disabled = false;
                loading.style.display = 'none';
            }
        });

        function showResults(data) {
            const tbody = document.getElementById('results-body');
            tbody.innerHTML = '';
            let matchCount = 0;

            for (const [filename, info] of Object.entries(data.matches)) {
                const tr = document.createElement('tr');
                const hasMatch = info.invoices.length > 0;
                if (hasMatch) matchCount++;
                tr.innerHTML = `
                    <td>${filename}</td>
                    <td class="arrow">${hasMatch ? '&rarr;' : ''}</td>
                    <td>${hasMatch ? (data.plan[filename] || '') : '<span class="no-match">No match</span>'}</td>
                    <td><span class="status ${hasMatch ? 'status-matched' : 'status-unmatched'}">${hasMatch ? info.invoices.join(', ') : 'unmatched'}</span></td>
                `;
                tbody.appendChild(tr);
            }

            document.getElementById('summary').textContent =
                `Found ${matchCount} matches out of ${Object.keys(data.matches).length} files. Master invoices: ${data.master_invoices.length}`;
            document.getElementById('results').style.display = 'block';

            if (matchCount > 0) {
                document.getElementById('rename-section').style.display = 'block';
                window._renamePlan = { directory: data.directory, plan: data.plan };
            }
        }

        document.getElementById('rename-btn').addEventListener('click', async () => {
            const btn = document.getElementById('rename-btn');
            btn.disabled = true;
            try {
                const resp = await fetch('/api/rename', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(window._renamePlan),
                });
                const result = await resp.json();
                const div = document.getElementById('rename-result');
                let html = '';
                for (const r of result.renamed) {
                    html += `<p><span class="status status-renamed">Renamed</span> ${r.old} &rarr; ${r.new}</p>`;
                }
                for (const s of result.skipped) {
                    html += `<p><span class="status status-skipped">Skipped</span> ${s.old} (${s.reason})</p>`;
                }
                div.innerHTML = html || '<p>No files renamed.</p>';
                document.getElementById('rename-section').querySelector('h2').textContent = 'Rename Complete';
                btn.style.display = 'none';
            } catch (err) {
                document.getElementById('rename-result').innerHTML =
                    `<p class="error">${err.message}</p>`;
            }
        });
    </script>
</body>
</html>
```

**Step 2: Rewrite app.py with full routes**

```python
# src/invoice_matcher/app.py
"""Invoice Matcher — FastAPI web application."""
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import uvicorn

from invoice_matcher.gemini import extract_invoice_list, extract_invoices_from_pdf
from invoice_matcher.matcher import generate_rename_plan, execute_renames

app = FastAPI(title="Invoice Matcher", version="0.1.0")

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

SUPPORTED_EXTENSIONS = {".pdf"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/list-files")
async def list_files(directory: str = Query(...)):
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise HTTPException(400, f"Not a valid directory: {directory}")
    files = sorted(
        f.name for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    return files


class ScanRequest(BaseModel):
    api_key: str
    directory: str
    master_file: str
    pattern: str = "{invoice}"


@app.post("/api/scan")
async def scan(req: ScanRequest):
    dir_path = Path(req.directory)
    if not dir_path.is_dir():
        raise HTTPException(400, f"Not a valid directory: {req.directory}")

    master_path = dir_path / req.master_file
    if not master_path.is_file():
        raise HTTPException(400, f"Master file not found: {req.master_file}")

    # Step 1: Extract invoice list from master
    master_bytes = master_path.read_bytes()
    try:
        master_invoices = extract_invoice_list(master_bytes, api_key=req.api_key)
    except Exception as e:
        raise HTTPException(500, f"Failed to read master file: {e}")

    if not master_invoices:
        raise HTTPException(400, "No invoice numbers found in master file")

    # Step 2: Scan each remaining PDF
    other_files = [
        f for f in dir_path.iterdir()
        if f.is_file()
        and f.suffix.lower() in SUPPORTED_EXTENSIONS
        and f.name != req.master_file
    ]

    matches: dict[str, dict] = {}
    for pdf_file in sorted(other_files, key=lambda f: f.name):
        try:
            pdf_bytes = pdf_file.read_bytes()
            found = extract_invoices_from_pdf(
                pdf_bytes, known_invoices=master_invoices, api_key=req.api_key
            )
            matches[pdf_file.name] = {"invoices": found}
        except Exception as e:
            matches[pdf_file.name] = {"invoices": [], "error": str(e)}

    # Step 3: Generate rename plan
    match_map = {name: info["invoices"] for name, info in matches.items()}
    plan = generate_rename_plan(match_map, pattern=req.pattern)

    return {
        "directory": req.directory,
        "master_invoices": master_invoices,
        "matches": matches,
        "plan": plan,
    }


class RenameRequest(BaseModel):
    directory: str
    plan: dict[str, str]


@app.post("/api/rename")
async def rename(req: RenameRequest):
    dir_path = Path(req.directory)
    if not dir_path.is_dir():
        raise HTTPException(400, f"Not a valid directory: {req.directory}")
    results = execute_renames(dir_path, req.plan)
    return results


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    uvicorn.run("invoice_matcher.app:app", host="127.0.0.1", port=8000, reload=True)
```

**Step 3: Verify the app starts and serves the UI**

Run:
```bash
cd invoice-matcher && invoice-matcher &
sleep 2 && curl -s http://127.0.0.1:8000/ | head -5 && kill %1
```
Expected: HTML output starting with `<!DOCTYPE html>`

**Step 4: Commit**

```bash
cd invoice-matcher && git add -A && git commit -m "feat: web UI and API routes for invoice matching"
```

---

### Task 5: Integration Test with Mock Gemini

**Files:**
- Create: `invoice-matcher/tests/test_app.py`

**Step 1: Write integration test**

```python
# tests/test_app.py
"""Integration tests for the web API."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from invoice_matcher.app import app

client = TestClient(app)


def test_index_returns_html():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Invoice Matcher" in resp.text


def test_list_files_returns_pdfs():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "a.pdf").write_bytes(b"fake")
        (Path(tmpdir) / "b.pdf").write_bytes(b"fake")
        (Path(tmpdir) / "c.txt").write_bytes(b"not a pdf")

        resp = client.get(f"/api/list-files?directory={tmpdir}")
        assert resp.status_code == 200
        assert resp.json() == ["a.pdf", "b.pdf"]


def test_list_files_invalid_directory():
    resp = client.get("/api/list-files?directory=/nonexistent/path")
    assert resp.status_code == 400


def _mock_gemini_response(text):
    r = MagicMock()
    r.text = text
    return r


def test_full_scan_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "master.pdf").write_bytes(b"master")
        (Path(tmpdir) / "doc1.pdf").write_bytes(b"doc1")
        (Path(tmpdir) / "doc2.pdf").write_bytes(b"doc2")

        mock_model = MagicMock()
        # First call: master extraction, then doc1 match, then doc2 match
        mock_model.generate_content.side_effect = [
            _mock_gemini_response('["INV-001", "INV-002"]'),
            _mock_gemini_response('["INV-001"]'),
            _mock_gemini_response('[]'),
        ]

        with patch("invoice_matcher.gemini._get_model", return_value=mock_model):
            resp = client.post("/api/scan", json={
                "api_key": "fake-key",
                "directory": tmpdir,
                "master_file": "master.pdf",
                "pattern": "{invoice}",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert data["master_invoices"] == ["INV-001", "INV-002"]
        assert data["matches"]["doc1.pdf"]["invoices"] == ["INV-001"]
        assert data["matches"]["doc2.pdf"]["invoices"] == []
        assert data["plan"]["doc1.pdf"] == "INV-001.pdf"
        assert "doc2.pdf" not in data["plan"]


def test_rename_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        (Path(tmpdir) / "doc1.pdf").write_bytes(b"content")

        resp = client.post("/api/rename", json={
            "directory": tmpdir,
            "plan": {"doc1.pdf": "INV-001.pdf"},
        })

        assert resp.status_code == 200
        assert len(resp.json()["renamed"]) == 1
        assert (Path(tmpdir) / "INV-001.pdf").exists()
```

**Step 2: Run all tests**

Run: `cd invoice-matcher && python -m pytest tests/ -v`
Expected: All tests PASS

**Step 3: Commit**

```bash
cd invoice-matcher && git add -A && git commit -m "test: integration tests for scan and rename API"
```

---

### Task 6: README with Non-Technical User Guide

**Files:**
- Create: `invoice-matcher/README.md`

**Step 1: Write README**

````markdown
# Invoice Matcher

Match and rename invoice PDFs using Gemini AI.

## What it does

You have a folder full of scanned PDFs — invoices, receipts, purchase orders. One file is a master list with all your invoice numbers. Invoice Matcher reads every PDF using Google's Gemini AI, finds which invoice number each file belongs to, and renames the file for you.

**Before:**
```
scan_001.pdf    ← contains invoice HD-2024-0042
scan_002.pdf    ← contains invoice HD-2024-0107
scan_003.pdf    ← no invoice found
master_list.pdf ← lists all invoice numbers
```

**After:**
```
HD-2024-0042.pdf
HD-2024-0107.pdf
scan_003.pdf        ← unchanged (no match)
master_list.pdf     ← unchanged (master file)
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

### 3. Filename Patterns

The pattern controls how matched files get renamed:

| Pattern | Example Result | When to use |
|---------|---------------|-------------|
| `{invoice}` | `56.pdf` | Simple — just the invoice number (default) |
| `{invoice}_{original}` | `56_scan_001.pdf` | Keep the original name too |
| `HD_{invoice}` | `HD_56.pdf` | Add a custom prefix |
| `MuaBan_{invoice}` | `MuaBan_56.pdf` | Vietnamese prefix example |

> **Note:** The file extension (.pdf, .PDF) is always preserved automatically from the original file. Numbers use the master list version (e.g., master has "56", even if the document shows "000056").

### 4. Scan & Review

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
````

**Step 2: Commit**

```bash
cd invoice-matcher && git add README.md && git commit -m "docs: add README with non-technical user guide and Gemini setup"
```

---

### Task 7: Comprehensive Edge Case Tests

**Files:**
- Create: `invoice-matcher/tests/test_edge_cases.py`

**Step 1: Write edge case tests**

```python
# tests/test_edge_cases.py
"""Edge case and error handling tests."""
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from invoice_matcher.app import app
from invoice_matcher.gemini import _parse_invoice_list
from invoice_matcher.matcher import generate_rename_plan, execute_renames

client = TestClient(app)


def _mock_gemini_response(text):
    r = MagicMock()
    r.text = text
    return r


# --- Parser edge cases ---

class TestParseInvoiceList:
    def test_json_array(self):
        assert _parse_invoice_list('["A", "B"]') == ["A", "B"]

    def test_newline_separated(self):
        assert _parse_invoice_list("A\nB\nC") == ["A", "B", "C"]

    def test_strips_whitespace(self):
        assert _parse_invoice_list("  A  \n  B  ") == ["A", "B"]

    def test_empty_string(self):
        assert _parse_invoice_list("") == []

    def test_json_with_markdown_fences(self):
        # Gemini sometimes wraps in ```json ... ```
        text = '```json\n["INV-1", "INV-2"]\n```'
        # Should fall back to line parsing which is acceptable
        result = _parse_invoice_list(text)
        assert len(result) > 0

    def test_skips_empty_lines(self):
        assert _parse_invoice_list("A\n\n\nB") == ["A", "B"]

    def test_mixed_formats_in_response(self):
        assert _parse_invoice_list('["INV-001"]') == ["INV-001"]

    def test_numeric_invoices(self):
        assert _parse_invoice_list('[12345, 67890]') == ["12345", "67890"]


# --- Matcher edge cases ---

class TestMatcherEdgeCases:
    def test_empty_matches(self):
        assert generate_rename_plan({}) == {}

    def test_all_unmatched(self):
        matches = {"a.pdf": [], "b.pdf": []}
        assert generate_rename_plan(matches) == {}

    def test_pattern_without_invoice_placeholder(self):
        matches = {"a.pdf": ["INV-1"]}
        # Pattern missing {invoice} — just produces the literal string + extension
        plan = generate_rename_plan(matches, pattern="renamed")
        assert plan == {"a.pdf": "renamed.pdf"}

    def test_special_characters_in_invoice(self):
        matches = {"a.pdf": ["INV/2024/001"]}
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {"a.pdf": "INV/2024/001.pdf"}

    def test_custom_prefix_pattern(self):
        matches = {"a.pdf": ["HD-2024-01"]}
        plan = generate_rename_plan(matches, pattern="HoaDon_{invoice}")
        assert plan == {"a.pdf": "HoaDon_HD-2024-01.pdf"}

    def test_preserves_uppercase_extension(self):
        matches = {"SCAN.PDF": ["56"]}
        plan = generate_rename_plan(matches, pattern="{invoice}")
        assert plan == {"SCAN.PDF": "56.PDF"}


class TestExecuteRenamesEdgeCases:
    def test_empty_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            results = execute_renames(Path(tmpdir), {})
            assert results == {"renamed": [], "skipped": []}

    def test_source_file_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            plan = {"nonexistent.pdf": "INV-001.pdf"}
            results = execute_renames(Path(tmpdir), plan)
            assert len(results["skipped"]) == 1
            assert results["skipped"][0]["reason"] == "source not found"

    def test_preserves_file_content_after_rename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            content = b"important invoice content"
            (Path(tmpdir) / "doc.pdf").write_bytes(content)
            execute_renames(Path(tmpdir), {"doc.pdf": "INV-001.pdf"})
            assert (Path(tmpdir) / "INV-001.pdf").read_bytes() == content

    def test_multiple_renames_in_one_plan(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(5):
                (Path(tmpdir) / f"doc{i}.pdf").write_bytes(b"x")
            plan = {f"doc{i}.pdf": f"INV-{i:03d}.pdf" for i in range(5)}
            results = execute_renames(Path(tmpdir), plan)
            assert len(results["renamed"]) == 5
            assert len(results["skipped"]) == 0


# --- API edge cases ---

class TestApiEdgeCases:
    def test_scan_with_missing_master_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resp = client.post("/api/scan", json={
                "api_key": "fake",
                "directory": tmpdir,
                "master_file": "nonexistent.pdf",
                "pattern": "{invoice}",
            })
            assert resp.status_code == 400

    def test_scan_with_invalid_directory(self):
        resp = client.post("/api/scan", json={
            "api_key": "fake",
            "directory": "/this/does/not/exist",
            "master_file": "master.pdf",
            "pattern": "{invoice}.pdf",
        })
        assert resp.status_code == 400

    def test_scan_empty_master(self):
        """Master file returns no invoices — should 400."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "master.pdf").write_bytes(b"empty")
            mock_model = MagicMock()
            mock_model.generate_content.return_value = _mock_gemini_response("[]")

            with patch("invoice_matcher.gemini._get_model", return_value=mock_model):
                resp = client.post("/api/scan", json={
                    "api_key": "fake",
                    "directory": tmpdir,
                    "master_file": "master.pdf",
                })
            assert resp.status_code == 400
            assert "No invoice numbers" in resp.json()["detail"]

    def test_scan_with_only_master_file(self):
        """Directory has master file but no other PDFs — should return empty matches."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "master.pdf").write_bytes(b"master")
            mock_model = MagicMock()
            mock_model.generate_content.return_value = _mock_gemini_response('["INV-001"]')

            with patch("invoice_matcher.gemini._get_model", return_value=mock_model):
                resp = client.post("/api/scan", json={
                    "api_key": "fake",
                    "directory": tmpdir,
                    "master_file": "master.pdf",
                })
            assert resp.status_code == 200
            assert resp.json()["matches"] == {}
            assert resp.json()["plan"] == {}

    def test_scan_gemini_error_on_one_file(self):
        """If Gemini fails on one file, it should still process the rest."""
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "master.pdf").write_bytes(b"master")
            (Path(tmpdir) / "good.pdf").write_bytes(b"good")
            (Path(tmpdir) / "bad.pdf").write_bytes(b"bad")

            mock_model = MagicMock()
            mock_model.generate_content.side_effect = [
                _mock_gemini_response('["INV-001"]'),  # master
                Exception("Gemini quota exceeded"),      # bad.pdf (alphabetically first)
                _mock_gemini_response('["INV-001"]'),    # good.pdf
            ]

            with patch("invoice_matcher.gemini._get_model", return_value=mock_model):
                resp = client.post("/api/scan", json={
                    "api_key": "fake",
                    "directory": tmpdir,
                    "master_file": "master.pdf",
                })
            assert resp.status_code == 200
            data = resp.json()
            assert data["matches"]["good.pdf"]["invoices"] == ["INV-001"]
            assert data["matches"]["bad.pdf"]["invoices"] == []
            assert "error" in data["matches"]["bad.pdf"]

    def test_rename_invalid_directory(self):
        resp = client.post("/api/rename", json={
            "directory": "/nonexistent",
            "plan": {"a.pdf": "b.pdf"},
        })
        assert resp.status_code == 400

    def test_list_files_empty_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            resp = client.get(f"/api/list-files?directory={tmpdir}")
            assert resp.status_code == 200
            assert resp.json() == []

    def test_list_files_ignores_non_pdf(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "a.pdf").write_bytes(b"x")
            (Path(tmpdir) / "b.xlsx").write_bytes(b"x")
            (Path(tmpdir) / "c.docx").write_bytes(b"x")
            (Path(tmpdir) / "d.jpg").write_bytes(b"x")
            resp = client.get(f"/api/list-files?directory={tmpdir}")
            assert resp.json() == ["a.pdf"]

    def test_health_endpoint(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
```

**Step 2: Run all tests**

Run: `cd invoice-matcher && python -m pytest tests/ -v --tb=short`
Expected: All tests PASS (~35+ tests total)

**Step 3: Commit**

```bash
cd invoice-matcher && git add -A && git commit -m "test: comprehensive edge case tests for parser, matcher, and API"
```

---

### Task 8: Live Gemini Integration Tests (Requires API Key)

**Files:**
- Create: `invoice-matcher/tests/test_gemini_live.py`
- Create: `invoice-matcher/tests/fixtures/` (test PDFs)

These tests run against the real Gemini API. They are **skipped by default** unless `GEMINI_API_KEY` env var is set.

**Step 1: Create a simple test PDF fixture**

```python
# tests/create_test_fixtures.py
"""Generate minimal test PDF fixtures for live Gemini tests.
Run once: python tests/create_test_fixtures.py
"""
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
FIXTURES_DIR.mkdir(exist_ok=True)


def create_minimal_pdf(text: str) -> bytes:
    """Create a minimal valid PDF with embedded text.
    Uses raw PDF syntax — no external libraries needed.
    """
    # Minimal PDF 1.4 with a single page containing text
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


# Master list with invoice numbers
master_text = "Invoice List: INV-2024-001, INV-2024-002, INV-2024-003"
(FIXTURES_DIR / "master.pdf").write_bytes(create_minimal_pdf(master_text))

# Document containing INV-2024-001
doc1_text = "Purchase Order - Invoice Number: INV-2024-001 - Total: $500.00"
(FIXTURES_DIR / "doc_scan_001.pdf").write_bytes(create_minimal_pdf(doc1_text))

# Document containing INV-2024-002
doc2_text = "Receipt for payment of invoice INV-2024-002 dated 2024-01-15"
(FIXTURES_DIR / "doc_scan_002.pdf").write_bytes(create_minimal_pdf(doc2_text))

# Document with no matching invoice
doc3_text = "Company memo - quarterly review meeting notes"
(FIXTURES_DIR / "doc_scan_003.pdf").write_bytes(create_minimal_pdf(doc3_text))

print(f"Created test fixtures in {FIXTURES_DIR}")
```

**Step 2: Write live Gemini tests**

```python
# tests/test_gemini_live.py
"""Live integration tests using real Gemini API.

These tests are SKIPPED unless GEMINI_API_KEY env var is set.
Run: GEMINI_API_KEY=your-key pytest tests/test_gemini_live.py -v

Uses free-tier Gemini API (15 req/min, 1500 req/day).
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
    reason="GEMINI_API_KEY env var not set — skipping live Gemini tests"
)

skip_no_fixtures = pytest.mark.skipif(
    not (FIXTURES_DIR / "master.pdf").exists(),
    reason="Test fixtures not found — run: python tests/create_test_fixtures.py"
)


@skip_no_key
@skip_no_fixtures
class TestLiveExtractInvoiceList:
    def test_extracts_invoices_from_master_pdf(self):
        """Gemini should find INV-2024-001, INV-2024-002, INV-2024-003 in master.pdf"""
        pdf_bytes = (FIXTURES_DIR / "master.pdf").read_bytes()
        invoices = extract_invoice_list(pdf_bytes, api_key=GEMINI_API_KEY)

        assert len(invoices) >= 3
        # Check that all expected invoices are found (allow flexible formatting)
        invoice_text = " ".join(invoices).upper()
        assert "001" in invoice_text
        assert "002" in invoice_text
        assert "003" in invoice_text


@skip_no_key
@skip_no_fixtures
class TestLiveExtractInvoicesFromPdf:
    def test_finds_matching_invoice_in_document(self):
        """doc_scan_001.pdf contains INV-2024-001"""
        pdf_bytes = (FIXTURES_DIR / "doc_scan_001.pdf").read_bytes()
        known = ["INV-2024-001", "INV-2024-002", "INV-2024-003"]
        found = extract_invoices_from_pdf(pdf_bytes, known_invoices=known, api_key=GEMINI_API_KEY)

        assert len(found) >= 1
        assert any("001" in inv for inv in found)

    def test_no_match_in_unrelated_document(self):
        """doc_scan_003.pdf has no invoice numbers"""
        pdf_bytes = (FIXTURES_DIR / "doc_scan_003.pdf").read_bytes()
        known = ["INV-2024-001", "INV-2024-002", "INV-2024-003"]
        found = extract_invoices_from_pdf(pdf_bytes, known_invoices=known, api_key=GEMINI_API_KEY)

        assert found == []


@skip_no_key
@skip_no_fixtures
class TestLiveEndToEnd:
    def test_full_scan_and_rename_flow(self):
        """End-to-end: scan fixtures, generate plan, execute renames."""
        # Copy fixtures to a temp directory (so we don't modify originals)
        with tempfile.TemporaryDirectory() as tmpdir:
            for f in FIXTURES_DIR.iterdir():
                if f.suffix == ".pdf":
                    shutil.copy2(f, tmpdir)

            tmpdir_path = Path(tmpdir)

            # Step 1: Extract master invoice list
            master_bytes = (tmpdir_path / "master.pdf").read_bytes()
            master_invoices = extract_invoice_list(master_bytes, api_key=GEMINI_API_KEY)
            assert len(master_invoices) >= 3

            # Step 2: Scan each document
            doc_files = [f for f in tmpdir_path.iterdir() if f.name != "master.pdf"]
            matches = {}
            for doc in sorted(doc_files):
                found = extract_invoices_from_pdf(
                    doc.read_bytes(),
                    known_invoices=master_invoices,
                    api_key=GEMINI_API_KEY,
                )
                matches[doc.name] = found

            # Step 3: At least doc_scan_001 and doc_scan_002 should have matches
            matched_files = {k: v for k, v in matches.items() if v}
            assert len(matched_files) >= 2, f"Expected at least 2 matches, got: {matches}"

            # Step 4: Generate and execute rename plan
            plan = generate_rename_plan(matches, pattern="{invoice}.pdf")
            assert len(plan) >= 2

            results = execute_renames(tmpdir_path, plan)
            assert len(results["renamed"]) >= 2

            # Verify renamed files exist
            for item in results["renamed"]:
                assert (tmpdir_path / item["new"]).exists()
```

**Step 3: Generate test fixtures**

Run:
```bash
cd invoice-matcher && python tests/create_test_fixtures.py
```
Expected: "Created test fixtures in tests/fixtures"

**Step 4: Run live tests with API key**

Run:
```bash
cd invoice-matcher && GEMINI_API_KEY=your-key-here python -m pytest tests/test_gemini_live.py -v
```
Expected: 4 live tests PASS (takes ~15-20 seconds due to API calls)

**Step 5: Verify all tests together (live tests skipped without key)**

Run:
```bash
cd invoice-matcher && python -m pytest tests/ -v
```
Expected: ~36 tests PASS, 4 SKIPPED (live tests)

**Step 6: Add fixtures to .gitignore (optional — they're tiny)**

```bash
echo "# Don't require fixtures for CI" >> .gitignore
```

**Step 7: Commit**

```bash
cd invoice-matcher && git add -A && git commit -m "test: live Gemini integration tests with PDF fixtures"
```

---

## Summary

| Task | What | Tests |
|------|------|-------|
| 1 | Project scaffold + FastAPI app | Manual health check |
| 2 | Gemini PDF extraction + fuzzy matching | 17 unit tests |
| 3 | Matcher module (rename plan + execution) | 8 unit tests |
| 4 | Web UI + API routes | Manual verification |
| 5 | Integration tests (mocked) | 5 integration tests |
| 6 | README with user guide + Gemini setup | — |
| 7 | Edge case & error handling tests | 21 tests |
| 8 | Live Gemini integration tests | 4 tests (skip without key) |

**Total: 8 tasks, ~55 tests (51 always run + 4 live with API key)**
