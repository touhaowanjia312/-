# 快速入门指南

## 第一步：测试信号解析器

在配置任何 API 之前，先测试信号解析是否正常工作：

```bash
python test_signal_parser.py
```

这将测试程序能否正确识别各种格式的交易信号。

## 第二步：安装依赖

```bash
pip install -r requirements.txt
```

如果遇到安装问题，可以尝试：
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 第三步：获取 Telegram API 凭证

### 3.1 访问 Telegram API 页面
打开浏览器访问：https://my.telegram.org/apps

### 3.2 登录
使用你的手机号登录（需要接收验证码）

### 3.3 创建应用
- 点击 "Create application"
- 填写应用信息：
  - **App title**: 随意填写，例如 "Trading Bot"
  - **Short name**: 随意填写，例如 "tradingbot"
  - **Platform**: 选择 "Other"
- 提交后会得到：
  - **api_id**: 一串数字
  - **api_hash**: 一串字母和数字

### 3.4 获取群组 ID

有两种方式：

**方式 1：使用群组用户名**
- 如果群组是公开的，可以直接使用 `@groupname`
- 例如：`@crypto_signals_group`

**方式 2：使用群组 ID**
1. 将机器人 `@userinfobot` 添加到群组
2. 它会发送群组 ID（类似 `-1001234567890`）
3. 使用这个 ID

## 第四步：创建 .env 配置文件

在项目根目录创建 `.env` 文件：

```bash
# Windows
copy config.example.txt .env

# Linux/Mac
cp config.example.txt .env
```

然后编辑 `.env` 文件，填入你的配置：

```env
# === 必填项 ===
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=abcdef1234567890abcdef1234567890
TELEGRAM_PHONE=+86138xxxxxxxx
TELEGRAM_GROUP_ID=@your_group_name

# === 以下是可选项 ===
# 如果只想测试信号识别，可以不配置交易所

# 交易所配置（暂时不用填）
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=
EXCHANGE_API_SECRET=
EXCHANGE_TESTNET=True

# 交易配置
TRADING_ENABLED=False
DEFAULT_POSITION_SIZE=0.01
MAX_POSITION_SIZE=0.1
RISK_PERCENTAGE=1.0
```

## 第五步：首次运行（仅监听模式）

```bash
python main.py
```

首次运行时会要求：
1. 输入手机验证码（查看 Telegram 消息）
2. 如果启用了两步验证，输入密码

验证成功后，程序会开始监听群组消息。

此时 `TRADING_ENABLED=False`，所以**不会执行任何交易**，只会识别和显示信号。

## 第六步：观察信号识别

让程序运行一段时间，观察：
- 是否能正确连接到群组
- 是否能识别出交易信号
- 识别的准确性如何

查看控制台输出，会显示类似：

```
收到消息:
🔥 LONG BTC/USDT
Entry: 42000
...

✓ 识别到交易信号: TradingSignal(type=LONG, symbol=BTC/USDT, entry=42000.0, ...)
```

## 第七步：（可选）配置交易所

⚠️ **注意：只有在充分测试信号识别准确后，才进行这一步！**

### 7.1 获取交易所 API（以币安为例）

1. 登录币安账户：https://www.binance.com
2. 进入 API 管理：用户中心 → API 管理
3. 创建新的 API 密钥
4. **重要安全设置**：
   - ✅ 启用 "现货与杠杆交易"
   - ✅ 启用 "合约交易"（如果需要）
   - ❌ **禁用 "提现"**
   - ✅ 设置 IP 白名单（可选但推荐）
5. 保存 API Key 和 Secret Key

### 7.2 更新 .env 配置

```env
EXCHANGE_API_KEY=your_actual_api_key
EXCHANGE_API_SECRET=your_actual_secret_key
EXCHANGE_TESTNET=True  # 先用测试网！
```

### 7.3 使用测试网（强烈推荐）

币安测试网：
- 注册：https://testnet.binance.vision/
- 获取测试网 API 密钥
- 免费获取测试币

使用测试网配置：
```env
EXCHANGE_TESTNET=True
```

## 第八步：启用交易（谨慎！）

⚠️ **再次警告：只有在充分测试后才启用！**

```env
TRADING_ENABLED=True
```

建议顺序：
1. 先在测试网启用交易，观察一周
2. 如果一切正常，切换到正式网络
3. 使用小额资金测试
4. 逐步增加仓位

## 常见问题

### Q1: 运行 main.py 时提示缺少模块？
**A**: 运行 `pip install -r requirements.txt`

### Q2: 无法连接 Telegram？
**A**: 
- 检查网络连接
- 中国大陆用户可能需要代理
- 确认 API ID 和 Hash 正确

### Q3: 一直没有识别到信号？
**A**:
- 确认群组 ID 正确
- 检查群组是否有消息
- 查看 `test_signal_parser.py` 中的格式，对比群组消息格式
- 可能需要自定义 `signal_parser.py`

### Q4: 收到验证码但程序没反应？
**A**: 直接在控制台输入验证码（不要在 Telegram 中输入）

### Q5: 如何停止程序？
**A**: 按 `Ctrl + C`

## 下一步

- 阅读 `README.md` 了解更多详细信息
- 查看 `signal_parser.py` 自定义信号解析规则
- 修改 `config.py` 调整风险参数

## 技术支持

如有问题，请：
1. 查看日志输出
2. 检查配置文件
3. 阅读完整的 README.md
4. 创建 GitHub Issue

祝交易顺利！🚀

