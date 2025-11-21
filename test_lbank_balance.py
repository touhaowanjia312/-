#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 LBANK 余额获取
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from multi_exchange_config import multi_exchange_config
from multi_exchange_client import MultiExchangeClient

def test_lbank_balance():
    """测试 LBANK 余额获取"""
    print("="*60)
    print("LBANK 余额测试")
    print("="*60)
    
    # 加载账户配置
    accounts = multi_exchange_config.get_enabled_accounts()
    print(f"\n✓ 加载了 {len(accounts)} 个账户配置")
    
    # 找到 LBANK 账户
    lbank_account = None
    for account in accounts:
        if 'lbank' in account.exchange_type.lower():
            lbank_account = account
            break
    
    if not lbank_account:
        print("✗ 未找到 LBANK 账户配置")
        return
    
    print(f"\n✓ 找到 LBANK 账户: {lbank_account.name}")
    
    # 初始化客户端
    client = MultiExchangeClient()
    for account in accounts:
        client.add_exchange(account)
    
    print(f"\n✓ 已初始化 {len(client.clients)} 个交易所客户端")
    
    # 测试获取余额
    if lbank_account.name not in client.clients:
        print(f"✗ LBANK 客户端未初始化")
        return
    
    print(f"\n{'='*60}")
    print("开始获取 LBANK 余额...")
    print(f"{'='*60}")
    
    try:
        ccxt_client = client.clients[lbank_account.name]
        
        # 1. 获取原始余额数据
        print("\n1️⃣ 原始余额数据:")
        balance_data = ccxt_client.fetch_balance()
        print(json.dumps(balance_data, indent=2, ensure_ascii=False))
        
        # 2. 检查 free 字段
        print("\n2️⃣ Free 余额:")
        if 'free' in balance_data:
            print(json.dumps(balance_data['free'], indent=2, ensure_ascii=False))
        else:
            print("✗ 没有 'free' 字段")
        
        # 3. 检查 USDT
        print("\n3️⃣ USDT 余额:")
        usdt_balance = balance_data['free'].get('USDT', None)
        print(f"USDT: {usdt_balance}")
        
        # 4. 检查所有非零余额
        print("\n4️⃣ 所有非零余额:")
        if 'free' in balance_data:
            for currency, amount in balance_data['free'].items():
                if amount and float(amount) > 0:
                    print(f"  {currency}: {amount}")
        
        # 5. 使用 MultiExchangeClient 的方法
        print("\n5️⃣ 使用 get_balance 方法:")
        balance = client.get_balance(lbank_account.name, 'USDT')
        print(f"USDT 余额: {balance}")
        
        # 6. 获取所有余额
        print("\n6️⃣ 获取所有账户余额:")
        all_balances = client.get_all_balances()
        print(json.dumps(all_balances, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

if __name__ == '__main__':
    test_lbank_balance()

