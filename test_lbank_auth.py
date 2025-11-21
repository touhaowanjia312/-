#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LBANK API 认证诊断脚本
测试不同的配置和认证方式
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import ccxt
import json
from multi_exchange_config import multi_exchange_config

def test_lbank_connection():
    """测试LBANK连接和认证"""
    
    print("=" * 80)
    print("LBANK API 认证诊断")
    print("=" * 80)
    
    # 从配置文件加载LBANK账户
    accounts = multi_exchange_config.get_enabled_accounts()
    lbank_account = None
    
    for account in accounts:
        if account.exchange_type.lower() == 'lbank':
            lbank_account = account
            break
    
    if not lbank_account:
        print("❌ 配置文件中没有找到LBANK账户")
        return
    
    print(f"\n📋 账户信息:")
    print(f"  名称: {lbank_account.name}")
    print(f"  API Key: {lbank_account.api_key[:10]}...")
    print(f"  Secret: {lbank_account.api_secret[:10]}...")
    print(f"  启用状态: {lbank_account.enabled}")
    print(f"  杠杆: {lbank_account.default_leverage}x")
    
    # 测试1: 基础配置
    print("\n" + "=" * 80)
    print("测试 1: 基础配置 (defaultType: future)")
    print("=" * 80)
    
    try:
        config1 = {
            'apiKey': lbank_account.api_key.strip(),
            'secret': lbank_account.api_secret.strip(),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        }
        
        lbank1 = ccxt.lbank(config1)
        print(f"✓ 客户端创建成功")
        
        # 加载市场
        markets = lbank1.load_markets()
        print(f"✓ 市场加载成功，共 {len(markets)} 个交易对")
        
        # 获取余额
        balance = lbank1.fetch_balance()
        print(f"✓ 余额获取成功")
        print(f"  USDT余额: {balance.get('USDT', {}).get('free', 0)}")
        
        # 尝试获取持仓
        try:
            positions = lbank1.fetch_positions()
            print(f"✓ 持仓获取成功，共 {len(positions)} 个持仓")
        except Exception as e:
            print(f"⚠ 持仓获取失败: {e}")
        
    except Exception as e:
        print(f"❌ 测试1失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试2: 无defaultType
    print("\n" + "=" * 80)
    print("测试 2: 无defaultType选项")
    print("=" * 80)
    
    try:
        config2 = {
            'apiKey': lbank_account.api_key.strip(),
            'secret': lbank_account.api_secret.strip(),
            'enableRateLimit': True,
        }
        
        lbank2 = ccxt.lbank(config2)
        print(f"✓ 客户端创建成功")
        
        # 加载市场
        markets = lbank2.load_markets()
        print(f"✓ 市场加载成功，共 {len(markets)} 个交易对")
        
        # 获取余额
        balance = lbank2.fetch_balance()
        print(f"✓ 余额获取成功")
        print(f"  USDT余额: {balance.get('USDT', {}).get('free', 0)}")
        
    except Exception as e:
        print(f"❌ 测试2失败: {e}")
    
    # 测试3: 指定合约URL
    print("\n" + "=" * 80)
    print("测试 3: 指定合约API URL")
    print("=" * 80)
    
    try:
        config3 = {
            'apiKey': lbank_account.api_key.strip(),
            'secret': lbank_account.api_secret.strip(),
            'enableRateLimit': True,
            'urls': {
                'api': {
                    'public': 'https://www.lbkex.net/v2',
                    'private': 'https://www.lbkex.net/v2',
                }
            },
            'options': {
                'defaultType': 'future',
            }
        }
        
        lbank3 = ccxt.lbank(config3)
        print(f"✓ 客户端创建成功")
        
        # 加载市场
        markets = lbank3.load_markets()
        print(f"✓ 市场加载成功，共 {len(markets)} 个交易对")
        
        # 获取余额
        balance = lbank3.fetch_balance()
        print(f"✓ 余额获取成功")
        print(f"  USDT余额: {balance.get('USDT', {}).get('free', 0)}")
        
    except Exception as e:
        print(f"❌ 测试3失败: {e}")
    
    # 测试4: 测试下单（小额）
    print("\n" + "=" * 80)
    print("测试 4: 测试下单 (XNY/USDT:USDT 做多)")
    print("=" * 80)
    
    try:
        # 使用测试1的客户端
        lbank_test = ccxt.lbank({
            'apiKey': lbank_account.api_key.strip(),
            'secret': lbank_account.api_secret.strip(),
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            }
        })
        
        lbank_test.load_markets()
        
        # 检查是否有XNY/USDT:USDT
        test_symbol = 'XNY/USDT:USDT'
        if test_symbol in lbank_test.markets:
            print(f"✓ 找到交易对: {test_symbol}")
            
            # 获取当前价格
            ticker = lbank_test.fetch_ticker(test_symbol)
            current_price = ticker['last']
            print(f"  当前价格: {current_price}")
            
            # 获取市场信息
            market = lbank_test.market(test_symbol)
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
            print(f"  最小数量: {min_amount}")
            
            # 计算小额测试数量
            test_amount = max(min_amount, 10)  # 至少10个币
            test_cost = test_amount * current_price
            print(f"  测试数量: {test_amount} 个 (约 {test_cost:.4f} USDT)")
            
            # 注意：这里只是打印信息，不实际下单
            print(f"\n⚠️  如果要测试下单，需要执行:")
            print(f"  order = lbank_test.create_market_order('{test_symbol}', 'buy', {test_amount})")
            
        else:
            print(f"❌ 未找到交易对: {test_symbol}")
            print(f"可用的USDT永续合约:")
            usdt_perps = [s for s in lbank_test.markets.keys() if ':USDT' in s]
            for s in usdt_perps[:10]:
                print(f"  - {s}")
        
    except Exception as e:
        print(f"❌ 测试4失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试5: 检查API权限
    print("\n" + "=" * 80)
    print("测试 5: 检查API权限")
    print("=" * 80)
    
    try:
        lbank_perm = ccxt.lbank({
            'apiKey': lbank_account.api_key.strip(),
            'secret': lbank_account.api_secret.strip(),
            'enableRateLimit': True,
        })
        
        lbank_perm.load_markets()
        
        print("尝试各种API调用来检测权限:")
        
        # 1. 账户信息
        try:
            balance = lbank_perm.fetch_balance()
            print("  ✓ fetch_balance() - 读取余额权限正常")
        except Exception as e:
            print(f"  ❌ fetch_balance() - {e}")
        
        # 2. 持仓信息
        try:
            positions = lbank_perm.fetch_positions()
            print("  ✓ fetch_positions() - 读取持仓权限正常")
        except Exception as e:
            print(f"  ❌ fetch_positions() - {e}")
        
        # 3. 订单历史
        try:
            orders = lbank_perm.fetch_orders()
            print("  ✓ fetch_orders() - 读取订单权限正常")
        except Exception as e:
            print(f"  ❌ fetch_orders() - {e}")
        
        # 4. 当前委托
        try:
            open_orders = lbank_perm.fetch_open_orders()
            print("  ✓ fetch_open_orders() - 读取当前委托权限正常")
        except Exception as e:
            print(f"  ❌ fetch_open_orders() - {e}")
        
    except Exception as e:
        print(f"❌ 测试5失败: {e}")
    
    print("\n" + "=" * 80)
    print("诊断完成")
    print("=" * 80)

if __name__ == '__main__':
    test_lbank_connection()

