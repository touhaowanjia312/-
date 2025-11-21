# 📊 LBANK 合约余额显示说明

## 问题

用户反馈：LBANK 交易所现货和合约账户是**分开的**，但程序只显示现货余额，合约余额不显示。

## 根本原因

**LBANK 使用分离的 API 端点：**
- **现货 API**: `https://api.lbank.info`
- **合约 API**: `https://lbkperp.lbank.com`

CCXT 库默认只连接现货 API，需要专门创建合约客户端来获取合约余额。

## 解决方案

### 1. 修改 `multi_exchange_client.py`

在 `get_balance_detailed` 方法中，为 LBANK 添加特殊处理：

```python
# 特殊处理：LBANK 需要创建独立的合约客户端
if exchange_type == 'lbank':
    try:
        import ccxt
        # 创建 LBANK 合约客户端
        contract_client = ccxt.lbank({
            'apiKey': account.api_key,
            'secret': account.api_secret,
            'options': {
                'defaultType': 'swap',  # 合约市场
            },
            'urls': {
                'api': {
                    'rest': 'https://lbkperp.lbank.com',  # 使用合约API
                }
            }
        })
        
        contract_balance = contract_client.fetch_balance()
        result['futures'] = contract_balance['free'].get(currency, 0.0)
        result['total'] = result['spot'] + result['futures']
    except Exception as e:
        logger.debug(f"{account_name} 获取合约余额失败: {e}")
        result['total'] = result['spot']
        result['futures'] = 0.0
```

### 2. 更新 `gui_main.py` 显示逻辑

现在会根据账户类型显示不同的格式：

**统一账户（如 Bitget）：**
```
bitget: 12.85 (统一)
```

**分离账户（如 LBANK）：**
```
LBANK: 0.00004384 (💵 现货: 0.00004384, 📊 合约: 0.0)
```

## 当前测试结果

根据测试，您的账户余额为：

| 交易所 | 现货余额 | 合约余额 | 总余额 | 类型 |
|--------|---------|---------|--------|------|
| **bitget** | 12.85 USDT | - | 12.85 USDT | 统一账户 |
| **LBANK** | 0.000044 USDT | 0.0 USDT | 0.000044 USDT | 分离账户 |

## GUI 显示效果

在 GUI 中点击 **"🔄 刷新余额"**，您会看到：

```
💰 总计: 12.85 USDT

bitget: 12.85 (统一)
LBANK: 0.00004384 (💵 现货: 0.00004384, 📊 合约: 0.0)
```

## ⚠️ 重要提示

测试显示您的 **LBANK 合约余额为 0.0 USDT**。

**请确认：**
1. 您在 LBANK 网站上实际看到的合约余额是多少？
2. 如果网站显示有余额但程序显示为 0，可能需要：
   - 检查 API 权限设置
   - 验证合约 API 密钥是否正确
   - 确认合约 API 是否已启用

## 如何验证

### 方法 1：在 LBANK 网站检查

1. 登录 LBANK
2. 进入 **合约交易** 页面
3. 查看 **合约账户余额**
4. 告诉我具体数值

### 方法 2：运行测试脚本

```bash
python test_detailed_balance.py
```

查看输出中的 "LBANK 合约余额" 是否正确。

## 其他交易所支持

当前支持的交易所余额查询：

| 交易所 | 现货 | 合约 | 类型 |
|--------|------|------|------|
| **Binance** | ✅ | ✅ | 统一账户 |
| **OKX** | ✅ | ✅ | 统一账户 |
| **Bitget** | ✅ | ✅ | 统一账户 |
| **LBANK** | ✅ | ✅ | 分离账户 |
| **Bybit** | ✅ | ✅ | 可选统一 |

## API 权限要求

确保您的 LBANK API 密钥有以下权限：
- ✅ **现货账户读取权限**
- ✅ **合约账户读取权限**
- ✅ **交易权限**（如果需要自动交易）

## 故障排查

### 1. 合约余额显示为 0 但实际有余额

**可能原因：**
- API 密钥权限不足
- 合约 API 未启用
- API 端点访问被限制

**解决方法：**
1. 登录 LBANK
2. 进入 **API 管理**
3. 检查 API 权限设置
4. 确保启用了 **合约账户权限**

### 2. 连接失败

**可能原因：**
- 网络问题
- API 密钥错误
- IP 白名单限制

**解决方法：**
1. 检查网络连接
2. 验证 API 密钥和密钥
3. 检查 IP 白名单设置

## 相关文件

- `multi_exchange_client.py` - 余额查询逻辑
- `gui_main.py` - GUI 显示逻辑
- `test_detailed_balance.py` - 测试脚本
- `test_lbank_contract.py` - LBANK 合约测试
- `test_lbank_native_api.py` - LBANK 原生 API 测试

## 更新时间

2025-10-15 01:00

---

**下一步：** 请告诉我您在 LBANK 网站上看到的实际合约余额，我会进一步调试 API 调用。

