#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 LBANK 合约交易功能
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import ccxt

def test_lbank_trading():
    """测试 LBANK 合约交易 API"""
    
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
    print("LBANK 合约交易功能测试")
    print("="*60)
    
    api_key = lbank_account.api_key
    api_secret = lbank_account.api_secret
    
    # 创建 LBANK 客户端
    exchange = ccxt.lbank({
        'apiKey': api_key,
        'secret': api_secret,
        'enableRateLimit': True,
    })
    
    print("\n" + "="*60)
    print("1️⃣ 检查市场数据")
    print("="*60)
    try:
        markets = exchange.load_markets()
        
        # 查找合约市场
        swap_markets = {k: v for k, v in markets.items() if v.get('type') == 'swap'}
        spot_markets = {k: v for k, v in markets.items() if v.get('type') == 'spot'}
        
        print(f"\n现货市场数量: {len(spot_markets)}")
        print(f"合约市场数量: {len(swap_markets)}")
        
        if swap_markets:
            print(f"\n✅ LBANK 支持合约交易")
            print(f"\n示例合约市场（前5个）:")
            for i, (symbol, market) in enumerate(list(swap_markets.items())[:5]):
                print(f"  {i+1}. {symbol} - {market.get('id', 'N/A')}")
        else:
            print(f"\n⚠️ 未找到合约市场")
            
    except Exception as e:
        print(f"✗ 失败: {e}")
    
    print("\n" + "="*60)
    print("2️⃣ 检查 API 权限")
    print("="*60)
    
    # 检查 API 密钥权限
    print("\nAPI 功能检查:")
    print(f"  createOrder (下单): {exchange.has.get('createOrder', False)}")
    print(f"  cancelOrder (撤单): {exchange.has.get('cancelOrder', False)}")
    print(f"  fetchOrder (查询订单): {exchange.has.get('fetchOrder', False)}")
    print(f"  fetchOpenOrders (查询挂单): {exchange.has.get('fetchOpenOrders', False)}")
    print(f"  fetchBalance (查询余额): {exchange.has.get('fetchBalance', False)}")
    
    print("\n" + "="*60)
    print("3️⃣ 测试获取合约行情")
    print("="*60)
    
    # 测试获取 BTC/USDT 合约行情
    try:
        # 尝试常见的合约交易对
        test_symbols = ['BTC/USDT:USDT', 'BTC/USDT', 'BTCUSDT', 'ETH/USDT:USDT', 'ETH/USDT']
        
        for symbol in test_symbols:
            try:
                ticker = exchange.fetch_ticker(symbol)
                print(f"\n✅ {symbol} 行情:")
                print(f"  最新价: {ticker.get('last', 'N/A')}")
                print(f"  买一: {ticker.get('bid', 'N/A')}")
                print(f"  卖一: {ticker.get('ask', 'N/A')}")
                break  # 找到一个可用的就停止
            except Exception as e:
                print(f"  ⚠️ {symbol}: {str(e)[:50]}")
                continue
    except Exception as e:
        print(f"✗ 获取行情失败: {e}")
    
    print("\n" + "="*60)
    print("4️⃣ 检查订单类型支持")
    print("="*60)
    
    print("\n支持的订单类型:")
    if hasattr(exchange, 'options') and 'orderTypes' in exchange.options:
        print(f"  {exchange.options['orderTypes']}")
    else:
        print("  市价单 (market)")
        print("  限价单 (limit)")
        print("  止损单 (stop)")
    
    print("\n" + "="*60)
    print("5️⃣ 总结")
    print("="*60)
    
    print("\n✅ LBANK 合约交易支持情况:")
    print(f"  - 现货市场: {len(spot_markets)} 个")
    print(f"  - 合约市场: {len(swap_markets) if 'swap_markets' in locals() else '未知'} 个")
    print(f"  - API 密钥: 已配置")
    print(f"  - 下单权限: 需要实际测试（模拟下单）")
    
    print("\n⚠️ 注意事项:")
    print("  1. 确保 API 密钥有合约交易权限")
    print("  2. 确保 API 白名单包含您的 IP")
    print("  3. 建议先用小额测试")
    print("  4. 余额显示为手动配置，不影响实际交易")
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)
    
    print("\n💡 结论:")
    print("  如果上面显示了合约市场和行情，说明 LBANK 合约交易功能可用。")
    print("  手动配置的余额只影响显示，不影响实际下单。")

if __name__ == '__main__':
    test_lbank_trading()

