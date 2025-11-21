#!/bin/bash

echo "========================================"
echo "Telegram 群组信号跟单程序 GUI 版本"
echo "========================================"
echo ""
echo "正在启动..."
echo ""

python3 gui_main.py

if [ $? -ne 0 ]; then
    echo ""
    echo "========================================"
    echo "启动失败！请检查："
    echo "1. 是否安装了依赖: pip3 install -r requirements.txt"
    echo "2. Python 是否正确安装"
    echo "========================================"
    read -p "按任意键继续..."
fi

