@echo off
python -m pip install --upgrade python-docx PyPDF2 sacremoses >nul 2>&1
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause