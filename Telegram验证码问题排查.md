# 📱 Telegram 验证码问题排查

## 常见原因和解决方案

### 1. 手机号格式问题

Telegram 需要**完整的国际格式**手机号。

#### ❌ 错误格式
```
13812345678          # 缺少国家代码
+86 138 1234 5678    # 有空格
+86-138-1234-5678    # 有连字符
```

#### ✅ 正确格式
```
+8613812345678       # 中国：+86 + 手机号（无空格）
+8613800138000       # 示例
```

#### 其他国家
```
+12025551234         # 美国：+1
+447700900000        # 英国：+44
+85212345678         # 香港：+852
```

---

### 2. Telegram 账号问题

#### 检查清单：
- [ ] 手机号已注册 Telegram
- [ ] Telegram 账号可以正常使用
- [ ] 没有被 Telegram 限制或封禁
- [ ] 手机可以接收短信

#### 测试方法：
```
1. 打开手机 Telegram
2. 退出登录
3. 重新登录
4. 看能否收到验证码
   - 如果能收到 → Telegram 账号正常
   - 如果收不到 → 账号可能有问题
```

---

### 3. 网络问题

#### 检查网络连接
```
1. 确认可以访问国际网络
2. 如果使用代理，确认代理正常
3. 尝试关闭代理再测试
```

#### 从日志看连接状态
```
✅ 成功连接：
INFO: Connection to 149.154.167.92:443/TcpFull complete!
Please enter the code you received:

❌ 连接失败：
ERROR: Connection timeout
ERROR: Unable to connect
```

你的日志显示**连接成功**，所以不是网络问题。

---

### 4. API 配置问题

#### 检查 API ID 和 API Hash

##### 获取 API 凭证
```
1. 访问：https://my.telegram.org/auth
2. 用手机号登录（会收到验证码）
3. 点击 "API development tools"
4. 创建应用（如果还没有）
5. 获取：
   - api_id: 一串数字（如：12345678）
   - api_hash: 一串字母数字（如：abcdef1234567890abcdef1234567890）
```

##### 常见错误
```
❌ api_id 写成字符串："12345678"
✅ 应该是数字：12345678

❌ api_hash 有引号或空格
✅ 应该是纯字母数字
```

---

### 5. 验证码接收方式

Telegram 可能通过不同方式发送验证码：

#### 方式1: 短信（SMS）
- 发送到你的手机号
- 查看手机短信

#### 方式2: Telegram 应用内
- 如果手机已登录 Telegram
- 验证码会发送到 Telegram 聊天
- 查看 "Telegram" 官方对话

#### 方式3: 语音电话
- 如果短信失败
- Telegram 会打电话给你
- 语音播报验证码

---

### 6. 程序运行方式问题

#### ❌ 后台运行（无法看到提示）
```powershell
Start-Process python -ArgumentList "gui_main.py" -WindowStyle Hidden
```
→ 看不到 "Please enter the code" 提示

#### ✅ 前台运行（能看到提示）
```powershell
python gui_main.py
```
→ 终端会显示：
```
Please enter the code you received: _
```

---

## 🔧 故障排查步骤

### Step 1: 验证手机号格式

检查 `.env` 文件：
```ini
TELEGRAM_PHONE=+8613812345678
```

确认：
- [ ] 有加号 `+`
- [ ] 有国家代码（中国是 `86`）
- [ ] 没有空格、横线、括号
- [ ] 格式：`+[国家代码][手机号]`

### Step 2: 验证 API 凭证

检查 `.env` 文件：
```ini
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
```

确认：
- [ ] API_ID 是纯数字
- [ ] API_HASH 是 32 位字母数字
- [ ] 没有引号、空格

### Step 3: 测试 Telegram 账号

```
1. 打开手机 Telegram
2. 看账号是否正常
3. 尝试退出重新登录
4. 确认能收到验证码
```

### Step 4: 检查运行方式

```powershell
# 停止后台进程
taskkill /F /IM python.exe

# 前台运行
python gui_main.py

# 点击 "启动监听"
# 观察终端输出
```

### Step 5: 查看详细日志

运行时应该看到：
```
INFO: 正在启动 Telegram 信号机器人...
INFO: Connecting to 149.154.167.92:443/TcpFull...
INFO: Connection complete!
INFO: Requesting code...
Please enter the code you received: 
```

如果卡在某一步，说明那里有问题。

---

## 💡 替代方案

### 方案1: 使用已有的 Session

如果你在其他地方已经验证过：

```
1. 找到 trading_bot_session.session 文件
2. 复制到 c:\python\cypto11\
3. 重新启动程序
4. 不再需要验证码
```

### 方案2: 使用 Bot Token

如果反复收不到验证码，可以改用 Bot 模式：

```
1. 在 Telegram 中联系 @BotFather
2. 创建新 Bot
3. 获取 Bot Token
4. 修改程序使用 Bot Token
```

---

## 📞 获取帮助

### 如果还是收不到验证码

#### 检查项目：
1. [ ] 手机号格式正确（+8613812345678）
2. [ ] API ID/Hash 正确
3. [ ] Telegram 账号正常（能正常登录手机版）
4. [ ] 网络连接正常（程序显示连接成功）
5. [ ] 前台运行（能看到终端提示）

#### 尝试：
1. 等待 2-3 分钟（验证码可能延迟）
2. 查看手机 Telegram 应用（验证码可能发在应用内）
3. 检查垃圾短信（验证码可能被拦截）
4. 重启手机（网络可能有问题）
5. 换个时间再试（Telegram 服务器可能繁忙）

---

## 🔍 调试方法

### 添加调试日志

修改 `telegram_client.py`，添加更详细的日志：

```python
async def start(self):
    logger.info("正在启动 Telegram 信号机器人...")
    logger.info(f"手机号: {Config.TELEGRAM_PHONE}")  # 添加这行
    logger.info(f"API ID: {Config.TELEGRAM_API_ID}")  # 添加这行
    
    self.client = TelegramClient(
        'trading_bot_session',
        Config.TELEGRAM_API_ID,
        Config.TELEGRAM_API_HASH
    )
    
    await self.client.start(phone=Config.TELEGRAM_PHONE)
    logger.info("Telegram 客户端已启动")
```

这样可以确认配置是否正确读取。

---

## ✅ 成功的标志

当一切正常时，你应该：

1. **在终端看到：**
```
Please enter the code you received: _
```

2. **在手机收到：**
   - 短信验证码，或
   - Telegram 应用内消息，或
   - 语音电话

3. **输入验证码后看到：**
```
INFO: 验证成功
INFO: 机器人已启动
```

---

**请检查以上各项，特别是手机号格式！** 📱

