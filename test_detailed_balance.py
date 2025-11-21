#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试详细余额显示
"""
import sys
import io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
from multi_exchange_config import multi_exchange_config
from multi_exchange_client import MultiExchangeClient

def test_detailed_balance():
    """测试详细余额显示"""
    print("="*60)
    print("详细余额测试")
    print("="*60)
    
    # 加载账户配置
    accounts = multi_exchange_config.get_enabled_accounts()
    print(f"\n✓ 加载了 {len(accounts)} 个账户配置")
    
    # 初始化客户端
    client = MultiExchangeClient()
    for account in accounts:
        client.add_exchange(account)
    
    print(f"\n✓ 已初始化 {len(client.clients)} 个交易所客户端")
    
    # 获取详细余额
    print("\n" + "="*60)
    print("获取所有账户详细余额")
    print("="*60)
    
    detailed_balances = client.get_all_balances_detailed()
    
    for name, bal_info in detailed_balances.items():
        print(f"\n📊 {name}:")
        print(f"  现货余额: {bal_info['spot']} USDT")
        if bal_info['futures'] is None:
            print(f"  账户模式: 统一账户")
        else:
            print(f"  合约余额: {bal_info['futures']} USDT")
        print(f"  总余额:   {bal_info['total']} USDT")
    
    # 模拟 GUI 显示
    print("\n" + "="*60)
    print("GUI 显示效果")
    print("="*60)
    
    def _format_balance(balance: float) -> str:
        if balance >= 1.0:
            return f"{balance:.2f}"
        elif balance >= 0.01:
            return f"{balance:.4f}"
        elif balance >= 0.0001:
            return f"{balance:.6f}"
        else:
            return f"{balance:.8f}"
    
    total = 0.0
    balance_text = ""
    
    for name, bal_info in detailed_balances.items():
        total += bal_info['total']
        
        if bal_info['futures'] is None:
            balance_text += f"{name}: {_format_balance(bal_info['total'])} (统一)\n"
        elif bal_info['futures'] > 0:
            balance_text += f"{name}: {_format_balance(bal_info['total'])} "
            balance_text += f"(现货: {_format_balance(bal_info['spot'])}, "
            balance_text += f"合约: {_format_balance(bal_info['futures'])})\n"
        else:
            balance_text += f"{name}: {_format_balance(bal_info['spot'])} (现货)\n"
    
    final_text = f"💰 总计: {_format_balance(total)} USDT\n\n{balance_text}"
    print("\n" + final_text.strip())
    
    print(f"\n{'='*60}")
    print("测试完成")
    print(f"{'='*60}")

if __name__ == '__main__':
    test_detailed_balance()

