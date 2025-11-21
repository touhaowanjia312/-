# 可能的BUG 12: Bitget做空可能也需要传cost而不是amount

## 当前代码

```python
# 做多
cost = amount * current_price  # 传cost
order = client.create_market_order(symbol, 'buy', cost, params)

# 做空
order = client.create_market_order(symbol, 'sell', amount, params)  # 传amount
```

## 问题

Bitget可能对做空也要求传cost（总价值），而不是amount（数量）。

## 需要测试

是否做空也应该：
```python
# 做空
cost = amount * current_price  # 像做多一样传cost？
order = client.create_market_order(symbol, 'sell', cost, params)
```

## 或者

Bitget做空可能需要特殊的单位参数？

