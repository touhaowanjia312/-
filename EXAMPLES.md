# 使用示例

## 示例 1：基本监听模式

```bash
# 1. 配置 .env 文件（只需 Telegram 配置）
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_hash
TELEGRAM_PHONE=+86138xxxxxxxx
TELEGRAM_GROUP_ID=@crypto_signals

TRADING_ENABLED=False  # 不执行交易

# 2. 运行程序
python main.py
```

**输出示例：**
```
==================================================
Telegram 群组信号跟单程序
==================================================
正在启动 Telegram 信号机器人...
✓ Telegram 客户端已启动
✓ 正在监听群组: @crypto_signals
✓ 交易状态: 已禁用（仅监听模式）

收到消息:
🔥 LONG BTC/USDT
Entry: 42000
Stop Loss: 41000
Take Profit: 43000
Leverage: 10x

✓ 识别到交易信号: TradingSignal(type=LONG, symbol=BTC/USDT, entry=42000.0, sl=41000.0, tp=[43000.0])
⚠ 交易已禁用，仅记录信号
```

## 示例 2：测试网交易模式

```bash
# .env 配置
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_hash
TELEGRAM_PHONE=+86138xxxxxxxx
TELEGRAM_GROUP_ID=@crypto_signals

# 币安测试网配置
EXCHANGE_NAME=binance
EXCHANGE_API_KEY=testnet_api_key
EXCHANGE_API_SECRET=testnet_secret
EXCHANGE_TESTNET=True

# 启用交易
TRADING_ENABLED=True
RISK_PERCENTAGE=1.0
```

**运行：**
```bash
python main.py
```

**输出示例：**
```
成功连接到 binance
已启用测试网模式
✓ 正在监听群组: @crypto_signals
✓ 交易状态: 已启用

收到消息:
LONG BTC/USDT
Entry: 42000
SL: 41000

✓ 识别到交易信号: TradingSignal(type=LONG, symbol=BTC/USDT, entry=42000.0, sl=41000.0, tp=[])
执行做多: BTC/USDT
已设置 BTC/USDT 杠杆为 10x
限价单已下: buy 0.012 BTC/USDT @ 42000.0
✓ 做多订单已执行: 12345678
止损设置在: 41000.0
```

## 示例 3：测试信号解析

在配置任何 API 之前，先测试信号解析：

```bash
python test_signal_parser.py
```

**输出：**
```
============================================================
Telegram 交易信号解析测试
============================================================

测试 #1
------------------------------------------------------------
原始消息:
🔥 LONG BTC/USDT
    Entry: 42000
    Stop Loss: 41000
    Take Profit: 43000
    Leverage: 10x

解析结果:
✓ 信号类型: LONG
✓ 交易对: BTC/USDT
✓ 入场价格: 42000.0
✓ 止损: 41000.0
✓ 止盈: [43000.0]
✓ 杠杆: 10x
------------------------------------------------------------
```

## 示例 4：自定义信号格式

如果你的群组信号格式不同，可以修改 `signal_parser.py`：

```python
# 在 signal_parser.py 中添加自定义关键词
class SignalParser:
    BUY_KEYWORDS = ['buy', 'long', '做多', '买入', '开多', '进场多', '多单']
    SELL_KEYWORDS = ['sell', 'short', '做空', '卖出', '开空', '进场空', '空单']
    CLOSE_KEYWORDS = ['close', 'exit', '平仓', '关闭', '止盈', '离场']
```

## 示例 5：查看账户余额

修改 `main.py` 添加余额查询功能：

```python
from exchange_client import ExchangeClient

exchange = ExchangeClient()
balance = exchange.get_balance('USDT')
print(f"USDT 余额: {balance}")

btc_price = exchange.get_current_price('BTC/USDT')
print(f"BTC 当前价格: {btc_price}")
```

## 常见信号格式

### 格式 1：标准格式
```
🔥 LONG BTC/USDT
Entry: 42000
Stop Loss: 41000
Take Profit 1: 43000
Take Profit 2: 44000
Take Profit 3: 45000
Leverage: 10x
```

### 格式 2：简洁格式
```
Buy BTCUSDT @ 42000
SL: 41000
TP: 43000
```

### 格式 3：Hashtag 格式
```
#BTC Long Signal
Entry Zone: 41800-42200
Stop: 41000
Targets: 43K, 44K, 45K
```

### 格式 4：表情符号格式
```
💎 $BTC
🟢 LONG
📍 Entry: 42000
🔴 SL: 41000
🎯 TP: 43000
```

### 格式 5：中文格式
```
币种：BTC
方向：做多
入场：42000
止损：41000
止盈：43000
```

## 风险管理示例

### 配置 1：保守型
```env
RISK_PERCENTAGE=0.5        # 每次风险 0.5%
MAX_POSITION_SIZE=0.05     # 最大 0.05 BTC
DEFAULT_POSITION_SIZE=0.01
```

### 配置 2：适中型
```env
RISK_PERCENTAGE=1.0        # 每次风险 1%
MAX_POSITION_SIZE=0.1      # 最大 0.1 BTC
DEFAULT_POSITION_SIZE=0.02
```

### 配置 3：激进型
```env
RISK_PERCENTAGE=2.0        # 每次风险 2%
MAX_POSITION_SIZE=0.2      # 最大 0.2 BTC
DEFAULT_POSITION_SIZE=0.05
```

⚠️ **警告**：加密货币交易风险极高，建议从保守配置开始！

## 多群组监听

如果要监听多个群组，可以修改 `telegram_client.py`：

```python
# 在 start() 方法中修改：
@self.client.on(events.NewMessage(chats=[
    '@group1',
    '@group2',
    '-1001234567890',  # 私有群组 ID
]))
async def message_handler(event):
    await self.handle_message(event)
```

## 日志记录

添加交易日志到文件：

```python
# 在 telegram_client.py 开头添加
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
```

这将同时输出到控制台和 `trading.log` 文件。

## 停止程序

按 `Ctrl + C` 停止程序。

程序会保存 session 文件，下次运行不需要再次登录。

