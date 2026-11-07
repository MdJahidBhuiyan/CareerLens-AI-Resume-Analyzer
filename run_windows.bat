@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (py -3.10 -m venv .venv) else (python -m venv .venv)
call .venv\Scripts\activate.bat
python -m pip install -r requirements.txt
if errorlevel 1 (echo Dependency installation failed. & pause & exit /b 1)
start "" http://127.0.0.1:5000
python app.py
pause
