#!/usr/bin/env bash
set -euo pipefail

# Analytics InAdvance - Google Cloud Shell setup
# Run from the repository root: bash cloudshell_setup.sh

if [[ ! -f "requirements.txt" || ! -f "app/main.py" ]]; then
  echo "Run this script from the analytics--inadvance repository root."
  exit 1
fi

echo "==> Creating Python virtual environment..."
python3 -m venv .venv

echo "==> Activating virtual environment..."
source .venv/bin/activate

echo "==> Installing dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "Setup complete."
echo "Starting Analytics InAdvance on port 8000..."
echo "In Cloud Shell, choose Web Preview > Preview on port 8000."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
