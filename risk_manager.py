"""
风险管理系统
包含最大亏损限制、连续亏损保护等
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class RiskLimits:
    """风险限制配置"""
    max_daily_loss_pct: float = 5.0  # 最大日亏损百分比
    max_daily_loss_amount: Optional[float] = None  # 最大日亏损金额（USDT）
    max_total_loss_pct: float = 20.0  # 最大总亏损百分比
    max_consecutive_losses: int = 3  # 最大连续亏损次数
    max_open_positions: int = 5  # 最大同时持仓数
    cooldown_after_limit: int = 60  # 触发限制后的冷却时间（分钟）
    min_account_balance: float = 100.0  # 最低账户余额要求

class RiskManager:
    """风险管理器"""
    
    def __init__(self, exchange_client):
        self.exchange = exchange_client
        self.limits = RiskLimits()
        
        # 账户风险状态
        self.account_risks: Dict[str, Dict] = {}  # {account_name: risk_state}
        
        # 每日统计
        self.daily_stats: Dict[str, Dict] = {}  # {account_name: {date: stats}}
        
        # 初始化账户
        self._init_accounts()
    
    def _init_accounts(self):
        """初始化所有账户的风险状态"""
        for account_name in self.exchange.clients.keys():
            self._init_account_risk_state(account_name)
    
    def _init_account_risk_state(self, account_name: str):
        """初始化账户风险状态"""
        if account_name not in self.account_risks:
            initial_balance = self.exchange.get_balance(account_name, 'USDT') or 0.0
            
            self.account_risks[account_name] = {
                'initial_balance': initial_balance,
                'current_balance': initial_balance,
                'daily_pnl': 0.0,
                'total_pnl': 0.0,
                'consecutive_losses': 0,
                'consecutive_wins': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'trading_enabled': True,
                'cooldown_until': None,
                'last_reset_date': datetime.now().date(),
                'open_positions_count': 0,
            }
        
        if account_name not in self.daily_stats:
            self.daily_stats[account_name] = {}
    
    def set_risk_limits(self, limits: RiskLimits):
        """设置风险限制"""
        self.limits = limits
        logger.info(f"✓ 风险限制已更新")
    
    def can_open_trade(self, account_name: str, trade_value: float) -> tuple[bool, str]:
        """
        检查是否可以开仓
        
        Returns:
            (bool, str): (是否允许, 原因)
        """
        if account_name not in self.account_risks:
            self._init_account_risk_state(account_name)
        
        risk_state = self.account_risks[account_name]
        
        # 1. 检查是否在冷却期
        if not risk_state['trading_enabled']:
            if risk_state['cooldown_until']:
                if datetime.now() < risk_state['cooldown_until']:
                    remaining = (risk_state['cooldown_until'] - datetime.now()).seconds // 60
                    return False, f"账户在冷却期，剩余 {remaining} 分钟"
                else:
                    # 冷却期结束，重新启用
                    risk_state['trading_enabled'] = True
                    risk_state['cooldown_until'] = None
                    logger.info(f"✓ {account_name} - 冷却期结束，交易已重新启用")
        
        if not risk_state['trading_enabled']:
            return False, "交易已被禁用"
        
        # 2. 检查账户余额
        current_balance = self.exchange.get_balance(account_name, 'USDT')
        if not current_balance:
            return False, "无法获取账户余额"
        
        if current_balance < self.limits.min_account_balance:
            return False, f"账户余额不足 {self.limits.min_account_balance} USDT"
        
        # 3. 检查每日亏损限制
        daily_pnl = risk_state['daily_pnl']
        
        # 百分比限制
        daily_loss_pct = abs(daily_pnl / risk_state['initial_balance'] * 100) if risk_state['initial_balance'] > 0 else 0
        if daily_pnl < 0 and daily_loss_pct >= self.limits.max_daily_loss_pct:
            self._trigger_cooldown(account_name, f"触发每日亏损限制 ({daily_loss_pct:.2f}%)")
            return False, f"已达每日最大亏损限制 ({daily_loss_pct:.2f}%)"
        
        # 金额限制
        if self.limits.max_daily_loss_amount:
            if daily_pnl < 0 and abs(daily_pnl) >= self.limits.max_daily_loss_amount:
                self._trigger_cooldown(account_name, f"触发每日亏损金额限制 ({abs(daily_pnl):.2f} USDT)")
                return False, f"已达每日最大亏损金额 ({abs(daily_pnl):.2f} USDT)"
        
        # 4. 检查总亏损限制
        total_pnl = risk_state['total_pnl']
        total_loss_pct = abs(total_pnl / risk_state['initial_balance'] * 100) if risk_state['initial_balance'] > 0 else 0
        if total_pnl < 0 and total_loss_pct >= self.limits.max_total_loss_pct:
            self._trigger_cooldown(account_name, f"触发总亏损限制 ({total_loss_pct:.2f}%)", duration=1440)  # 24小时
            return False, f"已达最大总亏损限制 ({total_loss_pct:.2f}%)"
        
        # 5. 检查连续亏损
        if risk_state['consecutive_losses'] >= self.limits.max_consecutive_losses:
            self._trigger_cooldown(account_name, f"连续亏损 {risk_state['consecutive_losses']} 次")
            return False, f"连续亏损 {risk_state['consecutive_losses']} 次，暂停交易"
        
        # 6. 检查最大持仓数
        if risk_state['open_positions_count'] >= self.limits.max_open_positions:
            return False, f"已达最大持仓数限制 ({self.limits.max_open_positions})"
        
        return True, "允许开仓"
    
    def record_trade(self, account_name: str, pnl: float, closed: bool = True):
        """
        记录交易结果
        
        Args:
            account_name: 账户名称
            pnl: 盈亏金额（正数为盈利，负数为亏损）
            closed: 是否平仓（False表示开仓）
        """
        if account_name not in self.account_risks:
            self._init_account_risk_state(account_name)
        
        risk_state = self.account_risks[account_name]
        
        # 检查是否需要重置每日统计
        self._check_daily_reset(account_name)
        
        if closed:
            # 平仓，更新统计
            risk_state['total_trades'] += 1
            risk_state['daily_pnl'] += pnl
            risk_state['total_pnl'] += pnl
            
            # 更新当前余额
            current_balance = self.exchange.get_balance(account_name, 'USDT')
            if current_balance:
                risk_state['current_balance'] = current_balance
            
            # 更新连续盈亏
            if pnl > 0:
                risk_state['winning_trades'] += 1
                risk_state['consecutive_wins'] += 1
                risk_state['consecutive_losses'] = 0
                logger.info(f"✓ {account_name} - 盈利交易: +{pnl:.2f} USDT (连胜 {risk_state['consecutive_wins']})")
            else:
                risk_state['losing_trades'] += 1
                risk_state['consecutive_losses'] += 1
                risk_state['consecutive_wins'] = 0
                logger.warning(f"⚠ {account_name} - 亏损交易: {pnl:.2f} USDT (连亏 {risk_state['consecutive_losses']})")
            
            # 保存到每日统计
            today = datetime.now().date()
            if today not in self.daily_stats[account_name]:
                self.daily_stats[account_name][today] = {
                    'trades': 0,
                    'pnl': 0.0,
                    'wins': 0,
                    'losses': 0,
                }
            
            daily_stat = self.daily_stats[account_name][today]
            daily_stat['trades'] += 1
            daily_stat['pnl'] += pnl
            if pnl > 0:
                daily_stat['wins'] += 1
            else:
                daily_stat['losses'] += 1
            
            # 检查是否触发风险限制
            can_trade, reason = self.can_open_trade(account_name, 0)
            if not can_trade:
                logger.warning(f"⚠ {account_name} - {reason}")
            
            risk_state['open_positions_count'] = max(0, risk_state['open_positions_count'] - 1)
        
        else:
            # 开仓
            risk_state['open_positions_count'] += 1
    
    def _trigger_cooldown(self, account_name: str, reason: str, duration: int = None):
        """触发冷却期"""
        if duration is None:
            duration = self.limits.cooldown_after_limit
        
        risk_state = self.account_risks[account_name]
        risk_state['trading_enabled'] = False
        risk_state['cooldown_until'] = datetime.now() + timedelta(minutes=duration)
        
        logger.warning(f"🚫 {account_name} - 交易已暂停: {reason} (冷却 {duration} 分钟)")
    
    def _check_daily_reset(self, account_name: str):
        """检查是否需要重置每日统计"""
        risk_state = self.account_risks[account_name]
        today = datetime.now().date()
        
        if risk_state['last_reset_date'] < today:
            # 新的一天，重置每日统计
            risk_state['daily_pnl'] = 0.0
            risk_state['last_reset_date'] = today
            logger.info(f"✓ {account_name} - 每日统计已重置")
    
    def get_risk_status(self, account_name: str) -> Dict:
        """获取风险状态"""
        if account_name not in self.account_risks:
            self._init_account_risk_state(account_name)
        
        risk_state = self.account_risks[account_name]
        
        # 计算胜率
        win_rate = 0.0
        if risk_state['total_trades'] > 0:
            win_rate = (risk_state['winning_trades'] / risk_state['total_trades']) * 100
        
        # 计算每日亏损百分比
        daily_loss_pct = 0.0
        if risk_state['initial_balance'] > 0 and risk_state['daily_pnl'] < 0:
            daily_loss_pct = abs(risk_state['daily_pnl'] / risk_state['initial_balance'] * 100)
        
        # 计算总亏损百分比
        total_loss_pct = 0.0
        if risk_state['initial_balance'] > 0 and risk_state['total_pnl'] < 0:
            total_loss_pct = abs(risk_state['total_pnl'] / risk_state['initial_balance'] * 100)
        
        return {
            'account_name': account_name,
            'trading_enabled': risk_state['trading_enabled'],
            'cooldown_until': risk_state['cooldown_until'],
            'initial_balance': risk_state['initial_balance'],
            'current_balance': risk_state['current_balance'],
            'daily_pnl': risk_state['daily_pnl'],
            'total_pnl': risk_state['total_pnl'],
            'daily_loss_pct': daily_loss_pct,
            'total_loss_pct': total_loss_pct,
            'consecutive_losses': risk_state['consecutive_losses'],
            'consecutive_wins': risk_state['consecutive_wins'],
            'total_trades': risk_state['total_trades'],
            'winning_trades': risk_state['winning_trades'],
            'losing_trades': risk_state['losing_trades'],
            'win_rate': win_rate,
            'open_positions_count': risk_state['open_positions_count'],
        }
    
    def get_all_risk_status(self) -> Dict[str, Dict]:
        """获取所有账户的风险状态"""
        return {
            account_name: self.get_risk_status(account_name)
            for account_name in self.exchange.clients.keys()
        }
    
    def reset_account(self, account_name: str):
        """重置账户统计（保留余额信息）"""
        if account_name in self.account_risks:
            current_balance = self.exchange.get_balance(account_name, 'USDT') or 0.0
            
            self.account_risks[account_name] = {
                'initial_balance': current_balance,
                'current_balance': current_balance,
                'daily_pnl': 0.0,
                'total_pnl': 0.0,
                'consecutive_losses': 0,
                'consecutive_wins': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'trading_enabled': True,
                'cooldown_until': None,
                'last_reset_date': datetime.now().date(),
                'open_positions_count': 0,
            }
            
            logger.info(f"✓ {account_name} - 风险统计已重置")
    
    def manually_enable_trading(self, account_name: str):
        """手动启用交易（解除冷却）"""
        if account_name in self.account_risks:
            self.account_risks[account_name]['trading_enabled'] = True
            self.account_risks[account_name]['cooldown_until'] = None
            logger.info(f"✓ {account_name} - 交易已手动启用")
    
    def manually_disable_trading(self, account_name: str, reason: str = "手动禁用"):
        """手动禁用交易"""
        if account_name in self.account_risks:
            self.account_risks[account_name]['trading_enabled'] = False
            logger.warning(f"🚫 {account_name} - 交易已手动禁用: {reason}")

# 全局实例（需要在使用时初始化）
risk_manager = None

def init_risk_manager(exchange_client, limits: Optional[RiskLimits] = None):
    """初始化风险管理器"""
    global risk_manager
    risk_manager = RiskManager(exchange_client)
    if limits:
        risk_manager.set_risk_limits(limits)
    return risk_manager

