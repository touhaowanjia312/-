import re
from typing import Optional, Dict, Any
from enum import Enum

class SignalType(Enum):
    """信号类型"""
    BUY = "BUY"
    SELL = "SELL"
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE = "CLOSE"
    UNKNOWN = "UNKNOWN"

class TradingSignal:
    """交易信号类"""
    
    def __init__(self, signal_type: SignalType, symbol: str, entry_price: Optional[float] = None,
                 stop_loss: Optional[float] = None, take_profit: Optional[list] = None,
                 leverage: Optional[int] = None, raw_message: str = ""):
        self.signal_type = signal_type
        self.symbol = symbol
        self.entry_price = entry_price
        self.stop_loss = stop_loss
        self.take_profit = take_profit or []
        self.leverage = leverage
        self.raw_message = raw_message
    
    def __repr__(self):
        return (f"TradingSignal(type={self.signal_type.value}, symbol={self.symbol}, "
                f"entry={self.entry_price}, sl={self.stop_loss}, tp={self.take_profit})")

class SignalParser:
    """信号解析器"""
    
    # 常见的信号关键词（支持简体和繁体）
    BUY_KEYWORDS = [
        'buy', 'long',
        '做多', '买入', '開多', '开多', '買入',
        '市价多', '市價多', '市价进多', '市價進多',
        '现价多', '現價多', '现价进多', '現價進多',
        '轻仓多', '半仓多', '重仓多', '輕倉多', '半倉多', '重倉多',
        '轻仓开多', '半仓开多', '重仓开多', '輕倉開多', '半倉開多', '重倉開多'
        , '进多', '進多', '市价开多', '市價開多', '多单', '多單', '反手多'
    ]
    SELL_KEYWORDS = [
        'sell', 'short',
        '做空', '卖出', '賣出', '開空', '开空',
        '市价空', '市價空', '市价进空', '市價進空',
        '现价空', '現價空', '现价进空', '現價進空',
        '轻仓空', '半仓空', '重仓空', '輕倉空', '半倉空', '重倉空',
        '轻仓开空', '半仓开空', '重仓开空', '輕倉開空', '半倉開空', '重倉開空',
        '进空', '進空', '市价开空', '市價開空', '空单', '空單', '反手空'
    ]
    CLOSE_KEYWORDS = ['close', 'exit', '平仓', '关闭', '平倉', '關閉', '清仓', '清倉', '平多', '平空']
    
    @staticmethod
    def parse(message: str) -> Optional[TradingSignal]:
        """
        解析 Telegram 消息，提取交易信号
        
        Args:
            message: Telegram 消息内容
            
        Returns:
            TradingSignal 对象或 None
        """
        message_lower = message.lower()
        
        # 确定信号类型
        signal_type = SignalParser._detect_signal_type(message_lower)
        if signal_type == SignalType.UNKNOWN:
            return None
        
        # 提取交易对
        symbol = SignalParser._extract_symbol(message)
        if not symbol:
            return None
        
        # 提取价格信息
        entry_price = SignalParser._extract_price(message, ['entry', 'price', '入场', '价格'])
        stop_loss = SignalParser._extract_price(message, ['stop loss', 'sl', '止损'])
        take_profit = SignalParser._extract_take_profit(message)
        leverage = SignalParser._extract_leverage(message)
        
        return TradingSignal(
            signal_type=signal_type,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            leverage=leverage,
            raw_message=message
        )
    
    @staticmethod
    def _detect_signal_type(message: str) -> SignalType:
        """
        检测信号类型
        
        🔧 BUG 16 修复：排除统计/总结类消息，但保留真实信号
        """
        # 🔧 排除规则1：回顾/战绩/统计/复盘/总结类消息
        review_keywords = [
            '获利', '獲利', '盈利', '盈亏', '盈虧', '胜率', '收益', '净值',
            '战绩', '戰績', '战报', '戰報', '统计', '統計', '月度', '周度', '复盘', '復盤', '总结', '總結',
            '回顾', '回顧', '本周', '上周', '每日总结', '每天战绩', '目标已达成', 'TP达成'
        ]
        if any(kw in message for kw in review_keywords):
            return SignalType.UNKNOWN
        
        # 🔧 排除规则2：如果包含多个排除关键词（统计、日期、推广等）
        exclude_keywords = ['号', '號', '点击', '点击进入', '免费', '体验', '每天', '每場']
        exclude_count = sum(1 for kw in exclude_keywords if kw in message)
        if exclude_count >= 2:
            return SignalType.UNKNOWN
        
        # 正常的信号类型检测
        for keyword in SignalParser.BUY_KEYWORDS:
            if keyword in message:
                return SignalType.LONG
        
        for keyword in SignalParser.SELL_KEYWORDS:
            if keyword in message:
                return SignalType.SHORT
        
        for keyword in SignalParser.CLOSE_KEYWORDS:
            if keyword in message:
                return SignalType.CLOSE
        
        # 补充：仅当“止盈/目标/TPx”同时出现明确价格格式（含冒号/空格后的数值）时，视为分批平仓
        # 避免 "TP1/TP2 已触发/达成" 这类无价格统计类提示被当成信号
        tp_price_patterns = [
            r'(?:第[一二三四五六七八九十1-9]\s*止盈|tp\s*\d*|目标)\s*[:：\s]+(\d+\.?\d*)',
            r'(?:止盈|目标)\s*[:：\s]+(\d+\.?\d*)'
        ]
        for pat in tp_price_patterns:
            if re.search(pat, message, re.IGNORECASE):
                return SignalType.CLOSE
        # 若仅出现 “已触发/达成/到位” 且不含明确价格，忽略
        trigger_only_keywords = ['已触发', '已觸發', '达成', '達成', '到位']
        if any(k in message for k in trigger_only_keywords):
            return SignalType.UNKNOWN
        
        return SignalType.UNKNOWN
    
    @staticmethod
    def _extract_symbol(message: str) -> Optional[str]:
        """
        提取交易对符号
        例如: BTC/USDT, BTCUSDT, #BTC, $BTC
        
        🔧 BUG 16 修复：优先匹配 # 和 $ 开头的符号，避免误匹配 URL
        """
        # 🔧 优先匹配带 # 或 $ 前缀的符号（最常见的信号格式）
        priority_patterns = [
            r'#([A-Z0-9]{1,10})\b',  # 支持以数字开头，如 #0G
            r'\$([A-Z0-9]{1,10})\b',  # 支持以数字开头，如 $0G
        ]
        
        for pattern in priority_patterns:
            match = re.search(pattern, message.upper())
            if match:
                # 只匹配到币种，默认配对 USDT
                return f"{match.group(1)}/USDT"
        
        # 🔧 其他格式（需要排除 URL）
        other_patterns = [
            r'([A-Z0-9]{2,10})/([A-Z]{3,5})',  # BTC/USDT 或 0G/USDT
            r'([A-Z0-9]{2,10})(USDT|BUSD|USDC|DAI)\b',  # BTCUSDT 或 0GUSDT
            r'\b([A-Z0-9]{2,10})\s*USDT',  # BTC USDT 或 0G USDT
        ]
        
        # 🔧 排除 URL 区域（http:// 或 https:// 开头到下一个空格）
        clean_message = re.sub(r'https?://[^\s]+', '', message, flags=re.IGNORECASE)
        
        for pattern in other_patterns:
            match = re.search(pattern, clean_message.upper())
            if match:
                if len(match.groups()) == 2:
                    # 匹配到完整交易对
                    return f"{match.group(1)}/{match.group(2)}"
                else:
                    # 只匹配到币种，默认配对 USDT
                    return f"{match.group(1)}/USDT"
        
        return None
    
    @staticmethod
    def _extract_price(message: str, keywords: list) -> Optional[float]:
        """提取价格"""
        for keyword in keywords:
            pattern = rf'{keyword}[:\s]*(\d+\.?\d*)'
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
        return None
    
    @staticmethod
    def _extract_take_profit(message: str) -> list:
        """提取止盈目标（可能有多个）- 增强版支持中文格式"""
        tp_list = []
        patterns = [
            # 英文格式
            r'tp\s*\d*[:\s：]*(\d+\.?\d*)',
            r'take\s*profit\s*\d*[:\s：]*(\d+\.?\d*)',
            r'target\s*\d*[:\s：]*(\d+\.?\d*)',
            # 中文格式（简体）
            r'止盈\s*\d*[:\s：]*(\d+\.?\d*)',
            r'目标\s*\d*[:\s：]*(\d+\.?\d*)',
            # 特殊中文格式："第一止盈"、"第二止盈"等
            r'第[一二三四五六七八九十1-9]\s*止盈[:\s：]*(\d+\.?\d*)',
            r'第[一二三四五六七八九十1-9]\s*目标[:\s：]*(\d+\.?\d*)',
            # Emoji 格式
            r'🎯\s*\d*[:\s：]*(\d+\.?\d*)',
            # 新增中文习惯用法："到0.0703 减仓/保本一次"、"到 0.0703" 等
            r'到[:\s]*?(\d+\.?\d*)',
            r'到价[:\s：]*?(\d+\.?\d*)',
            r'(?:减仓|減倉|保本)[:\s]*?(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, message, re.IGNORECASE)
            for match in matches:
                try:
                    price = float(match.group(1))
                    if price > 0 and price not in tp_list:
                        tp_list.append(price)
                except (ValueError, IndexError):
                    continue
        
        # 按价格排序
        return sorted(tp_list)
    
    @staticmethod
    def _extract_leverage(message: str) -> Optional[int]:
        """提取杠杆倍数"""
        patterns = [
            r'leverage[:\s]*(\d+)[x]?',
            r'(\d+)[x]\s*leverage',
            r'杠杆[:\s]*(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None

