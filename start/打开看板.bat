@echo off
rem ============================================================
rem  LeetCode Board launcher (Windows)
rem  NOTE: keep this file ASCII-only. cmd.exe reads .bat with the
rem  system code page (GBK on zh-CN), so UTF-8 Chinese comments
rem  turn into garbage and get executed as commands.
rem ============================================================
setlocal
cd /d "%~dp0"

set "PYEXE="
set "PYARG="

rem --- 1) look for python on PATH ---------------------------------
for /f "delims=" %%i in ('where python.exe 2^>nul') do (
    if not defined PYEXE set "PYEXE=%%i"
)
for /f "delims=" %%i in ('where python3.exe 2^>nul') do (
    if not defined PYEXE set "PYEXE=%%i"
)
if not defined PYEXE (
    for /f "delims=" %%i in ('where py.exe 2^>nul') do (
        if not defined PYEXE (
            set "PYEXE=%%i"
            set "PYARG=-3"
        )
    )
)

rem --- 2) fall back to common install locations -------------------
if not defined PYEXE if exist "%~dp0python\python.exe"          set "PYEXE=%~dp0python\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYEXE if exist "%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe" set "PYEXE=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

if not defined PYEXE (
    echo.
    echo   [X] Python not found.
    echo.
    echo   Install Python 3.8+ and tick "Add python.exe to PATH":
    echo       https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo   Using: %PYEXE% %PYARG%
"%PYEXE%" %PYARG% start.py

if errorlevel 1 (
    echo.
    echo   [X] Failed to start. See server.log for details.
    pause
)
endlocal