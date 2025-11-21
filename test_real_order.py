#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试实际下单 - 使用最小数量
"""

import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import ccxt
import json

print("=" * 70)
print("🧪 Bitget实际下单测试（最小数量）")
print("=" * 70)

# 加载配置
with open('exchanges_config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

bitget_config = None
for account in config['accounts']:
    if account['exchange_type'].lower() == 'bitget' and account['enabled']:
        bitget_config = account
        break

# 初始化客户端
client = ccxt.bitget({
    'apiKey': bitget_config['api_key'],
    'secret': bitget_config['api_secret'],
    'password': bitget_config['password'],
    'enableRateLimit': True,
    'options': {
        'defaultType': 'swap',
    }
})

client.load_markets()

symbol = 'TOWNS/USDT'
leverage = 20

# 获取当前价格
ticker = client.fetch_ticker(symbol)
current_price = ticker['last']
market = client.markets[symbol]

print(f"\n✅ 市场信息:")
print(f"  符号: {symbol}")
print(f"  当前价格: {current_price:.6f} USDT")
print(f"  最小金额: {market['limits']['cost']['min']} USDT")

# 计算最小可能的订单（满足5 USDT最小金额）
min_cost = 5.0  # Bitget最小
amount = (min_cost / current_price) * 1.1  # 多10%保险

# 精度处理
precision = market['precision']['amount']
if isinstance(precision, int):
    amount = round(amount, precision)
else:
    import decimal
    amount = float(decimal.Decimal(str(amount)).quantize(
        decimal.Decimal(str(precision)),
        rounding=decimal.ROUND_UP
    ))

print(f"\n📊 测试订单:")
print(f"  数量: {amount:.2f} TOWNS")
print(f"  价值: {amount * current_price:.2f} USDT")
print(f"  杠杆: {leverage}x")
print(f"  保证金: {(amount * current_price) / leverage:.2f} USDT")

# 设置杠杆
try:
    client.set_leverage(leverage, symbol, params={
        'marginCoin': 'USDT',
        'productType': 'USDT-FUTURES'
    })
    print(f"\n✅ 杠杆已设置: {leverage}x")
except Exception as e:
    print(f"\n⚠️ 杠杆设置: {e}")

# 测试1: 标准参数
print("\n" + "=" * 70)
print("测试1: 标准参数（当前程序使用）")
print("=" * 70)

params1 = {
    'marginCoin': 'USDT',
    'productType': 'USDT-FUTURES',
    'holdSide': 'short'
}

print(f"\n参数: {json.dumps(params1, ensure_ascii=False)}")
print(f"⚠️ 这将尝试实际下单！")
input("按Enter继续（或Ctrl+C取消）...")

try:
    order = client.create_market_order(symbol, 'sell', amount, params=params1)
    print(f"\n✅ 订单成功！")
    print(json.dumps(order, indent=2, ensure_ascii=False))
    
    # 立即平仓
    print(f"\n⚠️ 立即平仓...")
    close_params = {
        'marginCoin': 'USDT',
        'productType': 'USDT-FUTURES',
        'holdSide': 'short',
        'reduceOnly': True
    }
    close_order = client.create_market_order(symbol, 'buy', amount, params=close_params)
    print(f"✅ 已平仓")
    
except Exception as e:
    print(f"\n❌ 订单失败: {e}")
    print(f"\n详细错误:")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ 测试完成")
print("=" * 70)

