"""
获取 Telegram 群组 ID 的脚本
运行此脚本查看你有权访问的所有群组及其 ID
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from telethon import TelegramClient
from config import Config
import asyncio

async def get_all_groups():
    print("=" * 70)
    print("  Telegram 群组 ID 获取工具")
    print("=" * 70)
    print()
    
    # 创建客户端
    client = TelegramClient(
        'trading_bot_session',
        Config.TELEGRAM_API_ID,
        Config.TELEGRAM_API_HASH
    )
    
    await client.start(phone=Config.TELEGRAM_PHONE)
    
    print("✓ 已连接到 Telegram\n")
    print("你有权访问的群组和频道：\n")
    print("-" * 70)
    
    # 获取所有对话
    groups_found = False
    async for dialog in client.iter_dialogs():
        # 只显示群组和频道
        if dialog.is_group or dialog.is_channel:
            groups_found = True
            
            # 群组类型
            if dialog.is_group:
                group_type = "群组"
            elif dialog.is_channel and dialog.entity.broadcast:
                group_type = "频道"
            else:
                group_type = "超级群组"
            
            # 显示信息
            print(f"\n📍 {dialog.name}")
            print(f"   类型: {group_type}")
            print(f"   ID: {dialog.id}")
            print(f"   用户名: @{dialog.entity.username}" if dialog.entity.username else "   用户名: (无)")
            
            # 这就是你需要的 ID！
            if dialog.entity.username:
                print(f"   \n   ✅ 配置可以用: {dialog.id}")
                print(f"   或使用用户名: @{dialog.entity.username}")
            else:
                print(f"   \n   ✅ 配置可以用: {dialog.id}")
            
            print("-" * 70)
    
    if not groups_found:
        print("\n⚠️ 未找到任何群组或频道")
        print("请确认：")
        print("  1. 你的账号已加入一些群组")
        print("  2. Telegram 已正确登录")
    
    print("\n")
    print("=" * 70)
    print("  使用说明")
    print("=" * 70)
    print("""
1. 找到你想要监听的群组名称
2. 复制对应的 ID（包括负号）
3. 在 GUI 的 "详细设置" 中：
   - 将 Group ID 修改为复制的 ID
   - 或使用 @用户名（如果有的话）
4. 保存配置并重启机器人
""")
    
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(get_all_groups())

