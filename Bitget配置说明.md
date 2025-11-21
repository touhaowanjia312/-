# 🔐 Bitget 交易所配置说明

## ⚠️ Bitget 特殊要求

Bitget 交易所除了 API Key 和 Secret 外，还需要一个 **Password** 字段。

---

## 📝 完整配置步骤

### 1. 获取 Bitget API 凭证

登录 Bitget → API 管理 → 创建 API

会得到：
```
API Key: bg_xxxxxxxxxxxxxxxx
API Secret: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx  
Passphrase: xxxxxxxxx  ← 这就是 Password
```

### 2. 在GUI中配置

#### 方法：打开多交易所管理界面

```
1. 点击 "🚀 打开多交易所管理界面"
2. 点击 "➕ 添加账户"
3. 填写信息：

   账户名称: Bitget主账户
   
   交易所类型: bitget
   
   API Key: bg_xxxxxxxxxxxxxxxx
   
   API Secret: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   
   Password: xxxxxxxxx  ← 填写 Passphrase
   
   ☑ 启用此账户
   ☐ 使用测试网（Bitget需要正式网）
   
4. 点击 "💾 保存账户"
```

---

## 🔍 Password 字段说明

### 什么是 Password？
- Bitget 称为 **Passphrase**（密码短语）
- OKX 也称为 **Passphrase**
- 这是创建 API 时设置的密码
- **不是**登录密码

### 哪些交易所需要？
| 交易所 | 需要 Password | 字段名称 |
|--------|---------------|----------|
| Bitget | ✓ **必需** | Passphrase |
| OKX | ✓ **必需** | Passphrase |
| Binance | ✗ 不需要 | - |
| Bybit | ✗ 不需要 | - |
| Gate.io | ✗ 不需要 | - |

### 如果没有填写会怎样？
```
ERROR: bitget requires "password" credential
❌ 初始化失败，无法连接
```

---

## ✅ 正确的配置示例

### Bitget 配置
```json
{
  "name": "Bitget主账户",
  "exchange_type": "bitget",
  "api_key": "bg_4ab147c9449d81bdfdf8c5555639664d",
  "api_secret": "dc9ce3302b7db664d47f4b8adcc2252e159ed536d8047e76ad62e846c6c65f70",
  "password": "YourPassphrase123",  ← 必需！
  "testnet": false,
  "enabled": true,
  "default_leverage": 20,
  "risk_percentage": 1.0,
  "use_margin_amount": true,
  "margin_amount": 2.0
}
```

### OKX 配置
```json
{
  "name": "OKX账户",
  "exchange_type": "okx",
  "api_key": "your_okx_api_key",
  "api_secret": "your_okx_api_secret",
  "password": "your_okx_passphrase",  ← 必需！
  "testnet": true,
  "enabled": true
}
```

---

## 🎯 GUI 界面更新

### 新增 Password 输入框
```
⚙️ 账户配置
━━━━━━━━━━━━━━━━━━━━

基本信息
  账户名称: [__________]
  交易所类型: [bitget ▼]
  API Key: [**********]
  API Secret: [**********]
  Password: [可选（bitget/okx需要）]  ← 新增！
  
  ☑ 使用测试网
  ☑ 启用此账户
```

---

## 🔒 安全说明

### Password/Passphrase 安全建议

1. **创建时建议**
   - 使用强密码
   - 不要使用登录密码
   - 妥善保管，不要分享

2. **权限设置**
   - ✓ 读取账户信息
   - ✓ 交易（开仓/平仓）
   - ✗ **不要开启提现权限**

3. **测试网vs正式网**
   - Bitget：需要正式网 API
   - 先用小金额测试
   - 确认无误后增加仓位

---

## 📊 验证配置

### 测试连接
```
1. 保存账户后，查看日志：

INFO: 初始化交易所: Bitget主账户
INFO: ✓ 成功连接到 Bitget主账户 (bitget)

2. 点击 "🔄 刷新余额"

💼 账户余额
Bitget主账户
可用: X.XX USDT  ← 显示余额说明连接成功
```

---

## ❌ 常见错误

### 错误1：未填写 Password
```
ERROR: bitget requires "password" credential
```
**解决**：在 Password 字段填写 Passphrase

### 错误2：Password 错误
```
ERROR: Invalid API-signature
```
**解决**：检查 Passphrase 是否正确

### 错误3：API 权限不足
```
ERROR: Insufficient permissions
```
**解决**：检查 API 权限设置

---

## 🎮 完整配置流程

### Step 1: 获取 API
```
1. 登录 Bitget
2. 进入 API 管理
3. 创建新 API
4. 记录：
   ✓ API Key
   ✓ API Secret
   ✓ Passphrase（重要！）
```

### Step 2: GUI 配置
```
1. 打开多交易所管理
2. 添加账户
3. 填写完整信息（包括 Password）
4. 保存
```

### Step 3: 验证
```
1. 查看日志确认连接成功
2. 刷新余额查看数据
3. 开始使用
```

---

## 💡 提示

### 忘记 Passphrase 怎么办？
1. 无法找回
2. 需要删除旧 API
3. 创建新的 API
4. 重新记录 Passphrase

### 修改已保存的账户
1. 点击 "✏️ 编辑账户"
2. 选择要修改的账户
3. 更新 Password 字段
4. 点击 "💾 更新账户"

---

**现在你知道如何正确配置 Bitget 了！** 🎉

记住：**Bitget 和 OKX 都需要 Password（Passphrase）字段！**

