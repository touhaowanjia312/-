"""
测试图片中的实际MDT信号
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from signal_parser import SignalParser
from smart_order_manager import smart_order_manager

def test_mdt_signal():
    """测试图片中的MDT信号"""
    
    print("=" * 70)
    print("测试实际MDT信号")
    print("=" * 70)
    
    # 图片中的实际信号
    message = """#MDT 市價空
第一止盈：0.01972"""
    
    print("\n📱 收到Telegram信号：")
    print("-" * 70)
    print(message)
    print()
    
    # 1. 解析信号
    parser = SignalParser()
    signal = parser.parse(message)
    
    if not signal:
        print("❌ 信号解析失败！")
        return
    
    print("✅ 信号解析成功！")
    print("-" * 70)
    print(f"📊 解析结果：")
    print(f"  • 交易对: {signal.symbol}")
    print(f"  • 方向: {signal.signal_type.value} (做空)")
    print(f"  • 入场价: {'市价' if not signal.entry_price else signal.entry_price}")
    print(f"  • 止损: {signal.stop_loss if signal.stop_loss else '无（使用默认）'}")
    print(f"  • 止盈: {signal.take_profit if signal.take_profit else '无（使用默认）'}")
    print(f"  • 杠杆: {signal.leverage if signal.leverage else '默认'}")
    print()
    
    # 2. 创建智能订单计划
    print("🎯 智能订单管理器处理：")
    print("-" * 70)
    order_plan = smart_order_manager.create_order_plan(signal)
    
    # 3. 显示完整订单计划
    print(smart_order_manager.format_plan_summary(order_plan))
    print()
    
    # 4. 详细说明
    print("📝 执行说明：")
    print("-" * 70)
    print("1️⃣ 入场订单：")
    print(f"   • 交易对: MDT/USDT")
    print(f"   • 方向: 做空（SELL/SHORT）")
    print(f"   • 订单类型: 市价单（立即执行）")
    print(f"   • 仓位大小: 根据风险%自动计算")
    print()
    
    print("2️⃣ 止损订单：")
    if order_plan['stop_loss']:
        print(f"   • 止损价格: {order_plan['stop_loss']}")
        print(f"   • 止损类型: 自动计算（默认2%）")
        print(f"   • 说明: 信号没有止损，使用配置的默认止损%")
    print()
    
    print("3️⃣ 止盈订单：")
    for i, (tp, portion) in enumerate(zip(order_plan['take_profits'], order_plan['tp_portions']), 1):
        source = "信号止盈" if i == 1 else "额外止盈"
        print(f"   • TP{i}: {tp} ({portion:.1f}% 仓位) - {source}")
    print()
    
    print("4️⃣ 高级功能：")
    if order_plan['trailing_stop']:
        print(f"   ✓ 追踪止损: {order_plan['trailing_stop_percent']}%")
        print(f"     说明: 价格有利时止损自动跟随")
    if order_plan['move_to_breakeven']:
        print(f"   ✓ 保本止损: 盈利{order_plan['breakeven_trigger_percent']}%后触发")
        print(f"     说明: 达到盈利目标后，止损移动到成本价")
    print()
    
    print("=" * 70)
    print("✅ 订单计划完成！程序会按此计划自动执行交易")
    print("=" * 70)
    
    # 模拟执行流程
    print("\n🚀 模拟执行流程：")
    print("-" * 70)
    print("1. 收到Telegram信号 ✓")
    print("2. 解析信号内容 ✓")
    print("3. 创建智能订单计划 ✓")
    print("4. 市价开空MDT/USDT...")
    print("5. 设置止损订单...")
    print("6. 设置TP1（信号止盈）...")
    print("7. 设置TP2（额外止盈）...")
    print("8. 激活追踪止损...")
    print("9. 激活保本止损...")
    print("10. ✅ 完成！持仓管理中...")
    print()
    
    print("💡 提示：")
    print("  • 信号中的止盈价格会被优先使用")
    print("  • 程序会自动添加额外的止盈点")
    print("  • 止损会根据配置自动设置")
    print("  • 市价单会立即执行")

if __name__ == "__main__":
    test_mdt_signal()

