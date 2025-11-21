"""
智能订单管理器
优先使用信号中的止盈止损，然后添加额外的分批止盈
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TPSLConfig:
    """止盈止损配置"""
    use_signal_tpsl: bool = True  # 优先使用信号中的TP/SL
    additional_tps: List[Dict] = None  # 额外的止盈点
    default_stop_loss_percent: float = 2.0
    trailing_stop_enabled: bool = True
    trailing_stop_percent: float = 2.0
    breakeven_enabled: bool = True
    breakeven_trigger_percent: float = 1.0
    stop_trailing_after_breakeven: bool = False
    
    def __post_init__(self):
        if self.additional_tps is None:
            # 默认分批（用于“无价格型TP提示”的回退策略）：10%/20%/50%，仓位 50%/30%/20%
            self.additional_tps = [
                {'profit_percent': 10.0, 'portion_percent': 50.0},
                {'profit_percent': 20.0, 'portion_percent': 30.0},
                {'profit_percent': 50.0, 'portion_percent': 20.0}
            ]

class SmartOrderManager:
    """智能订单管理器"""
    
    def __init__(self, config_file: str = 'tpsl_config.json'):
        self.config_file = Path(config_file)
        self.config = self._load_config()
        
    def _load_config(self) -> TPSLConfig:
        """加载配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return TPSLConfig(
                    use_signal_tpsl=data.get('use_signal_tpsl', True),
                    additional_tps=data.get('additional_tps'),
                    default_stop_loss_percent=data.get('default_stop_loss_percent', 2.0),
                    trailing_stop_enabled=data.get('trailing_stop', {}).get('enabled', True),
                    trailing_stop_percent=data.get('trailing_stop', {}).get('percent', 2.0),
                    breakeven_enabled=data.get('breakeven', {}).get('enabled', True),
                    breakeven_trigger_percent=data.get('breakeven', {}).get('trigger_percent', 1.0),
                    stop_trailing_after_breakeven=data.get('stop_trailing_after_breakeven', False)
                )
            except Exception as e:
                logger.warning(f"加载配置失败，使用默认配置: {e}")
                return TPSLConfig()
        else:
            logger.info("配置文件不存在，使用默认配置")
            return TPSLConfig()
    
    def create_order_plan(self, signal: Any) -> Dict[str, Any]:
        """
        根据信号创建订单计划
        
        策略：
        1. 优先使用信号中的止盈止损
        2. 如果信号没有TP/SL，使用默认配置
        3. 在信号TP基础上，添加额外的TP2/TP3
        
        Args:
            signal: 交易信号对象
            
        Returns:
            订单计划字典
        """
        plan = {
            'symbol': signal.symbol,
            'side': signal.signal_type.value.lower(),
            'entry_price': signal.entry_price,
            'stop_loss': None,
            'take_profits': [],
            'tp_portions': [],  # 每个TP的仓位比例
            'leverage': signal.leverage,
            'trailing_stop': self.config.trailing_stop_enabled,
            'trailing_stop_percent': self.config.trailing_stop_percent,
            'move_to_breakeven': self.config.breakeven_enabled,
            'breakeven_trigger_percent': self.config.breakeven_trigger_percent,
            'stop_trailing_after_breakeven': getattr(self.config, 'stop_trailing_after_breakeven', False)
        }
        
        # 1. 处理止损
        if self.config.use_signal_tpsl and signal.stop_loss:
            # 使用信号中的止损
            plan['stop_loss'] = signal.stop_loss
            logger.info(f"✓ 使用信号止损: {signal.stop_loss}")
        else:
            # 使用默认止损百分比
            if signal.entry_price:
                sl_percent = self.config.default_stop_loss_percent / 100
                if signal.signal_type.value in ['LONG', 'BUY']:
                    plan['stop_loss'] = signal.entry_price * (1 - sl_percent)
                else:
                    plan['stop_loss'] = signal.entry_price * (1 + sl_percent)
                logger.info(f"✓ 使用默认止损: {plan['stop_loss']} ({self.config.default_stop_loss_percent}%)")
            else:
                # 市价单：止损百分比会在实际执行时基于成交价计算
                plan['stop_loss_percent'] = self.config.default_stop_loss_percent
                logger.info(f"✓ 市价单 - 止损将基于成交价计算: {self.config.default_stop_loss_percent}%")
        
        # 2. 处理止盈
        if self.config.use_signal_tpsl and signal.take_profit:
            # 使用信号中的止盈
            signal_tps = signal.take_profit if isinstance(signal.take_profit, list) else [signal.take_profit]
            
            # 计算信号TP的仓位分配
            num_signal_tps = len(signal_tps)
            if num_signal_tps > 0:
                # 信号TP占总仓位的60%，平均分配
                signal_portion = 60.0 / num_signal_tps
                for tp in signal_tps:
                    plan['take_profits'].append(tp)
                    plan['tp_portions'].append(signal_portion)
                
                logger.info(f"✓ 使用信号止盈: {signal_tps}")
                logger.info(f"  每个信号TP仓位: {signal_portion:.1f}%")
                
                # 3. 添加额外的止盈点（基于入场价）
                if signal.entry_price and self.config.additional_tps:
                    # 剩余40%仓位用于额外TP
                    total_additional_portion = sum(tp['portion_percent'] for tp in self.config.additional_tps)
                    
                    for additional_tp in self.config.additional_tps:
                        profit_pct = additional_tp['profit_percent'] / 100
                        
                        # 计算额外TP价格
                        if signal.signal_type.value in ['LONG', 'BUY']:
                            tp_price = signal.entry_price * (1 + profit_pct)
                        else:
                            tp_price = signal.entry_price * (1 - profit_pct)
                        
                        # 只添加比信号最高TP更高的额外TP
                        if signal.signal_type.value in ['LONG', 'BUY']:
                            if tp_price > max(signal_tps):
                                # 重新分配仓位比例（剩余40%中的比例）
                                portion = (additional_tp['portion_percent'] / total_additional_portion) * 40.0
                                plan['take_profits'].append(tp_price)
                                plan['tp_portions'].append(portion)
                        else:
                            if tp_price < min(signal_tps):
                                portion = (additional_tp['portion_percent'] / total_additional_portion) * 40.0
                                plan['take_profits'].append(tp_price)
                                plan['tp_portions'].append(portion)
                    
                    logger.info(f"✓ 添加额外止盈点: {len(plan['take_profits']) - num_signal_tps} 个")
        else:
            # 信号没有TP，完全使用默认配置
            if signal.entry_price:
                for additional_tp in self.config.additional_tps:
                    profit_pct = additional_tp['profit_percent'] / 100
                    
                    if signal.signal_type.value in ['LONG', 'BUY']:
                        tp_price = signal.entry_price * (1 + profit_pct)
                    else:
                        tp_price = signal.entry_price * (1 - profit_pct)
                    
                    plan['take_profits'].append(tp_price)
                    plan['tp_portions'].append(additional_tp['portion_percent'])
                
                logger.info(f"✓ 信号无止盈，使用默认配置: {len(plan['take_profits'])} 个TP")
        
        # 规范化仓位比例（确保总和为100%）
        if plan['tp_portions']:
            total = sum(plan['tp_portions'])
            plan['tp_portions'] = [p / total * 100 for p in plan['tp_portions']]
        
        return plan
    
    def format_plan_summary(self, plan: Dict[str, Any]) -> str:
        """格式化订单计划摘要"""
        entry_text = plan['entry_price'] if plan['entry_price'] else "市价（实时成交）"
        
        # 止损显示
        if plan.get('stop_loss'):
            sl_text = str(plan['stop_loss'])
        elif plan.get('stop_loss_percent'):
            sl_text = f"市价 {'+' if plan['side'] == 'short' else '-'}{plan['stop_loss_percent']}%"
        else:
            sl_text = "无"
        
        lines = [
            f"📊 订单计划",
            f"━━━━━━━━━━━━━━━━━━━━",
            f"交易对: {plan['symbol']}",
            f"方向: {plan['side'].upper()}",
            f"入场: {entry_text}",
            f"",
            f"🛑 止损: {sl_text}",
            f""
        ]
        
        if plan['take_profits']:
            lines.append(f"🎯 止盈点 ({len(plan['take_profits'])} 个):")
            for i, (tp, portion) in enumerate(zip(plan['take_profits'], plan['tp_portions']), 1):
                lines.append(f"  TP{i}: {tp} ({portion:.1f}%)")
        
        lines.append(f"")
        if plan['trailing_stop']:
            lines.append(f"📈 追踪止损: {plan['trailing_stop_percent']}%")
        if plan['move_to_breakeven']:
            lines.append(f"⚖️ 保本止损: 盈利 {plan['breakeven_trigger_percent']}% 后触发")
        
        return '\n'.join(lines)


# 全局实例
smart_order_manager = SmartOrderManager()


if __name__ == "__main__":
    # 测试代码
    import sys
    from signal_parser import SignalParser, SignalType, TradingSignal
    
    # Windows 编码修复
    if sys.platform == 'win32':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 50)
    print("测试智能订单管理器")
    print("=" * 50)
    
    # 测试1: 信号包含TP/SL
    print("\n📝 测试1: 信号包含止盈止损")
    print("-" * 50)
    
    signal1 = TradingSignal(
        signal_type=SignalType.LONG,
        symbol="BTC/USDT",
        entry_price=42000,
        stop_loss=41500,
        take_profit=[43000, 44000],  # 两个止盈
        leverage=10
    )
    
    manager = SmartOrderManager()
    plan1 = manager.create_order_plan(signal1)
    print(manager.format_plan_summary(plan1))
    
    # 测试2: 信号没有TP/SL
    print("\n\n📝 测试2: 信号没有止盈止损")
    print("-" * 50)
    
    signal2 = TradingSignal(
        signal_type=SignalType.SHORT,
        symbol="ETH/USDT",
        entry_price=2200,
        leverage=5
    )
    
    plan2 = manager.create_order_plan(signal2)
    print(manager.format_plan_summary(plan2))
    
    # 测试3: 信号只有一个TP
    print("\n\n📝 测试3: 信号只有一个止盈")
    print("-" * 50)
    
    signal3 = TradingSignal(
        signal_type=SignalType.LONG,
        symbol="SOL/USDT",
        entry_price=100,
        stop_loss=98,
        take_profit=[102],  # 只有一个止盈
        leverage=10
    )
    
    plan3 = manager.create_order_plan(signal3)
    print(manager.format_plan_summary(plan3))
    
    print("\n" + "=" * 50)
    print("测试完成！")
    print("=" * 50)

