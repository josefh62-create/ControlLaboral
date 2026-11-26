@echo off
setlocal

set "PROYECTO=%~dp0"
set "PYSIDE=%~dp0..\PyPortable314\Lib\site-packages\PySide6"
set "UIC=%PYSIDE%\uic.exe"
set "RCC=%PYSIDE%\rcc.exe"
set "QRC=%PROYECTO%Recursos\Imagenes\controllaboral.qrc"
set "RC_SALIDA=%PROYECTO%controllaboral_rc.py"

if not exist "%UIC%" (
    echo ERROR: No se encontro uic.exe en PyPortable314.
    exit /b 10
)
if not exist "%RCC%" (
    echo ERROR: No se encontro rcc.exe en PyPortable314.
    exit /b 11
)

if exist "%QRC%" (
    "%RCC%" -g python -o "%RC_SALIDA%" "%QRC%"
    if errorlevel 1 exit /b 20
)

if exist "%PROYECTO%Vistas\*.ui" (
    for %%F in ("%PROYECTO%Vistas\*.ui") do (
        "%UIC%" -g python -o "%PROYECTO%Vistas\%%~nF.py" "%%~fF"
        if errorlevel 1 exit /b 30
    )
)

echo Compilacion terminada correctamente.
endlocal
