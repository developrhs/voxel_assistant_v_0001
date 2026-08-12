@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0venv\Scripts\python.exe" (
    "%~dp0venv\Scripts\python.exe" "%~dp0main_teste.py" %*
) else (
    python "%~dp0main_teste.py" %*
)
set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" echo O teste terminou com erro. Codigo: %EXIT_CODE%
pause
exit /b %EXIT_CODE%
