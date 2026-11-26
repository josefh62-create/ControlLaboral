@echo off
setlocal
set "PYTHON_PORTABLE=%~dp0..\PyPortable314\python.exe"

if exist "%PYTHON_PORTABLE%" (
    "%PYTHON_PORTABLE%" "%~dp0main.py"
) else (
    echo ADVERTENCIA: No se encontro PyPortable314; se usara Python del PATH.
    python "%~dp0main.py"
)

endlocal
