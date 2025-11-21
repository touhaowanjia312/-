"""
测试市价单信号解析
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from signal_parser import SignalParser

def test_market_order_signals():
    """测试各种市价单格式"""
    
    parser = SignalParser()
    
    test_cases = [
        # 测试1：图片中的实际信号
        {
            'name': '实际信号 - MDT市价空',
            'message': '''#MDT 市價空
第一止盈：0.01972'''
        },
        
        # 测试2：变体1 - 有多个止盈
        {
            'name': 'MDT市价空 - 多个止盈',
            'message': '''#MDT 市價空
第一止盈：0.01972
第二止盈：0.01950
第三止盈：0.01920'''
        },
        
        # 测试3：市价多单
        {
            'name': 'BTC市价多',
            'message': '''#BTC 市价做多
第一止盈：43000
第二止盈：44000'''
        },
        
        # 测试4：只有交易对和方向
        {
            'name': 'ETH纯市价',
            'message': '''ETH 市價多'''
        },
        
        # 测试5：带止损的市价单
        {
            'name': 'SOL市价 + 止损',
            'message': '''SOL 市价空
第一止盈：95.5
止损：105'''
        },
        
        # 测试6：繁体中文格式
        {
            'name': '繁体格式',
            'message': '''#DOGE 市價空
第一止盈：0.085
第二止盈：0.082'''
        }
    ]
    
    print("=" * 60)
    print("测试市价单信号解析")
    print("=" * 60)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n📝 测试 {i}: {test['name']}")
        print("-" * 60)
        print(f"原始信号：")
        print(test['message'])
        print()
        
        signal = parser.parse(test['message'])
        
        if signal:
            print("✅ 解析成功！")
            print(f"  交易对: {signal.symbol}")
            print(f"  方向: {signal.signal_type.value}")
            print(f"  入场价: {signal.entry_price if signal.entry_price else '市价'}")
            print(f"  止损: {signal.stop_loss if signal.stop_loss else '无'}")
            print(f"  止盈: {signal.take_profit if signal.take_profit else '无'}")
            print(f"  杠杆: {signal.leverage if signal.leverage else '默认'}")
            
            # 模拟智能订单管理器处理
            print("\n🎯 智能订单计划:")
            if signal.take_profit:
                print(f"  ✓ 使用信号止盈: {signal.take_profit}")
                print(f"  ✓ 信号TP占60%仓位")
                print(f"  ✓ 额外TP将自动添加（占40%仓位）")
            else:
                print(f"  ✓ 无信号止盈，使用默认TP配置")
            
            if signal.stop_loss:
                print(f"  ✓ 使用信号止损: {signal.stop_loss}")
            else:
                print(f"  ✓ 无信号止损，使用默认止损%")
            
            if not signal.entry_price:
                print(f"  ✓ 市价订单 - 立即执行")
        else:
            print("❌ 解析失败")
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    test_market_order_signals()

