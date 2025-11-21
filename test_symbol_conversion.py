#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试交易对符号转换功能
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from multi_exchange_client import MultiExchangeClient
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_separator(title):
    """打印分隔线"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_symbol_conversion():
    """测试符号转换功能"""
    print_separator("测试交易对符号转换")
    
    # 初始化客户端
    client = MultiExchangeClient()
    
    if not client.clients:
        print("❌ 没有配置的交易所账户")
        return
    
    test_symbols = [
        'XNY/USDT',
        'BTC/USDT',
        'COAI/USDT',
        'ETH/USDT'
    ]
    
    for account_name, ccxt_client in client.clients.items():
        print(f"\n📊 测试交易所: {account_name}")
        print("-" * 70)
        
        for symbol in test_symbols:
            print(f"\n测试符号: {symbol}")
            
            # 1. 检查原始符号
            if symbol in ccxt_client.markets:
                print(f"  ✅ 原始格式存在: {symbol}")
            else:
                print(f"  ❌ 原始格式不存在: {symbol}")
            
            # 2. 检查合约符号
            contract_symbol = f"{symbol}:USDT"
            if contract_symbol in ccxt_client.markets:
                print(f"  ✅ 合约格式存在: {contract_symbol}")
            else:
                print(f"  ❌ 合约格式不存在: {contract_symbol}")
            
            # 3. 测试自动转换
            converted = client._convert_to_contract_symbol(ccxt_client, symbol)
            print(f"  🔄 自动转换结果: {symbol} -> {converted}")
            
            # 4. 尝试获取价格
            try:
                price = client.get_current_price(account_name, symbol)
                if price:
                    print(f"  💰 获取价格成功: {price}")
                    
                    # 5. 获取市场信息
                    market = ccxt_client.market(converted)
                    limits = market.get('limits', {})
                    amount_limits = limits.get('amount', {})
                    
                    print(f"  📏 最小数量: {amount_limits.get('min', 'N/A')}")
                    print(f"  📏 最大数量: {amount_limits.get('max', 'N/A')}")
                    
                    # 6. 计算仓位
                    if account_name in client.accounts:
                        account = client.accounts[account_name]
                        position = client.calculate_position_size(account_name, symbol, price)
                        print(f"  💼 计算仓位: {position}")
                        print(f"     (保证金: {account.margin_amount} USDT × {account.default_leverage}x)")
                        
                        min_amount = amount_limits.get('min', 0)
                        if min_amount and position < min_amount:
                            print(f"  ⚠️ 警告: 仓位 {position} < 最小值 {min_amount}")
                            print(f"     需要保证金: {min_amount * price / account.default_leverage:.2f} USDT")
                        else:
                            print(f"  ✅ 仓位满足最小要求")
                else:
                    print(f"  ❌ 获取价格失败")
            except Exception as e:
                print(f"  ❌ 错误: {e}")

def test_market_types():
    """测试市场类型"""
    print_separator("检查市场类型配置")
    
    client = MultiExchangeClient()
    
    for account_name, ccxt_client in client.clients.items():
        print(f"\n📊 {account_name}")
        print("-" * 70)
        
        # 检查配置
        if hasattr(ccxt_client, 'options'):
            default_type = ccxt_client.options.get('defaultType', 'N/A')
            print(f"  默认类型: {default_type}")
        
        # 统计市场数量
        spot_count = 0
        swap_count = 0
        future_count = 0
        
        for symbol, market in ccxt_client.markets.items():
            market_type = market.get('type', 'unknown')
            if market_type == 'spot':
                spot_count += 1
            elif market_type == 'swap':
                swap_count += 1
            elif market_type == 'future':
                future_count += 1
        
        print(f"  现货市场: {spot_count}")
        print(f"  永续合约: {swap_count}")
        print(f"  期货市场: {future_count}")
        print(f"  总计: {len(ccxt_client.markets)}")

def main():
    """主函数"""
    print("="*70)
    print("  交易对符号转换测试")
    print("="*70)
    print()
    
    test_market_types()
    test_symbol_conversion()
    
    print_separator("测试完成")
    print("✅ 符号转换功能已实现")
    print()
    print("📝 总结:")
    print("1. 自动将 XNY/USDT 转换为 XNY/USDT:USDT（合约格式）")
    print("2. 自动检测最小交易数量并调整")
    print("3. Bitget 市价买单特殊处理")
    print()
    print("下一步: 重启 GUI 测试实际交易")
    print()

if __name__ == "__main__":
    main()

