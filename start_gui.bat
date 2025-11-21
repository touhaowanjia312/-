@echo off
chcp 65001 >nul
echo ========================================
echo Telegram 群组信号跟单程序 GUI 版本
echo ========================================
echo.
echo 正在启动...
echo.

python gui_main.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo 启动失败！请检查：
    echo 1. 是否安装了依赖: pip install -r requirements.txt
    echo 2. Python 是否正确安装
    echo ========================================
    pause
)

