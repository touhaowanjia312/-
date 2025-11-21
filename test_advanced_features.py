"""
高级功能测试脚本
演示 TP/SL、风控、数据库、统计等功能
"""

import sys
import io

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from order_manager import TradePlan
from risk_manager import RiskLimits
from database import trading_db
from statistics import trading_stats
from datetime import datetime

def demo_trade_plan():
    """演示交易计划"""
    print("=" * 70)
    print("【演示 1】 完整交易计划")
    print("=" * 70)
    print()
    
    # 创建交易计划
    plan = TradePlan(
        symbol='BTC/USDT',
        side='buy',
        entry_price=42000,
        stop_loss=41000,
        take_profits=[43000, 44000, 45000],
        tp_portions=[30, 30, 40],
        leverage=10,
        trailing_stop_pct=2.0,
        move_sl_to_breakeven=True,
        breakeven_trigger_pct=1.0
    )
    
    print("📋 交易计划详情:")
    print(f"  交易对: {plan.symbol}")
    print(f"  方向: {'做多' if plan.side == 'buy' else '做空'}")
    print(f"  入场价格: ${plan.entry_price:,.2f}")
    print(f"  止损: ${plan.stop_loss:,.2f} (风险: {((plan.entry_price-plan.stop_loss)/plan.entry_price*100):.2f}%)")
    print(f"  杠杆: {plan.leverage}x")
    print()
    
    print("🎯 分批止盈设置:")
    for i, (tp, portion) in enumerate(zip(plan.take_profits, plan.tp_portions), 1):
        profit_pct = ((tp - plan.entry_price) / plan.entry_price * 100)
        print(f"  TP{i}: ${tp:,.2f} ({portion}% 仓位) - 利润: {profit_pct:.2f}%")
    print()
    
    print("📊 风险管理:")
    print(f"  ✓ 追踪止损: {plan.trailing_stop_pct}%")
    print(f"  ✓ 保本止损: 盈利 {plan.breakeven_trigger_pct}% 后触发")
    print()
    
    # 模拟价格变化
    print("💹 模拟价格变化:")
    prices = [42000, 42500, 43000, 43500, 44000, 43800]
    highest = plan.entry_price
    
    for price in prices:
        if price > highest:
            highest = price
        
        trailing_sl = highest * (1 - plan.trailing_stop_pct / 100)
        profit_pct = ((price - plan.entry_price) / plan.entry_price * 100)
        
        print(f"  当前价: ${price:,.0f} | 盈利: {profit_pct:+.2f}% | 追踪止损: ${trailing_sl:,.0f}")
        
        # 检查止盈
        if price >= plan.take_profits[0]:
            print(f"    → 🎯 触发 TP1，平仓 30%")
        if price >= plan.take_profits[1]:
            print(f"    → 🎯 触发 TP2，平仓 30%")
        if price >= plan.take_profits[2]:
            print(f"    → 🎯 触发 TP3，平仓 40%")
    
    print()
    print("─" * 70)
    print()

def demo_risk_manager():
    """演示风控管理"""
    print("=" * 70)
    print("【演示 2】 风险控制系统")
    print("=" * 70)
    print()
    
    # 创建风险限制
    limits = RiskLimits(
        max_daily_loss_pct=5.0,
        max_daily_loss_amount=500.0,
        max_total_loss_pct=20.0,
        max_consecutive_losses=3,
        max_open_positions=5,
        cooldown_after_limit=60,
        min_account_balance=100.0
    )
    
    print("🛡️ 风险限制配置:")
    print(f"  • 最大日亏损: {limits.max_daily_loss_pct}% 或 ${limits.max_daily_loss_amount}")
    print(f"  • 最大总亏损: {limits.max_total_loss_pct}%")
    print(f"  • 连续亏损限制: {limits.max_consecutive_losses} 次")
    print(f"  • 最大持仓数: {limits.max_open_positions}")
    print(f"  • 冷却时间: {limits.cooldown_after_limit} 分钟")
    print(f"  • 最低余额: ${limits.min_account_balance}")
    print()
    
    # 模拟交易场景
    print("📊 模拟交易场景:")
    initial_balance = 10000
    current_balance = initial_balance
    trades = [
        ('BTC/USDT', -100),
        ('ETH/USDT', -80),
        ('SOL/USDT', -120),  # 第3次连亏
        ('BTC/USDT', 150),   # 应被阻止
    ]
    
    consecutive_losses = 0
    daily_loss = 0
    
    for i, (symbol, pnl) in enumerate(trades, 1):
        print(f"\n交易 {i}: {symbol}")
        print(f"  盈亏: {pnl:+.2f} USDT")
        
        if pnl < 0:
            consecutive_losses += 1
            daily_loss += abs(pnl)
        else:
            consecutive_losses = 0
        
        current_balance += pnl
        daily_loss_pct = (daily_loss / initial_balance * 100)
        
        print(f"  余额: ${current_balance:,.2f}")
        print(f"  连续亏损: {consecutive_losses} 次")
        print(f"  当日亏损: ${daily_loss:.2f} ({daily_loss_pct:.2f}%)")
        
        # 检查风险限制
        if consecutive_losses >= limits.max_consecutive_losses:
            print(f"  🚫 触发限制: 连续亏损 {consecutive_losses} 次")
            print(f"  ⏰ 进入冷却期 {limits.cooldown_after_limit} 分钟")
            break
        
        if daily_loss_pct >= limits.max_daily_loss_pct:
            print(f"  🚫 触发限制: 日亏损 {daily_loss_pct:.2f}%")
            break
        
        if daily_loss >= limits.max_daily_loss_amount:
            print(f"  🚫 触发限制: 日亏损金额 ${daily_loss:.2f}")
            break
    
    print()
    print("─" * 70)
    print()

def demo_database():
    """演示数据库功能"""
    print("=" * 70)
    print("【演示 3】 数据库记录系统")
    print("=" * 70)
    print()
    
    print("💾 数据库表结构:")
    print("  1. trades - 交易记录表")
    print("  2. orders - 订单记录表")
    print("  3. daily_stats - 每日统计表")
    print("  4. signals - 信号记录表")
    print("  5. risk_events - 风险事件表")
    print()
    
    # 模拟记录交易
    print("📝 模拟记录交易:")
    
    # 记录信号
    signal_id = trading_db.record_signal(
        symbol='BTC/USDT',
        signal_type='LONG',
        entry_price=42000,
        stop_loss=41000,
        take_profit=[43000, 44000, 45000],
        leverage=10,
        raw_message="LONG BTC/USDT @ 42000"
    )
    print(f"  ✓ 信号已记录: ID={signal_id}")
    
    # 记录交易
    trade_id = trading_db.record_trade(
        account_name='测试账户',
        symbol='BTC/USDT',
        side='buy',
        entry_price=42000,
        position_size=0.1,
        leverage=10,
        stop_loss=41000,
        take_profit=[43000, 44000, 45000],
        trailing_stop_pct=2.0,
        notes="演示交易"
    )
    print(f"  ✓ 交易已记录: ID={trade_id}")
    
    # 模拟平仓
    trading_db.close_trade(trade_id, exit_price=43500, fees=5.0)
    print(f"  ✓ 交易已平仓: 出场价 $43,500, 手续费 $5")
    
    # 记录风险事件
    trading_db.record_risk_event(
        account_name='测试账户',
        event_type='PROFIT_TARGET',
        description='达到止盈目标',
        severity='INFO'
    )
    print(f"  ✓ 风险事件已记录")
    print()
    
    # 查询统计
    print("📊 查询统计:")
    summary = trading_db.get_summary_stats('测试账户')
    print(f"  总交易: {summary['total_trades']}")
    print(f"  胜率: {summary['win_rate']:.2f}%")
    print(f"  总盈亏: {summary['total_pnl']:.2f} USDT")
    print()
    
    print("─" * 70)
    print()

def demo_statistics():
    """演示统计分析"""
    print("=" * 70)
    print("【演示 4】 统计分析系统")
    print("=" * 70)
    print()
    
    # 生成报告
    print("📈 生成交易报告:")
    try:
        report = trading_stats.generate_report('测试账户', days=30)
        print(report)
    except:
        print("  (需要有实际交易数据)")
    
    print()
    
    # 盈亏曲线
    print("📉 盈亏曲线数据:")
    curve = trading_stats.generate_pnl_curve('测试账户')
    if curve:
        print(f"  数据点数: {len(curve)}")
        print(f"  最新盈亏: {curve[-1]['cumulative_pnl']:.2f} USDT")
    else:
        print("  (需要有实际交易数据)")
    
    print()
    
    # 按交易对统计
    print("🎯 按交易对统计:")
    symbol_stats = trading_stats.get_symbol_performance('测试账户')
    if symbol_stats:
        for symbol, stats in list(symbol_stats.items())[:3]:
            print(f"  {symbol}:")
            print(f"    交易次数: {stats['total_trades']}")
            print(f"    胜率: {stats['win_rate']:.2f}%")
            print(f"    总盈亏: {stats['total_pnl']:.2f} USDT")
    else:
        print("  (需要有实际交易数据)")
    
    print()
    print("─" * 70)
    print()

def main():
    """主函数"""
    print()
    print("🚀 高级功能完整演示")
    print()
    
    # 演示 1: 交易计划
    demo_trade_plan()
    
    # 演示 2: 风控管理
    demo_risk_manager()
    
    # 演示 3: 数据库
    demo_database()
    
    # 演示 4: 统计分析
    demo_statistics()
    
    print("=" * 70)
    print("✅ 演示完成！")
    print()
    print("💡 功能总结:")
    print("  ✓ 自动 TP/SL 订单")
    print("  ✓ 分批止盈（TP1, TP2, TP3）")
    print("  ✓ 追踪止损（Trailing Stop）")
    print("  ✓ 移动止损到成本价")
    print("  ✓ 最大亏损限制")
    print("  ✓ 连续亏损保护")
    print("  ✓ SQLite 数据库记录")
    print("  ✓ 完整统计分析")
    print()
    print("📚 详细文档: 高级功能使用指南.md")
    print("=" * 70)

if __name__ == "__main__":
    main()

