import re

def _column_hint(columns, candidates, fallback):
    for col in columns:
        normalized = re.sub(r"[^a-z0-9]", "", col.lower())
        if any(word in normalized for word in candidates):
            return col
    return fallback

def generate_excel_solution(prompt: str, columns: list[str]):
    q = prompt.lower()
    amount = _column_hint(columns, ["sales", "revenue", "amount", "total"], "Sales")
    date = _column_hint(columns, ["date", "orderdate", "month"], "Date")

    if any(k in q for k in ["duplicate", "duplicates", "repeated rows"]):
        title, formula = "Flag duplicate values", "=COUNTIF(A:A,A2)>1"
        explanation = "Checks whether the value in A2 appears more than once in column A. Replace A with the column you want to check."
        steps = ["Add a helper column named Duplicate?", "Enter the formula in row 2.", "Fill it down and filter TRUE."]
    elif any(k in q for k in ["top 5", "top five", "top 10", "top ten", "rank"]):
        title, formula = "Rank values from highest to lowest", "=RANK.EQ(B2,$B$2:$B$100,0)"
        explanation = "Assumes the metric is in column B. Rank 1 is the highest value."
        steps = ["Place the metric in column B.", "Add a Rank column.", "Enter the formula in row 2 and fill down.", "Filter ranks 1–5 or 1–10."]
    elif any(k in q for k in ["profit margin", "margin"]):
        title, formula = "Calculate profit margin", "=IFERROR((B2-C2)/B2,0)"
        explanation = "Assumes revenue is in B and cost is in C. Format the result as a percentage."
        steps = ["Put revenue in B and cost in C.", "Enter the formula in row 2.", "Format as Percentage and fill down."]
    elif any(k in q for k in ["monthly sales", "sales by month", "total sales for each month"]):
        title = "Calculate monthly sales"
        formula = '=SUMIFS($B:$B,$A:$A,">="&EOMONTH(E2,-1)+1,$A:$A,"<="&EOMONTH(E2,0))'
        explanation = f"Assumes {date} is in column A, {amount} is in column B, and E2 contains a date in the month to summarize."
        steps = ["Create a monthly summary date in E2.", "Keep transaction dates in A and sales values in B.", "Enter the formula in F2 and fill down."]
    elif any(k in q for k in ["total sales", "sum sales", "sum of sales", "revenue total"]):
        title, formula = "Calculate total sales", "=SUM(B:B)"
        explanation = f"Adds numeric values in the {amount} column; this example assumes sales values are in column B."
        steps = ["Confirm sales values are in column B.", "Paste the formula into a blank cell.", "Format as currency if required."]
    elif "average" in q or "mean" in q:
        title, formula = "Calculate average", "=AVERAGE(B2:B100)"
        explanation = "Calculates the arithmetic mean of values in B2:B100."
        steps = ["Replace the range with your data range.", "Enter the formula in a blank cell."]
    elif "lookup" in q or "find the name" in q:
        title, formula = "Look up a matching value", "=XLOOKUP(E2,A:A,B:B,\"Not found\")"
        explanation = "Looks for the value in E2 in column A and returns the matching value from column B."
        steps = ["Enter the lookup value in E2.", "Keep lookup values in A and return values in B.", "Paste the formula in the result cell."]
    elif "count" in q or "number of orders" in q:
        title, formula = "Count non-empty records", "=COUNTA(A2:A100)"
        explanation = "Counts non-empty cells in the example range A2:A100."
        steps = ["Choose a column populated for every record.", "Adjust the range to match your dataset."]
    elif "growth" in q or "year over year" in q or "yoy" in q:
        title, formula = "Calculate growth percentage", "=IFERROR((B3-B2)/B2,0)"
        explanation = "Compares current period B3 with previous period B2. Format as Percentage."
        steps = ["Put previous-period value in B2.", "Put current-period value in B3.", "Enter the formula and format as Percentage."]
    else:
        title, formula = "Conditional total (starter suggestion)", "=SUMIFS(B:B,A:A,E2)"
        explanation = "Example: sums values in B where the category in A matches E2. The request may need more detail."
        steps = ["Put categories in column A and values in B.", "Enter the category to match in E2.", "Adjust the column references for your workbook."]

    return {
        "title": title, "platform": "Excel", "formula": formula,
        "explanation": explanation, "steps": steps,
        "assumptions": [
            "Example cell references are used; exact workbook layout is not yet mapped.",
            "Check column letters and ranges before applying the formula."
        ],
        "confidence": "Starter rule-based match",
        "disclaimer": "Test generated formulas on a copy of your workbook before business use."
    }
