from pathlib import Path
from typing import Optional
import csv
import io
import json
import math
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
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



def _header_index(headers, keywords):
    for index, header in enumerate(headers):
        normalized = "".join(ch.lower() for ch in header if ch.isalnum())
        if any(word in normalized for word in keywords):
            return index
    return None


def _group_totals(headers, rows, group_index, value_index):
    if group_index is None or value_index is None:
        return []
    totals = {}
    for row in rows:
        group = row[group_index] if group_index < len(row) else None
        value = numeric_value(row[value_index] if value_index < len(row) else None)
        if is_missing(group) or value is None:
            continue
        label = str(group).strip()
        totals[label] = totals.get(label, 0.0) + value
    return [{"label": key, "value": round(value, 2)}
            for key, value in sorted(totals.items(), key=lambda item: item[1], reverse=True)[:10]]


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

    sales_index = _header_index(headers, ["sales", "revenue", "amount", "total"])
    profit_index = _header_index(headers, ["profit", "income", "netprofit"])
    date_index = _header_index(headers, ["date", "orderdate", "transactiondate"])
    region_index = _header_index(headers, ["region", "city", "location", "state"])
    product_index = _header_index(headers, ["product", "item", "category", "sku"])

    monthly = {}
    if date_index is not None and sales_index is not None:
        for row in rows:
            raw_date = row[date_index] if date_index < len(row) else None
            amount = numeric_value(row[sales_index] if sales_index < len(row) else None)
            if is_missing(raw_date) or amount is None:
                continue
            try:
                month = datetime.fromisoformat(str(raw_date).strip()[:10]).strftime("%Y-%m")
            except (TypeError, ValueError):
                continue
            monthly[month] = monthly.get(month, 0.0) + amount

    sales_values = [numeric_value(row[sales_index] if sales_index is not None and sales_index < len(row) else None) for row in rows]
    profit_values = [numeric_value(row[profit_index] if profit_index is not None and profit_index < len(row) else None) for row in rows]
    total_sales = round(sum(value for value in sales_values if value is not None), 2) if sales_index is not None else None
    total_profit = round(sum(value for value in profit_values if value is not None), 2) if profit_index is not None else None
    best_region = _group_totals(headers, rows, region_index, sales_index)
    best_product = _group_totals(headers, rows, product_index, sales_index)
    monthly_sorted = sorted(monthly.items())
    monthly_growth = None
    if len(monthly_sorted) >= 2:
        previous, current = monthly_sorted[-2][1], monthly_sorted[-1][1]
        if previous != 0:
            monthly_growth = round(((current - previous) / abs(previous)) * 100, 2)

    business_insights = {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "best_region": best_region[0] if best_region else None,
        "best_product": best_product[0] if best_product else None,
        "latest_month": monthly_sorted[-1][0] if monthly_sorted else None,
        "monthly_growth_percent": monthly_growth,
        "recommendations": [],
    }
    if business_insights["best_product"]:
        business_insights["recommendations"].append(
            f"Prioritize stock and promotion planning for {business_insights['best_product']['label']}, the highest-sales product in this dataset."
        )
    if business_insights["best_region"]:
        business_insights["recommendations"].append(
            f"Review what is driving sales in {business_insights['best_region']['label']} and test whether those practices can be repeated in other regions."
        )
    if monthly_growth is not None:
        direction = "increased" if monthly_growth >= 0 else "decreased"
        business_insights["recommendations"].append(
            f"Sales {direction} by {abs(monthly_growth):.1f}% in {monthly_sorted[-1][0]} compared with {monthly_sorted[-2][0]}; investigate major changes in orders, pricing or product mix."
        )
    if total_profit is None:
        business_insights["recommendations"].append(
            "Add a numeric Profit column to enable profit totals and profitability analysis."
        )
    if not business_insights["recommendations"]:
        business_insights["recommendations"].append(
            "Use column headers containing Date, Sales, Profit, Region and Product to unlock more business insights."
        )

    return {
        "filename": file.filename,
        "row_count": len(rows),
        "column_count": len(headers),
        "duplicate_rows": duplicate_count,
        "missing_cells": missing_cells,
        "columns": column_results,
        "insights": insights,
        "business_insights": business_insights,
        "preview": [[str(v) if v is not None else "" for v in row] for row in rows[:5]],
        "charts": {
            "monthly_sales": [{"label": key, "value": round(value, 2)} for key, value in sorted(monthly.items())],
            "region_sales": _group_totals(headers, rows, region_index, sales_index),
            "product_sales": _group_totals(headers, rows, product_index, sales_index),
            "profit_by_region": _group_totals(headers, rows, region_index, profit_index),
        },
    }


@app.post("/api/clean")
async def clean_dataset(
    file: UploadFile = File(...),
    remove_duplicates: bool = Form(True),
    missing_strategy: str = Form("keep"),
):
    """Return a cleaned CSV copy; the uploaded original is never changed."""
    if missing_strategy not in ("keep", "drop_rows", "fill_numeric_mean"):
        raise HTTPException(status_code=400, detail="Choose keep, drop_rows or fill_numeric_mean.")

    headers, rows = await read_tabular_upload(file)
    original_rows = len(rows)
    working = [list(row) for row in rows]

    if missing_strategy == "drop_rows":
        working = [row for row in working if not any(is_missing(v) for v in row)]
    elif missing_strategy == "fill_numeric_mean":
        for index in range(len(headers)):
            column = [row[index] if index < len(row) else None for row in working]
            present = [v for v in column if not is_missing(v)]
            numbers = [numeric_value(v) for v in present]
            if present and all(n is not None for n in numbers):
                mean_value = sum(numbers) / len(numbers)
                for row in working:
                    if index >= len(row):
                        row.extend([None] * (index + 1 - len(row)))
                    if is_missing(row[index]):
                        row[index] = round(mean_value, 4)

    before_dedup = len(working)
    if remove_duplicates:
        seen = set()
        unique_rows = []
        for row in working:
            key = tuple("" if is_missing(v) else str(v).strip() for v in row)
            if key not in seen:
                seen.add(key)
                unique_rows.append(row)
        working = unique_rows

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows([
        ["" if is_missing(v) else v for v in row[:len(headers)]]
        for row in working
    ])
    cleaned = output.getvalue().encode("utf-8-sig")
    removed_duplicates = before_dedup - len(working)
    removed_rows = original_rows - before_dedup
    stem = Path(file.filename or "dataset").stem
    return StreamingResponse(
        io.BytesIO(cleaned),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{stem}-cleaned.csv"',
            "X-Original-Rows": str(original_rows),
            "X-Cleaned-Rows": str(len(working)),
            "X-Duplicates-Removed": str(removed_duplicates),
            "X-Rows-Removed": str(removed_rows),
        },
    )


@app.post("/api/report/pdf")
async def download_pdf_report(file: UploadFile = File(...)):
    """Analyze an uploaded dataset and return a formatted PDF report."""
    report = await analyze_file(file)

    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="PDF export is unavailable. Install the reportlab dependency.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=14 * mm, leftMargin=14 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title="Analytics InAdvance Dataset Report"
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", parent=styles["Title"], fontSize=21,
        leading=25, textColor=colors.HexColor("#24345b"),
        alignment=TA_CENTER, spaceAfter=5
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", parent=styles["Heading2"],
        textColor=colors.HexColor("#167c70"), spaceBefore=12, spaceAfter=6
    ))
    styles.add(ParagraphStyle(
        name="SmallCell", parent=styles["BodyText"], fontSize=7,
        leading=9, wordWrap="CJK"
    ))

    story = [
        Paragraph("Analytics InAdvance", styles["ReportTitle"]),
        Paragraph("Dataset Analysis Report", styles["Heading2"]),
        Paragraph(f"File: {report['filename']}", styles["BodyText"]),
        Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}", styles["BodyText"]),
        Spacer(1, 8),
    ]

    metric_data = [
        ["Rows", "Columns", "Missing cells", "Duplicate rows"],
        [str(report["row_count"]), str(report["column_count"]),
         str(report["missing_cells"]), str(report["duplicate_rows"])]
    ]
    metric_table = Table(metric_data, colWidths=[doc.width / 4] * 4)
    metric_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24345b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#edf5f5")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#17233b")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("PADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
    ]))
    story.extend([metric_table, Paragraph("Key insights", styles["SectionHeading"])])
    for insight in report["insights"]:
        story.append(Paragraph("• " + insight, styles["BodyText"]))
    story.append(Paragraph("Visual analytics", styles["SectionHeading"]))

    from reportlab.graphics.shapes import Drawing, String
    from reportlab.graphics.charts.barcharts import VerticalBarChart

    chart_specs = [
        ("Monthly sales", "monthly_sales"),
        ("Sales by region", "region_sales"),
        ("Sales by product", "product_sales"),
        ("Profit by region", "profit_by_region"),
    ]

    def make_bar_chart(title, items):
        drawing = Drawing(350, 190)
        drawing.add(String(8, 174, title, fontName="Helvetica-Bold",
                           fontSize=10, fillColor=colors.HexColor("#167c70")))
        if not items:
            drawing.add(String(8, 90, "No matching columns found.",
                               fontSize=8, fillColor=colors.HexColor("#64748b")))
            return drawing

        chart = VerticalBarChart()
        chart.x = 42
        chart.y = 38
        chart.width = 292
        chart.height = 118
        chart.data = [[float(item["value"]) for item in items]]
        chart.categoryAxis.categoryNames = [str(item["label"])[:16] for item in items]
        chart.categoryAxis.labels.fontName = "Helvetica"
        chart.categoryAxis.labels.fontSize = 7
        chart.categoryAxis.labels.angle = 0
        chart.categoryAxis.labels.boxAnchor = "ne"
        chart.valueAxis.labels.fontName = "Helvetica"
        chart.valueAxis.labels.fontSize = 7
        chart.valueAxis.valueMin = min(0, min(float(item["value"]) for item in items))
        maximum = max(float(item["value"]) for item in items)
        chart.valueAxis.valueMax = maximum * 1.15 if maximum > 0 else 1
        chart.valueAxis.valueStep = max(chart.valueAxis.valueMax / 4, 1)
        chart.bars[0].fillColor = colors.HexColor("#38bfa7")
        chart.bars[0].strokeColor = colors.HexColor("#167c70")
        chart.barWidth = min(28, max(10, 210 / len(items)))
        chart.groupSpacing = 8
        drawing.add(chart)
        return drawing

    chart_cells = []
    for index in range(0, len(chart_specs), 2):
        left_title, left_key = chart_specs[index]
        right_title, right_key = chart_specs[index + 1]
        left_chart = make_bar_chart(left_title, report.get("charts", {}).get(left_key, []))
        right_chart = make_bar_chart(right_title, report.get("charts", {}).get(right_key, []))
        chart_cells.append([left_chart, right_chart])

    chart_table = Table(chart_cells, colWidths=[doc.width / 2] * 2, rowHeights=[205] * len(chart_cells))
    chart_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#dbe4ee")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(chart_table)

    story.append(Paragraph("Column profile", styles["SectionHeading"]))
    column_data = [["Column", "Non-empty", "Missing", "Sum", "Average", "Min", "Max"]]
    for col in report["columns"]:
        column_data.append([
            str(col["name"]), str(col["non_empty"]), str(col["missing"]),
            f"{col['sum']:,.2f}" if "sum" in col else "—",
            f"{col['average']:,.2f}" if "average" in col else "—",
            f"{col['minimum']:,.2f}" if "minimum" in col else "—",
            f"{col['maximum']:,.2f}" if "maximum" in col else "—",
        ])
    profile = Table(column_data, repeatRows=1)
    profile.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24345b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6fa")]),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(profile)

    if report.get("preview"):
        story.append(Paragraph("Data preview (first five rows)", styles["SectionHeading"]))
        preview_data = [[Paragraph(str(col["name"]), styles["SmallCell"]) for col in report["columns"]]]
        preview_data.extend([
            [Paragraph(str(v), styles["SmallCell"]) for v in row]
            for row in report["preview"]
        ])
        preview = Table(preview_data, repeatRows=1)
        preview.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#24345b")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(preview)

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "Generated by Analytics InAdvance. Review the original dataset before making business decisions.",
        styles["Italic"]
    ))
    doc.build(story)
    buffer.seek(0)
    safe_name = Path(report["filename"]).stem.replace('"', "").replace("\\", "_")
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-analysis-report.pdf"'}
    )
