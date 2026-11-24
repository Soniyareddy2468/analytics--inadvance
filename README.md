# Analytics InAdvance

**Ask. Analyze. Automate.**

An analytics productivity workspace for Advanced Excel, Power BI and Tableau. This first release delivers **Module 1: Excel Formula Assistant**.

## Current release
- Convert common business questions into Excel formulas.
- Show explanations, assumptions and application steps.
- Copy generated formulas.
- FastAPI backend and responsive web interface.
- Rule-based formula matching; no AI API key is required for this starter release.

## Run in GitHub Codespaces
1. Open this repository and choose **Code → Codespaces → Create codespace on main**.
2. In the terminal, run:
   ```bash
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. Open the **Ports** tab and click port 8000.

## API
- `GET /api/health`
- `POST /api/generate` with JSON such as `{"prompt":"Calculate total sales","platform":"Excel"}`
- `POST /api/inspect` accepts CSV/XLSX uploads and returns headers and a small preview.

## Roadmap
1. Excel formulas (starter module)
2. Power BI DAX and Power Query M
3. Tableau calculated fields and LOD expressions
4. Dataset profiling and cleaning
5. Business insights and report generation
6. Authentication, team workspaces and production controls

## Important
This is an early prototype. Formula suggestions are rule-based, may use example column references, and must be checked against your workbook. Power BI and Tableau generation are not implemented yet. Do not upload confidential company data to a public demo. Production use requires security, access controls, validation and privacy review.
