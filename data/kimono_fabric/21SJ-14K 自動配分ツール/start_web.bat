@echo off
setlocal

cd /d "%~dp0"
set "PORT=8000"
set "URL=http://localhost:%PORT%/web/"

where py >nul 2>nul
if not errorlevel 1 (
    set "PY_CMD=py"
) else (
    where python >nul 2>nul
    if not errorlevel 1 (
        set "PY_CMD=python"
    ) else (
        echo [ERROR] Python or py launcher was not found.
        echo Install Python, then run this file again.
        pause
        exit /b 1
    )
)

echo Opening %URL%
start "" "%URL%"
echo.
echo Starting local server on port %PORT% ...
echo Press Ctrl + C to stop.
echo.

%PY_CMD% -m http.server %PORT%

echo.
echo Server stopped.
pause
