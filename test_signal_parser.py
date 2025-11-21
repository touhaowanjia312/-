"""
信号解析器测试脚本
用于测试各种格式的交易信号是否能正确识别
"""

import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from signal_parser import SignalParser

# 测试信号示例
test_signals = [
    """
    🔥 LONG BTC/USDT
    Entry: 42000
    Stop Loss: 41000
    Take Profit: 43000
    Leverage: 10x
    """,
    
    """
    Buy ETHUSDT
    Price: 2500
    SL: 2400
    TP: 2600 2700 2800
    """,
    
    """
    做多 BTC
    入场: 42000
    止损: 41000
    止盈: 43000
    杠杆: 10
    """,
    
    """
    #BTC LONG 🚀
    Entry @ 42000
    SL 41000
    Target 43000
    """,
    
    """
    SHORT SOL/USDT
    Entry: 100.5
    Stop Loss: 102
    Take Profit: 95, 90, 85
    Leverage: 5x
    """,
    
    """
    CLOSE BTC/USDT
    Exit all positions
    """,
    
    """
    $ETH Buy Signal
    Target 2500
    SL 2400
    """,
]

def main():
    print("="*60)
    print("Telegram 交易信号解析测试")
    print("="*60)
    
    parser = SignalParser()
    
    for i, message in enumerate(test_signals, 1):
        print(f"\n测试 #{i}")
        print("-" * 60)
        print("原始消息:")
        print(message.strip())
        print("\n解析结果:")
        
        signal = parser.parse(message)
        
        if signal:
            print(f"✓ 信号类型: {signal.signal_type.value}")
            print(f"✓ 交易对: {signal.symbol}")
            if signal.entry_price:
                print(f"✓ 入场价格: {signal.entry_price}")
            if signal.stop_loss:
                print(f"✓ 止损: {signal.stop_loss}")
            if signal.take_profit:
                print(f"✓ 止盈: {signal.take_profit}")
            if signal.leverage:
                print(f"✓ 杠杆: {signal.leverage}x")
        else:
            print("✗ 未识别到有效信号")
        
        print("-" * 60)
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)

if __name__ == "__main__":
    main()

