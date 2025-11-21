"""
多交易所配置管理
支持同时配置多个交易所账户
"""

import os
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
import json

load_dotenv()

class ExchangeAccount:
    """单个交易所账户配置"""
    
    def __init__(self, name: str, exchange_type: str, api_key: str, 
                 api_secret: str, password: str = "", testnet: bool = True, enabled: bool = True,
                 default_leverage: int = 10, default_position_size: float = 0.01,
                 max_position_size: float = 0.1, risk_percentage: float = 1.0,
                 use_margin_amount: bool = False, margin_amount: float = 100.0,
                 manual_contract_balance: float = 0.0, risk_as_notional: bool = False):
        """
        Args:
            name: 账户名称（如 "币安主账户"）
            exchange_type: 交易所类型（如 "binance", "okx"）
            api_key: API Key
            api_secret: API Secret
            password: API Password (某些交易所需要，如bitget, okx)
            testnet: 是否使用测试网
            enabled: 是否启用此账户
            default_leverage: 默认杠杆倍数
            default_position_size: 默认仓位大小（币的数量）
            max_position_size: 最大仓位限制
            risk_percentage: 风险百分比（账户余额的百分比）
            use_margin_amount: 是否使用固定保证金金额
            margin_amount: 固定保证金金额（USDT）
        """
        self.name = name
        self.exchange_type = exchange_type
        self.api_key = api_key
        self.api_secret = api_secret
        self.password = password
        self.testnet = testnet
        self.enabled = enabled
        self.default_leverage = default_leverage
        self.default_position_size = default_position_size
        self.max_position_size = max_position_size
        self.risk_percentage = risk_percentage
        self.use_margin_amount = use_margin_amount
        self.margin_amount = margin_amount
        self.manual_contract_balance = manual_contract_balance
        self.risk_as_notional = risk_as_notional
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'name': self.name,
            'exchange_type': self.exchange_type,
            'api_key': self.api_key,
            'api_secret': self.api_secret,
            'password': self.password,
            'testnet': self.testnet,
            'enabled': self.enabled,
            'default_leverage': self.default_leverage,
            'default_position_size': self.default_position_size,
            'max_position_size': self.max_position_size,
            'risk_percentage': self.risk_percentage,
            'use_margin_amount': self.use_margin_amount,
            'margin_amount': self.margin_amount,
            'manual_contract_balance': self.manual_contract_balance,
            'risk_as_notional': self.risk_as_notional,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExchangeAccount':
        """从字典创建"""
        return cls(**data)
    
    def __repr__(self):
        status = "启用" if self.enabled else "禁用"
        network = "测试网" if self.testnet else "正式网"
        return f"<ExchangeAccount: {self.name} ({self.exchange_type}) - {status} - {network}>"

class MultiExchangeConfig:
    """多交易所配置管理器"""
    
    CONFIG_FILE = "exchanges_config.json"
    
    def __init__(self):
        self.accounts: List[ExchangeAccount] = []
        self.load_from_file()
        
        # 如果没有配置，尝试从 .env 加载默认配置
        if not self.accounts:
            self.load_from_env()
    
    def add_account(self, account: ExchangeAccount):
        """添加交易所账户"""
        self.accounts.append(account)
    
    def remove_account(self, name: str):
        """删除交易所账户"""
        self.accounts = [acc for acc in self.accounts if acc.name != name]
    
    def get_account(self, name: str) -> Optional[ExchangeAccount]:
        """获取指定账户"""
        for acc in self.accounts:
            if acc.name == name:
                return acc
        return None
    
    def get_enabled_accounts(self) -> List[ExchangeAccount]:
        """获取所有启用的账户"""
        return [acc for acc in self.accounts if acc.enabled]
    
    def save_to_file(self):
        """保存配置到文件"""
        data = {
            'accounts': [acc.to_dict() for acc in self.accounts]
        }
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_from_file(self):
        """从文件加载配置"""
        if not os.path.exists(self.CONFIG_FILE):
            return
        
        try:
            with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.accounts = [
                ExchangeAccount.from_dict(acc_data) 
                for acc_data in data.get('accounts', [])
            ]
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    def load_from_env(self):
        """从 .env 文件加载默认配置（向后兼容）"""
        from config import Config
        
        if Config.EXCHANGE_API_KEY and Config.EXCHANGE_API_SECRET:
            default_account = ExchangeAccount(
                name="默认账户",
                exchange_type=Config.EXCHANGE_NAME or "binance",
                api_key=Config.EXCHANGE_API_KEY,
                api_secret=Config.EXCHANGE_API_SECRET,
                testnet=Config.EXCHANGE_TESTNET,
                enabled=True,
                default_leverage=10,
                default_position_size=Config.DEFAULT_POSITION_SIZE,
                max_position_size=Config.MAX_POSITION_SIZE,
                risk_percentage=Config.RISK_PERCENTAGE,
                use_margin_amount=False,
                margin_amount=100.0
            )
            self.add_account(default_account)
    
    def __len__(self):
        return len(self.accounts)
    
    def __iter__(self):
        return iter(self.accounts)

# 全局配置实例
multi_exchange_config = MultiExchangeConfig()
