"""Invoice Matcher — FastAPI web application."""
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
    separator: str = "_"


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
    plan = generate_rename_plan(match_map, pattern=req.pattern, separator=req.separator)

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
