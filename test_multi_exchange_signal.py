"""
测试多交易所信号执行
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import logging
from multi_exchange_client import multi_exchange_client
from signal_parser import SignalParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_multi_exchange_connection():
    """测试多交易所连接"""
    print("=" * 70)
    print("多交易所连接测试")
    print("=" * 70)
    
    # 检查已连接的交易所
    print(f"\n已连接的交易所数量: {len(multi_exchange_client.clients)}")
    print("\n详细信息：")
    print("-" * 70)
    
    for name, client in multi_exchange_client.clients.items():
        account = multi_exchange_client.accounts[name]
        print(f"\n✓ {name}")
        print(f"  交易所类型: {account.exchange_type}")
        print(f"  测试网: {'是' if account.testnet else '否'}")
        print(f"  杠杆: {account.default_leverage}x")
        print(f"  状态: 已启用" if account.enabled else "  状态: 已禁用")
        
        # 尝试获取余额
        try:
            balance = multi_exchange_client.get_balance(name)
            if balance is not None:
                print(f"  余额: {balance:.2f} USDT")
            else:
                print(f"  余额: 无法获取")
        except Exception as e:
            print(f"  余额: 获取失败 - {e}")
    
    print("\n" + "=" * 70)
    
def test_signal_parsing():
    """测试信号解析"""
    print("\n信号解析测试")
    print("=" * 70)
    
    parser = SignalParser()
    
    test_signal = """#MDT 市價空
第一止盈：0.01972"""
    
    print(f"\n测试信号：")
    print(test_signal)
    print()
    
    signal = parser.parse(test_signal)
    
    if signal:
        print("✅ 解析成功")
        print(f"  交易对: {signal.symbol}")
        print(f"  方向: {signal.signal_type.value}")
        print(f"  止盈: {signal.take_profit}")
    else:
        print("❌ 解析失败")
    
    print("\n" + "=" * 70)

def main():
    print("\n🚀 Telegram 信号跟单系统 - 多交易所测试\n")
    
    # 测试1：多交易所连接
    test_multi_exchange_connection()
    
    # 测试2：信号解析
    test_signal_parsing()
    
    print("\n✅ 测试完成！")
    print("\n提示：")
    print("  • 如果看到多个交易所已连接，说明配置正确")
    print("  • 启动机器人时应该使用这些交易所执行交易")
    print("  • 不应该看到单独的 binance 连接")

if __name__ == "__main__":
    main()

