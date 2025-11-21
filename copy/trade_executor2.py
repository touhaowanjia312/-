import asyncio
import logging
from datetime import datetime
from typing import Optional
from config import Config
from retry_utils import log_struct

from signal_parser import SignalType
from smart_order_manager import smart_order_manager
from database import trading_db
import order_manager
from risk_manager import risk_manager

logger = logging.getLogger(__name__)


class TradeExecutor:
    def __init__(self, multi_exchange):
        self.multi_exchange = multi_exchange

    async def execute(self, signal):
        if len(self.multi_exchange.clients) > 0:
            await self._execute_multi_exchange(signal)
        else:
            logger.info("单交易所执行器抽象将在下一步对接，当前仅走多交易所路径")

    async def execute_single(self, signal, exchange_client):
        """单交易所执行路径。account_name 固定为 'single'。"""
        try:
            try:
                log_struct(logger, logging.INFO, 'exec_start', mode='single', symbol=getattr(signal, 'symbol', None), signal_type=str(getattr(signal, 'signal_type', None)), leverage=getattr(signal, 'leverage', None))
            except Exception:
                pass
            order_plan = smart_order_manager.create_order_plan(signal)
            logger.info(f"\n{smart_order_manager.format_plan_summary(order_plan)}\n")

            # 获取入场价
            entry_price = signal.entry_price
            if not entry_price:
                entry_price = exchange_client.get_current_price(signal.symbol)
                if not entry_price:
                    logger.error("无法获取当前价格")
                    return

            # CLOSE 处理
            if signal.signal_type == SignalType.CLOSE:
                tp_price = None
                if signal.take_profit:
                    tp_price = signal.take_profit[0]
                if tp_price:
                    pos = exchange_client.get_position(signal.symbol)
                    if not pos:
                        logger.info("  ⚠ 无持仓可平")
                        return
                    msg = (signal.raw_message or "")
                    if ("第一" in msg) or ("第1" in msg):
                        portion = 0.5
                    elif "第二" in msg:
                        portion = 0.3
                    else:
                        logger.info("  ⏭ 已有自动分批策略，忽略非‘第一/第二’的止盈提示")
                        return
                    amount_to_close = float(pos['contracts']) * portion
                    side = 'buy' if pos['side'] == 'short' else 'sell'
                    tp_order = exchange_client.place_take_profit_order(
                        signal.symbol, side, amount_to_close, tp_price
                    )
                    if tp_order:
                        logger.info(f"  ✓ 已挂出分批止盈: {tp_price}，数量: {amount_to_close:.6f}")
                        try:
                            trading_db.record_order(None, 'single', signal.symbol, 'take_profit', side,
                                                    price=tp_price, amount=amount_to_close,
                                                    status=(tp_order.get('status') if isinstance(tp_order, dict) else 'placed'),
                                                    order_id=(tp_order.get('id') if isinstance(tp_order, dict) else None))
                        except Exception:
                            pass
                    else:
                        logger.warning("  ⚠ 分批止盈下单失败，已忽略（不全平）")
                    return
                else:
                    pre = None
                    try:
                        pre = exchange_client.get_position(signal.symbol)
                    except Exception:
                        pre = None
                    closed = exchange_client.close_position(signal.symbol)
                    logger.info("  ✓ 已平仓" if closed else "  ⚠ 无持仓可平")
                    if closed and pre and risk_manager:
                        try:
                            entry_p = float(pre.get('entry_price') or 0.0)
                            side_p = str(pre.get('side') or '')
                            cur_p = exchange_client.get_current_price(signal.symbol) or entry_p
                            lev = int(signal.leverage or 1)
                            contracts = float(pre.get('contracts') or 0.0)
                            pnl = 0.0
                            if entry_p and contracts:
                                if side_p == 'long':
                                    pnl = (cur_p - entry_p) * contracts * lev
                                elif side_p == 'short':
                                    pnl = (entry_p - cur_p) * contracts * lev
                            risk_manager.record_trade('single', pnl, closed=True)
                        except Exception:
                            pass
                    if closed:
                        try:
                            ti = None
                            if order_manager.position_manager:
                                info = order_manager.position_manager.get_position_info('single', signal.symbol)
                                if info:
                                    ti = info.get('trade_id')
                            if ti:
                                ep = exchange_client.get_current_price(signal.symbol)
                                if ep:
                                    trading_db.close_trade(ti, float(ep))
                        except Exception:
                            pass
                    return

            # 计算仓位
            position_size = exchange_client.calculate_position_size(
                signal.symbol,
                entry_price,
                Config.RISK_PERCENTAGE,
            )
            if position_size <= 0:
                logger.error("仓位大小计算错误")
                return
            tv = 0.0
            try:
                tv = float(position_size) * float(entry_price)
            except Exception:
                tv = 0.0
            rm = None
            try:
                rm = risk_manager
            except Exception:
                rm = None
            if rm:
                try:
                    ok, reason = rm.can_open_trade('single', tv)
                except Exception:
                    ok, reason = True, ""
                if not ok:
                    logger.warning(f"  ⚠ 受风控限制，拒绝开仓: {reason}")
                    try:
                        log_struct(logger, logging.WARNING, 'risk_blocked', account='single', symbol=signal.symbol, reason=reason, tv=tv)
                    except Exception:
                        pass
                    try:
                        trading_db.record_risk_event('single', 'BLOCKED_OPEN', reason, severity='WARN')
                    except Exception:
                        pass
                    return

            # 下单
            side = 'buy' if signal.signal_type in [SignalType.LONG, SignalType.BUY] else 'sell'
            order_result = None
            if signal.entry_price:
                order_result = exchange_client.place_limit_order(signal.symbol, side, position_size, signal.entry_price)
            else:
                order_result = exchange_client.place_market_order(signal.symbol, side, position_size)
            if not order_result:
                logger.error("  ✗ 单交易所: 订单执行失败")
                return
            logger.info("  ✓ 入场订单已执行")
            try:
                log_struct(logger, logging.INFO, 'entry_order_placed', account='single', symbol=signal.symbol, side=side, amount=position_size, price=(order_result.get('price') or entry_price), order_id=(order_result.get('id') if isinstance(order_result, dict) else None))
            except Exception:
                pass
            try:
                trading_db.record_order(None, 'single', signal.symbol, 'entry', side,
                                        price=(order_result.get('price') or entry_price), amount=(order_result.get('amount') or position_size),
                                        status=(order_result.get('status') or 'placed'), order_id=(order_result.get('id') if isinstance(order_result, dict) else None))
            except Exception:
                pass

            # 记录 trade
            sl_price = entry_price * (0.96 if side == 'buy' else 1.04)
            trade_id = None
            try:
                lev = int(signal.leverage or 1)
                base_price2 = order_result.get('price') or entry_price
                trade_id = trading_db.record_trade(
                    'single', signal.symbol, side,
                    base_price2, position_size, lev,
                    stop_loss=sl_price,
                    take_profit=(order_plan['take_profits'] or []),
                    trailing_stop_pct=order_plan.get('trailing_stop_percent'),
                    notes='single'
                )
                try:
                    log_struct(logger, logging.INFO, 'trade_recorded', account='single', trade_id=trade_id, symbol=signal.symbol, entry_price=base_price2, size=position_size, leverage=lev)
                except Exception:
                    pass
            except Exception:
                trade_id = None
            try:
                if risk_manager:
                    risk_manager.record_trade('single', 0.0, closed=False)
            except Exception:
                pass

            # 设置止损
            try:
                sl_side = 'sell' if side == 'buy' else 'buy'
                sl_order = exchange_client.place_stop_loss_order(
                    signal.symbol, sl_side, position_size, sl_price
                )
                if sl_order:
                    logger.info(f"  ✓ 已设置初始止损(-4%): {sl_price}")
                    try:
                        log_struct(logger, logging.INFO, 'sl_placed', account='single', symbol=signal.symbol, side=sl_side, amount=position_size, stop_price=sl_price)
                    except Exception:
                        pass
                    try:
                        trading_db.record_order(None, 'single', signal.symbol, 'stop_loss', sl_side,
                                                price=sl_price, amount=position_size,
                                                status=(sl_order.get('status') if isinstance(sl_order, dict) else 'placed'),
                                                order_id=(sl_order.get('id') if isinstance(sl_order, dict) else None))
                    except Exception:
                        pass
                else:
                    logger.warning("  ⚠ 初始止损设置失败")
            except Exception as e:
                logger.warning(f"  ⚠ 初始止损设置失败: {e}")

            # 登记持仓信息（供后台监控自动落库PnL）
            try:
                self._register_position_for_trailing('single', signal.symbol, side, entry_price, position_size, order_plan, sl_price, trade_id)
                try:
                    log_struct(logger, logging.INFO, 'position_registered', account='single', symbol=signal.symbol, entry_price=entry_price, size=position_size, trade_id=trade_id)
                except Exception:
                    pass
            except Exception:
                pass

            # 止盈
            base_price = order_result.get('price') or entry_price
            if order_plan['take_profits']:
                tp_side = 'sell' if side == 'buy' else 'buy'
                for i, (tp_price, tp_portion) in enumerate(zip(order_plan['take_profits'], order_plan['tp_portions']), 1):
                    try:
                        tp_size = position_size * (tp_portion / 100.0)
                        tp_order = exchange_client.place_take_profit_order(
                            signal.symbol, tp_side, tp_size, tp_price
                        )
                        if tp_order:
                            logger.info(f"  ✓ TP{i} 已设置: {tp_price} ({tp_portion}% 仓位, 数量: {tp_size:.4f})")
                            try:
                                log_struct(logger, logging.INFO, 'tp_placed', account='single', symbol=signal.symbol, idx=i, portion=tp_portion, amount=tp_size, price=tp_price)
                            except Exception:
                                pass
                            try:
                                trading_db.record_order(None, 'single', signal.symbol, 'take_profit', tp_side,
                                                        price=tp_price, amount=tp_size,
                                                        status=(tp_order.get('status') if isinstance(tp_order, dict) else 'placed'),
                                                        order_id=(tp_order.get('id') if isinstance(tp_order, dict) else None))
                            except Exception:
                                pass
                        else:
                            logger.warning(f"  ⚠ TP{i} 设置失败")
                    except Exception as e:
                        logger.warning(f"  ⚠ TP{i} 设置失败: {e}")
            else:
                try:
                    cfg = getattr(smart_order_manager, 'config', None)
                    add_tps = (cfg.additional_tps if cfg else None) or [
                        {'profit_percent': 10.0, 'portion_percent': 50.0},
                        {'profit_percent': 20.0, 'portion_percent': 30.0},
                        {'profit_percent': 50.0, 'portion_percent': 20.0},
                    ]
                    tp_side = 'sell' if side == 'buy' else 'buy'
                    for i, tp in enumerate(add_tps, 1):
                        profit_pct = float(tp.get('profit_percent', 0.0)) / 100.0
                        portion_pct = float(tp.get('portion_percent', 0.0))
                        tp_amount = position_size * (portion_pct / 100.0)
                        if tp_amount <= 0 or not base_price:
                            continue
                        tp_price = base_price * (1 + profit_pct) if side == 'buy' else base_price * (1 - profit_pct)
                        tp_order = exchange_client.place_take_profit_order(
                            signal.symbol, tp_side, tp_amount, tp_price
                        )
                        if tp_order:
                            logger.info(f"  ✓ 回退TP{i} 已设置: {tp_price} ({portion_pct}% 仓位, 数量: {tp_amount:.4f})")
                            try:
                                log_struct(logger, logging.INFO, 'tp_fallback_placed', account='single', symbol=signal.symbol, idx=i, portion=portion_pct, amount=tp_amount, price=tp_price)
                            except Exception:
                                pass
                            try:
                                trading_db.record_order(None, 'single', signal.symbol, 'take_profit', tp_side,
                                                        price=tp_price, amount=tp_amount,
                                                        status=(tp_order.get('status') if isinstance(tp_order, dict) else 'placed'),
                                                        order_id=(tp_order.get('id') if isinstance(tp_order, dict) else None))
                            except Exception:
                                pass
                        else:
                            logger.warning(f"  ⚠ 回退TP{i} 设置失败")
                except Exception as e:
                    logger.warning(f"  ⚠ 回退分批止盈挂单失败: {e}")
        except Exception as e:
            logger.error(f"单交易所执行失败: {e}")

    async def _execute_multi_exchange(self, signal):
        try:
            log_struct(logger, logging.INFO, 'exec_start', mode='multi', symbol=getattr(signal, 'symbol', None), signal_type=str(getattr(signal, 'signal_type', None)), leverage=getattr(signal, 'leverage', None))
        except Exception:
            pass
        order_plan = smart_order_manager.create_order_plan(signal)
        logger.info(f"\n{smart_order_manager.format_plan_summary(order_plan)}\n")
        for account_name in self.multi_exchange.clients.keys():
            try:
                logger.info(f"📍 正在 {account_name} 执行...")
                entry_price = signal.entry_price
                if not entry_price:
                    entry_price = self.multi_exchange.get_current_price(account_name, signal.symbol)
                    if not entry_price:
                        logger.warning(f"⚠ {account_name}: 无法获取 {signal.symbol} 价格")
                        continue
                if signal.signal_type == SignalType.CLOSE:
                    tp_price = None
                    if signal.take_profit:
                        tp_price = signal.take_profit[0]
                    if tp_price:
                        pos = self.multi_exchange.get_position(account_name, signal.symbol)
                        if not pos:
                            logger.info("  ⚠ 无持仓可平")
                            continue
                        msg = (signal.raw_message or "")
                        if ("第一" in msg) or ("第1" in msg):
                            portion = 0.5
                        elif "第二" in msg:
                            portion = 0.3
                        else:
                            logger.info("  ⏭ 已有自动分批策略，忽略非‘第一/第二’的止盈提示")
                            continue
                        if ("第一" in msg) or ("第1" in msg):
                            portion = 0.5
                        else:
                            portion = 0.3
                        amount_to_close = pos['contracts'] * portion
                        side = 'buy' if pos['side'] == 'short' else 'sell'
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
                            if ("第一" in msg) or ("第1" in msg):
                                entry_p = pos.get('entry_price')
                                self._place_followup_tps(
                                    account_name, signal.symbol, pos.get('side'), entry_p,
                                    original_contracts=pos['contracts'], already_closed=amount_to_close
                                )
                                try:
                                    order_id = tp_order.get('order_id') if isinstance(tp_order, dict) else None
                                    if order_id:
                                        asyncio.create_task(
                                            self._monitor_tp1_and_move_sl(account_name, signal.symbol, pos.get('side'), order_id)
                                        )
                                except Exception:
                                    pass
                        else:
                            logger.warning("  ⚠ 分批止盈下单失败，已忽略（不全平）")
                    else:
                        raw = (signal.raw_message or "")
                        trigger_words = ["止盈", "已触发", "已觸發", "請平倉", "请平仓", "已觸發 請平倉"]
                        if any(w in raw for w in trigger_words):
                            logger.info("  ⏭ 触发类提示(无价格)已忽略，不进行平仓")
                            continue
                        pre = None
                        try:
                            pre = self.multi_exchange.get_position(account_name, signal.symbol)
                        except Exception:
                            pre = None
                        closed = self.multi_exchange.close_position(account_name, signal.symbol)
                        logger.info("  ✓ 已平仓" if closed else "  ⚠ 无持仓可平")
                        if closed and pre and risk_manager:
                            try:
                                entry_p = float(pre.get('entry_price') or 0.0)
                                side_p = str(pre.get('side') or '')
                                cur_p = self.multi_exchange.get_current_price(account_name, signal.symbol) or entry_p
                                lev = getattr(self.multi_exchange.accounts.get(account_name, None), 'default_leverage', 1) or 1
                                contracts = float(pre.get('contracts') or 0.0)
                                pnl = 0.0
                                if entry_p and contracts:
                                    if side_p == 'long':
                                        pnl = (cur_p - entry_p) * contracts * lev
                                    elif side_p == 'short':
                                        pnl = (entry_p - cur_p) * contracts * lev
                                risk_manager.record_trade(account_name, pnl, closed=True)
                                try:
                                    log_struct(logger, logging.INFO, 'trade_closed_signal', account=account_name, symbol=signal.symbol, pnl=pnl)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                        if closed:
                            try:
                                ti = None
                                if order_manager.position_manager:
                                    info = order_manager.position_manager.get_position_info(account_name, signal.symbol)
                                    if info:
                                        ti = info.get('trade_id')
                                if ti:
                                    ep = self.multi_exchange.get_current_price(account_name, signal.symbol)
                                    if ep:
                                        trading_db.close_trade(ti, float(ep))
                            except Exception:
                                pass
                        continue
                position_size = self.multi_exchange.calculate_position_size(account_name, signal.symbol, entry_price)
                if position_size <= 0:
                    logger.warning(f"⚠ {account_name}: 仓位大小计算错误")
                    continue
                try:
                    tv = float(position_size) * float(entry_price)
                except Exception:
                    tv = 0.0
                rm = None
                try:
                    rm = risk_manager
                except Exception:
                    rm = None
                if rm:
                    try:
                        ok, reason = rm.can_open_trade(account_name, tv)
                    except Exception:
                        ok, reason = True, ""
                    if not ok:
                        logger.warning(f"  ⚠ 受风控限制，拒绝开仓: {reason}")
                        try:
                            log_struct(logger, logging.WARNING, 'risk_blocked', account=account_name, symbol=signal.symbol, reason=reason, tv=tv)
                        except Exception:
                            pass
                        try:
                            trading_db.record_risk_event(account_name, 'BLOCKED_OPEN', reason, severity='WARN')
                        except Exception:
                            pass
                        continue
                logger.info(f"  仓位大小: {position_size}")
                if signal.signal_type in [SignalType.LONG, SignalType.BUY]:
                    side = 'buy'
                elif signal.signal_type in [SignalType.SHORT, SignalType.SELL]:
                    side = 'sell'
                else:
                    continue
                sl_price = entry_price * (0.96 if side == 'buy' else 1.04)
                order_result = self.multi_exchange.place_market_order(
                    account_name, signal.symbol, side, position_size
                )
                if order_result and order_result.get('status') == 'success':
                    logger.info("  ✓ 入场订单已执行")
                    logger.info(f"  订单ID: {order_result.get('order_id')}")
                    try:
                        log_struct(logger, logging.INFO, 'entry_order_placed', account=account_name, symbol=signal.symbol, side=side, amount=position_size, price=(order_result.get('price') or entry_price), order_id=(order_result.get('order_id') if isinstance(order_result, dict) else None))
                    except Exception:
                        pass
                    try:
                        trading_db.record_order(None, account_name, signal.symbol, 'entry', side,
                                                price=(order_result.get('price')), amount=(order_result.get('amount')),
                                                status=order_result.get('status'), order_id=order_result.get('order_id'))
                    except Exception:
                        pass
                    trade_id = None
                    try:
                        acct = self.multi_exchange.accounts.get(account_name)
                        lev = getattr(acct, 'default_leverage', None) or 1
                        base_price2 = order_result.get('price') or entry_price
                        trade_id = trading_db.record_trade(
                            account_name, signal.symbol, side,
                            base_price2, position_size, lev,
                            stop_loss=sl_price,
                            take_profit=(order_plan['take_profits'] or []),
                            trailing_stop_pct=order_plan.get('trailing_stop_percent'),
                            notes='multi'
                        )
                        try:
                            log_struct(logger, logging.INFO, 'trade_recorded', account=account_name, trade_id=trade_id, symbol=signal.symbol, entry_price=base_price2, size=position_size, leverage=lev)
                        except Exception:
                            pass
                    except Exception:
                        trade_id = None
                    try:
                        if risk_manager:
                            risk_manager.record_trade(account_name, 0.0, closed=False)
                    except Exception:
                        pass
                    try:
                        sl_side = 'sell' if side == 'buy' else 'buy'
                        sl_order = self.multi_exchange.place_stop_loss_order(
                            account_name, signal.symbol, sl_side, position_size, sl_price
                        )
                        if sl_order:
                            if isinstance(sl_order, dict) and sl_order.get('program_sl'):
                                logger.info(f"  ✓ 程序化止损已启用 (止损价: {sl_price})")
                                logger.info("  📊 程序将监控价格并在达到止损价时自动平仓")
                                try:
                                    log_struct(logger, logging.INFO, 'sl_program_mode', account=account_name, symbol=signal.symbol, side=sl_side, amount=position_size, stop_price=sl_price)
                                except Exception:
                                    pass
                            elif isinstance(sl_order, dict) and sl_order.get('status') == 'manual_required':
                                logger.info(f"  ✓ Bitget TPSL不可用，已启用手动止损模式 (止损价: {sl_price})")
                                logger.info("  📝 请通过发送 '止损：价格' 信号来手动设置止损")
                                try:
                                    log_struct(logger, logging.INFO, 'sl_manual_mode', account=account_name, symbol=signal.symbol, side=sl_side, amount=position_size, stop_price=sl_price)
                                except Exception:
                                    pass
                            else:
                                logger.info(f"  ✓ 已设置初始止损(-4%): {sl_price}")
                                try:
                                    log_struct(logger, logging.INFO, 'sl_placed', account=account_name, symbol=signal.symbol, side=sl_side, amount=position_size, stop_price=sl_price)
                                except Exception:
                                    pass
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
                    base_price = order_result.get('price') or entry_price
                    try:
                        self._register_position_for_trailing(account_name, signal.symbol, side, base_price, position_size, order_plan, sl_price, trade_id)
                        try:
                            log_struct(logger, logging.INFO, 'position_registered', account=account_name, symbol=signal.symbol, entry_price=base_price, size=position_size, trade_id=trade_id)
                        except Exception:
                            pass
                    except Exception:
                        pass
                    if order_plan['take_profits']:
                        tp_side = 'sell' if side == 'buy' else 'buy'
                        first_tp_order_id = None
                        for i, (tp_price, tp_portion) in enumerate(zip(order_plan['take_profits'], order_plan['tp_portions']), 1):
                            try:
                                tp_size = position_size * (tp_portion / 100.0)
                                tp_order = self.multi_exchange.place_take_profit_order(
                                    account_name, signal.symbol, tp_side,
                                    tp_size, tp_price
                                )
                                if tp_order:
                                    logger.info(f"  ✓ TP{i} 已设置: {tp_price} ({tp_portion}% 仓位, 数量: {tp_size:.4f})")
                                    try:
                                        log_struct(logger, logging.INFO, 'tp_placed', account=account_name, symbol=signal.symbol, idx=i, portion=tp_portion, amount=tp_size, price=tp_price)
                                    except Exception:
                                        pass
                                    if i == 1:
                                        first_tp_order_id = tp_order.get('order_id') if isinstance(tp_order, dict) else None
                                        try:
                                            log_struct(logger, logging.INFO, 'tp1_order_id', account=account_name, symbol=signal.symbol, order_id=first_tp_order_id)
                                        except Exception:
                                            pass
                                else:
                                    logger.warning(f"  ⚠ TP{i} 设置失败")
                            except Exception as e:
                                logger.warning(f"  ⚠ TP{i} 设置失败: {e}")
                        if first_tp_order_id:
                            pos_side = 'long' if side == 'buy' else 'short'
                            try:
                                asyncio.create_task(
                                    self._monitor_tp1_and_move_sl(account_name, signal.symbol, pos_side, first_tp_order_id)
                                )
                            except Exception:
                                pass
                    else:
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
                                    try:
                                        log_struct(logger, logging.INFO, 'tp_fallback_placed', account=account_name, symbol=signal.symbol, idx=i, portion=portion_pct, amount=tp_amount, price=tp_price)
                                    except Exception:
                                        pass
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
        logger.info("✅ 多交易所信号执行完成")

    def _register_position_for_trailing(self, account_name, symbol, side, entry_price, position_size, order_plan, stop_loss_price, trade_id=None):
        try:
            if order_manager.position_manager is None:
                return
            lev = None
            try:
                acct = self.multi_exchange.accounts.get(account_name)
                lev = getattr(acct, 'default_leverage', None) or None
            except Exception:
                lev = None
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
                'trade_id': trade_id,
                'leverage': lev,
            }
            order_manager.position_manager._save_position_info(account_name, symbol, info)
        except Exception:
            pass

    async def _monitor_tp1_and_move_sl(self, account_name: str, symbol: str, pos_side: str, tp_order_id: str):
        try:
            deadline = asyncio.get_event_loop().time() + 2 * 60 * 60
            status = None
            while asyncio.get_event_loop().time() < deadline:
                status = self.multi_exchange.fetch_order_status(account_name, symbol, tp_order_id)
                if status and status.get('status') in ('closed', 'canceled'):
                    break
                await asyncio.sleep(3)
            if not status or status.get('status') != 'closed':
                logger.info("  ⚠ TP1 未在监控窗口内成交/已取消，跳过保本止损移动")
                return
            pos = self.multi_exchange.get_position(account_name, symbol)
            if not pos:
                logger.info("  ⚠ TP1 成交后无剩余持仓")
                return
            entry_price = pos.get('entry_price')
            remaining = float(pos.get('contracts') or 0)
            if not entry_price or remaining <= 0:
                logger.info("  ⚠ 无法获取保本价或无剩余仓位")
                return
            # 正确的平仓方向：多仓→卖(sell)止损；空仓→买(buy)止损
            sl_side = 'sell' if pos_side == 'long' else 'buy'
            sl_order = self.multi_exchange.place_stop_loss_order(
                account_name, symbol, sl_side, remaining, entry_price
            )
            if sl_order:
                if isinstance(sl_order, dict) and sl_order.get('program_sl'):
                    try:
                        pm = getattr(order_manager, 'position_manager', None)
                        if pm is not None:
                            pos_info = pm.get_position_info(account_name, symbol)
                            if pos_info is not None:
                                pos_info['stop_loss'] = float(entry_price)
                                pos_info['sl_moved_to_breakeven'] = True
                                logger.info(f"  ✓ 程序化保本止损价已同步到监控: {symbol} @ {entry_price}")
                    except Exception:
                        pass
                    logger.info(f"  ✓ 程序化保本止损已设置 (保本价: {entry_price})")
                    logger.info("  📊 程序将监控价格并在跌破保本价时自动平仓")
                elif isinstance(sl_order, dict) and sl_order.get('status') == 'manual_required':
                    logger.info(f"  ✓ Bitget TPSL不可用，保本止损需要手动设置 (保本价: {entry_price})")
                    logger.info("  📝 请通过发送 '止损：价格' 信号来手动设置保本止损")
                else:
                    logger.info(f"  ✓ 已将止损移动到保本位: {entry_price}")
            else:
                logger.warning("  ⚠ 保本止损下单失败")
        except Exception as e:
            logger.warning(f"  ⚠ 监控TP1并移动保本止损失败: {e}")

    def _place_followup_tps(self, account_name: str, symbol: str, pos_side: str, entry_price: float, original_contracts: float, already_closed: float):
        try:
            if not entry_price or original_contracts <= 0:
                return
            remaining = max(original_contracts - already_closed, 0.0)
            if remaining <= 0:
                return
            tp_side = 'buy' if pos_side == 'short' else 'sell'
            targets = [{'profit_percent': 20.0}, {'profit_percent': 40.0}]
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
