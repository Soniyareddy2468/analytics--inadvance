from pathlib import Path
from typing import Optional
import csv
import io
import json
import math

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.excel_engine import generate_excel_solution
from app.bi_engine import generate_bi_solution

BASE_DIR = Path(__file__).resolve().parent
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
app = FastAPI(title="Analytics InAdvance", version="0.2.0",
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
    return {"status": "ok", "product": "Analytics InAdvance",
            "modules": ["Excel Formula Assistant", "Excel Dataset Analyzer", "Power BI DAX Assistant", "Tableau Calculated Field Assistant"]}


@app.post("/api/generate")
def generate(request: FormulaRequest):
    if not request.prompt.strip():
        raise HTTPException(status_code=400, detail="Please enter a task.")
    if request.platform == "Excel":
        return generate_excel_solution(request.prompt, request.columns or [])
    if request.platform in ("Power BI", "Tableau"):
        return generate_bi_solution(request.prompt, request.columns or [], request.platform)
    raise HTTPException(status_code=400, detail="Choose Excel, Power BI or Tableau.")


async def read_tabular_upload(file: UploadFile):
    filename = (file.filename or "").lower()
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File must be 10 MB or smaller.")
    try:
        if filename.endswith(".csv"):
            text = raw.decode("utf-8-sig")
            values = list(csv.reader(io.StringIO(text)))
        elif filename.endswith((".xlsx", ".xlsm")):
            from openpyxl import load_workbook
            workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
            sheet = workbook.active
            values = list(sheet.iter_rows(values_only=True))
            workbook.close()
        else:
            raise HTTPException(status_code=400, detail="Upload a .csv or .xlsx file.")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read the file. Check that it is a valid CSV or XLSX workbook.")

    if not values:
        raise HTTPException(status_code=400, detail="The file has no rows.")
    headers = [str(v).strip() if v is not None else "" for v in values[0]]
    headers = [name or f"Column {i + 1}" for i, name in enumerate(headers)]
    if len(set(headers)) != len(headers):
        seen = {}
        unique = []
        for name in headers:
            seen[name] = seen.get(name, 0) + 1
            unique.append(name if seen[name] == 1 else f"{name} ({seen[name]})")
        headers = unique
    data_rows = []
    for row in values[1:]:
        cells = list(row[:len(headers)]) + [None] * max(0, len(headers) - len(row))
        data_rows.append(cells)
    return headers, data_rows


def is_missing(value):
    return value is None or (isinstance(value, str) and not value.strip())


def numeric_value(value):
    if isinstance(value, bool) or is_missing(value):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        try:
            number = float(str(value).replace(",", "").replace("$", "").replace("₹", "").strip())
        except (TypeError, ValueError):
            return None
    return number if math.isfinite(number) else None


@app.post("/api/inspect")
async def inspect_file(file: UploadFile = File(...)):
    headers, rows = await read_tabular_upload(file)
    preview = [[str(v) if v is not None else "" for v in row] for row in rows[:5]]
    return {"filename": file.filename, "columns": headers, "preview": preview,
            "row_count": len(rows)}


@app.post("/api/analyze")
async def analyze_file(file: UploadFile = File(...)):
    headers, rows = await read_tabular_upload(file)
    column_results = []
    for index, name in enumerate(headers):
        values = [row[index] if index < len(row) else None for row in rows]
        missing_count = sum(is_missing(value) for value in values)
        numbers = [number for value in values if (number := numeric_value(value)) is not None]
        result = {
            "name": name,
            "non_empty": len(values) - missing_count,
            "missing": missing_count,
            "numeric": len(numbers) == len(values) - missing_count and bool(numbers),
        }
        if numbers:
            result.update({
                "sum": round(sum(numbers), 4),
                "average": round(sum(numbers) / len(numbers), 4),
                "minimum": round(min(numbers), 4),
                "maximum": round(max(numbers), 4),
            })
        column_results.append(result)

    normalized_rows = [tuple("" if is_missing(v) else str(v).strip() for v in row) for row in rows]
    duplicate_count = len(normalized_rows) - len(set(normalized_rows))
    missing_cells = sum(item["missing"] for item in column_results)
    numeric_columns = [item for item in column_results if item["numeric"]]
    insights = [
        f"The dataset contains {len(rows):,} data rows and {len(headers)} columns.",
        f"{missing_cells:,} empty cells were found across the dataset.",
        f"{duplicate_count:,} duplicate rows were found.",
    ]
    if numeric_columns:
        largest = max(numeric_columns, key=lambda item: item["sum"])
        insights.append(f"{largest['name']} has the largest numeric column total ({largest['sum']:,.2f}).")
    else:
        insights.append("No numeric columns were detected for summary statistics.")

    return {
        "filename": file.filename,
        "row_count": len(rows),
        "column_count": len(headers),
        "duplicate_rows": duplicate_count,
        "missing_cells": missing_cells,
        "columns": column_results,
        "insights": insights,
        "preview": [[str(v) if v is not None else "" for v in row] for row in rows[:5]],
    }
