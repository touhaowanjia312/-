"""
交互式止盈止损计算器
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def calculate_tpsl(entry_price, direction, sl_percent, tp_percents):
    """
    计算止盈止损价格
    
    Args:
        entry_price: 入场价格
        direction: 'long' 或 'short'
        sl_percent: 止损百分比
        tp_percents: 止盈百分比列表
    """
    print("=" * 70)
    print(f"📊 {'做多(LONG)' if direction == 'long' else '做空(SHORT)'} 止盈止损计算")
    print("=" * 70)
    print()
    
    print(f"💰 入场价格: {entry_price:,.8f} USDT".rstrip('0').rstrip('.'))
    print(f"📈 方向: {direction.upper()}")
    print()
    
    # 计算止损
    if direction == 'long':
        sl_price = entry_price * (1 - sl_percent / 100)
        print("🛑 止损计算（做多）")
        print(f"   公式: 入场价 × (1 - 止损%/100)")
        print(f"   计算: {entry_price:,.8f} × (1 - {sl_percent}/100)".rstrip('0').rstrip('.'))
        print(f"   结果: {entry_price:,.8f} × {1 - sl_percent/100}".rstrip('0').rstrip('.'))
        print(f"   止损价: {sl_price:,.8f} USDT".rstrip('0').rstrip('.'))
        print(f"   实际亏损: {-sl_percent}%")
    else:
        sl_price = entry_price * (1 + sl_percent / 100)
        print("🛑 止损计算（做空）")
        print(f"   公式: 入场价 × (1 + 止损%/100)")
        print(f"   计算: {entry_price:,.8f} × (1 + {sl_percent}/100)".rstrip('0').rstrip('.'))
        print(f"   结果: {entry_price:,.8f} × {1 + sl_percent/100}".rstrip('0').rstrip('.'))
        print(f"   止损价: {sl_price:,.8f} USDT".rstrip('0').rstrip('.'))
        print(f"   实际亏损: {-sl_percent}%")
    
    print()
    
    # 计算止盈
    print("🎯 止盈计算")
    if direction == 'long':
        print("   公式: 入场价 × (1 + 止盈%/100)")
        print()
        for i, tp_percent in enumerate(tp_percents, 1):
            tp_price = entry_price * (1 + tp_percent / 100)
            print(f"   TP{i}: {tp_percent}%")
            print(f"      计算: {entry_price:,.8f} × (1 + {tp_percent}/100)".rstrip('0').rstrip('.'))
            print(f"      结果: {entry_price:,.8f} × {1 + tp_percent/100}".rstrip('0').rstrip('.'))
            print(f"      止盈价: {tp_price:,.8f} USDT".rstrip('0').rstrip('.'))
            print(f"      实际盈利: +{tp_percent}%")
            print()
    else:
        print("   公式: 入场价 × (1 - 止盈%/100)")
        print()
        for i, tp_percent in enumerate(tp_percents, 1):
            tp_price = entry_price * (1 - tp_percent / 100)
            print(f"   TP{i}: {tp_percent}%")
            print(f"      计算: {entry_price:,.8f} × (1 - {tp_percent}/100)".rstrip('0').rstrip('.'))
            print(f"      结果: {entry_price:,.8f} × {1 - tp_percent/100}".rstrip('0').rstrip('.'))
            print(f"      止盈价: {tp_price:,.8f} USDT".rstrip('0').rstrip('.'))
            print(f"      实际盈利: +{tp_percent}%")
            print()
    
    print("=" * 70)
    print()


def main():
    """主函数"""
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║            🧮 止盈止损计算器 v1.0                            ║")
    print("║          详细展示每一步计算过程                              ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    
    # 示例1: BTC 做多
    print("📝 示例1: BTC/USDT 做多")
    print("-" * 70)
    calculate_tpsl(
        entry_price=42000,
        direction='long',
        sl_percent=2,
        tp_percents=[2, 4, 6]
    )
    
    # 示例2: MDT 做空（图片信号）
    print("📝 示例2: MDT/USDT 做空（图片信号）")
    print("-" * 70)
    calculate_tpsl(
        entry_price=0.02000,
        direction='short',
        sl_percent=2,
        tp_percents=[1.4]  # 信号中的止盈约1.4%
    )
    
    # 示例3: ETH 做空
    print("📝 示例3: ETH/USDT 做空")
    print("-" * 70)
    calculate_tpsl(
        entry_price=2200,
        direction='short',
        sl_percent=2,
        tp_percents=[2, 4, 6]
    )
    
    # 示例4: 小币种 DOGE 做多
    print("📝 示例4: DOGE/USDT 做多")
    print("-" * 70)
    calculate_tpsl(
        entry_price=0.085,
        direction='long',
        sl_percent=2,
        tp_percents=[2, 4, 6]
    )
    
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║                    📚 公式总结                                ║")
    print("╠═══════════════════════════════════════════════════════════════╣")
    print("║ 做多(LONG):                                                   ║")
    print("║   止损价 = 入场价 × (1 - 止损%/100)                          ║")
    print("║   止盈价 = 入场价 × (1 + 止盈%/100)                          ║")
    print("║                                                               ║")
    print("║ 做空(SHORT):                                                  ║")
    print("║   止损价 = 入场价 × (1 + 止损%/100)                          ║")
    print("║   止盈价 = 入场价 × (1 - 止盈%/100)                          ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print()
    
    print("💡 关键要点：")
    print("   1. 百分比始终基于入场价格计算")
    print("   2. 做多：止损在下方，止盈在上方")
    print("   3. 做空：止损在上方，止盈在下方")
    print("   4. 确保风险回报比合理（建议 ≥ 1:2）")
    print()


if __name__ == "__main__":
    main()

