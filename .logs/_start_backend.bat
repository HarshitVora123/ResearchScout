@echo off
cd /D "D:\Projects\Researchscout\backend"
D:\Projects\Researchscout\backend\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >> "D:\Projects\Researchscout\.logs\backend.log" 2>&1
