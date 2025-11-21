"""
高级订单管理系统
支持 TP/SL、分批止盈、追踪止损、移动止损
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

# 全局持仓管理器实例
position_manager = None

class OrderType(Enum):
    """订单类型"""
    ENTRY = "entry"              # 入场订单
    TAKE_PROFIT = "take_profit"  # 止盈订单
    STOP_LOSS = "stop_loss"      # 止损订单
    TRAILING_STOP = "trailing_stop"  # 追踪止损

class OrderStatus(Enum):
    """订单状态"""
    PENDING = "pending"          # 待执行
    FILLED = "filled"            # 已成交
    PARTIALLY_FILLED = "partially_filled"  # 部分成交
    CANCELLED = "cancelled"      # 已取消
    FAILED = "failed"           # 失败

@dataclass
class TradePlan:
    """交易计划"""
    symbol: str
    side: str  # 'buy' or 'sell'
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profits: List[float] = None  # 多个止盈价格
    tp_portions: List[float] = None   # 每个止盈的仓位比例
    leverage: Optional[int] = None
    trailing_stop_pct: Optional[float] = None  # 追踪止损百分比
    move_sl_to_breakeven: bool = False  # 是否移动止损到成本价
    breakeven_trigger_pct: float = 1.0  # 触发移动止损的盈利百分比
    stop_trailing_after_breakeven: bool = False  # 保本后是否停止追踪止损
    
    def __post_init__(self):
        if self.take_profits is None:
            self.take_profits = []
        if self.tp_portions is None:
            # 默认平均分配
            if self.take_profits:
                portion = 100.0 / len(self.take_profits)
                self.tp_portions = [portion] * len(self.take_profits)
            else:
                self.tp_portions = []

class PositionManager:
    """持仓管理器"""
    
    def __init__(self, exchange_client):
        self.exchange = exchange_client
        self.active_positions: Dict[str, Dict] = {}  # {account_name: {symbol: position_info}}
        self.active_orders: Dict[str, List] = {}  # {account_name: [orders]}
        
    def create_position_with_plan(self, account_name: str, trade_plan: TradePlan, 
                                  position_size: float) -> Dict[str, Any]:
        """
        根据交易计划创建持仓
        
        Args:
            account_name: 账户名称
            trade_plan: 交易计划
            position_size: 仓位大小
            
        Returns:
            Dict: 执行结果
        """
        results = {
            'entry_order': None,
            'stop_loss_order': None,
            'take_profit_orders': [],
            'status': 'success',
            'errors': []
        }
        
        try:
            # 1. 设置杠杆
            if trade_plan.leverage:
                self.exchange.set_leverage(account_name, trade_plan.symbol, trade_plan.leverage)
            
            # 2. 下入场单
            if trade_plan.entry_price:
                # 限价单
                entry_order = self.exchange.place_limit_order(
                    account_name, trade_plan.symbol, trade_plan.side, 
                    trade_plan.entry_price, position_size
                )
            else:
                # 市价单
                entry_order = self.exchange.place_market_order(
                    account_name, trade_plan.symbol, trade_plan.side, position_size
                )
            
            results['entry_order'] = entry_order
            
            if not entry_order:
                results['status'] = 'failed'
                results['errors'].append('入场订单失败')
                return results
            
            # 获取实际成交价格
            actual_price = self._get_order_price(entry_order, trade_plan.entry_price)
            
            # 3. 设置止损
            if trade_plan.stop_loss:
                sl_order = self._place_stop_loss(
                    account_name, trade_plan.symbol, trade_plan.side,
                    trade_plan.stop_loss, position_size
                )
                results['stop_loss_order'] = sl_order
            
            # 4. 设置分批止盈
            if trade_plan.take_profits:
                tp_orders = self._place_take_profits(
                    account_name, trade_plan.symbol, trade_plan.side,
                    trade_plan.take_profits, trade_plan.tp_portions, position_size
                )
                results['take_profit_orders'] = tp_orders
            
            # 5. 记录持仓信息
            self._save_position_info(
                account_name, trade_plan.symbol, {
                    'entry_price': actual_price,
                    'position_size': position_size,
                    'side': trade_plan.side,
                    'stop_loss': trade_plan.stop_loss,
                    'take_profits': trade_plan.take_profits,
                    'tp_portions': trade_plan.tp_portions,
                    'trailing_stop_pct': trade_plan.trailing_stop_pct,
                    'move_sl_to_breakeven': trade_plan.move_sl_to_breakeven,
                    'stop_trailing_after_breakeven': getattr(trade_plan, 'stop_trailing_after_breakeven', False),
                    'breakeven_trigger_pct': trade_plan.breakeven_trigger_pct,
                    'highest_price': actual_price if trade_plan.side == 'buy' else None,
                    'lowest_price': actual_price if trade_plan.side == 'sell' else None,
                    'sl_moved_to_breakeven': False,
                    'entry_time': datetime.now(),
                }
            )
            
            logger.info(f"✓ {account_name} - 持仓创建成功: {trade_plan.symbol}")
            
        except Exception as e:
            logger.error(f"✗ {account_name} - 创建持仓失败: {e}")
            results['status'] = 'failed'
            results['errors'].append(str(e))
        
        return results
    
    def _place_stop_loss(self, account_name: str, symbol: str, side: str,
                        stop_price: float, amount: float) -> Optional[Dict]:
        """设置止损订单"""
        try:
            # 止损订单方向与入场相反
            sl_side = 'sell' if side == 'buy' else 'buy'
            
            # 使用交易所的止损单功能
            client = self.exchange.clients.get(account_name)
            if not client:
                return None
            
            # 不同交易所的止损单API可能不同，这里使用通用方法
            order = client.create_order(
                symbol=symbol,
                type='stop_market',  # 止损市价单
                side=sl_side,
                amount=amount,
                params={'stopPrice': stop_price}
            )
            
            logger.info(f"✓ {account_name} - 止损已设置: {symbol} @ {stop_price}")
            return order
            
        except Exception as e:
            logger.error(f"✗ {account_name} - 设置止损失败: {e}")
            return None
    
    def _place_take_profits(self, account_name: str, symbol: str, side: str,
                           tp_prices: List[float], tp_portions: List[float],
                           total_amount: float) -> List[Dict]:
        """设置分批止盈订单"""
        tp_orders = []
        
        try:
            # 止盈订单方向与入场相反
            tp_side = 'sell' if side == 'buy' else 'buy'
            
            client = self.exchange.clients.get(account_name)
            if not client:
                return tp_orders
            
            for i, (tp_price, portion) in enumerate(zip(tp_prices, tp_portions), 1):
                # 计算这个止盈的数量
                tp_amount = total_amount * (portion / 100.0)
                
                try:
                    # 使用限价单作为止盈
                    order = client.create_limit_order(
                        symbol=symbol,
                        side=tp_side,
                        amount=tp_amount,
                        price=tp_price
                    )
                    
                    tp_orders.append(order)
                    logger.info(f"✓ {account_name} - TP{i} 已设置: {symbol} @ {tp_price} ({portion}%)")
                    
                except Exception as e:
                    logger.error(f"✗ {account_name} - TP{i} 设置失败: {e}")
            
        except Exception as e:
            logger.error(f"✗ {account_name} - 设置止盈失败: {e}")
        
        return tp_orders
    
    def update_trailing_stop(self, account_name: str, symbol: str, 
                            current_price: float) -> bool:
        """
        更新追踪止损
        
        Args:
            account_name: 账户名称
            symbol: 交易对
            current_price: 当前价格
        """
        if account_name not in self.active_positions:
            return False
        
        if symbol not in self.active_positions[account_name]:
            return False
        
        position = self.active_positions[account_name][symbol]
        trailing_stop_pct = position.get('trailing_stop_pct')
        
        if not trailing_stop_pct:
            return False
        
        side = position['side']
        entry_price = position['entry_price']
        current_sl = position.get('stop_loss')
        
        try:
            if side == 'buy':
                # 做多：追踪最高价
                highest = position.get('highest_price', entry_price)
                if current_price > highest:
                    position['highest_price'] = current_price
                    highest = current_price
                
                # 计算新的止损价格
                new_sl = highest * (1 - trailing_stop_pct / 100.0)
                
                # 只有当新止损高于当前止损时才更新
                if not current_sl or new_sl > current_sl:
                    self._update_stop_loss_order(account_name, symbol, new_sl, position['position_size'])
                    position['stop_loss'] = new_sl
                    logger.info(f"✓ {account_name} - 追踪止损已更新: {symbol} @ {new_sl:.2f}")
                    return True
            
            else:  # sell
                # 做空：追踪最低价
                lowest = position.get('lowest_price', entry_price)
                if current_price < lowest:
                    position['lowest_price'] = current_price
                    lowest = current_price
                
                # 计算新的止损价格
                new_sl = lowest * (1 + trailing_stop_pct / 100.0)
                
                # 只有当新止损低于当前止损时才更新
                if not current_sl or new_sl < current_sl:
                    self._update_stop_loss_order(account_name, symbol, new_sl, position['position_size'])
                    position['stop_loss'] = new_sl
                    logger.info(f"✓ {account_name} - 追踪止损已更新: {symbol} @ {new_sl:.2f}")
                    return True
        
        except Exception as e:
            logger.error(f"✗ {account_name} - 更新追踪止损失败: {e}")
        
        return False
    
    def move_stop_to_breakeven(self, account_name: str, symbol: str,
                              current_price: float) -> bool:
        """
        移动止损到盈亏平衡点（成本价）
        
        Args:
            account_name: 账户名称
            symbol: 交易对
            current_price: 当前价格
        """
        if account_name not in self.active_positions:
            return False
        
        if symbol not in self.active_positions[account_name]:
            return False
        
        position = self.active_positions[account_name][symbol]
        
        if not position.get('move_sl_to_breakeven'):
            return False
        
        if position.get('sl_moved_to_breakeven'):
            return False  # 已经移动过了
        
        entry_price = position['entry_price']
        side = position['side']
        trigger_pct = position.get('breakeven_trigger_pct', 1.0)
        
        try:
            # 检查是否达到触发条件
            if side == 'buy':
                profit_pct = ((current_price - entry_price) / entry_price) * 100
                if profit_pct >= trigger_pct:
                    # 移动止损到入场价（或略高一点以覆盖手续费）
                    new_sl = entry_price * 1.001  # +0.1% 覆盖手续费
                    self._update_stop_loss_order(account_name, symbol, new_sl, position['position_size'])
                    position['stop_loss'] = new_sl
                    position['sl_moved_to_breakeven'] = True
                    logger.info(f"✓ {account_name} - 止损已移至盈亏平衡: {symbol} @ {new_sl:.2f}")
                    return True
            
            else:  # sell
                profit_pct = ((entry_price - current_price) / entry_price) * 100
                if profit_pct >= trigger_pct:
                    new_sl = entry_price * 0.999  # -0.1% 覆盖手续费
                    self._update_stop_loss_order(account_name, symbol, new_sl, position['position_size'])
                    position['stop_loss'] = new_sl
                    position['sl_moved_to_breakeven'] = True
                    logger.info(f"✓ {account_name} - 止损已移至盈亏平衡: {symbol} @ {new_sl:.2f}")
                    return True
        
        except Exception as e:
            logger.error(f"✗ {account_name} - 移动止损到盈亏平衡失败: {e}")
        
        return False
    
    def _update_stop_loss_order(self, account_name: str, symbol: str,
                               new_sl_price: float, amount: float):
        """更新止损订单（取消旧的，创建新的）- 在程序化止损模式下只更新内存"""
        try:
            # 对于程序化止损，只需要更新内存中的止损价格即可
            # 不需要实际挂订单，因为程序会监控价格并自动平仓
            position = self.active_positions.get(account_name, {}).get(symbol)
            if position and position.get('stop_loss'):
                logger.info(f"✓ {account_name} - 程序化止损价格已更新: {symbol} @ {new_sl_price:.4f}")
                return {'status': 'updated', 'price': new_sl_price}
            
            # 如果不是程序化止损模式，尝试挂实际订单
            client = self.exchange.clients.get(account_name)
            if not client:
                return
            
            # 取消现有的止损订单
            # 注意：实际实现中需要记录订单ID来取消
            # 这里简化处理
            
            # 创建新的止损订单
            side = self.active_positions[account_name][symbol]['side']
            sl_side = 'sell' if side == 'buy' else 'buy'
            
            order = client.create_order(
                symbol=symbol,
                type='stop_market',
                side=sl_side,
                amount=amount,
                params={'stopPrice': new_sl_price}
            )
            
            return order
            
        except Exception as e:
            logger.error(f"更新止损订单失败: {e}")
    
    def _save_position_info(self, account_name: str, symbol: str, position_info: Dict):
        """保存持仓信息"""
        if account_name not in self.active_positions:
            self.active_positions[account_name] = {}
        
        self.active_positions[account_name][symbol] = position_info
    
    def _get_order_price(self, order: Dict, fallback_price: Optional[float]) -> float:
        """从订单中获取成交价格"""
        if order and 'price' in order:
            return float(order['price'])
        elif order and 'average' in order:
            return float(order['average'])
        return fallback_price or 0.0
    
    def get_position_info(self, account_name: str, symbol: str) -> Optional[Dict]:
        """获取持仓信息"""
        if account_name in self.active_positions:
            return self.active_positions[account_name].get(symbol)
        return None

    def iter_active_positions(self):
        """遍历所有活跃持仓，产出 (account_name, symbol, position_info)"""
        for account_name, positions in self.active_positions.items():
            for symbol, info in positions.items():
                yield account_name, symbol, info

    def remove_position(self, account_name: str, symbol: str):
        """移除持仓记录（用于检测到已完全平仓后清理内存状态）"""
        try:
            if account_name in self.active_positions and symbol in self.active_positions[account_name]:
                del self.active_positions[account_name][symbol]
                logger.info(f"✓ {account_name} - 已移除持仓记录: {symbol}")
        except Exception as e:
            logger.debug(f"移除持仓记录失败 {account_name} {symbol}: {e}")
    
    def close_position(self, account_name: str, symbol: str) -> bool:
        """关闭持仓"""
        try:
            # 平仓
            result = self.exchange.close_position(account_name, symbol)
            
            # 取消所有相关订单
            # TODO: 实现取消订单逻辑
            
            # 移除持仓记录
            if account_name in self.active_positions:
                if symbol in self.active_positions[account_name]:
                    del self.active_positions[account_name][symbol]
            
            logger.info(f"✓ {account_name} - 持仓已关闭: {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"✗ {account_name} - 关闭持仓失败: {e}")
            return False
    
    def monitor_positions(self):
        """监控所有持仓，更新追踪止损、移动止损和程序化止损"""
        # 统计所有账户的总持仓数，空仓时不输出监控日志，直接返回
        total_positions = sum(len(positions) for positions in self.active_positions.values())
        if total_positions == 0:
            logger.debug("🔍 当前无任何持仓，监控循环略过")
            return

        logger.info(f"🔍 开始监控持仓，总账户数: {len(self.active_positions)}，总持仓数: {total_positions}")
        # 使用浅拷贝列表进行遍历，避免在遍历过程中修改字典大小导致错误
        for account_name, positions in list(self.active_positions.items()):
            position_count = len(positions)
            if position_count == 0:
                # 账户存在但当前无持仓时，仅输出 DEBUG，避免 INFO 日志刷屏
                logger.debug(f"🔍 账户 {account_name} 当前无持仓，跳过监控")
                continue

            logger.info(f"🔍 监控账户 {account_name}，持仓数: {position_count}")
            
            for symbol, position in list(positions.items()):
                try:
                    # 获取当前价格
                    current_price = self.exchange.get_current_price(account_name, symbol)
                    if not current_price:
                        logger.warning(f"🔍 {account_name} {symbol} - 获取价格失败")
                        continue
                    
                    logger.info(f"🔍 {account_name} {symbol} - 当前价格: {current_price:.4f}, 持仓信息: {position}")
                    
                    # 更新追踪止损
                    if position.get('trailing_stop_pct'):
                        # 如果配置为保本后停止追踪止损，且已移动到保本位，则跳过追踪止损
                        if position.get('stop_trailing_after_breakeven') and position.get('sl_moved_to_breakeven'):
                            logger.debug(f"🔍 {account_name} {symbol} - 已保本且配置为停止追踪止损，跳过追踪止损更新")
                        else:
                            logger.debug(f"🔍 检查追踪止损: {account_name} {symbol}")
                            self.update_trailing_stop(account_name, symbol, current_price)
                    
                    # 检查是否需要移动止损到盈亏平衡
                    if position.get('move_sl_to_breakeven') and not position.get('sl_moved_to_breakeven'):
                        logger.debug(f"🔍 检查保本止损: {account_name} {symbol}")
                        self.move_stop_to_breakeven(account_name, symbol, current_price)
                    
                    # 检查程序化止损：当价格达到止损点位时自动平仓
                    logger.debug(f"🔍 调用程序化止损检查: {account_name} {symbol}")
                    if self._check_and_trigger_program_sl(account_name, symbol, current_price):
                        # 止损已触发，持仓已被关闭，跳过后续处理
                        continue
                    
                except Exception as e:
                    logger.error(f"监控持仓出错 {account_name} {symbol}: {e}")
        
        logger.debug(f"🔍 监控循环完成")

    def _check_and_trigger_program_sl(self, account_name: str, symbol: str, current_price: float) -> bool:
        """
        检查并触发程序化止损
        
        Args:
            account_name: 账户名称
            symbol: 交易对
            current_price: 当前价格
            
        Returns:
            bool: 是否触发了止损（True=已触发并平仓，False=未触发）
        """
        position = self.active_positions[account_name][symbol]
        stop_loss = position.get('stop_loss')
        
        logger.info(f"🔍 检查程序化止损: {account_name} {symbol} @ {current_price:.4f}, 止损价: {stop_loss}, 持仓: {position}")
        
        if not stop_loss:
            logger.info(f"🔍 {account_name} {symbol} - 未设置止损价格")
            return False  # 没有设置止损
        
        side = position['side']
        triggered = False
        
        try:
            if side == 'buy':
                # 做多仓位：价格跌破止损价时触发
                if current_price <= stop_loss:
                    triggered = True
                    logger.warning(f"⚠ {account_name} - 程序化止损触发: {symbol} 多仓 @ {current_price:.4f} <= 止损价 {stop_loss:.4f}")
                else:
                    logger.info(f"🔍 {account_name} {symbol} 多仓 - 价格 {current_price:.4f} > 止损价 {stop_loss:.4f}, 未触发")
            else:  # side == 'sell'
                # 做空仓位：价格涨破止损价时触发
                if current_price >= stop_loss:
                    triggered = True
                    logger.warning(f"⚠ {account_name} - 程序化止损触发: {symbol} 空仓 @ {current_price:.4f} >= 止损价 {stop_loss:.4f}")
                else:
                    logger.info(f"🔍 {account_name} {symbol} 空仓 - 价格 {current_price:.4f} < 止损价 {stop_loss:.4f}, 未触发")
            
            if triggered:
                # 执行平仓
                try:
                    # 记录止损前的PnL
                    entry_price = position.get('entry_price', 0)
                    position_size = position.get('position_size', 0)
                    leverage = position.get('leverage', 1)
                    
                    if side == 'buy':
                        pnl = (current_price - entry_price) * position_size * leverage
                    else:
                        pnl = (entry_price - current_price) * position_size * leverage
                    
                    logger.warning(f"⚠ {account_name} - 止损执行前PnL: {pnl:.4f}")
                    
                    logger.info(f"🔍 执行市价平仓: {account_name} {symbol}, 方向: {side}")
                    # 执行市价平仓
                    result = self.exchange.close_position(account_name, symbol)
                    logger.info(f"🔍 平仓结果: {result}")
                    
                    if result:
                        logger.warning(f"⚠ {account_name} - 程序化止损已执行: {symbol} @ {current_price:.4f}")
                        # 移除持仓记录
                        self.remove_position(account_name, symbol)
                        return True
                    else:
                        logger.error(f"✗ {account_name} - 程序化止损平仓失败: {symbol}")
                        return False
                        
                except Exception as close_e:
                    logger.error(f"✗ {account_name} - 程序化止损执行失败: {close_e}")
                    return False
        
        except Exception as e:
            logger.error(f"✗ {account_name} - 检查程序化止损失败 {symbol}: {e}")
        
        return False

