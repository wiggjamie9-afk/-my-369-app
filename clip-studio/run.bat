@echo off
rem One-click launcher for Windows.   run.bat            start the studio
rem                                   run.bat --install  also create .venv and install optional extras
cd /d "%~dp0"
where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo ffmpeg not found. Install it first, e.g.:  winget install Gyan.FFmpeg
  pause
  exit /b 1
)
set PY=python
where py >nul 2>nul && set PY=py
if "%1"=="--install" (
  %PY% -m venv .venv
  .venv\Scripts\python.exe -m pip install -r requirements-optional.txt
)
if exist .venv\Scripts\python.exe set PY=.venv\Scripts\python.exe
if "%PORT%"=="" set PORT=8369
start "" http://127.0.0.1:%PORT%
%PY% server.py
