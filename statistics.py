"""
交易统计分析模块
生成详细的盈亏报表和图表数据
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from database import trading_db

logger = logging.getLogger(__name__)

class TradingStatistics:
    """交易统计分析器"""
    
    def __init__(self):
        self.db = trading_db
    
    def get_account_performance(self, account_name: str, days: int = 30) -> Dict:
        """
        获取账户表现分析
        
        Args:
            account_name: 账户名称
            days: 统计天数
        """
        # 获取基本统计
        summary = self.db.get_summary_stats(account_name)
        
        # 获取每日数据
        daily_stats = self.db.get_daily_stats(account_name, days)
        
        # 计算额外指标
        trades = self.db.get_trades(account_name, limit=1000, status='closed')
        
        return {
            'summary': summary,
            'daily_stats': daily_stats,
            'recent_trades': trades[:10],  # 最近10笔交易
            'metrics': self._calculate_metrics(trades),
        }
    
    def _calculate_metrics(self, trades: List[Dict]) -> Dict:
        """计算详细指标"""
        if not trades:
            return {}
        
        pnls = [t['pnl'] for t in trades if t['pnl'] is not None]
        
        if not pnls:
            return {}
        
        # 计算回撤
        cumulative_pnl = []
        total = 0
        for pnl in pnls:
            total += pnl
            cumulative_pnl.append(total)
        
        max_drawdown = 0
        peak = cumulative_pnl[0]
        for value in cumulative_pnl:
            if value > peak:
                peak = value
            drawdown = peak - value
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # 夏普比率（简化版）
        if len(pnls) > 1:
            avg_return = sum(pnls) / len(pnls)
            std_dev = (sum((x - avg_return) ** 2 for x in pnls) / len(pnls)) ** 0.5
            sharpe_ratio = (avg_return / std_dev) if std_dev > 0 else 0
        else:
            sharpe_ratio = 0
        
        # 平均持仓时间
        durations = []
        for trade in trades:
            if trade['entry_time'] and trade['exit_time']:
                try:
                    entry = datetime.fromisoformat(trade['entry_time'])
                    exit = datetime.fromisoformat(trade['exit_time'])
                    duration = (exit - entry).total_seconds() / 3600  # 小时
                    durations.append(duration)
                except:
                    pass
        
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_holding_time_hours': avg_duration,
            'total_fees': sum(t['fees'] for t in trades if t['fees']),
            'roi': (sum(pnls) / abs(pnls[0])) * 100 if pnls else 0,
        }
    
    def generate_pnl_curve(self, account_name: Optional[str] = None, days: int = 30) -> List[Dict]:
        """
        生成盈亏曲线数据
        
        Returns:
            List[Dict]: [{'date': '2024-01-01', 'cumulative_pnl': 100.5}, ...]
        """
        trades = self.db.get_trades(account_name, limit=1000, status='closed')
        
        if not trades:
            return []
        
        # 按时间排序
        trades.sort(key=lambda x: x['exit_time'] if x['exit_time'] else '')
        
        # 计算累计盈亏
        cumulative = 0
        curve_data = []
        
        for trade in trades:
            if trade['exit_time'] and trade['pnl']:
                cumulative += trade['pnl']
                curve_data.append({
                    'date': trade['exit_time'][:10],  # YYYY-MM-DD
                    'time': trade['exit_time'],
                    'cumulative_pnl': cumulative,
                    'trade_pnl': trade['pnl'],
                    'symbol': trade['symbol'],
                })
        
        return curve_data
    
    def get_symbol_performance(self, account_name: Optional[str] = None) -> Dict[str, Dict]:
        """
        按交易对统计表现
        
        Returns:
            Dict: {symbol: stats}
        """
        trades = self.db.get_trades(account_name, limit=1000, status='closed')
        
        symbol_stats = {}
        
        for trade in trades:
            symbol = trade['symbol']
            if symbol not in symbol_stats:
                symbol_stats[symbol] = {
                    'total_trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'total_pnl': 0,
                    'win_rate': 0,
                }
            
            stats = symbol_stats[symbol]
            stats['total_trades'] += 1
            
            if trade['pnl']:
                stats['total_pnl'] += trade['pnl']
                if trade['pnl'] > 0:
                    stats['wins'] += 1
                else:
                    stats['losses'] += 1
        
        # 计算胜率
        for stats in symbol_stats.values():
            if stats['total_trades'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total_trades']) * 100
        
        return symbol_stats
    
    def get_time_analysis(self, account_name: Optional[str] = None) -> Dict:
        """
        时间段分析（哪个时间段交易更好）
        """
        trades = self.db.get_trades(account_name, limit=1000, status='closed')
        
        hour_stats = {i: {'total': 0, 'wins': 0, 'pnl': 0} for i in range(24)}
        weekday_stats = {i: {'total': 0, 'wins': 0, 'pnl': 0} for i in range(7)}
        
        for trade in trades:
            if trade['entry_time']:
                try:
                    dt = datetime.fromisoformat(trade['entry_time'])
                    hour = dt.hour
                    weekday = dt.weekday()
                    
                    hour_stats[hour]['total'] += 1
                    weekday_stats[weekday]['total'] += 1
                    
                    if trade['pnl']:
                        hour_stats[hour]['pnl'] += trade['pnl']
                        weekday_stats[weekday]['pnl'] += trade['pnl']
                        
                        if trade['pnl'] > 0:
                            hour_stats[hour]['wins'] += 1
                            weekday_stats[weekday]['wins'] += 1
                except:
                    pass
        
        # 计算胜率
        for stats in hour_stats.values():
            if stats['total'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total']) * 100
        
        for stats in weekday_stats.values():
            if stats['total'] > 0:
                stats['win_rate'] = (stats['wins'] / stats['total']) * 100
        
        weekday_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        weekday_stats_named = {
            weekday_names[day]: stats 
            for day, stats in weekday_stats.items()
        }
        
        return {
            'by_hour': hour_stats,
            'by_weekday': weekday_stats_named,
        }
    
    def generate_report(self, account_name: str, days: int = 30) -> str:
        """
        生成文本格式的交易报告
        
        Returns:
            str: 格式化的报告文本
        """
        performance = self.get_account_performance(account_name, days)
        summary = performance['summary']
        metrics = performance['metrics']
        
        report = []
        report.append("=" * 60)
        report.append(f"交易报告 - {account_name}")
        report.append(f"统计周期: 最近 {days} 天")
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 60)
        report.append("")
        
        # 基本统计
        report.append("【基本统计】")
        report.append(f"  总交易次数: {summary['total_trades']}")
        report.append(f"  盈利交易: {summary['winning_trades']}")
        report.append(f"  亏损交易: {summary['losing_trades']}")
        report.append(f"  胜率: {summary['win_rate']:.2f}%")
        report.append("")
        
        # 盈亏统计
        report.append("【盈亏统计】")
        report.append(f"  总盈亏: {summary['total_pnl']:.2f} USDT")
        report.append(f"  平均盈亏: {summary['average_pnl']:.2f} USDT")
        report.append(f"  最大单笔盈利: {summary['largest_win']:.2f} USDT")
        report.append(f"  最大单笔亏损: {summary['largest_loss']:.2f} USDT")
        report.append(f"  盈亏比: {summary['profit_factor']:.2f}")
        report.append("")
        
        # 风险指标
        if metrics:
            report.append("【风险指标】")
            report.append(f"  最大回撤: {metrics.get('max_drawdown', 0):.2f} USDT")
            report.append(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
            report.append(f"  平均持仓时间: {metrics.get('avg_holding_time_hours', 0):.2f} 小时")
            report.append(f"  总手续费: {metrics.get('total_fees', 0):.2f} USDT")
            report.append(f"  投资回报率: {metrics.get('roi', 0):.2f}%")
            report.append("")
        
        # 最近交易
        report.append("【最近5笔交易】")
        for i, trade in enumerate(performance['recent_trades'][:5], 1):
            pnl_str = f"+{trade['pnl']:.2f}" if trade['pnl'] > 0 else f"{trade['pnl']:.2f}"
            report.append(f"  {i}. {trade['symbol']} - {trade['side'].upper()} - {pnl_str} USDT")
        report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def export_to_csv(self, account_name: Optional[str] = None, 
                     filename: str = "trades_export.csv") -> bool:
        """导出交易记录到 CSV"""
        try:
            import csv
            
            trades = self.db.get_trades(account_name, limit=10000, status='closed')
            
            if not trades:
                logger.warning("没有交易记录可导出")
                return False
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(f, fieldnames=trades[0].keys())
                writer.writeheader()
                writer.writerows(trades)
            
            logger.info(f"✓ 交易记录已导出到: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"✗ 导出CSV失败: {e}")
            return False

# 全局实例
trading_stats = TradingStatistics()

