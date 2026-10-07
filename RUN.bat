@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
    py -3 run_local.py
) else (
    python run_local.py
)
pause
