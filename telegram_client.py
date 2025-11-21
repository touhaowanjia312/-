from telethon import TelegramClient, events
from datetime import datetime, timedelta
from config import Config
from signal_parser import SignalParser, SignalType, TradingSignal
from exchange_client import ExchangeClient
from multi_exchange_client import multi_exchange_client
import logging
import asyncio
import re
import order_manager
from database import trading_db
from risk_manager import init_risk_manager, risk_manager
from trade_executor import TradeExecutor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramSignalBot:
    """Telegram 信号监听机器人"""
    
    def __init__(self, enable_internal_monitor: bool = False):
        self.client = None
        # 使用多交易所客户端
        self.multi_exchange = multi_exchange_client
        self.executor = TradeExecutor(self.multi_exchange)
        # 单交易所客户端（仅在需要时初始化）
        self.exchange = None
        self.signal_parser = SignalParser()
        # 记录每个群最近一次开仓（用于无币种的止盈消息推断）
        self.recent_entries = {}  # chat_id -> { 'symbol': str, 'time': datetime }
        self.tp_infer_window = timedelta(minutes=20)
        # 记录每个群最近一次“止盈价格提示”（用于后续无价格的触发消息回填）
        self.last_tp_hint = {}  # chat_id -> { 'price': float, 'time': datetime }
        # 去重：记录已处理的消息ID（仅保留近期窗口，避免内存膨胀）
        self.processed_ids = {}  # chat_id -> set(ids)
        # 是否在内部启用 PositionManager 监控（服务器/无界面模式）
        self.enable_internal_monitor = enable_internal_monitor
        
    async def start(self):
        """启动机器人"""
        logger.info("正在启动 Telegram 信号机器人...")
        
        # 验证配置
        try:
            Config.validate()
        except ValueError as e:
            logger.error(f"配置验证失败: {e}")
            return
        
        # 创建 Telegram 客户端
        self.client = TelegramClient(
            'trading_bot_session',
            Config.TELEGRAM_API_ID,
            Config.TELEGRAM_API_HASH,
            connection_retries=None,  # 无限重试，避免 5 次后直接退出
            retry_delay=2
        )
        
        # 启动客户端
        await self.client.start(phone=Config.TELEGRAM_PHONE)
        logger.info("✓ Telegram 客户端已启动")
        
        # 获取群组实体对象（支持多个ID，以逗号分隔；并临时加入测试群）
        try:
            group_ids_raw = []
            if Config.TELEGRAM_GROUP_ID:
                group_ids_raw.extend([s.strip() for s in str(Config.TELEGRAM_GROUP_ID).split(',') if s.strip()])
            # 临时加入用户提供的测试群（若未在配置中）
            test_group_id = '-5053530836'
            if test_group_id and test_group_id not in group_ids_raw:
                group_ids_raw.append(test_group_id)
            # 新增：Bubblu-加密口袋🛍讨论（-1002552493074）
            extra_group_id = '-1002552493074'
            if extra_group_id and extra_group_id not in group_ids_raw:
                group_ids_raw.append(extra_group_id)

            group_entities = []
            resolved_labels = []
            for gid in group_ids_raw:
                try:
                    parsed = int(gid) if str(gid).lstrip('-').isdigit() else gid
                    entity = await self.client.get_entity(parsed)
                    group_entities.append(entity)
                    resolved_labels.append(f"{getattr(entity, 'title', gid)} ({gid})")
                except Exception as ie:
                    logger.warning(f"⚠ 获取群组失败: {gid} -> {ie}")
            if not group_entities:
                raise RuntimeError("无可用群组可监听")

            # 注册消息处理器（可同时监听多个群组）
            @self.client.on(events.NewMessage(chats=group_entities))
            async def message_handler(event):
                await self.handle_message(event)

            # 监听消息编辑，防止“先发后补价格/修改价格”的情况漏接
            @self.client.on(events.MessageEdited(chats=group_entities))
            async def message_edited_handler(event):
                await self.handle_message(event)

            logger.info("✓ 正在监听群组: " + "; ".join(resolved_labels))
        except Exception as e:
            logger.error(f"✗ 无法获取群组: {e}")
            logger.info("  请检查：1) Group ID是否正确  2) 你的账号是否在该群组中")
            return
        
        logger.info(f"✓ 交易状态: {'已启用' if Config.TRADING_ENABLED else '已禁用（仅监听模式）'}")
        
        # 保持运行（断线后持续重试连接，不退出进程）
        # 启动后回补近30分钟内遗漏消息（后台任务）
        try:
            asyncio.create_task(self._backfill_recent_messages(group_entities, minutes=30, limit=80))
        except Exception:
            pass
        try:
            init_risk_manager(self.multi_exchange)
        except Exception:
            pass
        # 服务器/无界面模式下，在此初始化 PositionManager 并启动监控任务
        try:
            if self.enable_internal_monitor:
                if order_manager.position_manager is None:
                    order_manager.position_manager = order_manager.PositionManager(self.multi_exchange)
                    logger.info("✓ 服务器模式: PositionManager 已初始化")
                try:
                    asyncio.create_task(self._trailing_monitor_loop())
                    logger.info("✓ 服务器模式: 持仓监控任务已启动")
                except Exception as me:
                    logger.error(f"服务器模式: 启动持仓监控任务失败: {me}")
        except Exception:
            pass
        try:
            asyncio.create_task(self._position_fill_monitor_loop())
        except Exception:
            pass
        while True:
            try:
                if not self.client.is_connected():
                    await self.client.connect()
                await self.client.run_until_disconnected()
            except Exception as e:
                logger.error(f"连接中断: {e}，将继续重试连接...")
                await asyncio.sleep(10)
                continue
    
    async def handle_message(self, event):
        """处理接收到的消息"""
        message = getattr(event, 'message', None)
        message_text = getattr(message, 'text', None)
        chat_id = getattr(event, 'chat_id', None)
        msg_id = getattr(message, 'id', None)
        
        # 基于消息ID去重：同一条消息只处理一次，防止重复开仓
        if chat_id is not None and msg_id is not None:
            pid = self.processed_ids.setdefault(chat_id, set())
            if msg_id in pid:
                logger.info(f"⏭ 已处理过的消息 {msg_id}，跳过执行")
                return
            # 第一次遇到该消息ID时立即写入，避免并发触发导致重复执行
            pid.add(msg_id)
        
        if not message_text:
            return
        
        logger.info(f"\n收到消息:\n{message_text}\n")
        
        # 预判是否为止盈提示及价格提取（无论是否解析出正式信号，都可用于缓存/回填）
        text_lower = (message_text or '').lower()
        # 扩展止盈提示：支持“减仓/減倉/保本/到 价格”类文案
        is_tp_hint = (
            ('止盈' in message_text) or ('目标' in message_text) or ('tp' in text_lower)
            or ('减仓' in message_text) or ('減倉' in message_text) or ('保本' in message_text)
            or (re.search(r'到\s*\d+\.?\d*', message_text) is not None)
        )
        tp_prices = SignalParser._extract_take_profit(message_text) if is_tp_hint else []

        # 解析信号
        signal = self.signal_parser.parse(message_text)
        
        if signal:
            logger.info(f"✓ 识别到交易信号: {signal}")
            # 记录最近开仓（仅 LONG/SHORT）
            if signal.signal_type in [SignalType.LONG, SignalType.BUY, SignalType.SHORT, SignalType.SELL] and chat_id is not None:
                try:
                    self.recent_entries[chat_id] = {
                        'symbol': signal.symbol,
                        'time': datetime.utcnow()
                    }
                except Exception:
                    pass

            # 若本条消息自身属于“止盈提示”，则缓存价格（用于后续无价格触发消息的回填）
            if is_tp_hint and tp_prices and chat_id is not None:
                try:
                    self.last_tp_hint[chat_id] = {'price': tp_prices[0], 'time': datetime.utcnow()}
                except Exception:
                    pass

            # CLOSE 且无价格，但包含“第一/第二”关键词时，尝试使用最近缓存价格进行回填
            if signal.signal_type == SignalType.CLOSE and (not signal.take_profit) and chat_id is not None:
                if (('第一' in message_text) or ('第二' in message_text)) and (chat_id in self.last_tp_hint):
                    hint = self.last_tp_hint.get(chat_id)
                    if hint and (datetime.utcnow() - hint['time'] <= self.tp_infer_window):
                        signal.take_profit = [hint['price']]
                        logger.info(f"✓ 使用缓存止盈价回填分批平仓: {signal.symbol} @ {hint['price']}")
            await self.execute_signal(signal)
        else:
            # 邻近消息推断：无币种的止盈/目标消息，尝试套用窗口内的最近开仓
            try:
                if is_tp_hint and tp_prices and chat_id is not None:
                    # 先缓存价格
                    try:
                        self.last_tp_hint[chat_id] = {'price': tp_prices[0], 'time': datetime.utcnow()}
                    except Exception:
                        pass
                    # 仅当消息包含“第一/第1”或“保本/减仓/減倉”时，即时触发TP1；否则只缓存
                    if (('第一' not in message_text) and ('第1' not in message_text)
                        and ('保本' not in message_text) and ('减仓' not in message_text) and ('減倉' not in message_text)):
                        logger.info("✓ 识别到止盈提示，但非‘第一止盈’，已缓存价格，等待自动策略/后续触发")
                        return
                    inferred_symbol = None
                    # -1) 尝试直接从当前消息中解析币种（例如包含 #0G 等）
                    try:
                        cur_sym = SignalParser._extract_symbol(message_text)
                        if cur_sym:
                            inferred_symbol = cur_sym
                    except Exception:
                        pass
                    # 0) 若为回复消息，优先从被回复内容中解析币种
                    try:
                        reply = await event.get_reply_message() if hasattr(event, 'get_reply_message') else None
                        if reply and getattr(reply, 'text', None):
                            sym = SignalParser._extract_symbol(reply.text)
                            if sym:
                                inferred_symbol = sym
                    except Exception:
                        pass
                    # 1) 优先用20分钟内的最近开仓
                    last = self.recent_entries.get(chat_id)
                    if last and (datetime.utcnow() - last['time'] <= self.tp_infer_window):
                        inferred_symbol = inferred_symbol or last['symbol']
                    # 2) 无近期开仓，则若当前仅有一个持仓，则使用该持仓
                    if not inferred_symbol and len(self.multi_exchange.clients) > 0:
                        # 仅在单账户场景下做此推断，避免多账户错配
                        if len(self.multi_exchange.clients.keys()) == 1:
                            account_name = next(iter(self.multi_exchange.clients.keys()))
                            opens = self.multi_exchange.list_open_positions(account_name)
                            if len(opens) == 1 and opens[0].get('symbol'):
                                inferred_symbol = opens[0]['symbol']
                    if inferred_symbol:
                        inferred_signal = TradingSignal(
                            signal_type=SignalType.CLOSE,
                            symbol=inferred_symbol,
                            entry_price=None,
                            stop_loss=None,
                            take_profit=[tp_prices[0]],
                            leverage=None,
                            raw_message=message_text
                        )
                        logger.info(f"✓ 即时第一止盈：推断 {inferred_symbol}，按50%限价挂单 @ {tp_prices[0]}")
                        await self.execute_signal(inferred_signal)
                    else:
                        logger.debug("止盈提示但缺少可推断的标的，忽略")
                else:
                    logger.debug("未识别到有效的交易信号")
            except Exception as e:
                logger.debug(f"邻近消息推断失败: {e}")
        # 记录已处理消息ID，避免重复处理
        try:
            if chat_id is not None and hasattr(event, 'message') and hasattr(event.message, 'id'):
                pid = self.processed_ids.setdefault(chat_id, set())
                pid.add(event.message.id)
                # 控制集合大小
                if len(pid) > 500:
                    # 任意裁剪（简单做法）
                    self.processed_ids[chat_id] = set(list(pid)[-300:])
        except Exception:
            pass
    
    async def execute_signal(self, signal):
        """执行交易信号"""
        if not Config.TRADING_ENABLED:
            logger.info("⚠ 交易已禁用，仅记录信号")
            return
        
        # 优先使用多交易所客户端
        if len(self.multi_exchange.clients) > 0:
            logger.info(f"📊 使用多交易所模式执行信号")
            await self.executor.execute(signal)
            return
        
        # 后备：使用单交易所客户端
        if self.exchange is None:
            logger.info("初始化单交易所客户端（后备模式）...")
            self.exchange = ExchangeClient()
        if not self.exchange.initialized:
            logger.error("交易所未初始化")
            return
        await self.executor.execute_single(signal, self.exchange)
    

    async def _trailing_monitor_loop(self):
        while True:
            try:
                if order_manager.position_manager:
                    order_manager.position_manager.monitor_positions()
            except Exception:
                pass
            await asyncio.sleep(3)

    async def _position_fill_monitor_loop(self):
        while True:
            try:
                pm = order_manager.position_manager
                if pm is None:
                    await asyncio.sleep(5)
                    continue
                for account_name, symbol, info in list(pm.iter_active_positions()):
                    try:
                        if account_name == 'single' and self.exchange and getattr(self.exchange, 'initialized', False):
                            pos = self.exchange.get_position(symbol)
                            cur_price = self.exchange.get_current_price(symbol)
                        else:
                            pos = self.multi_exchange.get_position(account_name, symbol)
                            cur_price = self.multi_exchange.get_current_price(account_name, symbol)
                        contracts = float(pos.get('contracts')) if pos else 0.0
                        if contracts > 0:
                            continue
                        trade_id = info.get('trade_id') if isinstance(info, dict) else None
                        entry_price = float(info.get('entry_price') or 0.0)
                        position_size = float(info.get('position_size') or 0.0)
                        side = str(info.get('side') or '')
                        lev = int(info.get('leverage') or 1)
                        exit_price = cur_price or entry_price
                        if trade_id and exit_price:
                            try:
                                trading_db.close_trade(int(trade_id), float(exit_price))
                            except Exception:
                                pass
                        try:
                            pnl = 0.0
                            if entry_price and position_size and exit_price:
                                if side == 'buy':
                                    pnl = (exit_price - entry_price) * position_size * lev
                                elif side == 'sell':
                                    pnl = (entry_price - exit_price) * position_size * lev
                            if risk_manager:
                                risk_manager.record_trade(account_name, pnl, closed=True)
                        except Exception:
                            pass
                        try:
                            pm.remove_position(account_name, symbol)
                        except Exception:
                            pass
                    except Exception:
                        continue
            except Exception:
                pass
            await asyncio.sleep(5)


    async def _backfill_recent_messages(self, group_entities, minutes: int = 30, limit: int = 80):
        try:
            since = datetime.utcnow() - timedelta(minutes=minutes)
            for entity in group_entities:
                try:
                    async for msg in self.client.iter_messages(entity, offset_date=since, limit=limit, reverse=True):
                        if not getattr(msg, 'text', None):
                            continue
                        chat_id = getattr(msg, 'chat_id', None)
                        if chat_id is not None:
                            pid = self.processed_ids.setdefault(chat_id, set())
                            if getattr(msg, 'id', None) in pid:
                                continue
                        class _Event:
                            __slots__ = ('message', 'chat_id')
                            def __init__(self, m):
                                self.message = m
                                self.chat_id = getattr(m, 'chat_id', None)
                            async def get_reply_message(self):
                                try:
                                    return await self.message.get_reply_message()
                                except Exception:
                                    return None
                        await self.handle_message(_Event(msg))
                except Exception:
                    continue
        except Exception:
            pass

    def stop(self):
        """停止机器人"""
        if self.client:
            self.client.disconnect()
        logger.info("机器人已停止")

