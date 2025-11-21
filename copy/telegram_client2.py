from telethon import TelegramClient, events
from datetime import datetime, timedelta
from config import Config
from signal_parser import SignalParser, SignalType, TradingSignal
from exchange_client import ExchangeClient
from multi_exchange_client import multi_exchange_client
from smart_order_manager import smart_order_manager
import logging
import asyncio
import re
import order_manager
from database import trading_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TelegramSignalBot:
    """Telegram 信号监听机器人"""
    
    def __init__(self):
        self.client = None
        # 使用多交易所客户端
        self.multi_exchange = multi_exchange_client
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
            order_manager.init_position_manager(self.multi_exchange)
            asyncio.create_task(self._trailing_monitor_loop())
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
        message_text = event.message.text
        chat_id = getattr(event, 'chat_id', None)
        
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
            await self._execute_multi_exchange(signal)
            return
        
        # 后备：使用单交易所客户端
        if self.exchange is None:
            logger.info("初始化单交易所客户端（后备模式）...")
            self.exchange = ExchangeClient()
        
        if not self.exchange.initialized:
            logger.error("交易所未初始化")
            return
        
        try:
            # 设置杠杆
            if signal.leverage:
                self.exchange.set_leverage(signal.symbol, signal.leverage)
            
            # 根据信号类型执行操作
            if signal.signal_type in [SignalType.LONG, SignalType.BUY]:
                await self._execute_long(signal)
            
            elif signal.signal_type in [SignalType.SHORT, SignalType.SELL]:
                await self._execute_short(signal)
            
            elif signal.signal_type == SignalType.CLOSE:
                self.exchange.close_position(signal.symbol)
        
        except Exception as e:
            logger.error(f"执行信号时出错: {e}")
    
    async def _execute_long(self, signal):
        """执行做多操作"""
        logger.info(f"执行做多: {signal.symbol}")
        
        # 1. 创建智能订单计划
        order_plan = smart_order_manager.create_order_plan(signal)
        logger.info(f"\n{smart_order_manager.format_plan_summary(order_plan)}\n")
        
        # 获取当前价格
        current_price = self.exchange.get_current_price(signal.symbol)
        if not current_price:
            logger.error("无法获取当前价格")
            return
        
        # 计算仓位大小
        position_size = self.exchange.calculate_position_size(
            signal.symbol,
            signal.entry_price or current_price,
            Config.RISK_PERCENTAGE
        )
        
        if position_size <= 0:
            logger.error("仓位大小计算错误")
            return
        
        # 2. 执行入场订单
        if signal.entry_price:
            order = self.exchange.place_limit_order(
                signal.symbol, 'buy', position_size, signal.entry_price
            )
        else:
            order = self.exchange.place_market_order(
                signal.symbol, 'buy', position_size
            )
        
        if order:
            logger.info(f"✓ 做多订单已执行: {order.get('id', 'N/A')}")
            try:
                trading_db.record_order(
                    None, 'single', signal.symbol, 'entry', 'buy',
                    price=(order.get('price') or current_price),
                    amount=position_size,
                    status=(order.get('status') or 'placed'),
                    order_id=(order.get('id') if isinstance(order, dict) else None),
                    filled_amount=(order.get('filled') if isinstance(order, dict) else None)
                )
            except Exception:
                pass
            
            # 3. 设置止损订单
            if order_plan['stop_loss']:
                try:
                    sl_order = self.exchange.place_stop_loss_order(
                        signal.symbol, 'sell', position_size, order_plan['stop_loss']
                    )
                    if sl_order:
                        logger.info(f"✓ 止损订单已设置: {order_plan['stop_loss']}")
                        try:
                            trading_db.record_order(None, 'single', signal.symbol, 'stop_loss', 'sell',
                                                    price=order_plan['stop_loss'], amount=position_size,
                                                    status=(sl_order.get('status') if isinstance(sl_order, dict) else 'placed'),
                                                    order_id=(sl_order.get('id') if isinstance(sl_order, dict) else None))
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"⚠ 止损订单设置失败: {e}")
            elif order_plan.get('stop_loss_percent'):
                try:
                    ap = 0.0
                    try:
                        ap = float(order.get('price') or 0)
                    except Exception:
                        ap = 0.0
                    if not ap:
                        try:
                            ap = float(order.get('average') or 0)
                        except Exception:
                            ap = 0.0
                    if not ap:
                        ap = current_price
                    pct = float(order_plan.get('stop_loss_percent', 0)) / 100.0
                    slp = ap * (1 - pct)
                    sl_order = self.exchange.place_stop_loss_order(
                        signal.symbol, 'sell', position_size, slp
                    )
                    if sl_order:
                        logger.info(f"✓ 止损订单已设置: {slp}")
                        try:
                            trading_db.record_order(None, 'single', signal.symbol, 'stop_loss', 'sell',
                                                    price=slp, amount=position_size,
                                                    status=(sl_order.get('status') if isinstance(sl_order, dict) else 'placed'),
                                                    order_id=(sl_order.get('id') if isinstance(sl_order, dict) else None))
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"⚠ 止损订单设置失败: {e}")
            
            # 4. 设置分批止盈订单
            if order_plan['take_profits']:
                for i, (tp_price, tp_portion) in enumerate(
                    zip(order_plan['take_profits'], order_plan['tp_portions']), 1
                ):
                    try:
                        tp_size = position_size * (tp_portion / 100)
                        tp_order = self.exchange.place_take_profit_order(
                            signal.symbol, 'sell', tp_size, tp_price
                        )
                        if tp_order:
                            logger.info(f"✓ TP{i} 已设置: {tp_price} ({tp_portion:.1f}% 仓位)")
                            try:
                                trading_db.record_order(None, 'single', signal.symbol, 'take_profit', 'sell',
                                                        price=tp_price, amount=tp_size,
                                                        status=(tp_order.get('status') if isinstance(tp_order, dict) else 'placed'),
                                                        order_id=(tp_order.get('id') if isinstance(tp_order, dict) else None))
                            except Exception:
                                pass
                    except Exception as e:
                        logger.warning(f"⚠ TP{i} 设置失败: {e}")
            
            logger.info(f"✅ 订单计划执行完成！")
    
    async def _execute_short(self, signal):
        """执行做空操作"""
        logger.info(f"执行做空: {signal.symbol}")
        
        # 1. 创建智能订单计划
        order_plan = smart_order_manager.create_order_plan(signal)
        logger.info(f"\n{smart_order_manager.format_plan_summary(order_plan)}\n")
        
        # 获取当前价格
        current_price = self.exchange.get_current_price(signal.symbol)
        if not current_price:
            logger.error("无法获取当前价格")
            return
        
        # 计算仓位大小
        position_size = self.exchange.calculate_position_size(
            signal.symbol,
            signal.entry_price or current_price,
            Config.RISK_PERCENTAGE
        )
        
        if position_size <= 0:
            logger.error("仓位大小计算错误")
            return
        
        # 2. 执行入场订单
        if signal.entry_price:
            order = self.exchange.place_limit_order(
                signal.symbol, 'sell', position_size, signal.entry_price
            )
        else:
            order = self.exchange.place_market_order(
                signal.symbol, 'sell', position_size
            )
        
        if order:
            logger.info(f"✓ 做空订单已执行: {order.get('id', 'N/A')}")
            try:
                trading_db.record_order(
                    None, 'single', signal.symbol, 'entry', 'sell',
                    price=(order.get('price') or current_price),
                    amount=position_size,
                    status=(order.get('status') or 'placed'),
                    order_id=(order.get('id') if isinstance(order, dict) else None),
                    filled_amount=(order.get('filled') if isinstance(order, dict) else None)
                )
            except Exception:
                pass
            
            # 3. 设置止损订单
            if order_plan['stop_loss']:
                try:
                    sl_order = self.exchange.place_stop_loss_order(
                        signal.symbol, 'buy', position_size, order_plan['stop_loss']
                    )
                    if sl_order:
                        logger.info(f"✓ 止损订单已设置: {order_plan['stop_loss']}")
                except Exception as e:
                    logger.warning(f"⚠ 止损订单设置失败: {e}")
            elif order_plan.get('stop_loss_percent'):
                try:
                    ap = 0.0
                    try:
                        ap = float(order.get('price') or 0)
                    except Exception:
                        ap = 0.0
                    if not ap:
                        try:
                            ap = float(order.get('average') or 0)
                        except Exception:
                            ap = 0.0
                    if not ap:
                        ap = current_price
                    pct = float(order_plan.get('stop_loss_percent', 0)) / 100.0
                    slp = ap * (1 + pct)
                    sl_order = self.exchange.place_stop_loss_order(
                        signal.symbol, 'buy', position_size, slp
                    )
                    if sl_order:
                        logger.info(f"✓ 止损订单已设置: {slp}")
                        try:
                            trading_db.record_order(None, 'single', signal.symbol, 'stop_loss', 'buy',
                                                    price=slp, amount=position_size,
                                                    status=(sl_order.get('status') if isinstance(sl_order, dict) else 'placed'),
                                                    order_id=(sl_order.get('id') if isinstance(sl_order, dict) else None))
                        except Exception:
                            pass
                except Exception as e:
                    logger.warning(f"⚠ 止损订单设置失败: {e}")
    async def _execute_multi_exchange(self, signal):
        """在多个交易所执行信号"""
        logger.info(f"🔄 开始在 {len(self.multi_exchange.clients)} 个交易所执行信号")
        
        # 创建智能订单计划
        order_plan = smart_order_manager.create_order_plan(signal)
        logger.info(f"\n{smart_order_manager.format_plan_summary(order_plan)}\n")
        
        # 在每个启用的交易所执行
        for account_name in self.multi_exchange.clients.keys():
            try:
                logger.info(f"📍 正在 {account_name} 执行...")
                
                # 获取当前价格（用于市价单）
                entry_price = signal.entry_price
                if not entry_price:
                    # 市价单，获取当前价格
                    entry_price = self.multi_exchange.get_current_price(account_name, signal.symbol)
                    if not entry_price:
                        logger.warning(f"⚠ {account_name}: 无法获取 {signal.symbol} 价格")
                        continue
                
                # CLOSE 信号：支持分批平仓（按消息中的'第一/第二止盈'关键词与价格）
                if signal.signal_type == SignalType.CLOSE:
                    # 优先尝试价格型平仓（reduce-only 限价部分平仓）
                    tp_price = None
                    if signal.take_profit:
                        # 取首个价格
                        tp_price = signal.take_profit[0]
                    
                    if tp_price:
                        pos = self.multi_exchange.get_position(account_name, signal.symbol)
                        if not pos:
                            logger.info("  ⚠ 无持仓可平")
                            continue
                        # 仅处理“第一/第二止盈”，其它提示忽略（已由自动策略管理）
                        msg = (signal.raw_message or "")
                        if ("第一" in msg) or ("第1" in msg):
                            portion = 0.5
                        elif "第二" in msg:
                            portion = 0.3
                        else:
                            logger.info("  ⏭ 已有自动分批策略，忽略非‘第一/第二’的止盈提示")
                            continue
                        # 份额：第一止盈默认50%，第二止盈30%
                        if ("第一" in msg) or ("第1" in msg):
                            portion = 0.5
                        else:
                            portion = 0.3
                        amount_to_close = pos['contracts'] * portion
                        side = 'buy' if pos['side'] == 'short' else 'sell'
                        # 切换到价格型TP前，先清理可能存在的回退 reduce-only 止盈挂单
                        try:
                            cancelled = self.multi_exchange.cancel_open_reduce_only_orders(account_name, signal.symbol)
                            if cancelled:
                                logger.info(f"  ✓ 已取消 {cancelled} 个回退止盈挂单，改用价格型TP1")
                        except Exception:
                            pass

                        tp_order = self.multi_exchange.place_take_profit_order(
                            account_name, signal.symbol, side, amount_to_close, tp_price
                        )
                        if tp_order:
                            logger.info(f"  ✓ 已挂出分批止盈: {tp_price}，数量: {amount_to_close:.6f}")
                            try:
                                trading_db.record_order(None, account_name, signal.symbol, 'take_profit', side,
                                                        price=tp_price, amount=amount_to_close,
                                                        status=(tp_order.get('status') if isinstance(tp_order, dict) else 'placed'),
                                                        order_id=(tp_order.get('id') if isinstance(tp_order, dict) else None))
                            except Exception:
                                pass
                            # 若为“第一止盈”消息：
                            if ("第一" in msg) or ("第1" in msg):
                                # 1) 自动挂出后续TP2/TP3（30% / 20% 原始仓位）
                                entry_price = pos.get('entry_price')
                                self._place_followup_tps(
                                    account_name, signal.symbol, pos.get('side'), entry_price,
                                    original_contracts=pos['contracts'], already_closed=amount_to_close
                                )
                                # 2) 监控TP1成交后，将止损移动到保本位
                                try:
                                    order_id = tp_order.get('order_id') if isinstance(tp_order, dict) else None
                                    if order_id:
                                        asyncio.create_task(
                                            self._monitor_tp1_and_move_sl(account_name, signal.symbol, pos.get('side'), order_id)
                                        )
                                except Exception:
                                    pass
                        else:
                            # 分批止盈下单失败：仅告警，不触发全平，避免误清仓
                            logger.warning("  ⚠ 分批止盈下单失败，已忽略（不全平）")
                    else:
                        # 无价格：如果是“止盈已触发/請平倉”等提示，跳过，不全平
                        raw = (signal.raw_message or "")
                        trigger_words = ["止盈", "已触发", "已觸發", "請平倉", "请平仓", "已觸發 請平倉"]
                        if any(w in raw for w in trigger_words):
                            logger.info("  ⏭ 触发类提示(无价格)已忽略，不进行平仓")
                            continue
                        # 非触发提示的明确 CLOSE（无价格）才执行全平
                        closed = self.multi_exchange.close_position(account_name, signal.symbol)
                        logger.info("  ✓ 已平仓" if closed else "  ⚠ 无持仓可平")
                    continue

                # 计算仓位大小
                position_size = self.multi_exchange.calculate_position_size(account_name, signal.symbol, entry_price)
                
                if position_size <= 0:
                    logger.warning(f"⚠ {account_name}: 仓位大小计算错误")
                    continue
                
                logger.info(f"  仓位大小: {position_size}")
                
                # 根据信号类型执行
                if signal.signal_type in [SignalType.LONG, SignalType.BUY]:
                    side = 'buy'
                elif signal.signal_type in [SignalType.SHORT, SignalType.SELL]:
                    side = 'sell'
                else:
                    continue
                
                # 🔧 计算初始止损价格（入场价±4%）
                sl_price = entry_price * (0.96 if side == 'buy' else 1.04)
                
                # 执行入场订单（不附带止损）
                order_result = self.multi_exchange.place_market_order(
                    account_name, signal.symbol, side, position_size
                )
                
                if order_result and order_result.get('status') == 'success':
                    logger.info(f"  ✓ 入场订单已执行")
                    logger.info(f"  订单ID: {order_result.get('order_id')}")
                    try:
                        trading_db.record_order(None, account_name, signal.symbol, 'entry', side,
                                                price=(order_result.get('price')), amount=(order_result.get('amount')),
                                                status=order_result.get('status'), order_id=order_result.get('order_id'))
                    except Exception:
                        pass
                    
                    # 单独提交初始止损计划单
                    try:
                        sl_side = 'sell' if side == 'buy' else 'buy'
                        sl_order = self.multi_exchange.place_stop_loss_order(
                            account_name, signal.symbol, sl_side, position_size, sl_price
                        )
                        if sl_order:
                            logger.info(f"  ✓ 已设置初始止损(-4%): {sl_price}")
                            try:
                                trading_db.record_order(None, account_name, signal.symbol, 'stop_loss', sl_side,
                                                        price=sl_price, amount=position_size,
                                                        status=(sl_order.get('status') if isinstance(sl_order, dict) else 'placed'),
                                                        order_id=(sl_order.get('id') if isinstance(sl_order, dict) else None))
                            except Exception:
                                pass
                        else:
                            logger.warning("  ⚠ 初始止损设置失败")
                    except Exception as e:
                        logger.warning(f"  ⚠ 初始止损设置失败: {e}")
                    
                    # 执行止盈订单
                    base_price = order_result.get('price') or entry_price
                    try:
                        self._register_position_for_trailing(account_name, signal.symbol, side, base_price, position_size, order_plan, sl_price)
                    except Exception:
                        pass
                    if order_plan['take_profits']:
                        tp_side = 'sell' if side == 'buy' else 'buy'
                        first_tp_order_id = None
                        for i, (tp_price, tp_portion) in enumerate(zip(
                            order_plan['take_profits'], 
                            order_plan['tp_portions']
                        ), 1):
                            try:
                                tp_size = position_size * (tp_portion / 100.0)
                                tp_order = self.multi_exchange.place_take_profit_order(
                                    account_name, signal.symbol, tp_side,
                                    tp_size, tp_price
                                )
                                if tp_order:
                                    logger.info(f"  ✓ TP{i} 已设置: {tp_price} ({tp_portion}% 仓位, 数量: {tp_size:.4f})")
                                    if i == 1:
                                        first_tp_order_id = tp_order.get('order_id') if isinstance(tp_order, dict) else None
                                else:
                                    logger.warning(f"  ⚠ TP{i} 设置失败")
                            except Exception as e:
                                logger.warning(f"  ⚠ TP{i} 设置失败: {e}")

                        # 监控回退TP1成交后移动止损到保本位
                        if first_tp_order_id:
                            pos_side = 'long' if side == 'buy' else 'short'
                            try:
                                asyncio.create_task(
                                    self._monitor_tp1_and_move_sl(account_name, signal.symbol, pos_side, first_tp_order_id)
                                )
                            except Exception:
                                pass
                    else:
                        # 无价格型TP：入场后按 10%/20%/50% 自动挂三档 reduce-only（50%/30%/20%）
                        try:
                            cfg = getattr(smart_order_manager, 'config', None)
                            add_tps = (cfg.additional_tps if cfg else None) or [
                                {'profit_percent': 10.0, 'portion_percent': 50.0},
                                {'profit_percent': 20.0, 'portion_percent': 30.0},
                                {'profit_percent': 50.0, 'portion_percent': 20.0},
                            ]
                            tp_side = 'sell' if side == 'buy' else 'buy'
                            first_tp_order_id = None
                            placed_total = 0.0
                            for i, tp in enumerate(add_tps, 1):
                                profit_pct = float(tp.get('profit_percent', 0.0)) / 100.0
                                portion_pct = float(tp.get('portion_percent', 0.0))
                                tp_amount = position_size * (portion_pct / 100.0)
                                if tp_amount <= 0 or not base_price:
                                    continue
                                tp_price = base_price * (1 + profit_pct) if side == 'buy' else base_price * (1 - profit_pct)
                                tp_order = self.multi_exchange.place_take_profit_order(
                                    account_name, signal.symbol, tp_side, tp_amount, tp_price
                                )
                                if tp_order:
                                    placed_total += tp_amount
                                    logger.info(f"  ✓ 回退TP{i} 已设置: {tp_price} ({portion_pct}% 仓位, 数量: {tp_amount:.4f})")
                                    if i == 1:
                                        first_tp_order_id = tp_order.get('order_id') if isinstance(tp_order, dict) else None
                                    try:
                                        trading_db.record_order(None, account_name, signal.symbol, 'take_profit', tp_side,
                                                                price=tp_price, amount=tp_amount,
                                                                status=(tp_order.get('status') if isinstance(tp_order, dict) else 'placed'),
                                                                order_id=(tp_order.get('id') if isinstance(tp_order, dict) else None))
                                    except Exception:
                                        pass
                                else:
                                    logger.warning(f"  ⚠ 回退TP{i} 设置失败")

                            # 监控回退TP1成交后移动止损到保本位
                            if first_tp_order_id:
                                pos_side = 'long' if side == 'buy' else 'short'
                                try:
                                    asyncio.create_task(
                                        self._monitor_tp1_and_move_sl(account_name, signal.symbol, pos_side, first_tp_order_id)
                                    )
                                except Exception:
                                    pass
                        except Exception as e:
                            logger.warning(f"  ⚠ 回退分批止盈挂单失败: {e}")
                else:
                    logger.error(f"  ✗ {account_name}: 订单执行失败")
                    continue
                
            except Exception as e:
                logger.error(f"✗ {account_name} 执行失败: {e}")
                continue
        
        logger.info(f"✅ 多交易所信号执行完成")

    async def _trailing_monitor_loop(self):
        while True:
            try:
                if order_manager.position_manager:
                    order_manager.position_manager.monitor_positions()
            except Exception:
                pass
            await asyncio.sleep(3)

    def _register_position_for_trailing(self, account_name, symbol, side, entry_price, position_size, order_plan, stop_loss_price):
        try:
            if order_manager.position_manager is None:
                return
            info = {
                'entry_price': entry_price,
                'position_size': position_size,
                'side': side,
                'stop_loss': stop_loss_price,
                'take_profits': order_plan.get('take_profits'),
                'tp_portions': order_plan.get('tp_portions'),
                'trailing_stop_pct': (order_plan.get('trailing_stop_percent') if order_plan.get('trailing_stop') else None),
                'move_sl_to_breakeven': order_plan.get('move_to_breakeven'),
                'breakeven_trigger_pct': order_plan.get('breakeven_trigger_percent'),
                'highest_price': entry_price if side == 'buy' else None,
                'lowest_price': entry_price if side == 'sell' else None,
                'sl_moved_to_breakeven': False,
                'entry_time': datetime.now(),
            }
            order_manager.position_manager._save_position_info(account_name, symbol, info)
        except Exception:
            pass
    
    async def _monitor_tp1_and_move_sl(self, account_name: str, symbol: str, pos_side: str, tp_order_id: str):
        """轮询监控 TP1 是否成交，成交后将止损移动到保本位，并保持追踪止损策略。"""
        try:
            # 轮询最多2小时，每3秒检查一次
            deadline = asyncio.get_event_loop().time() + 2 * 60 * 60
            while asyncio.get_event_loop().time() < deadline:
                status = self.multi_exchange.fetch_order_status(account_name, symbol, tp_order_id)
                if status and status.get('status') in ('closed', 'canceled'):  # 成交或被取消则退出
                    break
                await asyncio.sleep(3)

            if not status or status.get('status') != 'closed':
                logger.info("  ⚠ TP1 未在监控窗口内成交/已取消，跳过保本止损移动")
                return

            # 成交后，获取最新持仓与入场价
            pos = self.multi_exchange.get_position(account_name, symbol)
            if not pos:
                logger.info("  ⚠ TP1 成交后无剩余持仓")
                return
            entry_price = pos.get('entry_price')
            remaining = float(pos.get('contracts') or 0)
            if not entry_price or remaining <= 0:
                logger.info("  ⚠ 无法获取保本价或无剩余仓位")
                return

            sl_side = 'buy' if pos_side == 'long' else 'sell'
            sl_order = self.multi_exchange.place_stop_loss_order(
                account_name, symbol, sl_side, remaining, entry_price
            )
            if sl_order:
                logger.info(f"  ✓ 已将止损移动到保本位: {entry_price}")
            else:
                logger.warning("  ⚠ 保本止损下单失败")
        except Exception as e:
            logger.warning(f"  ⚠ 监控TP1并移动保本止损失败: {e}")

    def _place_followup_tps(self, account_name: str, symbol: str, pos_side: str, entry_price: float, original_contracts: float, already_closed: float):
        """在 TP1 挂出后，自动为剩余仓位挂出后续 TP2/TP3 限价 reduce-only 订单。"""
        try:
            if not entry_price or original_contracts <= 0:
                return
            # 剩余仓位 = 原仓位 - 已挂出的TP1数量（50%）
            remaining = max(original_contracts - already_closed, 0.0)
            if remaining <= 0:
                return

            # 方向：止盈下单方向与持仓方向相反
            tp_side = 'buy' if pos_side == 'short' else 'sell'

            # 价格：固定使用 20% 与 40% 作为 TP2/TP3 目标
            targets = [{'profit_percent': 20.0}, {'profit_percent': 40.0}]

            # 数量：第二止盈按原始仓位的30%，第三止盈按原始仓位的20%（剩余全挂在第三止盈以抵消精度误差）
            tp2_amount = original_contracts * 0.30
            tp3_amount = max(remaining - tp2_amount, 0.0)

            for idx, (target, amount) in enumerate(zip(targets, [tp2_amount, tp3_amount]), start=2):
                if amount <= 0:
                    continue
                profit_pct = float(target.get('profit_percent') or 0.0) / 100.0
                if pos_side == 'long':
                    tp_price = entry_price * (1 + profit_pct)
                else:
                    tp_price = entry_price * (1 - profit_pct)
                order = self.multi_exchange.place_take_profit_order(
                    account_name, symbol, tp_side, amount, tp_price
                )
                if order:
                    logger.info(f"  ✓ 自动挂出TP{idx}: 价 {tp_price}, 数量 {amount:.6f}")
                else:
                    logger.warning(f"  ⚠ 自动TP{idx} 下单失败")
        except Exception as e:
            logger.warning(f"  ⚠ 自动挂出后续TP失败: {e}")

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

