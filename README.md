# Analytics InAdvance

**Ask. Analyze. Automate.**

An analytics productivity workspace for Advanced Excel, Power BI and Tableau. This first release delivers **Module 1: Excel Formula Assistant**.

## Current release
- Convert common business questions into Excel formulas.
- Show explanations, assumptions and application steps.
- Copy generated formulas.
- FastAPI backend and responsive web interface.
- Rule-based formula matching; no AI API key is required for this starter release.

## Run in Google Cloud Shell
1. Open [Google Cloud Shell](https://shell.cloud.google.com/) and wait for the terminal to load.
2. Clone this repository:
   ```bash
   git clone https://github.com/Soniyareddy2468/analytics--inadvance.git
   cd analytics--inadvance
   ```
   If the folder already exists, use `cd ~/analytics--inadvance` instead of cloning again.
3. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install dependencies and start the app:
   ```bash
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. In Cloud Shell, select **Web Preview → Preview on port 8000**. The app opens in a browser tab. Keep the terminal running while using it.
6. To stop the app, press `Ctrl+C` in the terminal.

## Run locally
The same commands work in a local terminal after installing Python 3.11+ and Git. On Windows, activate the environment with `.venv\\Scripts\\Activate.ps1`.

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
