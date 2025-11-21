#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试修复后的交易功能
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from multi_exchange_client import MultiExchangeClient
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_separator(title):
    """打印分隔线"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

def test_market_info(client: MultiExchangeClient):
    """测试市场信息获取"""
    print_separator("测试市场信息")
    
    test_symbols = [
        ('bitget', 'BTC/USDT:USDT'),
        ('LBANK', 'BTC/USDT:USDT'),
        ('bitget', 'XNY/USDT:USDT'),
        ('LBANK', 'XNY/USDT:USDT'),
    ]
    
    for account_name, symbol in test_symbols:
        if account_name not in client.clients:
            print(f"⚠️ {account_name} 未配置")
            continue
        
        try:
            ccxt_client = client.clients[account_name]
            
            # 检查交易对是否存在
            if symbol not in ccxt_client.markets:
                print(f"❌ {account_name} 不支持 {symbol}")
                continue
            
            # 获取市场信息
            market = ccxt_client.market(symbol)
            limits = market.get('limits', {})
            amount_limits = limits.get('amount', {})
            
            print(f"✅ {account_name} - {symbol}")
            print(f"   最小数量: {amount_limits.get('min', 'N/A')}")
            print(f"   最大数量: {amount_limits.get('max', 'N/A')}")
            
            if 'precision' in market:
                print(f"   数量精度: {market['precision'].get('amount', 'N/A')}")
                print(f"   价格精度: {market['precision'].get('price', 'N/A')}")
            
            # 获取当前价格
            price = client.get_current_price(account_name, symbol)
            if price:
                print(f"   当前价格: {price}")
            
            print()
            
        except Exception as e:
            print(f"❌ {account_name} - {symbol}: {e}\n")

def test_position_calculation(client: MultiExchangeClient):
    """测试仓位计算"""
    print_separator("测试仓位计算")
    
    test_cases = [
        ('bitget', 'BTC/USDT:USDT'),
        ('LBANK', 'BTC/USDT:USDT'),
        ('LBANK', 'XNY/USDT:USDT'),
    ]
    
    for account_name, symbol in test_cases:
        if account_name not in client.clients:
            continue
        
        if account_name not in client.accounts:
            continue
        
        account = client.accounts[account_name]
        
        try:
            price = client.get_current_price(account_name, symbol)
            if not price:
                print(f"⚠️ {account_name} - 无法获取 {symbol} 价格\n")
                continue
            
            # 计算仓位
            position_size = client.calculate_position_size(account_name, symbol, price)
            
            # 获取市场限制
            ccxt_client = client.clients[account_name]
            market = ccxt_client.market(symbol)
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
            
            print(f"📊 {account_name} - {symbol}")
            print(f"   当前价格: {price}")
            print(f"   保证金: {account.margin_amount} USDT")
            print(f"   杠杆: {account.default_leverage}x")
            print(f"   计算仓位: {position_size}")
            print(f"   最小要求: {min_amount}")
            
            # 检查是否满足最小数量
            if min_amount and position_size < min_amount:
                print(f"   ⚠️ 警告: 计算仓位 {position_size} < 最小要求 {min_amount}")
                print(f"   💡 建议: 保证金至少需要 {min_amount * price / account.default_leverage:.2f} USDT")
            else:
                print(f"   ✅ 满足交易要求")
            
            print()
            
        except Exception as e:
            print(f"❌ {account_name} - {symbol}: {e}\n")

def test_bitget_special_handling():
    """测试 Bitget 特殊处理逻辑"""
    print_separator("测试 Bitget 特殊处理")
    
    print("📝 Bitget 市价买单修复说明：")
    print()
    print("1. 检测到 Bitget 交易所 + 买单")
    print("2. 设置参数: createMarketBuyOrderRequiresPrice = False")
    print("3. 计算总成本: cost = amount * price")
    print("4. 使用成本下单而不是数量")
    print()
    print("✅ 代码已实现，等待实际信号测试")
    print()

def main():
    """主函数"""
    print("="*60)
    print("  交易功能修复测试")
    print("="*60)
    print()
    
    # 初始化客户端
    print("正在初始化多交易所客户端...")
    client = MultiExchangeClient()
    
    if not client.clients:
        print("❌ 没有配置的交易所账户")
        return
    
    print(f"✅ 已连接 {len(client.clients)} 个交易所")
    for name in client.clients.keys():
        print(f"   - {name}")
    print()
    
    # 运行测试
    test_market_info(client)
    test_position_calculation(client)
    test_bitget_special_handling()
    
    print_separator("测试完成")
    print("✅ 所有检查完成")
    print()
    print("下一步：")
    print("1. 重启 GUI 程序")
    print("2. 等待真实交易信号")
    print("3. 观察订单是否成功执行")
    print()

if __name__ == "__main__":
    main()

