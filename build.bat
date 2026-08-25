@echo off
chcp 65001 >nul
REM ============================================================
REM  WorkBuddy MC 启动器 - Windows 一键打包脚本
REM  在 Windows 上运行本脚本，生成可双击运行的 .exe
REM ============================================================

echo.
echo  === WorkBuddy MC 启动器打包 ===
echo.

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.9+ 并勾选 "Add to PATH"
    pause
    exit /b 1
)

echo  [1/3] 安装依赖...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

echo.
echo  [2/3] 开始打包（首次打包较慢，请耐心等待）...
pyinstaller --clean mc-launcher.spec

echo.
echo  [3/3] 完成！
echo.
echo  生成的程序位于： dist\WorkBuddyMC启动器.exe
echo  双击该文件即可运行启动器。
echo.
pause
