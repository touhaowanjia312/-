#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 LBANK 合约余额获取
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from multi_exchange_config import multi_exchange_config
from multi_exchange_client import MultiExchangeClient

def test_lbank_futures():
    """测试 LBANK 合约余额获取"""
    print("="*60)
    print("LBANK 合约余额测试")
    print("="*60)
    
    # 加载账户配置
    accounts = multi_exchange_config.get_enabled_accounts()
    
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
    
    try:
        ccxt_client = client.clients[lbank_account.name]
        
        print("\n" + "="*60)
        print("测试不同类型的余额")
        print("="*60)
        
        # 1. 现货余额
        print("\n1️⃣ 现货余额 (Spot):")
        try:
            spot_balance = ccxt_client.fetch_balance()
            if 'USDT' in spot_balance.get('free', {}):
                print(f"  USDT: {spot_balance['free']['USDT']}")
            else:
                print("  无 USDT 现货余额")
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")
        
        # 2. 合约余额 - 方式1
        print("\n2️⃣ 合约余额 (Swap/Futures) - 方式1:")
        try:
            futures_balance = ccxt_client.fetch_balance({'type': 'swap'})
            print(json.dumps(futures_balance, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")
        
        # 3. 合约余额 - 方式2
        print("\n3️⃣ 合约余额 - 方式2 (futures):")
        try:
            futures_balance = ccxt_client.fetch_balance({'type': 'future'})
            print(json.dumps(futures_balance, indent=2, ensure_ascii=False))
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")
        
        # 4. 检查市场类型
        print("\n4️⃣ 检查支持的市场类型:")
        print(f"  has['spot']: {ccxt_client.has.get('spot', False)}")
        print(f"  has['margin']: {ccxt_client.has.get('margin', False)}")
        print(f"  has['swap']: {ccxt_client.has.get('swap', False)}")
        print(f"  has['future']: {ccxt_client.has.get('future', False)}")
        
        # 5. 获取所有余额（不指定类型）
        print("\n5️⃣ 所有账户余额:")
        try:
            all_balance = ccxt_client.fetch_balance()
            print(f"  账户类型: {all_balance.get('info', {}).get('account_type', 'unknown')}")
            for currency, amount in all_balance.get('free', {}).items():
                if amount and float(amount) > 0:
                    print(f"  {currency}: {amount}")
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")
        
        # 6. 尝试获取持仓
        print("\n6️⃣ 获取持仓信息:")
        try:
            positions = ccxt_client.fetch_positions()
            print(f"  持仓数量: {len(positions)}")
            if positions:
                print(json.dumps(positions, indent=2, ensure_ascii=False))
            else:
                print("  无持仓")
        except Exception as e:
            print(f"  ✗ 获取失败: {e}")
            
    except Exception as e:
        print(f"\n✗ 错误: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

if __name__ == '__main__':
    test_lbank_futures()

