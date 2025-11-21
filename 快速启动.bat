@echo off
chcp 65001 >nul
echo.
echo ═══════════════════════════════════════════════
echo   Telegram 信号跟单系统 - 前台启动
echo   （首次使用需要 Telegram 验证）
echo ═══════════════════════════════════════════════
echo.
echo 正在启动程序...
echo.
echo 重要提示：
echo   1. 不要关闭此窗口
echo   2. GUI 会自动打开
echo   3. 如果需要输入验证码，请在此窗口输入
echo.
echo ═══════════════════════════════════════════════
echo.

python gui_main.py

echo.
echo 程序已退出
pause

