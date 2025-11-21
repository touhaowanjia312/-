"""
配置检查脚本
验证 .env 文件是否正确设置
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from config import Config
from multi_exchange_client import multi_exchange_client

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def main():
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║                                                                   ║")
    print("║         🔍 配置检查工具                                            ║")
    print("║         检查 .env 和其他配置文件                                   ║")
    print("║                                                                   ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    
    # 1. Telegram 配置
    print_section("📱 Telegram 配置")
    
    print(f"\nAPI ID: ", end="")
    if Config.TELEGRAM_API_ID:
        print(f"✓ {Config.TELEGRAM_API_ID}")
    else:
        print("❌ 未设置")
    
    print(f"API Hash: ", end="")
    if Config.TELEGRAM_API_HASH:
        masked = Config.TELEGRAM_API_HASH[:8] + "..." + Config.TELEGRAM_API_HASH[-4:]
        print(f"✓ {masked}")
    else:
        print("❌ 未设置")
    
    print(f"Phone: ", end="")
    if Config.TELEGRAM_PHONE:
        if Config.TELEGRAM_PHONE.startswith('+'):
            print(f"✓ {Config.TELEGRAM_PHONE}")
        else:
            print(f"⚠️ {Config.TELEGRAM_PHONE} (缺少 + 号)")
    else:
        print("❌ 未设置")
    
    print(f"Group ID: ", end="")
    if Config.TELEGRAM_GROUP_ID:
        print(f"✓ {Config.TELEGRAM_GROUP_ID}")
    else:
        print("❌ 未设置")
    
    # 2. 交易配置
    print_section("💰 交易配置")
    
    print(f"\n交易状态: {'✓ 已启用' if Config.TRADING_ENABLED else '○ 已禁用'}")
    print(f"默认仓位: {Config.DEFAULT_POSITION_SIZE}")
    print(f"最大仓位: {Config.MAX_POSITION_SIZE}")
    print(f"风险比例: {Config.RISK_PERCENTAGE}%")
    
    # 3. 多交易所配置
    print_section("🏦 多交易所配置")
    
    if len(multi_exchange_client.clients) > 0:
        print(f"\n✓ 已配置 {len(multi_exchange_client.clients)} 个交易所：")
        for name, account in multi_exchange_client.accounts.items():
            print(f"\n  📍 {name}")
            print(f"     类型: {account.exchange_type}")
            print(f"     测试网: {'是' if account.testnet else '否'}")
            print(f"     杠杆: {account.default_leverage}x")
            print(f"     状态: {'启用' if account.enabled else '禁用'}")
    else:
        print("\n○ 未配置多交易所")
        print("\n单交易所配置：")
        print(f"  交易所: {Config.EXCHANGE_NAME}")
        print(f"  API Key: {'✓ 已设置' if Config.EXCHANGE_API_KEY else '❌ 未设置'}")
        print(f"  API Secret: {'✓ 已设置' if Config.EXCHANGE_API_SECRET else '❌ 未设置'}")
        print(f"  测试网: {'是' if Config.EXCHANGE_TESTNET else '否'}")
    
    # 4. 验证配置
    print_section("✅ 配置验证")
    
    print()
    try:
        Config.validate()
        print("✅ 配置验证通过！\n")
        print("所有必需的配置项都已正确设置。")
    except ValueError as e:
        print(f"❌ 配置验证失败\n")
        print(f"错误: {e}\n")
        print("请检查并修复以上问题。")
    
    # 5. Session 文件
    print_section("📂 Session 文件")
    
    import os
    session_file = "trading_bot_session.session"
    
    print()
    if os.path.exists(session_file):
        file_size = os.path.getsize(session_file)
        print(f"✓ Session 文件已存在")
        print(f"  文件大小: {file_size} bytes")
        print(f"  说明: 之前已成功验证过 Telegram")
    else:
        print(f"○ Session 文件不存在")
        print(f"  说明: 首次运行需要 Telegram 验证")
    
    # 6. 建议
    print_section("💡 建议")
    
    print()
    issues = []
    
    if not Config.TELEGRAM_API_ID:
        issues.append("设置 TELEGRAM_API_ID")
    if not Config.TELEGRAM_API_HASH:
        issues.append("设置 TELEGRAM_API_HASH")
    if not Config.TELEGRAM_PHONE:
        issues.append("设置 TELEGRAM_PHONE")
    elif not Config.TELEGRAM_PHONE.startswith('+'):
        issues.append("修正 TELEGRAM_PHONE 格式（需要 + 开头）")
    if not Config.TELEGRAM_GROUP_ID:
        issues.append("设置 TELEGRAM_GROUP_ID")
    
    if len(multi_exchange_client.clients) == 0 and Config.TRADING_ENABLED:
        if not Config.EXCHANGE_API_KEY:
            issues.append("配置交易所（多交易所或单交易所）")
    
    if issues:
        print("需要完成以下配置：")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print("\n编辑 .env 文件或在 GUI 中配置。")
    else:
        print("✅ 配置完整！可以开始使用。")
        print("\n下一步：")
        print("  1. 运行: python gui_main.py")
        print("  2. 点击 '▶️ 启动监听'")
        if not os.path.exists(session_file):
            print("  3. 输入 Telegram 验证码（首次需要）")
    
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()

