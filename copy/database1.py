"""
SQLite 数据库管理
记录所有交易历史和统计数据
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class TradingDatabase:
    """交易数据库管理器"""
    
    def __init__(self, db_path: str = "trading_history.db"):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 返回字典而不是元组
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """初始化数据库表"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 交易记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry_price REAL,
                    exit_price REAL,
                    position_size REAL,
                    leverage INTEGER,
                    entry_time TIMESTAMP,
                    exit_time TIMESTAMP,
                    pnl REAL,
                    pnl_percentage REAL,
                    fees REAL,
                    status TEXT,
                    stop_loss REAL,
                    take_profit TEXT,
                    trailing_stop_pct REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 订单记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id INTEGER,
                    account_name TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    order_type TEXT NOT NULL,
                    side TEXT NOT NULL,
                    price REAL,
                    amount REAL,
                    filled_amount REAL,
                    status TEXT,
                    order_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trade_id) REFERENCES trades(id)
                )
            ''')
            
            # 每日统计表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_name TEXT NOT NULL,
                    date DATE NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    winning_trades INTEGER DEFAULT 0,
                    losing_trades INTEGER DEFAULT 0,
                    total_pnl REAL DEFAULT 0,
                    total_fees REAL DEFAULT 0,
                    win_rate REAL DEFAULT 0,
                    largest_win REAL DEFAULT 0,
                    largest_loss REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(account_name, date)
                )
            ''')
            
            # 信号记录表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    entry_price REAL,
                    stop_loss REAL,
                    take_profit TEXT,
                    leverage INTEGER,
                    raw_message TEXT,
                    parsed_data TEXT,
                    executed BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 风险事件表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS risk_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    account_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    description TEXT,
                    severity TEXT,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 创建索引
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_account ON trades(account_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_account ON orders(account_name)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_daily_stats_account_date ON daily_stats(account_name, date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_created ON signals(created_at)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_risk_events_account ON risk_events(account_name)')
            
            logger.info("✓ 数据库初始化完成")
    
    def record_trade(self, account_name: str, symbol: str, side: str,
                    entry_price: float, position_size: float, leverage: int = 1,
                    stop_loss: Optional[float] = None, take_profit: Optional[List[float]] = None,
                    trailing_stop_pct: Optional[float] = None, notes: str = "") -> int:
        """
        记录新交易
        
        Returns:
            int: 交易ID
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO trades (account_name, symbol, side, entry_price, position_size,
                                  leverage, entry_time, status, stop_loss, take_profit,
                                  trailing_stop_pct, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                account_name, symbol, side, entry_price, position_size,
                leverage, datetime.now(), 'open',
                stop_loss, str(take_profit) if take_profit else None,
                trailing_stop_pct, notes
            ))
            
            trade_id = cursor.lastrowid
            logger.info(f"✓ 交易已记录: ID={trade_id}, {account_name} {symbol}")
            return trade_id
    
    def close_trade(self, trade_id: int, exit_price: float, fees: float = 0.0):
        """平仓，更新交易记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 获取交易信息
            cursor.execute('SELECT * FROM trades WHERE id = ?', (trade_id,))
            trade = cursor.fetchone()
            
            if not trade:
                logger.error(f"交易 ID {trade_id} 不存在")
                return
            
            # 计算盈亏
            entry_price = trade['entry_price']
            position_size = trade['position_size']
            side = trade['side']
            leverage = trade['leverage']
            
            if side == 'buy':
                pnl = (exit_price - entry_price) * position_size * leverage - fees
            else:  # sell
                pnl = (entry_price - exit_price) * position_size * leverage - fees
            
            pnl_pct = (pnl / (entry_price * position_size)) * 100 if entry_price > 0 else 0
            
            # 更新交易记录
            cursor.execute('''
                UPDATE trades
                SET exit_price = ?, exit_time = ?, pnl = ?, pnl_percentage = ?,
                    fees = ?, status = ?
                WHERE id = ?
            ''', (exit_price, datetime.now(), pnl, pnl_pct, fees, 'closed', trade_id))
            
            # 更新每日统计
            self._update_daily_stats(cursor, trade['account_name'], pnl, fees)
            
            logger.info(f"✓ 交易已平仓: ID={trade_id}, PnL={pnl:.2f} ({pnl_pct:.2f}%)")
    
    def _update_daily_stats(self, cursor, account_name: str, pnl: float, fees: float):
        """更新每日统计"""
        today = datetime.now().date()
        
        # 检查今天的统计是否存在
        cursor.execute('''
            SELECT * FROM daily_stats WHERE account_name = ? AND date = ?
        ''', (account_name, today))
        
        stat = cursor.fetchone()
        
        if stat:
            # 更新
            total_trades = stat['total_trades'] + 1
            winning_trades = stat['winning_trades'] + (1 if pnl > 0 else 0)
            losing_trades = stat['losing_trades'] + (1 if pnl < 0 else 0)
            total_pnl = stat['total_pnl'] + pnl
            total_fees = stat['total_fees'] + fees
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            largest_win = max(stat['largest_win'], pnl) if pnl > 0 else stat['largest_win']
            largest_loss = min(stat['largest_loss'], pnl) if pnl < 0 else stat['largest_loss']
            
            cursor.execute('''
                UPDATE daily_stats
                SET total_trades = ?, winning_trades = ?, losing_trades = ?,
                    total_pnl = ?, total_fees = ?, win_rate = ?,
                    largest_win = ?, largest_loss = ?
                WHERE account_name = ? AND date = ?
            ''', (total_trades, winning_trades, losing_trades, total_pnl, total_fees,
                  win_rate, largest_win, largest_loss, account_name, today))
        else:
            # 插入新记录
            cursor.execute('''
                INSERT INTO daily_stats (account_name, date, total_trades, winning_trades,
                                        losing_trades, total_pnl, total_fees, win_rate,
                                        largest_win, largest_loss)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (account_name, today, 1, 1 if pnl > 0 else 0, 1 if pnl < 0 else 0,
                  pnl, fees, 100 if pnl > 0 else 0,
                  pnl if pnl > 0 else 0, pnl if pnl < 0 else 0))
    
    def record_signal(self, symbol: str, signal_type: str, entry_price: Optional[float],
                     stop_loss: Optional[float], take_profit: Optional[List[float]],
                     leverage: Optional[int], raw_message: str, parsed_data: str = "") -> int:
        """记录信号"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO signals (symbol, signal_type, entry_price, stop_loss,
                                   take_profit, leverage, raw_message, parsed_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (symbol, signal_type, entry_price, stop_loss,
                  str(take_profit) if take_profit else None, leverage,
                  raw_message, parsed_data))
            
            return cursor.lastrowid
    
    def mark_signal_executed(self, signal_id: int):
        """标记信号已执行"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE signals SET executed = 1 WHERE id = ?', (signal_id,))
    
    def record_risk_event(self, account_name: str, event_type: str,
                         description: str, severity: str = "INFO", data: str = ""):
        """记录风险事件"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO risk_events (account_name, event_type, description, severity, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (account_name, event_type, description, severity, data))
            
            logger.info(f"✓ 风险事件已记录: {account_name} - {event_type}")
    
    def get_trades(self, account_name: Optional[str] = None, limit: int = 100,
                  status: Optional[str] = None) -> List[Dict]:
        """获取交易记录"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM trades WHERE 1=1'
            params = []
            
            if account_name:
                query += ' AND account_name = ?'
                params.append(account_name)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            query += ' ORDER BY entry_time DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_daily_stats(self, account_name: Optional[str] = None, days: int = 30) -> List[Dict]:
        """获取每日统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = '''
                SELECT * FROM daily_stats
                WHERE date >= date('now', '-{} days')
            '''.format(days)
            
            if account_name:
                query += ' AND account_name = ?'
                cursor.execute(query + ' ORDER BY date DESC', (account_name,))
            else:
                cursor.execute(query + ' ORDER BY date DESC')
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_summary_stats(self, account_name: Optional[str] = None) -> Dict:
        """获取总体统计"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT * FROM trades WHERE status = "closed"'
            params = []
            
            if account_name:
                query += ' AND account_name = ?'
                params.append(account_name)
            
            cursor.execute(query, params)
            trades = cursor.fetchall()
            
            if not trades:
                return {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'win_rate': 0,
                    'total_pnl': 0,
                    'average_pnl': 0,
                    'largest_win': 0,
                    'largest_loss': 0,
                    'profit_factor': 0,
                }
            
            total_pnl = sum(t['pnl'] for t in trades if t['pnl'])
            winning_trades = [t for t in trades if t['pnl'] and t['pnl'] > 0]
            losing_trades = [t for t in trades if t['pnl'] and t['pnl'] < 0]
            
            total_profit = sum(t['pnl'] for t in winning_trades)
            total_loss = abs(sum(t['pnl'] for t in losing_trades))
            
            return {
                'total_trades': len(trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': (len(winning_trades) / len(trades) * 100) if trades else 0,
                'total_pnl': total_pnl,
                'average_pnl': total_pnl / len(trades) if trades else 0,
                'largest_win': max([t['pnl'] for t in winning_trades]) if winning_trades else 0,
                'largest_loss': min([t['pnl'] for t in losing_trades]) if losing_trades else 0,
                'profit_factor': (total_profit / total_loss) if total_loss > 0 else 0,
            }

    def record_order(self, trade_id: Optional[int], account_name: str, symbol: str,
                     order_type: str, side: str, price: Optional[float] = None,
                     amount: Optional[float] = None, status: Optional[str] = None,
                     order_id: Optional[str] = None, filled_amount: Optional[float] = None) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO orders (trade_id, account_name, symbol, order_type, side,
                                    price, amount, filled_amount, status, order_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_id, account_name, symbol, order_type, side,
                price, amount, filled_amount, status, order_id
            ))
            return cursor.lastrowid

# 全局实例
trading_db = TradingDatabase()

