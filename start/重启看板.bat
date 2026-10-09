@echo off
rem ============================================================
rem  LeetCode Board restart (Windows)
rem
rem  What it does:
rem    1. Kill whatever process is listening on port 8765
rem       (the old board server -- it runs hidden, no window).
rem    2. Relaunch server.py through start.py and open the browser.
rem
rem  Why you need this: double-clicking the normal shortcut only
rem  opens a browser tab when the service is already running --
rem  it does NOT restart it. After editing server.py, run this
rem  to make the new code actually take effect.
rem
rem  NOTE: keep this file ASCII-only. cmd.exe reads .bat with
rem  the system code page (GBK on zh-CN), so UTF-8 Chinese
rem  comments turn into garbage and get executed as commands.
rem ============================================================
setlocal
cd /d "%~dp0"

rem --- 1) stop the old service ---------------------------------
set "KILLED="
for /f "tokens=5" %%a in ('netstat -ano ^| findstr /r /c:":8765 .*LISTENING"') do (
    taskkill /PID %%a /F >nul 2>nul && set "KILLED=1"
)
if defined KILLED (
    echo   Old service stopped.
    ping -n 3 127.0.0.1 >nul
) else (
    echo   Nothing was listening on port 8765 - starting fresh.
)

rem --- 2) find python (same search order as the launcher) -----
set "PYEXE="
set "PYARG="
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
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PYEXE if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PYEXE=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PYEXE if exist "%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe" set "PYEXE=%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts\python.exe"

if not defined PYEXE (
    echo.
    echo   [X] Python not found.
    echo.
    pause
    exit /b 1
)

rem --- 3) relaunch (start.py spawns a detached server) --------
echo   Restarting with: %PYEXE% %PYARG%
"%PYEXE%" %PYARG% start.py
if errorlevel 1 (
    echo.
    echo   [X] Failed to restart. See server.log for details.
    pause
    exit /b 1
)

rem --- 4) verify the port is really listening ------------------
netstat -ano | findstr /r /c:":8765 .*LISTENING" >nul 2>nul
if errorlevel 1 (
    echo   [X] Service did not come up. See server.log for details.
    pause
    exit /b 1
)
echo   Restart OK - board is at http://127.0.0.1:8765
endlocal
