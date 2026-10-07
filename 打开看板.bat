@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem 依次尝试 python / py / python3，找到哪个用哪个
where python >nul 2>nul && (python start.py && goto :done)
where py     >nul 2>nul && (py -3    start.py && goto :done)
where python3>nul 2>nul && (python3 start.py && goto :done)

echo.
echo   没有找到 Python。请先安装 Python 3.8+ 并勾选 "Add to PATH"：
echo   https://www.python.org/downloads/
echo.
pause
:done