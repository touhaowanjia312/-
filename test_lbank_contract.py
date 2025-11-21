#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
深度测试 LBANK 合约余额
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import ccxt

def test_lbank_contract():
    """测试 LBANK 合约余额的各种获取方式"""
    
    # 从配置文件读取 LBANK 配置
    from multi_exchange_config import multi_exchange_config
    
    accounts = multi_exchange_config.get_enabled_accounts()
    lbank_account = None
    for account in accounts:
        if 'lbank' in account.exchange_type.lower():
            lbank_account = account
            break
    
    if not lbank_account:
        print("✗ 未找到 LBANK 账户配置")
        return
    
    print("="*60)
    print("LBANK 合约余额深度测试")
    print("="*60)
    print(f"\n账户名: {lbank_account.name}")
    print(f"测试网: {lbank_account.testnet}")
    
    # 初始化 LBANK 客户端
    exchange = ccxt.lbank({
        'apiKey': lbank_account.api_key,
        'secret': lbank_account.api_secret,
        'enableRateLimit': True,
    })
    
    if lbank_account.testnet:
        exchange.set_sandbox_mode(True)
    
    print("\n" + "="*60)
    print("1️⃣ 测试默认余额获取")
    print("="*60)
    try:
        balance = exchange.fetch_balance()
        print(f"\n账户类型: {balance.get('info', {}).get('account_type', 'unknown')}")
        print(f"\n所有非零余额:")
        for key in ['free', 'used', 'total']:
            if key in balance:
                for currency, amount in balance[key].items():
                    if amount and float(amount) > 0:
                        print(f"  {key}.{currency}: {amount}")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("2️⃣ 测试 params={'type': 'spot'}")
    print("="*60)
    try:
        spot_balance = exchange.fetch_balance({'type': 'spot'})
        print(f"\nUSDT 余额: {spot_balance.get('free', {}).get('USDT', 0)}")
        print(f"原始数据:")
        print(json.dumps(spot_balance.get('info', {}), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("3️⃣ 测试 params={'type': 'swap'}")
    print("="*60)
    try:
        swap_balance = exchange.fetch_balance({'type': 'swap'})
        print(f"\nUSDT 余额: {swap_balance.get('free', {}).get('USDT', 0)}")
        print(f"原始数据:")
        print(json.dumps(swap_balance.get('info', {}), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("4️⃣ 测试 params={'type': 'future'}")
    print("="*60)
    try:
        future_balance = exchange.fetch_balance({'type': 'future'})
        print(f"\nUSDT 余额: {future_balance.get('free', {}).get('USDT', 0)}")
        print(f"原始数据:")
        print(json.dumps(future_balance.get('info', {}), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("5️⃣ 测试 params={'type': 'contract'}")
    print("="*60)
    try:
        contract_balance = exchange.fetch_balance({'type': 'contract'})
        print(f"\nUSDT 余额: {contract_balance.get('free', {}).get('USDT', 0)}")
        print(f"原始数据:")
        print(json.dumps(contract_balance.get('info', {}), indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("6️⃣ 检查 CCXT 支持的选项")
    print("="*60)
    print(f"\nhas:")
    for key in ['spot', 'margin', 'swap', 'future', 'option']:
        print(f"  {key}: {exchange.has.get(key, 'undefined')}")
    
    print(f"\noptions:")
    if hasattr(exchange, 'options'):
        for key, value in exchange.options.items():
            if 'type' in key.lower() or 'account' in key.lower():
                print(f"  {key}: {value}")
    
    print("\n" + "="*60)
    print("7️⃣ 尝试直接调用 API (如果支持)")
    print("="*60)
    
    # 检查 LBANK 的市场类型
    try:
        markets = exchange.load_markets()
        market_types = set()
        for market_id, market in markets.items():
            if 'type' in market:
                market_types.add(market['type'])
        print(f"\n支持的市场类型: {market_types}")
    except Exception as e:
        print(f"✗ 获取市场失败: {e}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == '__main__':
    test_lbank_contract()

