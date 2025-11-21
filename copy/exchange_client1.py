import ccxt
from typing import Optional, Dict, Any
from config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExchangeClient:
    """交易所客户端"""
    
    def __init__(self):
        self.exchange = None
        self.initialized = False
        self._init_exchange()
    
    def _init_exchange(self):
        """初始化交易所连接"""
        try:
            exchange_class = getattr(ccxt, Config.EXCHANGE_NAME)
            self.exchange = exchange_class({
                'apiKey': Config.EXCHANGE_API_KEY,
                'secret': Config.EXCHANGE_API_SECRET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # 默认使用合约交易
                }
            })
            
            if Config.EXCHANGE_TESTNET:
                if hasattr(self.exchange, 'set_sandbox_mode'):
                    self.exchange.set_sandbox_mode(True)
                    logger.info("已启用测试网模式")
            
            # 测试连接
            self.exchange.load_markets()
            self.initialized = True
            logger.info(f"成功连接到 {Config.EXCHANGE_NAME}")
            
        except Exception as e:
            logger.error(f"初始化交易所失败: {e}")
            self.initialized = False
    
    def get_balance(self, currency: str = 'USDT') -> Optional[float]:
        """获取账户余额"""
        if not self.initialized:
            return None
        
        try:
            balance = self.exchange.fetch_balance()
            return balance['free'].get(currency, 0.0)
        except Exception as e:
            logger.error(f"获取余额失败: {e}")
            return None
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前市场价格"""
        if not self.initialized:
            return None
        
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"获取价格失败 {symbol}: {e}")
            return None
    
    def place_market_order(self, symbol: str, side: str, amount: float) -> Optional[Dict[str, Any]]:
        """
        下市价单
        
        Args:
            symbol: 交易对，如 'BTC/USDT'
            side: 'buy' 或 'sell'
            amount: 交易数量
            
        Returns:
            订单信息或 None
        """
        if not self.initialized or not Config.TRADING_ENABLED:
            logger.warning("交易未启用或交易所未初始化")
            return None
        
        try:
            order = self.exchange.create_market_order(symbol, side, amount)
            logger.info(f"订单已下: {side} {amount} {symbol}")
            return order
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return None
    
    def place_limit_order(self, symbol: str, side: str, amount: float, price: float) -> Optional[Dict[str, Any]]:
        """
        下限价单
        
        Args:
            symbol: 交易对
            side: 'buy' 或 'sell'
            amount: 交易数量
            price: 限价
            
        Returns:
            订单信息或 None
        """
        if not self.initialized or not Config.TRADING_ENABLED:
            logger.warning("交易未启用或交易所未初始化")
            return None
        
        try:
            order = self.exchange.create_limit_order(symbol, side, amount, price)
            logger.info(f"限价单已下: {side} {amount} {symbol} @ {price}")
            return order
        except Exception as e:
            logger.error(f"下限价单失败: {e}")
            return None
    
    def set_leverage(self, symbol: str, leverage: int) -> bool:
        """设置杠杆倍数"""
        if not self.initialized:
            return False
        
        try:
            self.exchange.set_leverage(leverage, symbol)
            logger.info(f"已设置 {symbol} 杠杆为 {leverage}x")
            return True
        except Exception as e:
            logger.error(f"设置杠杆失败: {e}")
            return False
    
    def close_position(self, symbol: str) -> bool:
        """平仓"""
        if not self.initialized or not Config.TRADING_ENABLED:
            return False
        
        try:
            # 获取当前持仓
            positions = self.exchange.fetch_positions([symbol])
            for position in positions:
                if float(position['contracts']) > 0:
                    side = 'sell' if position['side'] == 'long' else 'buy'
                    amount = abs(float(position['contracts']))
                    self.place_market_order(symbol, side, amount)
                    logger.info(f"已平仓 {symbol}")
                    return True
            
            logger.info(f"没有 {symbol} 的持仓")
            return False
            
        except Exception as e:
            logger.error(f"平仓失败: {e}")
            return False
    
    def calculate_position_size(self, symbol: str, price: float, risk_percentage: float) -> float:
        """
        根据风险百分比计算仓位大小
        
        Args:
            symbol: 交易对
            price: 入场价格
            risk_percentage: 风险百分比（账户余额的百分比）
            
        Returns:
            交易数量
        """
        balance = self.get_balance('USDT')
        if not balance:
            return 0.0
        
        risk_amount = balance * (risk_percentage / 100)
        position_size = risk_amount / price
        
        # 限制最大仓位
        max_position = Config.MAX_POSITION_SIZE
        position_size = min(position_size, max_position)
        
        return round(position_size, 3)

    def place_stop_loss_order(self, symbol: str, side: str, amount: float, stop_price: float) -> Optional[Dict[str, Any]]:
        """设置止损订单（通用实现，使用统一参数 stopLossPrice）"""
        if not self.initialized or not Config.TRADING_ENABLED:
            return None
        try:
            # 使用统一的 stopLossPrice 参数，reduceOnly 防止加仓
            params = {
                'reduceOnly': True,
                'stopLossPrice': stop_price,
            }
            order = self.exchange.create_order(
                symbol=symbol,
                type='market',
                side=side,
                amount=amount,
                price=None,
                params=params,
            )
            logger.info(f"止损单已下: {side} {amount} {symbol} @ SL {stop_price}")
            return order
        except Exception as e:
            logger.error(f"止损下单失败: {e}")
            return None

    def place_take_profit_order(self, symbol: str, side: str, amount: float, tp_price: float) -> Optional[Dict[str, Any]]:
        """设置止盈限价单（reduce-only）"""
        if not self.initialized or not Config.TRADING_ENABLED:
            return None
        try:
            params = {
                'reduceOnly': True,
            }
            order = self.exchange.create_limit_order(symbol, side, amount, tp_price, params=params)
            logger.info(f"止盈单已下: {side} {amount} {symbol} @ {tp_price}")
            return order
        except Exception as e:
            logger.error(f"止盈下单失败: {e}")
            return None

