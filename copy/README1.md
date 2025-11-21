# Telegram 群组信号跟单程序

这是一个自动化的加密货币交易机器人，可以监听 Telegram 群组中的交易信号并自动执行交易。

## 🎯 两种版本

### 🖥️ GUI 版本（推荐）
现代化图形界面，功能全面，操作简单。

**启动方式：**
```bash
python gui_main.py
# 或双击 start_gui.bat (Windows)
```

**GUI 特性：**
- 🎨 现代化美观界面
- 📊 实时仪表板和统计
- 📝 彩色日志显示
- 🧪 信号测试工具
- 📈 交易历史记录
- ⚙️ 可视化配置
- 🌓 深色/浅色主题

查看 **[GUI_README.md](GUI_README.md)** 了解详细使用说明。

### 💻 命令行版本
轻量级，适合在服务器或后台运行。

**启动方式：**
```bash
python main.py
```

## 功能特性

- ✅ 监听 Telegram 群组消息
- ✅ 自动解析交易信号（做多/做空/平仓）
- ✅ 支持多种交易所（基于 CCXT）
- ✅ 智能信号识别（支持多种格式）
- ✅ 风险管理（可配置仓位大小和风险比例）
- ✅ 测试网模式（安全测试）
- ✅ 杠杆交易支持
- ✅ 止损和止盈支持
- ✅ **高级 GUI 界面**（新增！）

### 当前功能扩展（2025-10）
- Bitget 合约深度适配：自动设杠杆、单向持仓、参数补全（`productType/marginCoin`）
- 市价入场的最小数量/最小名义金额校验与精度上调（避免向下取整导致不达标）
- 余额不足(43012)时的“数量递减重试”（最多3次），并打印可用保证金/名义/所需保证金
- 固定保证金模式与“风险按名义”模式可选，支持 2U×20 等小额开仓
- 合约交易对优先使用 `:USDT`（如 `ENSO/USDT:USDT`），并遍历 `swap` 市场兜底
- CLOSE 分批平仓：按“第一/第二止盈”自动平 50%/30%，默认 reduce-only 限价
- 邻近消息推断：开仓后20分钟内的“止盈/目标/tp+价格”可自动继承最近币种
- 第一止盈即时挂单：收到“第一止盈：价格X”，立即按持仓50%挂 reduce-only 限价单（不等待“已触发”）
- TP1 成交后自动保本：首个止盈成交后，将剩余仓位止损移动到保本位（入场价），并继续按配置的追踪止损
- 自动后续分批止盈：无需后续消息，按既定策略自动挂出剩余分批（默认第二止盈30%、第三止盈20%）
- Telegram 无限重连：断线后持续重试，避免 5 次失败即退出

## Bitget 适配要点（已内置）
- 下单前自动 `set_leverage`；若已设置会忽略错误继续
- 自动设置单向持仓（oneway），避免 40774 错误
- 合约下单统一走“数量参数”，并记录“数量/名义”双字段日志
- `close_position` 和止盈/止损下单均补齐 `productType: USDT-FUTURES` 与 `marginCoin: USDT`

## 信号解析与执行增强
- 优先识别 `#`/`$` 币种；移除 URL 片段，避免把链接误识别成交易对
- 过滤回顾/统计类消息（如“战绩/盈利/统计”等）
- 识别“第一/第二止盈 价格”类消息：
  - 若含币种：直接对该币种分批平仓
  - 若不含币种：
    1) 在开仓后20分钟内，自动继承最近一次开仓的币种；
    2) 若无近期开仓，且全账户仅有一个持仓，则使用该持仓币种；
    3) 否则跳过并记录原因
  - “第一止盈：价格X”消息到达时立即挂 50% 限价 reduce-only 单；随后自动挂出后续分批（默认30%/20%）

## 风险与仓位计算
- 固定保证金：`数量 = (保证金 × 杠杆) / 价格`
- 风险百分比：
  - 默认将风险额度视为保证金：`名义 = 风险 × 杠杆`
  - 可选“风险按名义”模式（`risk_as_notional=true`）：直接以风险额度作为名义金额
- 限制最大仓位，且依据可用保证金给出“最大可开名义”的上限提示

## 程序稳定性
- Telegram 客户端设置 `connection_retries=None`，并在循环中 `run_until_disconnected`，断线持续重试
- GUI 关闭时的清理流程优化（避免后台残留影响再次启动）

---

## 近期重要修改与时间线

- 2025-10-20
  - 修复余额获取：显式拉取合约余额（`type=swap/future`），区分现货与合约
- 2025-10-21
  - 修复单字符币种解析（支持 `#F`）
  - 过滤统计/回顾类消息，避免误触发
- 2025-10-22
  - 解析前移除 URL，避免把链接误识别成交易对（如 `ME/JEAM`）
- 2025-10-23
  - 启动与运行稳定性验证
- 2025-10-25 ~ 10-26
  - 定位 Bitget 做空参数错误（此前将“成本 USDT”错误当成数量传入）
  - 增加“最大可开名义”与 43012 的数量递减重试与诊断日志
- 2025-10-27
  - 启用固定保证金 2U×20 配置，确保小额名义与手动一致
- 2025-10-28
  - 统一 Bitget 走“数量下单”，并完善 `:USDT` 合约符号优先策略
  - 修复 `close_position` 缺少 `productType/marginCoin`（40019）
- 2025-10-29
  - CLOSE 分批平仓：按“第一/第二止盈”自动分仓，reduce-only 限价
  - 邻近消息推断：开仓后5分钟内的止盈价格可自动继承最近币种
  - Telegram 无限重连逻辑合入

- 2025-11-02
  - **自动初始止损**：入场成交后自动设置初始止损（做多=入场价-4%，做空=入场价+4%）
  - **Bitget 止损参数修正（1）**：采用 `type=market + stopLossPrice`，不再传 `triggerType/planType`，避免 400172；单向持仓模式下默认不传 `holdSide`
  - **“价格型 TP1 即时挂单”**：收到“第一止盈：价格X/到X/减仓保本”时，立即挂 50% reduce-only 限价单（不等待“已触发”类消息）
  - **自动后续分批**：TP1 挂出后，自动为剩余仓位挂出 TP2/TP3（默认 30%/20%）

- 2025-11-03
  - **无价格提示的回退分批**：若开仓后未收到“第一止盈价格”，自动按 5%/10%/20% 三档 reduce-only 分批止盈，仓位 50%/30%/20%
  - **保本止损**：监控 TP1 成交后，自动把剩余仓位止损移动到保本位（入场价），并继续执行已配置的追踪止损
  - **清理回退挂单**：当后续收到“价格型 TP1”时，会先取消已存在的回退分批挂单，避免重复/冲突
  - **新增群组监听**：Bubblu-加密口袋🛍讨论（-1002552493074）

- 2025-11-04
  - **Bitget 止损参数修正（2）自适应重试**：
    - 首次尝试：单向持仓下不带 `holdSide`，仅传 `stopLossPrice`/`productType`/`marginCoin`/`reduceOnly`
    - 若返回 43011（holdSide error）：查询当前持仓，携带 `positionId` 并按持仓方向补充 `holdSide` 重试；仍失败则尝试相反方向再重试一次
  - 保持统一日志：打印止损设置状态与错误返回 JSON，便于进一步诊断

- 2025-11-05
  - **TP 策略调整**：
    - 有价格 TP1：收到“第一止盈：价格X”即刻挂 50% reduce-only 限价单；随后自动挂出 TP2/TP3 在 ±20%/±40%（相对入场），份额 30%/20%；TP1 成交后自动移保本
    - 无价格提示：自动按 10%/20%/50% 三档 reduce-only 分批止盈，份额 50%/30%/20%；若后续收到价格型 TP1，会先撤回回退挂单再按价格型流程执行
  - **信号解析扩展**：补充“进多/进空/现价多/现价空/市价开多/市价开空/多单/空单/反手多/反手空/清仓/平多/平空”等常见口语，降低遗漏；当前“轻仓/半仓/重仓”不改变下单规模，如需比例映射可按需启用
  - **Bitget 止损下单**：切换使用专用 TPSL 接口（`/api/v2/mix/order/place-tpsl-order`，经 ccxt `privatePostMixV2PlanPlacePlan`），仅传必要字段，避免与 `createOrder` 的 `triggerPrice/stopLossPrice/takeProfitPrice/trailingPercent` 参数冲突；`productType=usdt-futures`（小写），`symbol` 使用交易所 `marketId`
  - **群组监听**：补充测试群“信号测试” (-5053530836)

---

## 配置要点（Bitget 示例）
- `exchanges_config.json` 建议：
  - `default_leverage`: 20
  - `use_margin_amount`: true（固定保证金模式）
  - `margin_amount`: 2.0（示例）
  - `risk_as_notional`: false（默认），如需可改为 true
  - `enabled`: true, `testnet`: false（请按需调整）

> 建议先用极小额度或测试网验证，确认“数量≈(保证金×杠杆/价格)、名义≈数量×价格”的日志与预期一致。

## 安装步骤

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 获取 Telegram API 凭证

1. 访问 https://my.telegram.org/apps
2. 登录你的 Telegram 账号
3. 创建一个新应用
4. 获取 `api_id` 和 `api_hash`

### 3. 获取交易所 API 密钥

以币安为例：
1. 登录币安账户
2. 前往 API 管理页面
3. 创建新的 API 密钥
4. 保存 `API Key` 和 `Secret Key`

**⚠️ 重要安全提示：**
- 仅启用必要的权限（交易权限）
- 禁用提现权限
- 设置 IP 白名单

### 4. 配置环境变量

复制 `.env.example` 为 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件，填入你的配置：

```env
# Telegram API 配置
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_PHONE=+86138xxxxxxxx
TELEGRAM_GROUP_ID=@your_group_name  # 或群组 ID

# 交易所配置
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=your_api_key
EXCHANGE_API_SECRET=your_api_secret
EXCHANGE_TESTNET=True  # 建议先使用测试网

# 交易配置
TRADING_ENABLED=False  # 设为 True 启用实际交易
DEFAULT_POSITION_SIZE=0.01
MAX_POSITION_SIZE=0.1
RISK_PERCENTAGE=1.0
```

## 使用方法

### GUI 版本（推荐新手）

**Windows 用户：**
```bash
# 双击运行
start_gui.bat
```

**所有平台：**
```bash
python gui_main.py
```

详细使用说明请查看 **[GUI_README.md](GUI_README.md)**

### 命令行版本

```bash
python main.py
```

### 首次运行

首次运行时，程序会要求你：
1. 输入手机号验证码
2. 输入两步验证密码（如果启用了）

验证成功后，会生成 `trading_bot_session.session` 文件，以后运行不需要再次验证。

**GUI 版本注意**：验证码需要在终端窗口输入，不是在 GUI 界面。

## 信号格式示例

程序可以识别多种格式的交易信号：

### 格式 1：标准格式
```
🔥 LONG BTC/USDT
Entry: 42000
Stop Loss: 41000
Take Profit: 43000, 44000, 45000
Leverage: 10x
```

### 格式 2：简化格式
```
Buy BTCUSDT
Price: 42000
SL: 41000
TP: 43000
```

### 格式 3：中文格式
```
做多 BTC
入场: 42000
止损: 41000
止盈: 43000
杠杆: 10
```

### 格式 4：社交媒体格式
```
#BTC LONG 🚀
Entry @ 42k
SL 41k
Target 43k 44k 45k
```

## 安全建议

1. **先使用测试网**：将 `EXCHANGE_TESTNET` 设为 `True`
2. **模拟模式**：将 `TRADING_ENABLED` 设为 `False`，先观察信号识别准确性
3. **小额测试**：正式使用时，先用小额资金测试
4. **风险控制**：合理设置 `RISK_PERCENTAGE` 和 `MAX_POSITION_SIZE`
5. **定期监控**：定期检查程序运行状态和交易记录

## 配置说明

### TRADING_ENABLED
- `False`: 仅监听和解析信号，不执行交易（推荐初次使用）
- `True`: 启用实际交易

### EXCHANGE_TESTNET
- `True`: 使用交易所测试网络
- `False`: 使用正式网络

### RISK_PERCENTAGE
账户余额的百分比用于单次交易风险
- 例如：`1.0` 表示每次交易风险为账户余额的 1%

### MAX_POSITION_SIZE
单次交易的最大仓位大小（币的数量）

## 支持的交易所

通过 CCXT 库，程序支持 100+ 交易所，常见的包括：

- Binance (币安)
- OKX (欧易)
- Bybit
- Huobi (火币)
- Bitget
- Gate.io
- 等等...

修改 `EXCHANGE_NAME` 即可切换交易所。

## 故障排除

### 问题 1：无法连接 Telegram
- 检查网络连接
- 确认 API ID 和 Hash 正确
- 可能需要代理（中国大陆用户）

### 问题 2：无法识别信号
- 检查信号格式是否符合常见格式
- 查看日志中的原始消息
- 可以修改 `signal_parser.py` 添加自定义解析规则

### 问题 3：交易所连接失败
- 检查 API 密钥是否正确
- 确认 API 权限已启用
- 检查是否使用了正确的网络（测试网/正式网）

## 免责声明

⚠️ **重要提示**

本程序仅供学习和研究使用。加密货币交易具有高风险，可能导致资金损失。

- 使用本程序造成的任何损失，作者不承担责任
- 请在充分了解风险的情况下使用
- 建议先在测试环境中充分测试
- 请遵守当地法律法规

## 许可证

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

如有问题，请创建 GitHub Issue。

---

# 统一执行器与自动平仓说明（2025-11）

- **统一执行器（TradeExecutor）**：
  - `telegram_client.py` 不再直接执行下单逻辑，而是调用 `TradeExecutor`。
  - 支持多交易所与单交易所两种路径，逻辑保持一致：风控校验 → 入场 → 初始止损 → 止盈（价格型/回退） → 登记持仓信息（含 trade_id/leverage）。

- **结构化日志事件（retry_utils.log_struct）**：
  - `exec_start`、`risk_blocked`、`entry_order_placed`、`sl_placed`
  - `tp_placed`/`tp_fallback_placed`、`tp1_order_id`、`position_registered`
  - `trade_recorded`、`trade_closed_signal`

- **自动平仓与真实 PnL 入库**：
  - 后台循环 `_position_fill_monitor_loop` 统一检测仓位归零（TP/SL/主动平仓）。
  - 自动 `trading_db.close_trade(trade_id, exit_price)`，并 `risk_manager.record_trade(..., closed=True)`。
  - 使用 `order_manager.PositionManager.remove_position` 清理内存持仓状态。

- **止盈策略**：
  - 价格型 TP1：第一止盈默认平 50%，自动挂出 TP2/TP3（默认 30%/20%），TP1 成交后移动止损到保本位。
  - 无价格提示：回退三档（10%/20%/50%），份额 50%/30%/20%，若后续收到价格型 TP1，会先清理回退挂单再按价格型执行。

---

# 最小化集成测试（本地快速验证）

- 文件：`integration_test_executor.py`
- 使用独立测试库 `test_trading_history.db`（不影响生产库）。
- 步骤：
  1. 运行 `python integration_test_executor.py`
  2. 观察结构化日志：`exec_start/entry_order_placed/sl_placed/tp_placed/position_registered/trade_recorded`
  3. 脚本会模拟平仓并调用 `close_trade`，输出 `Closed trade ...` 与 `Expected pnl ...` 对比

如需端到端联调，请在 GUI 中实际发送 LONG/SHORT 信号，验证：入场→TP1→保本→完全平仓 后的统计与 PnL。

