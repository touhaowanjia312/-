#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试 LBANK 合约 API - 应该显示 10 USDT
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import ccxt

def debug_lbank():
    """调试 LBANK 合约余额获取"""
    
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
    print("LBANK 合约余额调试 - 期望显示 10 USDT")
    print("="*60)
    
    api_key = lbank_account.api_key
    api_secret = lbank_account.api_secret
    
    print("\n" + "="*60)
    print("1️⃣ 测试现货 API")
    print("="*60)
    try:
        spot_client = ccxt.lbank({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        print(f"现货 API URL: {spot_client.urls['api']['rest']}")
        balance = spot_client.fetch_balance()
        print(f"现货 USDT: {balance['free'].get('USDT', 0)}")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("2️⃣ 测试合约 API - 方法 1 (修改 defaultType)")
    print("="*60)
    try:
        contract_client_1 = ccxt.lbank({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'swap',
            }
        })
        
        print(f"API URL: {contract_client_1.urls['api']}")
        balance = contract_client_1.fetch_balance()
        print(f"合约 USDT: {balance['free'].get('USDT', 0)}")
        print(f"详细数据: {json.dumps(balance.get('info', {}), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("3️⃣ 测试合约 API - 方法 2 (直接设置 URL)")
    print("="*60)
    try:
        contract_client_2 = ccxt.lbank({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        # 直接修改 URL
        contract_client_2.urls['api']['rest'] = 'https://lbkperp.lbank.com'
        
        print(f"修改后的 API URL: {contract_client_2.urls['api']['rest']}")
        balance = contract_client_2.fetch_balance()
        print(f"合约 USDT: {balance['free'].get('USDT', 0)}")
        print(f"详细数据: {json.dumps(balance.get('info', {}), indent=2, ensure_ascii=False)}")
    except Exception as e:
        print(f"✗ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("4️⃣ 测试合约 API - 方法 3 (使用 params)")
    print("="*60)
    try:
        spot_client = ccxt.lbank({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
        })
        
        # 尝试使用 params 参数
        balance = spot_client.fetch_balance({'type': 'contract'})
        print(f"合约 USDT: {balance['free'].get('USDT', 0)}")
        print(f"详细数据: {json.dumps(balance.get('info', {}), indent=2, ensure_ascii=False)[:500]}")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("5️⃣ 检查 LBANK 的 API 配置")
    print("="*60)
    try:
        client = ccxt.lbank({
            'apiKey': api_key,
            'secret': api_secret,
        })
        
        print("URLs 配置:")
        print(json.dumps(client.urls, indent=2, ensure_ascii=False))
        
        print("\nOptions 配置:")
        if hasattr(client, 'options'):
            print(json.dumps(client.options, indent=2, ensure_ascii=False))
        
        print("\nAPI 端点:")
        if hasattr(client, 'api'):
            for section, endpoints in client.api.items():
                if isinstance(endpoints, dict):
                    for method, paths in endpoints.items():
                        if 'balance' in method.lower() or 'account' in method.lower():
                            print(f"  {section}.{method}: {paths}")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("6️⃣ 查看市场信息")
    print("="*60)
    try:
        client = ccxt.lbank({
            'apiKey': api_key,
            'secret': api_secret,
        })
        
        markets = client.load_markets()
        
        # 查找合约市场
        contract_markets = [m for m in markets.values() if m.get('type') == 'swap']
        spot_markets = [m for m in markets.values() if m.get('type') == 'spot']
        
        print(f"现货市场数量: {len(spot_markets)}")
        print(f"合约市场数量: {len(contract_markets)}")
        
        if contract_markets:
            print(f"\n示例合约市场:")
            print(json.dumps(contract_markets[0], indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("调试完成")
    print("="*60)

if __name__ == '__main__':
    debug_lbank()

