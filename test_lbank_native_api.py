#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
直接调用 LBANK 原生 API 获取合约余额
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import time
import hashlib
import hmac
import requests
from urllib.parse import urlencode

def test_lbank_native_api():
    """使用 LBANK 原生 API 获取合约余额"""
    
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
    print("LBANK 原生 API 测试")
    print("="*60)
    print(f"\n账户名: {lbank_account.name}")
    
    api_key = lbank_account.api_key
    api_secret = lbank_account.api_secret
    
    # LBANK API 基础URL
    base_url = "https://www.lbkex.net"
    
    def sign_request(params, secret):
        """生成 LBANK API 签名"""
        # 排序参数
        sorted_params = sorted(params.items())
        # 生成查询字符串
        query_string = urlencode(sorted_params)
        # 使用 MD5 签名
        sign_str = hashlib.md5((query_string + f"&secret_key={secret}").encode()).hexdigest().upper()
        return sign_str
    
    print("\n" + "="*60)
    print("1️⃣ 获取现货账户余额")
    print("="*60)
    try:
        endpoint = "/v2/supplement/user_info_account.do"
        params = {
            'api_key': api_key,
            'timestamp': str(int(time.time() * 1000))
        }
        params['sign'] = sign_request(params, api_secret)
        
        response = requests.post(base_url + endpoint, data=params, timeout=10)
        data = response.json()
        
        print(f"响应状态: {response.status_code}")
        print(f"响应数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("2️⃣ 获取合约账户资产")
    print("="*60)
    try:
        # LBANK 合约API可能使用不同的端点
        endpoint = "/v2/supplement/customer_trade_fee.do"
        params = {
            'api_key': api_key,
            'timestamp': str(int(time.time() * 1000))
        }
        params['sign'] = sign_request(params, api_secret)
        
        response = requests.post(base_url + endpoint, data=params, timeout=10)
        data = response.json()
        
        print(f"响应状态: {response.status_code}")
        print(f"响应数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("3️⃣ 尝试获取所有账户资产 (asset)")
    print("="*60)
    try:
        endpoint = "/v2/supplement/asset_detail.do"
        params = {
            'api_key': api_key,
            'timestamp': str(int(time.time() * 1000))
        }
        params['sign'] = sign_request(params, api_secret)
        
        response = requests.post(base_url + endpoint, data=params, timeout=10)
        data = response.json()
        
        print(f"响应状态: {response.status_code}")
        print(f"响应数据:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("4️⃣ 查看 CCXT 的原始请求")
    print("="*60)
    try:
        import ccxt
        exchange = ccxt.lbank({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'verbose': True  # 开启详细日志
        })
        
        # 查看 CCXT 使用的 URL
        print(f"\nCCXT URLs:")
        if hasattr(exchange, 'urls'):
            print(json.dumps(exchange.urls, indent=2, ensure_ascii=False))
        
        # 查看 API 配置
        print(f"\nCCXT API:")
        if hasattr(exchange, 'api'):
            for key, value in exchange.api.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for k, v in value.items():
                        if 'balance' in k.lower() or 'account' in k.lower():
                            print(f"    {k}: {v}")
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    
    print("\n提示：")
    print("如果您知道 LBANK 网页上显示的合约余额是多少，")
    print("请告诉我具体数值，这样我可以帮您找到正确的 API 接口。")

if __name__ == '__main__':
    test_lbank_native_api()

