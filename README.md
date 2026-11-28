---
title: Analytics InAdvance
emoji: 📊
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
---

# Analytics InAdvance

**Ask. Analyze. Automate.**

An analytics productivity workspace for Advanced Excel, Power BI and Tableau. The current prototype includes an Excel Formula Assistant, an Excel/CSV Dataset Analyzer, and rule-based starter assistants for Power BI DAX and Tableau calculated fields.

## Current features
- Convert common business questions into Excel formulas with explanations and application steps.
- Upload CSV, XLSX and XLSM datasets (maximum 10 MB).
- Detect column headers and preview the first five data rows.
- Profile each column for non-empty and missing cells.
- Calculate sum, average, minimum and maximum for numeric columns.
- Detect duplicate rows and summarize dataset quality.
- Display key findings and download a JSON analysis report.
- Power BI starter DAX measures for totals, averages, profit margin, distinct customers, row counts, minimums and maximums.
- Tableau starter calculated fields for totals, averages, profit margin, distinct customers, record counts, minimums, maximums and a FIXED customer-level LOD expression.
- Optional comma-separated column names to tailor Power BI and Tableau suggestions.
- FastAPI backend and responsive browser interface.

The formula assistant currently uses rule-based matching; no AI API key is required. Dataset profiling is deterministic and runs on the uploaded file during the request.

## Deploy on Hugging Face Spaces (Docker)

This repository includes Docker configuration for Hugging Face Spaces. Create a new Space with the Docker SDK and push/import this repository into that Space. The container listens on port 7860. **Important:** Hugging Face currently requires a paid plan to create Docker or Gradio Spaces; free Static Spaces cannot run this FastAPI backend. Check the current plan requirements before creating a Space.

## Run in Google Cloud Shell
1. Open [Google Cloud Shell](https://shell.cloud.google.com/) and wait for the terminal to load.
2. Clone this repository:
   ```bash
   git clone https://github.com/Soniyareddy2468/analytics--inadvance.git
   cd analytics--inadvance
   ```
   If the folder already exists, use `cd ~/.vscode/analytics--inadvance` or the location where you cloned it.
3. Pull the latest changes:
   ```bash
   git pull origin main
   ```
4. Create/activate the virtual environment and install dependencies (first setup):
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Start the app:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
6. In Cloud Shell, select **Web Preview → Preview on port 8000**. Keep the terminal running while using it.
7. To stop the app, press `Ctrl+C` in the terminal.

If port 8000 is already in use, the server may already be running. Try Web Preview first rather than starting a second server.

## API
- `GET /api/health`
- `POST /api/generate` with JSON such as `{"prompt":"Calculate total sales","platform":"Excel"}`
- `POST /api/inspect` accepts CSV/XLSX uploads and returns headers and a preview.
- `POST /api/analyze` accepts a CSV/XLSX/XLSM upload and returns dataset statistics, missing values, duplicate-row count, insights and a preview.

## Roadmap
1. Excel formula assistant and dataset analysis (prototype)
2. Advanced Excel automation and downloadable reports
3. Expand Power BI DAX coverage and add Power Query M generation
4. Expand Tableau calculated fields and LOD expressions
5. More advanced cleaning, visualization and business insights
6. Authentication, team workspaces and production controls

## Important
This is an early prototype. Formula suggestions are rule-based and must be checked against your workbook. Numeric profiling treats values that can be parsed as numbers as numeric; dates and other text are not included in numeric summaries. Power BI and Tableau currently provide limited rule-based starter suggestions, not complete semantic-model or workbook integrations. Power Query M generation, live Power BI/Tableau connections, authentication, multi-user workspaces, deployment hardening and automated integration tests are not yet implemented. Do not upload confidential company data to a public demo. Production use requires security, access controls, validation and privacy review.
