"""Invoice Matcher — FastAPI web application."""
import io
import json
import tempfile
import zipfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile
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
CONFIG_DIR = Path.home() / ".config" / "invoice-matcher"
CONFIG_FILE = CONFIG_DIR / "settings.json"


def _load_settings() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}


def _save_settings(settings: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(settings, indent=2))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/settings")
async def get_settings():
    settings = _load_settings()
    # Mask key for display: show first 8 + last 4 chars
    api_key = settings.get("api_key", "")
    has_key = bool(api_key)
    masked = ""
    if api_key and len(api_key) > 12:
        masked = api_key[:8] + "..." + api_key[-4:]
    elif api_key:
        masked = api_key[:4] + "..."
    return {"has_key": has_key, "masked_key": masked}


class SaveKeyRequest(BaseModel):
    api_key: str


@app.post("/api/settings/key")
async def save_key(req: SaveKeyRequest):
    if not req.api_key.strip():
        raise HTTPException(400, "API key cannot be empty")
    settings = _load_settings()
    settings["api_key"] = req.api_key.strip()
    _save_settings(settings)
    return {"status": "saved"}


@app.delete("/api/settings/key")
async def delete_key():
    settings = _load_settings()
    settings.pop("api_key", None)
    _save_settings(settings)
    return {"status": "deleted"}


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


@app.post("/api/browse-folder")
async def browse_folder():
    """Open a native folder picker dialog and return the selected path."""
    import subprocess
    import sys

    if sys.platform == "darwin":
        result = subprocess.run(
            ["osascript", "-e", 'POSIX path of (choose folder with prompt "Select folder containing PDF invoices")'],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(400, "No folder selected")
        folder = result.stdout.strip().rstrip("/")
    elif sys.platform == "win32":
        script = (
            'Add-Type -AssemblyName System.Windows.Forms; '
            '$d = New-Object System.Windows.Forms.FolderBrowserDialog; '
            '$d.Description = "Select folder containing PDF invoices"; '
            'if ($d.ShowDialog() -eq "OK") { $d.SelectedPath } else { exit 1 }'
        )
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(400, "No folder selected")
        folder = result.stdout.strip()
    else:
        # Linux — try zenity
        result = subprocess.run(
            ["zenity", "--file-selection", "--directory", "--title=Select folder containing PDF invoices"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(400, "No folder selected")
        folder = result.stdout.strip()

    dir_path = Path(folder)
    if not dir_path.is_dir():
        raise HTTPException(400, f"Not a valid directory: {folder}")
    files = sorted(
        f.name for f in dir_path.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    return {"directory": folder, "files": files}


@app.post("/api/upload-zip")
async def upload_zip(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Only .zip files are accepted")
    content = await file.read()
    try:
        tmp_dir = tempfile.mkdtemp(prefix="invoice-matcher-")
        with zipfile.ZipFile(io.BytesIO(content)) as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                # Only extract PDF files, flatten into tmp_dir
                if Path(member.filename).suffix.lower() in SUPPORTED_EXTENSIONS:
                    filename = Path(member.filename).name
                    target = Path(tmp_dir) / filename
                    target.write_bytes(zf.read(member))
    except zipfile.BadZipFile:
        raise HTTPException(400, "Invalid zip file")
    files = sorted(
        f.name for f in Path(tmp_dir).iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if not files:
        raise HTTPException(400, "No PDF files found in zip archive")
    return {"directory": tmp_dir, "files": files}


class ScanRequest(BaseModel):
    api_key: str = ""
    directory: str
    output_dir: str = ""
    master_file: str = ""
    master_path: str = ""
    pattern: str = "{invoice}"
    separator: str = "_"


@app.post("/api/scan")
async def scan(req: ScanRequest):
    # Use saved key if none provided
    api_key = req.api_key.strip()
    if not api_key:
        settings = _load_settings()
        api_key = settings.get("api_key", "")
    if not api_key:
        raise HTTPException(400, "No API key configured. Go to Settings to save your Gemini API key.")

    dir_path = Path(req.directory)
    if not dir_path.is_dir():
        raise HTTPException(400, f"Not a valid directory: {req.directory}")

    # Master file: full path or filename in directory
    if req.master_path:
        mp = Path(req.master_path)
        if not mp.is_file():
            raise HTTPException(400, f"Master file not found: {req.master_path}")
        master_bytes = mp.read_bytes()
        master_filename = mp.name
    elif req.master_file:
        mp = dir_path / req.master_file
        if not mp.is_file():
            raise HTTPException(400, f"Master file not found: {req.master_file}")
        master_bytes = mp.read_bytes()
        master_filename = req.master_file
    else:
        raise HTTPException(400, "Master file is required")

    # Step 1: Extract invoice list from master
    try:
        master_invoices = extract_invoice_list(master_bytes, api_key=api_key)
    except Exception as e:
        raise HTTPException(500, f"Failed to read master file: {e}")

    if not master_invoices:
        raise HTTPException(400, "No invoice numbers found in master file")

    # Step 2: Scan each remaining PDF
    other_files = [
        f for f in dir_path.iterdir()
        if f.is_file()
        and f.suffix.lower() in SUPPORTED_EXTENSIONS
        and f.name != master_filename
    ]

    matches: dict[str, dict] = {}
    for pdf_file in sorted(other_files, key=lambda f: f.name):
        try:
            pdf_bytes = pdf_file.read_bytes()
            found = extract_invoices_from_pdf(
                pdf_bytes, known_invoices=master_invoices, api_key=api_key
            )
            matches[pdf_file.name] = {"invoices": found}
        except Exception as e:
            matches[pdf_file.name] = {"invoices": [], "error": str(e)}

    # Step 3: Generate rename plan
    match_map = {name: info["invoices"] for name, info in matches.items()}
    plan = generate_rename_plan(match_map, pattern=req.pattern, separator=req.separator)

    # Resolve output directory
    output_dir = req.output_dir.strip() if req.output_dir else ""
    if not output_dir:
        output_dir = str(dir_path / "outputs")

    return {
        "directory": req.directory,
        "output_dir": output_dir,
        "master_invoices": master_invoices,
        "matches": matches,
        "plan": plan,
    }


@app.post("/api/browse-master")
async def browse_master():
    """Open a native file picker dialog for selecting the master PDF."""
    import subprocess
    import sys

    if sys.platform == "darwin":
        result = subprocess.run(
            ["osascript", "-e", 'POSIX path of (choose file with prompt "Select master invoice PDF" of type {"pdf"})'],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(400, "No file selected")
        file_path = result.stdout.strip()
    elif sys.platform == "win32":
        script = (
            'Add-Type -AssemblyName System.Windows.Forms; '
            '$d = New-Object System.Windows.Forms.OpenFileDialog; '
            '$d.Title = "Select master invoice PDF"; '
            '$d.Filter = "PDF files (*.pdf)|*.pdf"; '
            'if ($d.ShowDialog() -eq "OK") { $d.FileName } else { exit 1 }'
        )
        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(400, "No file selected")
        file_path = result.stdout.strip()
    else:
        result = subprocess.run(
            ["zenity", "--file-selection", "--file-filter=PDF files | *.pdf", "--title=Select master invoice PDF"],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise HTTPException(400, "No file selected")
        file_path = result.stdout.strip()

    p = Path(file_path)
    if not p.is_file():
        raise HTTPException(400, f"File not found: {file_path}")
    return {"path": str(p), "filename": p.name, "directory": str(p.parent)}



class RenameRequest(BaseModel):
    directory: str
    output_dir: str = ""
    plan: dict[str, str]


@app.post("/api/rename")
async def rename(req: RenameRequest):
    import shutil

    dir_path = Path(req.directory)
    if not dir_path.is_dir():
        raise HTTPException(400, f"Not a valid directory: {req.directory}")

    output_dir = Path(req.output_dir) if req.output_dir else dir_path / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, list[dict]] = {"renamed": [], "skipped": []}
    for old_name, new_name in req.plan.items():
        old_path = dir_path / old_name
        new_path = output_dir / new_name
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
        shutil.copy2(old_path, new_path)
        results["renamed"].append({"old": old_name, "new": new_name})

    return {**results, "output_dir": str(output_dir)}


@app.get("/health")
async def health():
    return {"status": "ok"}


def main():
    uvicorn.run("invoice_matcher.app:app", host="127.0.0.1", port=8000, reload=True)
