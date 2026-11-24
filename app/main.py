from pathlib import Path
from typing import Optional
import csv
import io

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.excel_engine import generate_excel_solution

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Analytics InAdvance", version="0.1.0",
              description="Analytics productivity assistant")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

class FormulaRequest(BaseModel):
    prompt: str
    columns: Optional[list[str]] = None
    platform: str = "Excel"

@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/api/health")
def health():
    return {"status": "ok", "product": "Analytics InAdvance", "module": "Excel Formula Assistant"}

@app.post("/api/generate")
def generate(request: FormulaRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Please enter a task.")
    if request.platform != "Excel":
        raise HTTPException(status_code=501, detail=f"{request.platform} support is planned for a later module. Excel is available now.")
    return generate_excel_solution(request.prompt, request.columns or [])

@app.post("/api/inspect")
async def inspect_file(file: UploadFile = File(...)):
    filename = (file.filename or "").lower()
    raw = await file.read()
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File must be 10 MB or smaller.")
    try:
        if filename.endswith(".csv"):
            rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
            headers = rows[0] if rows else []
            preview = rows[1:6]
            row_count = max(0, len(rows) - 1)
        elif filename.endswith((".xlsx", ".xlsm")):
            from openpyxl import load_workbook
            workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            values = list(workbook.active.iter_rows(values_only=True))
            headers = [str(v) if v is not None else "" for v in (values[0] if values else [])]
            preview = [[str(v) if v is not None else "" for v in row] for row in values[1:6]]
            row_count = max(0, len(values) - 1)
        else:
            raise HTTPException(status_code=400, detail="Upload a .csv or .xlsx file.")
        return {"filename": file.filename, "columns": headers, "preview": preview, "row_count": row_count}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read file: {exc}")
