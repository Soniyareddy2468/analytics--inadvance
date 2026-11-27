import re


def _field(columns, candidates, fallback):
    for col in columns:
        normalized = re.sub(r"[^a-z0-9]", "", col.lower())
        if any(term in normalized for term in candidates):
            return col
    return fallback


def generate_bi_solution(prompt: str, columns: list[str], platform: str):
    q = prompt.lower()
    sales = _field(columns, ["sales", "revenue", "amount", "total"], "Sales")
    profit = _field(columns, ["profit", "income", "net"], "Profit")
    category = _field(columns, ["category", "product", "region", "department"], "Category")
    date = _field(columns, ["date", "orderdate", "month"], "Date")
    table = "Data"

    if platform == "Power BI":
        if any(x in q for x in ["average", "mean"]):
            title, expression = "Average sales", f"Average Sales = AVERAGE('{table}'[{sales}])"
            explanation = "Creates a measure that calculates the average of the sales column in the current filter context."
        elif any(x in q for x in ["distinct customer", "unique customer", "count customers"]):
            customer = _field(columns, ["customer", "client"], "Customer")
            title, expression = "Distinct customers", f"Distinct Customers = DISTINCTCOUNT('{table}'[{customer}])"
            explanation = "Counts unique customer values in the current filter context."
        elif "profit margin" in q or "margin" in q:
            title = "Profit margin"
            expression = f"Profit Margin = DIVIDE(SUM('{table}'[{profit}]), SUM('{table}'[{sales}]), 0)"
            explanation = "Divides total profit by total sales and safely returns zero when sales is zero. Format the measure as Percentage."
        elif "count" in q or "number of orders" in q:
            title, expression = "Row count", f"Record Count = COUNTROWS('{table}')"
            explanation = "Counts rows in the Data table under the current filters."
        elif any(x in q for x in ["maximum", "highest", "max"]):
            title, expression = "Maximum sales", f"Maximum Sales = MAX('{table}'[{sales}])"
            explanation = "Returns the highest value in the sales column under the current filters."
        elif any(x in q for x in ["minimum", "lowest", "min"]):
            title, expression = "Minimum sales", f"Minimum Sales = MIN('{table}'[{sales}])"
            explanation = "Returns the lowest value in the sales column under the current filters."
        else:
            title, expression = "Total sales", f"Total Sales = SUM('{table}'[{sales}])"
            explanation = "Creates a reusable measure for total sales. Add the date or category field to a visual to break the measure down by month or category."
        steps = ["In Power BI Desktop, select Modeling → New measure.", "Paste the DAX measure into the formula bar.", "If your model table is not named Data, replace the table name.", "Check the column names against your model and format the measure appropriately."]
        assumptions = [f"Assumes the model table is named '{table}' and uses the detected '{sales}' field where relevant.", "This is a starter DAX suggestion; validate relationships, data types and filter context in your model."]
        return {"title": title, "platform": platform, "formula": expression, "explanation": explanation, "steps": steps, "assumptions": assumptions, "confidence": "Rule-based starter suggestion", "disclaimer": "Validate DAX against your model before publishing."}

    if platform == "Tableau":
        if "profit margin" in q or "margin" in q:
            title, expression = "Profit margin", f"SUM([{profit}]) / SUM([{sales}])"
            explanation = "Calculates total profit divided by total sales. Set the calculated field's default number format to Percentage."
        elif any(x in q for x in ["average", "mean"]):
            title, expression = "Average sales", f"AVG([{sales}])"
            explanation = "Returns the average sales value at the level of detail in the view."
        elif any(x in q for x in ["distinct", "unique customer"]):
            customer = _field(columns, ["customer", "client"], "Customer")
            title, expression = "Unique customers", f"COUNTD([{customer}])"
            explanation = "Counts distinct customer values at the level of detail in the view."
        elif "fixed" in q or "per customer" in q or "each customer" in q:
            customer = _field(columns, ["customer", "client"], "Customer")
            title, expression = "Sales per customer (FIXED LOD)", f"{{ FIXED [{customer}] : SUM([{sales}]) }}"
            explanation = "Computes sales for each customer independently of dimensions in the view (subject to Tableau filter order)."
        elif any(x in q for x in ["count", "number of orders"]):
            title, expression = "Record count", "COUNT([Number of Records])"
            explanation = "Counts records using Tableau's generated Number of Records field when available."
        elif any(x in q for x in ["maximum", "highest", "max"]):
            title, expression = "Maximum sales", f"MAX([{sales}])"
            explanation = "Returns the maximum sales value at the level of detail in the view."
        elif any(x in q for x in ["minimum", "lowest", "min"]):
            title, expression = "Minimum sales", f"MIN([{sales}])"
            explanation = "Returns the minimum sales value at the level of detail in the view."
        else:
            title, expression = "Total sales", f"SUM([{sales}])"
            explanation = "Sums sales at the level of detail in the current visualization. Add a date or category dimension to the view to split the result."
        steps = ["In Tableau, open a worksheet and choose Analysis → Create Calculated Field.", "Give the field a clear name and paste the expression.", "Confirm the field names match the Data pane exactly.", "Click OK and drag the calculated field into the view."]
        assumptions = [f"Assumes a field named '{sales}' exists in the connected data source.", "Aggregation and level of detail depend on dimensions, filters and the worksheet context."]
        return {"title": title, "platform": platform, "formula": expression, "explanation": explanation, "steps": steps, "assumptions": assumptions, "confidence": "Rule-based starter suggestion", "disclaimer": "Validate calculated fields in Tableau before sharing."}

    raise ValueError("Unsupported analytics platform.")
