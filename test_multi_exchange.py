"""
多交易所功能测试脚本
演示如何配置和使用多个交易所账户
"""

import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from multi_exchange_config import ExchangeAccount, multi_exchange_config
from multi_exchange_client import multi_exchange_client

def demo_configuration():
    """演示配置功能"""
    print("=" * 60)
    print("多交易所配置演示")
    print("=" * 60)
    print()
    
    # 示例 1: 币安账户 - 使用风险百分比模式
    print("📝 创建示例账户 1: 币安（风险百分比模式）")
    binance_account = ExchangeAccount(
        name="币安主账户",
        exchange_type="binance",
        api_key="demo_key_binance",
        api_secret="demo_secret_binance",
        testnet=True,
        enabled=True,
        default_leverage=10,
        default_position_size=0.01,
        max_position_size=0.1,
        risk_percentage=1.0,
        use_margin_amount=False,
        margin_amount=100.0
    )
    print(binance_account)
    print()
    
    # 示例 2: OKX账户 - 使用固定保证金模式
    print("📝 创建示例账户 2: OKX（固定保证金模式）")
    okx_account = ExchangeAccount(
        name="OKX测试账户",
        exchange_type="okx",
        api_key="demo_key_okx",
        api_secret="demo_secret_okx",
        testnet=True,
        enabled=True,
        default_leverage=20,
        default_position_size=0.02,
        max_position_size=0.2,
        risk_percentage=2.0,
        use_margin_amount=True,  # 使用固定保证金
        margin_amount=200.0      # 每次 200 USDT
    )
    print(okx_account)
    print()
    
    # 示例 3: Bybit账户 - 禁用状态
    print("📝 创建示例账户 3: Bybit（禁用）")
    bybit_account = ExchangeAccount(
        name="Bybit备用账户",
        exchange_type="bybit",
        api_key="demo_key_bybit",
        api_secret="demo_secret_bybit",
        testnet=True,
        enabled=False,  # 禁用
        default_leverage=5,
        default_position_size=0.01,
        max_position_size=0.05,
        risk_percentage=0.5,
        use_margin_amount=False,
        margin_amount=50.0
    )
    print(bybit_account)
    print()
    
    # 添加到配置
    print("💾 添加账户到配置...")
    multi_exchange_config.add_account(binance_account)
    multi_exchange_config.add_account(okx_account)
    multi_exchange_config.add_account(bybit_account)
    
    # 保存配置
    multi_exchange_config.save_to_file()
    print("✓ 配置已保存到 exchanges_config.json")
    print()
    
    # 显示所有账户
    print("📋 当前配置的账户:")
    for i, account in enumerate(multi_exchange_config, 1):
        status = "✓ 启用" if account.enabled else "✗ 禁用"
        mode = "固定保证金" if account.use_margin_amount else "风险百分比"
        print(f"{i}. {account.name} ({account.exchange_type})")
        print(f"   状态: {status}")
        print(f"   杠杆: {account.default_leverage}x")
        print(f"   模式: {mode}")
        if account.use_margin_amount:
            print(f"   保证金: {account.margin_amount} USDT")
        else:
            print(f"   风险: {account.risk_percentage}%")
        print()
    
    print("─" * 60)
    print()

def demo_position_calculation():
    """演示仓位计算"""
    print("=" * 60)
    print("仓位计算演示")
    print("=" * 60)
    print()
    
    # 模拟场景
    btc_price = 42000.0  # BTC 价格
    account_balance = 10000.0  # 账户余额
    
    print(f"假设场景:")
    print(f"  BTC/USDT 价格: ${btc_price:,.2f}")
    print(f"  账户余额: ${account_balance:,.2f} USDT")
    print()
    
    # 场景 1: 风险百分比模式
    print("📊 场景 1: 风险百分比模式")
    print("─" * 60)
    risk_pct = 1.0  # 1%
    leverage = 10
    
    risk_amount = account_balance * (risk_pct / 100)
    position_size = risk_amount / btc_price
    position_value = position_size * btc_price
    leveraged_value = position_value * leverage
    
    print(f"  风险百分比: {risk_pct}%")
    print(f"  杠杆倍数: {leverage}x")
    print(f"  ────────────────")
    print(f"  风险金额: ${risk_amount:,.2f}")
    print(f"  仓位大小: {position_size:.6f} BTC")
    print(f"  仓位价值: ${position_value:,.2f}")
    print(f"  实际控制: ${leveraged_value:,.2f} (含杠杆)")
    print()
    
    # 场景 2: 固定保证金模式
    print("📊 场景 2: 固定保证金模式")
    print("─" * 60)
    margin = 200.0  # 200 USDT
    leverage = 20
    
    leveraged_amount = margin * leverage
    position_size = leveraged_amount / btc_price
    
    print(f"  保证金金额: ${margin:,.2f}")
    print(f"  杠杆倍数: {leverage}x")
    print(f"  ────────────────")
    print(f"  实际仓位价值: ${leveraged_amount:,.2f}")
    print(f"  仓位大小: {position_size:.6f} BTC")
    print(f"  占用保证金: ${margin:,.2f}")
    print()
    
    # 对比
    print("💡 两种模式对比:")
    print("─" * 60)
    print("风险百分比模式:")
    print("  ✓ 根据账户余额动态调整")
    print("  ✓ 适合长期稳定运行")
    print("  ✓ 风险可控")
    print()
    print("固定保证金模式:")
    print("  ✓ 每次投入固定金额")
    print("  ✓ 便于资金管理")
    print("  ✓ 适合固定策略")
    print()
    
    print("─" * 60)
    print()

def demo_multi_exchange_usage():
    """演示多交易所使用"""
    print("=" * 60)
    print("多交易所使用演示")
    print("=" * 60)
    print()
    
    print("注意: 以下是模拟代码，实际运行需要真实的 API 密钥")
    print()
    
    # 代码示例
    code_example = """
# 1. 查询所有账户余额
balances = multi_exchange_client.get_all_balances()
for account_name, balance in balances.items():
    print(f"{account_name}: {balance:.2f} USDT")

# 2. 查询单个账户余额
balance = multi_exchange_client.get_balance('币安主账户')
print(f"币安余额: {balance:.2f} USDT")

# 3. 获取当前价格
price = multi_exchange_client.get_current_price('币安主账户', 'BTC/USDT')
print(f"BTC价格: ${price:,.2f}")

# 4. 计算仓位大小（自动根据账户配置）
position = multi_exchange_client.calculate_position_size(
    '币安主账户', 
    'BTC/USDT', 
    42000.0
)
print(f"建议仓位: {position:.6f} BTC")

# 5. 下市价单（自动计算仓位）
order = multi_exchange_client.place_market_order(
    '币安主账户',
    'BTC/USDT',
    'buy'  # 不需要指定数量，自动计算
)

# 6. 下限价单（自动计算仓位）
order = multi_exchange_client.place_limit_order(
    '币安主账户',
    'BTC/USDT',
    'buy',
    42000.0  # 价格
    # 数量会自动计算
)

# 7. 在所有启用的账户上执行
results = multi_exchange_client.execute_on_all(
    symbol='BTC/USDT',
    side='buy',
    leverage=10
)
# 返回: {'币安主账户': order1, 'OKX测试账户': order2}

# 8. 设置杠杆
multi_exchange_client.set_leverage('币安主账户', 'BTC/USDT', 10)

# 9. 平仓
multi_exchange_client.close_position('币安主账户', 'BTC/USDT')

# 10. 获取账户信息
info = multi_exchange_client.get_account_info('币安主账户')
print(info)
"""
    
    print("📝 代码示例:")
    print(code_example)
    
    print("─" * 60)
    print()

def main():
    """主函数"""
    print()
    print("🚀 多交易所功能测试")
    print()
    
    # 演示 1: 配置
    demo_configuration()
    
    # 演示 2: 仓位计算
    demo_position_calculation()
    
    # 演示 3: 使用方法
    demo_multi_exchange_usage()
    
    print("=" * 60)
    print("✅ 演示完成！")
    print()
    print("💡 提示:")
    print("  1. 配置已保存到 exchanges_config.json")
    print("  2. 使用真实 API 前，请先在测试网测试")
    print("  3. 阅读 '多交易所功能说明.md' 了解更多")
    print()
    print("=" * 60)

if __name__ == "__main__":
    main()

