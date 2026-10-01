@echo off
rem Windows 双击启动入口：切到脚本所在目录，用 venv 里的 Python 跑 run.py。
rem 中文提示都放在 run.py 里（Python 处理编码没问题），这里只留英文，避免乱码。
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] venv not found at venv\Scripts\python.exe
    echo Please create the virtual environment and install dependencies first.
    pause
    exit /b 1
)

venv\Scripts\python.exe run.py

echo.
echo Server stopped.
pause
