@echo off
setlocal
cd /d "%~dp0"

where system-explorer >nul 2>&1
if errorlevel 1 (
  echo Could not find system-explorer.
  echo.
  echo Install it once with:
  echo   pip install "git+https://github.com/PatrykPrezyna/SE_assistant.git"
  echo.
  pause
  exit /b 1
)

echo Building the view-only Viewer in:
echo   %CD%\_site
echo.
system-explorer . --publish _site
if errorlevel 1 (
  echo.
  echo The Viewer was not built.
  pause
  exit /b 1
)

start "" "%~dp0_site\index.html"
