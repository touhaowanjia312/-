import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """配置类"""
    
    # Telegram 配置
    TELEGRAM_API_ID = os.getenv('TELEGRAM_API_ID')
    TELEGRAM_API_HASH = os.getenv('TELEGRAM_API_HASH')
    TELEGRAM_PHONE = os.getenv('TELEGRAM_PHONE')
    TELEGRAM_GROUP_ID = os.getenv('TELEGRAM_GROUP_ID')
    
    # 交易所配置
    EXCHANGE_NAME = os.getenv('EXCHANGE_NAME', 'binance')
    EXCHANGE_API_KEY = os.getenv('EXCHANGE_API_KEY')
    EXCHANGE_API_SECRET = os.getenv('EXCHANGE_API_SECRET')
    EXCHANGE_TESTNET = os.getenv('EXCHANGE_TESTNET', 'True').lower() == 'true'
    
    # 交易配置
    TRADING_ENABLED = os.getenv('TRADING_ENABLED', 'False').lower() == 'true'
    DEFAULT_POSITION_SIZE = float(os.getenv('DEFAULT_POSITION_SIZE', '0.01'))
    MAX_POSITION_SIZE = float(os.getenv('MAX_POSITION_SIZE', '0.1'))
    RISK_PERCENTAGE = float(os.getenv('RISK_PERCENTAGE', '1.0'))
    
    @classmethod
    def validate(cls):
        """验证配置是否完整"""
        required = [
            ('TELEGRAM_API_ID', cls.TELEGRAM_API_ID),
            ('TELEGRAM_API_HASH', cls.TELEGRAM_API_HASH),
            ('TELEGRAM_PHONE', cls.TELEGRAM_PHONE),
            ('TELEGRAM_GROUP_ID', cls.TELEGRAM_GROUP_ID),
        ]
        
        # 检查是否有多交易所配置
        has_multi_exchange = False
        try:
            from multi_exchange_client import multi_exchange_client
            has_multi_exchange = len(multi_exchange_client.clients) > 0
        except:
            pass
        
        # 只有在启用交易且没有多交易所配置时，才要求单交易所配置
        if cls.TRADING_ENABLED and not has_multi_exchange:
            required.extend([
                ('EXCHANGE_API_KEY', cls.EXCHANGE_API_KEY),
                ('EXCHANGE_API_SECRET', cls.EXCHANGE_API_SECRET),
            ])
        
        missing = [name for name, value in required if not value]
        
        if missing:
            raise ValueError(f"缺少必要的配置项: {', '.join(missing)}")
        
        return True

