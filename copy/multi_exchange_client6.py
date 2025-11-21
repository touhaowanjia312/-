"""
多交易所客户端管理
支持同时操作多个交易所账户
"""

import ccxt
from typing import Dict, List, Optional, Any
from multi_exchange_config import ExchangeAccount, multi_exchange_config
import logging
from retry_utils import retry_call, log_struct

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MultiExchangeClient:
    """多交易所客户端管理器"""
    
    def __init__(self):
        self.clients: Dict[str, ccxt.Exchange] = {}
        self.accounts: Dict[str, ExchangeAccount] = {}
        self._init_all_exchanges()
    
    def _init_all_exchanges(self):
        """初始化所有启用的交易所"""
        for account in multi_exchange_config.get_enabled_accounts():
            self.add_exchange(account)
    
    def add_exchange(self, account: ExchangeAccount):
        """添加并初始化一个交易所"""
        try:
            # 确保交易所类型是小写（ccxt要求）
            exchange_type = account.exchange_type.lower()
            
            # 验证交易所是否支持
            if not hasattr(ccxt, exchange_type):
                raise ValueError(f"不支持的交易所: {exchange_type}，请检查名称是否正确（必须小写）")
            
            exchange_class = getattr(ccxt, exchange_type)
            
            # 基础配置
            config = {
                'apiKey': account.api_key.strip(),  # 移除可能的空格和换行
                'secret': account.api_secret.strip(),
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',
                }
            }
            
            # 某些交易所需要 password（如 bitget, okx）
            if account.password and account.password.strip():
                config['password'] = account.password.strip()
            
            client = exchange_class(config)
            
            if account.testnet:
                if hasattr(client, 'set_sandbox_mode'):
                    client.set_sandbox_mode(True)
                    logger.info(f"{account.name} - 已启用测试网模式")
            
            # 测试连接
            retry_call(
                client.load_markets,
                retries=3,
                delay=0.6,
                logger=logger,
                op=f"{account.name}.load_markets",
            )
            
            self.clients[account.name] = client
            self.accounts[account.name] = account
            
            logger.info(f"✓ 成功连接到 {account.name} ({exchange_type})")
            
        except Exception as e:
            logger.error(f"✗ 初始化 {account.name} 失败: {e}")
    
    def remove_exchange(self, account_name: str):
        """移除交易所"""
        if account_name in self.clients:
            del self.clients[account_name]
            del self.accounts[account_name]
            logger.info(f"已移除交易所: {account_name}")
    
    def get_balance(self, account_name: str, currency: str = 'USDT') -> Optional[float]:
        """
        获取指定账户余额
        对于合约交易，获取合约账户余额而不是现货余额
        """
        if account_name not in self.clients:
            return None
        
        if account_name not in self.accounts:
            return None
        
        account = self.accounts[account_name]
        exchange_type = account.exchange_type.lower()
        
        try:
            client = self.clients[account_name]
            
            # 特殊处理：LBANK - 使用手动配置的合约余额
            if exchange_type == 'lbank':
                if hasattr(account, 'manual_contract_balance') and account.manual_contract_balance > 0:
                    logger.debug(f"{account_name} 使用手动配置的合约余额: {account.manual_contract_balance}")
                    return account.manual_contract_balance
                else:
                    # 回退到现货余额
                    balance = retry_call(
                        client.fetch_balance,
                        {'type': 'spot'},
                        retries=3,
                        delay=0.6,
                        logger=logger,
                        op=f"{account_name}.fetch_balance",
                    )
                    return balance['free'].get(currency, 0.0)
            
            # 其他交易所：尝试获取合约余额
            try:
                # 🔧 修复：明确获取合约余额（swap/future类型）
                futures_balance = retry_call(
                    client.fetch_balance,
                    {'type': 'swap'},
                    retries=3,
                    delay=0.6,
                    logger=logger,
                    op=f"{account_name}.fetch_balance",
                )
                futures_amount = futures_balance['free'].get(currency, 0.0)
                
                logger.debug(f"{account_name} 合约可用余额: {futures_amount}")
                return futures_amount
                
            except Exception as e:
                # 如果获取合约余额失败，尝试future类型
                logger.debug(f"获取swap余额失败，尝试future: {e}")
                try:
                    futures_balance = retry_call(
                        client.fetch_balance,
                        {'type': 'future'},
                        retries=3,
                        delay=0.6,
                        logger=logger,
                        op=f"{account_name}.fetch_balance",
                    )
                    futures_amount = futures_balance['free'].get(currency, 0.0)
                    logger.debug(f"{account_name} 期货可用余额: {futures_amount}")
                    return futures_amount
                except Exception as e2:
                    # 最后尝试默认余额
                    logger.debug(f"获取future余额失败，使用默认余额: {e2}")
                    balance = retry_call(
                        client.fetch_balance,
                        retries=3,
                        delay=0.6,
                        logger=logger,
                        op=f"{account_name}.fetch_balance",
                    )
                    return balance['free'].get(currency, 0.0)
                
        except Exception as e:
            logger.error(f"获取 {account_name} 余额失败: {e}")
            return None
    
    def get_balance_detailed(self, account_name: str, currency: str = 'USDT') -> Optional[Dict[str, float]]:
        """
        获取详细余额信息（现货+合约）
        返回: {'spot': xxx, 'futures': xxx, 'total': xxx}
        """
        if account_name not in self.clients:
            return None
        
        if account_name not in self.accounts:
            return None
        
        account = self.accounts[account_name]
        exchange_type = account.exchange_type.lower()
        
        try:
            client = self.clients[account_name]
            result = {'spot': 0.0, 'futures': 0.0, 'total': 0.0}
            
            # 🔧 修复：明确获取现货余额
            try:
                spot_balance = retry_call(
                    client.fetch_balance,
                    {'type': 'spot'},
                    retries=3,
                    delay=0.6,
                    logger=logger,
                    op=f"{account_name}.fetch_balance",
                )
                result['spot'] = spot_balance['free'].get(currency, 0.0)
                logger.debug(f"{account_name} 现货余额: {result['spot']}")
            except Exception as e:
                logger.debug(f"获取 {account_name} 现货余额失败: {e}")
                # 如果获取现货失败，尝试默认方式
                try:
                    default_balance = retry_call(
                        client.fetch_balance,
                        retries=3,
                        delay=0.6,
                        logger=logger,
                        op=f"{account_name}.fetch_balance",
                    )
                    result['spot'] = default_balance['free'].get(currency, 0.0)
                except:
                    result['spot'] = 0.0
            
            # 特殊处理：LBANK - 使用手动输入的合约余额
            if exchange_type == 'lbank':
                # LBANK的合约API被Cloudflare保护，CCXT暂不支持
                # 使用手动配置的合约余额
                if hasattr(account, 'manual_contract_balance') and account.manual_contract_balance > 0:
                    result['futures'] = account.manual_contract_balance
                    result['total'] = result['spot'] + result['futures']
                    logger.debug(f"{account_name} 使用手动配置的合约余额: {result['futures']}")
                else:
                    result['futures'] = 0.0
                    result['total'] = result['spot']
                    logger.debug(f"{account_name} 未配置合约余额，仅显示现货")
            else:
                # 其他交易所：尝试获取合约余额
                try:
                    # 🔧 修复：明确获取合约余额
                    futures_balance = retry_call(
                        client.fetch_balance,
                        {'type': 'swap'},
                        retries=3,
                        delay=0.6,
                        logger=logger,
                        op=f"{account_name}.fetch_balance",
                    )
                    futures_amount = futures_balance['free'].get(currency, 0.0)
                    
                    # 🔧 修复：Bitget是分离账户，不需要判断统一账户
                    # 只有当合约余额为0且现货余额>0时，才可能是纯现货账户
                    result['futures'] = futures_amount
                    result['total'] = result['spot'] + result['futures']
                    logger.debug(f"{account_name} 现货: {result['spot']}, 合约: {result['futures']}")
                except Exception as e:
                    # 不支持合约
                    result['total'] = result['spot']
                    result['futures'] = 0.0
                    logger.debug(f"{account_name} 合约查询失败: {e}")
            
            return result
        except Exception as e:
            logger.error(f"获取 {account_name} 详细余额失败: {e}")
            return None
    
    def get_all_balances(self) -> Dict[str, float]:
        """获取所有账户余额（简化版，返回总余额）"""
        balances = {}
        for account_name in self.clients.keys():
            balance = self.get_balance(account_name)
            if balance is not None:
                balances[account_name] = balance
        return balances
    
    def get_all_balances_detailed(self) -> Dict[str, Dict[str, float]]:
        """获取所有账户的详细余额"""
        balances = {}
        for account_name in self.clients.keys():
            balance = self.get_balance_detailed(account_name)
            if balance is not None:
                balances[account_name] = balance
        return balances
    
    def _convert_to_contract_symbol(self, client: ccxt.Exchange, symbol: str) -> str:
        """
        将符号转换为合约格式（优先返回 USDT 本位合约，如 X/USDT:USDT）
        对 Bitget 等同时存在现货/合约市场的交易所，优先选择合约符号。
        """
        # 已经是合约格式
        if ':' in symbol:
            return symbol

        # 构造常见的 USDT 本位合约候选
        candidates = []
        if symbol.endswith('/USDT'):
            candidates.append(f"{symbol}:USDT")
        else:
            # 传入可能是不完整的 base，补全到 base/USDT:USDT
            base = symbol.split('/')[0]
            candidates.append(f"{base}/USDT:USDT")

        # 先尝试候选合约符号
        for cs in candidates:
            if cs in getattr(client, 'markets', {}):
                return cs

        # 遍历市场，优先找 swap 类型（USDT 本位）
        markets = getattr(client, 'markets', {}) or {}
        base_upper = (symbol.split('/')[0] if '/' in symbol else symbol).upper()
        for m_symbol, m in markets.items():
            try:
                if m.get('type') == 'swap' and m.get('base') == base_upper and m.get('quote') == 'USDT':
                    return m_symbol
            except Exception:
                continue

        # 找不到合约，则如果现货存在，返回现货符号；否则原样返回
        if symbol in markets:
            return symbol
        return symbol
    
    def get_current_price(self, account_name: str, symbol: str) -> Optional[float]:
        """获取当前市场价格"""
        if account_name not in self.clients:
            return None
        
        try:
            client = self.clients[account_name]
            # 转换为合约符号
            symbol = self._convert_to_contract_symbol(client, symbol)
            ticker = retry_call(
                client.fetch_ticker,
                symbol,
                retries=3,
                delay=0.6,
                logger=logger,
                op=f"{account_name}.fetch_ticker",
            )
            return ticker['last']
        except Exception as e:
            logger.error(f"获取 {account_name} {symbol} 价格失败: {e}")
            return None
    
    def calculate_position_size(self, account_name: str, symbol: str, price: float) -> float:
        """
        计算仓位大小
        根据账户配置使用风险百分比或固定保证金
        """
        if account_name not in self.accounts:
            return 0.0
        
        # 🔧 价格验证
        if price <= 0:
            logger.error(f"{account_name} - 价格无效: {price}")
            return 0.0
        
        account = self.accounts[account_name]
        
        if account.use_margin_amount:
            # 使用固定保证金金额：名义金额 = 保证金 × 杠杆
            position_size = (account.margin_amount * account.default_leverage) / price
        else:
            balance = self.get_balance(account_name, 'USDT')
            if not balance:
                return 0.0
            risk_amount = balance * (account.risk_percentage / 100)
            if getattr(account, 'risk_as_notional', False):
                # 风险额度按名义金额（直接作为成本），则数量 = 名义金额 / 价格
                position_size = risk_amount / price
            else:
                # 默认：风险额度视为保证金，名义金额 = 风险 × 杠杆
                position_size = (risk_amount * account.default_leverage) / price
        
        # 限制最大仓位
        position_size = min(position_size, account.max_position_size)
        
        return round(position_size, 6)
    
    def place_market_order(self, account_name: str, symbol: str, side: str, 
                          amount: float = None, stop_loss_price: float = None) -> Optional[Dict[str, Any]]:
        """
        下市价单
        如果 amount 为 None，自动计算仓位大小
        如果 stop_loss_price 不为 None，将在订单中附带止损价格（Bitget 专用）
        """
        if account_name not in self.clients:
            logger.error(f"账户 {account_name} 不存在")
            return None
        
        client = self.clients[account_name]
        account = self.accounts[account_name]
        exchange_type = account.exchange_type.lower()
        
        try:
            # 转换为合约符号格式
            contract_symbol = self._convert_to_contract_symbol(client, symbol)
            
            # 获取当前价格
            current_price = self.get_current_price(account_name, symbol)
            if not current_price or current_price <= 0:
                logger.error(f"{account_name} - 无法获取有效价格")
                return None
            
            # 🔧 关键修复：Bitget合约必须先设置杠杆！
            if exchange_type == 'bitget':
                try:
                    # 设置杠杆（Bitget合约必需）
                    retry_call(
                        client.set_leverage,
                        account.default_leverage,
                        contract_symbol,
                        retries=2,
                        delay=0.5,
                        logger=logger,
                        op=f"{account_name}.set_leverage",
                        params={
                            'marginCoin': 'USDT',
                            'productType': 'USDT-FUTURES'
                        }
                    )
                    logger.debug(f"{account_name} - 已设置杠杆 {account.default_leverage}x")
                except Exception as e:
                    # 如果杠杆已设置，会报错但不影响下单
                    logger.debug(f"{account_name} - 设置杠杆: {e}")
                # 🔧 同步设置为单向持仓（oneway），避免 40774
                try:
                    # False 表示单向持仓，True 表示双向/对冲
                    retry_call(
                        client.set_position_mode,
                        False,
                        retries=2,
                        delay=0.5,
                        logger=logger,
                        op=f"{account_name}.set_position_mode",
                        params={'productType': 'USDT-FUTURES', 'marginCoin': 'USDT'}
                    )
                except Exception as e:
                    logger.debug(f"{account_name} - 设置单向持仓: {e}")
            
            # 如果没有指定数量，自动计算
            if amount is None:
                amount = self.calculate_position_size(account_name, symbol, current_price)
            
            if amount <= 0:
                logger.error(f"{account_name} - 仓位大小计算错误")
                return None
            
            # 获取市场信息，检查最小交易数量和金额
            try:
                market = client.market(contract_symbol)
                min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
                min_cost = market.get('limits', {}).get('cost', {}).get('min', 0)
            except Exception as e:
                logger.error(f"{account_name} - 获取市场信息失败: {e}")
                return None
            
            # 1️⃣ 调整数量以满足最小交易数量要求
            if min_amount and amount < min_amount:
                logger.warning(f"{account_name} - 数量 {amount} 小于最小值 {min_amount}，调整为最小值")
                amount = min_amount
            
            # 2️⃣ 检查订单总价值是否满足最小要求（关键！）
            order_value = amount * current_price
            if min_cost and order_value < min_cost:
                # 根据最小金额重新计算数量
                required_amount = min_cost / current_price
                logger.warning(f"{account_name} - 订单金额 {order_value:.2f} USDT 小于最小值 {min_cost:.2f} USDT，调整数量从 {amount:.2f} 到 {required_amount:.2f}")
                amount = required_amount

            # 2.5️⃣ 基于可用保证金的‘最大可开仓成本’上限，防止交易所返回余额不足
            try:
                available_usdt = self.get_balance(account_name, 'USDT') or 0.0
            except Exception:
                available_usdt = 0.0
            if available_usdt is None:
                available_usdt = 0.0

            # 最大允许成本 = 可用保证金 * 杠杆 * 安全缓冲
            safety_buffer = 0.98  # 留出手续费/滑点余量
            max_cost_allowed = available_usdt * account.default_leverage * safety_buffer

            # 如果交易所有最小成本要求，且最大允许成本低于最小成本，则直接提示余额不足，避免无谓请求
            if min_cost and max_cost_allowed > 0 and max_cost_allowed < min_cost:
                logger.error(
                    f"{account_name} - 可用保证金不足: 可开最大成本 {max_cost_allowed:.2f} USDT < 交易所最小成本 {min_cost:.2f} USDT"
                )
                return None

            # 若当前订单成本超过账户可承受上限，则下调数量以适配上限
            planned_cost = amount * current_price
            if max_cost_allowed > 0 and planned_cost > max_cost_allowed:
                adjusted_amount = max_cost_allowed / current_price
                logger.warning(
                    f"{account_name} - 成本 {planned_cost:.2f} USDT 超过可承受上限 {max_cost_allowed:.2f} USDT，数量调整为 {adjusted_amount:.6f}"
                )
                amount = adjusted_amount
            
            # 对数量进行精度处理
            if 'precision' in market and 'amount' in market['precision']:
                precision = market['precision']['amount']
                if precision is not None:
                    import decimal
                    # precision 可能是整数（小数位数）或浮点数（步长）
                    if isinstance(precision, int):
                        # 整数：表示小数位数
                        amount = round(amount, precision)
                    else:
                        # 浮点数：表示步长，需要按步长取整
                        # ⚠️ 使用ROUND_UP确保不会低于最小金额要求
                        amount = float(decimal.Decimal(str(amount)).quantize(
                            decimal.Decimal(str(precision)),
                            rounding=decimal.ROUND_UP  # 改为向上取整
                        ))
            
            # 3️⃣ 精度处理后再次检查最小金额（防止向下取整导致不足）
            final_order_value = amount * current_price
            if min_cost and final_order_value < min_cost:
                # 需要再次调整
                import decimal
                import math
                precision_value = market.get('precision', {}).get('amount', None)
                if precision_value and not isinstance(precision_value, int) and precision_value > 0:
                    # 步长精度：计算满足最小金额的最小步数
                    min_steps = math.ceil(min_cost / current_price / precision_value)
                    amount = min_steps * precision_value
                else:
                    # 小数位精度：直接计算并向上取整
                    amount = min_cost / current_price
                    if precision_value and isinstance(precision_value, int):
                        amount = round(amount + 0.5 * (10 ** -precision_value), precision_value)
                logger.warning(f"{account_name} - 精度处理后金额不足，再次调整数量到 {amount:.6f}")
            
            # Bitget 合约特殊处理
            if exchange_type == 'bitget':
                # Bitget合约需要特定参数
                params = {
                    'marginCoin': 'USDT',
                    'productType': 'USDT-FUTURES'
                }
                
                # 🔧 优先在双向模式参数下尝试下单
                try:
                    notional = amount * current_price
                    if side == 'buy':
                        # 做多（买入开仓）
                        params['createMarketBuyOrderRequiresPrice'] = False
                        params['holdSide'] = 'long'
                    else:
                        # 做空（卖出开仓）
                        params['holdSide'] = 'short'

                    # 对于 Bitget 合约，CCXT 接口第三个参数为数量（币的数量），而非 USDT 成本
                    logger.info(f"{account_name} - 准备下单: 符号: {contract_symbol}, side: {side}, 数量: {amount:.6f}, 名义: {notional:.2f} USDT, 参数: {params}")
                    order = retry_call(
                        client.create_market_order,
                        contract_symbol,
                        side,
                        amount,
                        retries=2,
                        delay=0.5,
                        logger=logger,
                        op=f"{account_name}.create_market_order",
                        params=params,
                    )
                    logger.info(f"{account_name} - 订单已下: {('做多' if side=='buy' else '做空')} {contract_symbol}, 数量: {amount:.6f}, 名义: {notional:.2f} USDT, 杠杆: {account.default_leverage}x")
                    try:
                        log_struct(logger, logging.INFO, "order_placed", account=account_name, symbol=contract_symbol, side=side, type="market", amount=amount, price=current_price, order_id=(order.get('id') if isinstance(order, dict) else None))
                    except Exception:
                        pass

                    # 统一返回结构，便于上层判断
                    return {
                        'status': 'success',
                        'order_id': order.get('id') if isinstance(order, dict) else None,
                        'amount': amount,
                        'price': current_price,
                        'order': order
                    }
                    
                except Exception as e:
                    error_str = str(e)
                    # 🔧 如果是持仓模式错误（40774），尝试单向持仓模式
                    if '40774' in error_str:
                        logger.warning(f"{account_name} - 检测到单向持仓模式，重试...")
                        
                        # 移除 holdSide 参数
                        if 'holdSide' in params:
                            del params['holdSide']
                        # 明确声明单向持仓
                        params['positionMode'] = 'oneway'
                        
                        if side == 'buy':
                            params['createMarketBuyOrderRequiresPrice'] = False
                            cost = amount * current_price
                            order = retry_call(
                                client.create_market_order,
                                contract_symbol,
                                side,
                                cost,
                                retries=2,
                                delay=0.5,
                                logger=logger,
                                op=f"{account_name}.create_market_order",
                                params=params,
                            )
                            logger.info(f"{account_name} - 订单已下（单向模式）: 做多 {contract_symbol}, 成本: {cost:.2f} USDT")
                        else:
                            # 🔧 BUG 15 修复：单向模式的做空订单也要传入成本！
                            cost = amount * current_price
                            order = retry_call(
                                client.create_market_order,
                                contract_symbol,
                                side,
                                cost,
                                retries=2,
                                delay=0.5,
                                logger=logger,
                                op=f"{account_name}.create_market_order",
                                params=params,
                            )
                            logger.info(f"{account_name} - 订单已下（单向模式）: 做空 {contract_symbol}, 成本: {cost:.2f} USDT")
                        # 统一返回结构，便于上层判断
                        return {
                            'status': 'success',
                            'order_id': order.get('id') if isinstance(order, dict) else None,
                            'amount': amount,
                            'price': current_price,
                            'order': order
                        }
                    elif '43012' in error_str:
                        # 🔁 余额不足/风控：递减重试，逐步降低数量
                        available_usdt = self.get_balance(account_name, 'USDT') or 0.0
                        required_margin = (amount * current_price) / max(account.default_leverage, 1)
                        logger.error(
                            f"{account_name} - 余额不足(43012): 目标名义 {(amount*current_price):.2f} USDT, 所需保证金约 {required_margin:.2f} USDT, 可用 {available_usdt:.2f} USDT"
                        )
                        retries = 3
                        success = None
                        try_amount = amount
                        for i in range(retries):
                            try_amount *= 0.7  # 逐步降低数量
                            if min_amount and try_amount < min_amount:
                                logger.error(f"{account_name} - 降低后数量 {try_amount:.6f} 低于最小数量 {min_amount}，放弃重试")
                                break
                            logger.info(f"{account_name} - 第 {i+1} 次降额重试: 数量 {try_amount:.6f}, 名义 {(try_amount*current_price):.2f} USDT")
                            try:
                                success = retry_call(
                                    client.create_market_order,
                                    contract_symbol,
                                    side,
                                    try_amount,
                                    retries=1,
                                    delay=0.5,
                                    logger=logger,
                                    op=f"{account_name}.create_market_order",
                                    params=params,
                                )
                                amount = try_amount
                                break
                            except Exception as e2:
                                logger.warning(f"{account_name} - 降额重试失败: {e2}")
                                continue
                        if success:
                            return {
                                'status': 'success',
                                'order_id': success.get('id') if isinstance(success, dict) else None,
                                'amount': amount,
                                'price': current_price,
                                'order': success
                            }
                        return None
                    else:
                        # 其他错误，直接抛出
                        raise
            else:
                # 其他交易所：正常下单
                order = retry_call(
                    client.create_market_order,
                    contract_symbol,
                    side,
                    amount,
                    retries=2,
                    delay=0.5,
                    logger=logger,
                    op=f"{account_name}.create_market_order",
                )
                logger.info(f"{account_name} - 订单已下: {side} {amount} {contract_symbol}")
                try:
                    log_struct(logger, logging.INFO, "order_placed", account=account_name, symbol=contract_symbol, side=side, type="market", amount=amount, price=current_price, order_id=(order.get('id') if isinstance(order, dict) else None))
                except Exception:
                    pass

            # 统一返回
            return {
                'status': 'success',
                'order_id': order.get('id') if isinstance(order, dict) else None,
                'amount': amount,
                'price': current_price,
                'order': order
            }
            
        except Exception as e:
            logger.error(f"{account_name} - 下单失败: {e}")
            return None
    
    def place_limit_order(self, account_name: str, symbol: str, side: str, 
                         price: float, amount: float = None) -> Optional[Dict[str, Any]]:
        """下限价单"""
        if account_name not in self.clients:
            return None
        
        client = self.clients[account_name]
        account = self.accounts[account_name]
        exchange_type = account.exchange_type.lower()
        
        try:
            # 🔧 转换为合约符号
            contract_symbol = self._convert_to_contract_symbol(client, symbol)
            
            # 如果没有指定数量，自动计算
            if amount is None:
                amount = self.calculate_position_size(account_name, symbol, price)
            
            if amount <= 0:
                logger.error(f"{account_name} - 仓位大小计算错误")
                return None
            
            # 获取市场信息，检查最小值
            try:
                market = client.market(contract_symbol)
                min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
                min_cost = market.get('limits', {}).get('cost', {}).get('min', 0)
            except Exception as e:
                logger.error(f"{account_name} - 获取市场信息失败: {e}")
                return None
            
            # 检查并调整最小数量
            if min_amount and amount < min_amount:
                logger.warning(f"{account_name} - 数量 {amount} 小于最小值 {min_amount}，调整为最小值")
                amount = min_amount
            
            # 检查并调整最小金额
            order_value = amount * price
            if min_cost and order_value < min_cost:
                required_amount = min_cost / price
                logger.warning(f"{account_name} - 订单金额 {order_value:.2f} USDT 小于最小值 {min_cost:.2f} USDT，调整数量从 {amount:.2f} 到 {required_amount:.2f}")
                amount = required_amount
            
            # 精度处理
            if 'precision' in market and 'amount' in market['precision']:
                precision = market['precision']['amount']
                if precision is not None:
                    import decimal
                    if isinstance(precision, int):
                        amount = round(amount, precision)
                    else:
                        # 使用ROUND_UP确保不会低于最小金额要求
                        amount = float(decimal.Decimal(str(amount)).quantize(
                            decimal.Decimal(str(precision)),
                            rounding=decimal.ROUND_UP
                        ))
            
            # 精度处理后再次检查最小金额
            final_order_value = amount * price
            if min_cost and final_order_value < min_cost:
                import decimal
                import math
                precision_value = market.get('precision', {}).get('amount', None)
                if precision_value and not isinstance(precision_value, int) and precision_value > 0:
                    min_steps = math.ceil(min_cost / price / precision_value)
                    amount = min_steps * precision_value
                else:
                    amount = min_cost / price
                    if precision_value and isinstance(precision_value, int):
                        amount = round(amount + 0.5 * (10 ** -precision_value), precision_value)
                logger.warning(f"{account_name} - 精度处理后金额不足，再次调整数量到 {amount:.6f}")
            
            # 🔧 Bitget特定参数
            params = {}
            if exchange_type == 'bitget':
                params = {
                    'marginCoin': 'USDT',
                    'productType': 'USDT-FUTURES'
                }
            
            order = retry_call(
                client.create_limit_order,
                contract_symbol,
                side,
                amount,
                price,
                retries=2,
                delay=0.5,
                logger=logger,
                op=f"{account_name}.create_limit_order",
                params=params,
            )
            logger.info(f"{account_name} - 限价单已下: {side} {amount} {contract_symbol} @ {price}")
            try:
                log_struct(logger, logging.INFO, "order_placed", account=account_name, symbol=contract_symbol, side=side, type="limit", amount=amount, price=price, order_id=(order.get('id') if isinstance(order, dict) else None))
            except Exception:
                pass
            return order
            
        except Exception as e:
            logger.error(f"{account_name} - 下限价单失败: {e}")
            return None
    
    def set_leverage(self, account_name: str, symbol: str, leverage: int = None) -> bool:
        """设置杠杆倍数"""
        if account_name not in self.clients:
            return False
        
        client = self.clients[account_name]
        account = self.accounts[account_name]
        exchange_type = account.exchange_type.lower()
        
        # 如果没有指定杠杆，使用账户默认值
        if leverage is None:
            leverage = account.default_leverage
        
        try:
            # 🔧 转换为合约符号
            contract_symbol = self._convert_to_contract_symbol(client, symbol)
            
            # 🔧 Bitget需要特定参数
            if exchange_type == 'bitget':
                params = {
                    'marginCoin': 'USDT',
                    'productType': 'USDT-FUTURES'
                }
                client.set_leverage(leverage, contract_symbol, params=params)
            else:
                client.set_leverage(leverage, contract_symbol)
            
            logger.info(f"{account_name} - 已设置 {symbol} 杠杆为 {leverage}x")
            return True
        except Exception as e:
            logger.debug(f"{account_name} - 设置杠杆: {e}")  # 降为debug，因为可能已设置
            return True  # 继续执行，杠杆可能已设置
    
    def close_position(self, account_name: str, symbol: str) -> bool:
        """平仓"""
        if account_name not in self.clients:
            return False
        
        client = self.clients[account_name]
        account = self.accounts.get(account_name)
        exchange_type = (account.exchange_type.lower() if account else '').strip()
        
        try:
            # 🔧 转换为合约符号格式
            contract_symbol = self._convert_to_contract_symbol(client, symbol)
            
            # Bitget 需要带上 productType/marginCoin
            fetch_params = {}
            if exchange_type == 'bitget':
                fetch_params = {'productType': 'USDT-FUTURES', 'marginCoin': 'USDT'}
            positions = retry_call(
                client.fetch_positions,
                [contract_symbol],
                retries=3,
                delay=0.6,
                logger=logger,
                op=f"{account_name}.fetch_positions",
                params=fetch_params,
            )
            for position in positions:
                if float(position['contracts']) > 0:
                    side = 'sell' if position['side'] == 'long' else 'buy'
                    amount = abs(float(position['contracts']))
                    # 平仓下单同样补齐 Bitget 参数
                    if exchange_type == 'bitget':
                        try:
                            retry_call(
                                client.set_position_mode,
                                False,
                                retries=2,
                                delay=0.5,
                                logger=logger,
                                op=f"{account_name}.set_position_mode",
                                params={'productType': 'USDT-FUTURES', 'marginCoin': 'USDT'}
                            )
                        except Exception:
                            pass
                    self.place_market_order(account_name, symbol, side, amount)
                    logger.info(f"{account_name} - 已平仓 {symbol}")
                    try:
                        log_struct(logger, logging.INFO, "position_closed", account=account_name, symbol=contract_symbol, side=side, amount=amount)
                    except Exception:
                        pass
                    return True
            
            logger.info(f"{account_name} - 没有 {symbol} 的持仓")
            return False
            
        except Exception as e:
            logger.error(f"{account_name} - 平仓失败: {e}")
            return False

    def get_position(self, account_name: str, symbol: str) -> Optional[Dict[str, Any]]:
        """获取当前持仓信息（数量与方向）"""
        if account_name not in self.clients:
            return None
        client = self.clients[account_name]
        account = self.accounts.get(account_name)
        exchange_type = (account.exchange_type.lower() if account else '').strip()
        try:
            contract_symbol = self._convert_to_contract_symbol(client, symbol)
            params = {'productType': 'USDT-FUTURES', 'marginCoin': 'USDT'} if exchange_type == 'bitget' else {}
            positions = client.fetch_positions([contract_symbol], params=params)
            for p in positions:
                contracts = abs(float(p.get('contracts') or 0))
                if contracts > 0:
                    # 兼容不同交易所字段名，尽力取入场均价
                    entry_price = None
                    for k in ['entryPrice', 'entry_price', 'avgEntryPrice', 'avgPrice']:
                        try:
                            v = p.get(k)
                            if v is not None:
                                entry_price = float(v)
                                break
                        except Exception:
                            continue
                    return {
                        'contracts': contracts,
                        'side': p.get('side'),  # 'long' or 'short'
                        'entry_price': entry_price
                    }
            return None
        except Exception as e:
            logger.error(f"{account_name} - 获取持仓失败: {e}")
            return None

    def list_open_positions(self, account_name: str) -> List[Dict[str, Any]]:
        """列出账户当前所有持仓（仅返回有仓位的合约）"""
        if account_name not in self.clients:
            return []
        client = self.clients[account_name]
        account = self.accounts.get(account_name)
        exchange_type = (account.exchange_type.lower() if account else '').strip()
        try:
            params = {'productType': 'USDT-FUTURES', 'marginCoin': 'USDT'} if exchange_type == 'bitget' else {}
            positions = retry_call(
                client.fetch_positions,
                retries=3,
                delay=0.6,
                logger=logger,
                op=f"{account_name}.fetch_positions",
                params=params,
            )
            results: List[Dict[str, Any]] = []
            for p in positions:
                try:
                    contracts = abs(float(p.get('contracts') or 0))
                    if contracts > 0:
                        results.append({
                            'symbol': p.get('symbol'),
                            'contracts': contracts,
                            'side': p.get('side'),
                        })
                except Exception:
                    continue
            return results
        except Exception as e:
            logger.error(f"{account_name} - 列出持仓失败: {e}")
            return []
    
    def fetch_order_status(self, account_name: str, symbol: str, order_id: str) -> Optional[Dict[str, Any]]:
        """查询订单状态，返回统一结构：{'status': 'open|closed|canceled', 'filled': float, 'remaining': float} """
        if account_name not in self.clients:
            return None
        client = self.clients[account_name]
        try:
            contract_symbol = self._convert_to_contract_symbol(client, symbol)
            order = retry_call(
                client.fetch_order,
                order_id,
                contract_symbol,
                retries=3,
                delay=0.6,
                logger=logger,
                op=f"{account_name}.fetch_order",
            )
            status = (order.get('status') or '').lower()
            filled = float(order.get('filled') or 0)
            remaining = float(order.get('remaining') or 0)
            try:
                log_struct(logger, logging.INFO, "order_status", account=account_name, symbol=contract_symbol, order_id=order_id, status=status, filled=filled, remaining=remaining)
            except Exception:
                pass
            return {
                'status': status,
                'filled': filled,
                'remaining': remaining,
                'info': order
            }
        except Exception as e:
            logger.debug(f"{account_name} - 查询订单状态失败: {e}")
            return None

    def cancel_open_reduce_only_orders(self, account_name: str, symbol: str) -> int:
        """取消该交易对的所有未成交 reduce-only 限价单（用于切换到价格型TP策略时清理回退挂单）。
        返回取消数量。
        """
        if account_name not in self.clients:
            return 0
        client = self.clients[account_name]
        account = self.accounts.get(account_name)
        exchange_type = (account.exchange_type.lower() if account else '').strip()
        cancelled = 0
        try:
            contract_symbol = self._convert_to_contract_symbol(client, symbol)
            params = {'productType': 'USDT-FUTURES', 'marginCoin': 'USDT'} if exchange_type == 'bitget' else {}
            open_orders = retry_call(
                client.fetch_open_orders,
                contract_symbol,
                retries=3,
                delay=0.6,
                logger=logger,
                op=f"{account_name}.fetch_open_orders",
                params=params,
            )
            for o in open_orders or []:
                try:
                    info = o.get('info') or {}
                    reduce_only = o.get('reduceOnly')
                    if reduce_only is None:
                        # 尝试从原始字段判断
                        reduce_only = bool(info.get('reduceOnly')) if isinstance(info.get('reduceOnly'), (bool, str)) else False
                    if reduce_only:
                        retry_call(
                            client.cancel_order,
                            o.get('id'),
                            contract_symbol,
                            retries=2,
                            delay=0.5,
                            logger=logger,
                            op=f"{account_name}.cancel_order",
                            params=params,
                        )
                        cancelled += 1
                        try:
                            log_struct(logger, logging.INFO, "order_cancelled", account=account_name, symbol=contract_symbol, order_id=o.get('id'), reason="reduce_only_cleanup")
                        except Exception:
                            pass
                except Exception as ie:
                    logger.debug(f"{account_name} 取消订单失败: {ie}")
                    continue
        except Exception as e:
            logger.debug(f"{account_name} 获取/取消 open orders 失败: {e}")
        return cancelled

    def execute_on_all(self, symbol: str, side: str, entry_price: Optional[float] = None,
                      leverage: Optional[int] = None) -> Dict[str, Any]:
        """
        在所有启用的账户上执行交易
        
        Returns:
            Dict: {account_name: order_result}
        """
        results = {}
        
        for account_name in self.clients.keys():
            account = self.accounts[account_name]
            
            # 设置杠杆
            if leverage:
                self.set_leverage(account_name, symbol, leverage)
            else:
                self.set_leverage(account_name, symbol)  # 使用默认杠杆
            
            # 下单
            if entry_price:
                order = self.place_limit_order(account_name, symbol, side, entry_price)
            else:
                order = self.place_market_order(account_name, symbol, side)
            
            results[account_name] = order
        
        return results
    
    def get_account_info(self, account_name: str) -> Dict[str, Any]:
        """获取账户详细信息"""
        if account_name not in self.accounts:
            return {}
        
        account = self.accounts[account_name]
        balance = self.get_balance(account_name)
        
        return {
            'name': account.name,
            'exchange_type': account.exchange_type,
            'testnet': account.testnet,
            'enabled': account.enabled,
            'balance': balance,
            'default_leverage': account.default_leverage,
            'risk_percentage': account.risk_percentage,
            'use_margin_amount': account.use_margin_amount,
            'margin_amount': account.margin_amount,
        }
    
    def get_all_accounts_info(self) -> List[Dict[str, Any]]:
        """获取所有账户信息"""
        return [
            self.get_account_info(account_name) 
            for account_name in self.clients.keys()
        ]
    
    def place_stop_loss_order(self, account_name: str, symbol: str, side: str, 
                              amount: float, stop_price: float) -> Optional[Dict]:
        """
        设置止损订单
        
        Args:
            account_name: 账户名称
            symbol: 交易对 (如 'BTC/USDT')
            side: 'buy' 或 'sell'
            amount: 数量
            stop_price: 止损价格
            
        Returns:
            订单信息字典，失败返回None
        """
        if account_name not in self.clients:
            logger.error(f"账户 {account_name} 不存在")
            return None
        
        try:
            client = self.clients[account_name]
            account = self.accounts[account_name]
            exchange_type = account.exchange_type.lower()
            
            # 转换为合约符号
            contract_symbol = self._convert_to_contract_symbol(client, symbol)
            
            # 获取市场精度，用于对止损价与数量做取整，避免因精度导致计划单被取消
            market = None
            try:
                market = client.market(contract_symbol)
            except Exception:
                market = None
            
            # Bitget: 在下触发单前确保为单向持仓，避免模式报错
            if exchange_type == 'bitget':
                try:
                    pass
                except Exception:
                    pass

            # 对价格做精度取整
            try:
                if market:
                    price_precision = market.get('precision', {}).get('price')
                    if price_precision is not None:
                        import decimal
                        if isinstance(price_precision, int):
                            stop_price = round(float(stop_price), price_precision)
                        else:
                            stop_price = float(decimal.Decimal(str(stop_price)).quantize(
                                decimal.Decimal(str(price_precision)),
                                rounding=decimal.ROUND_HALF_UP
                            ))
            except Exception:
                pass

            # Bitget 专用：使用 v2 TPSL 接口下止损计划单，避免 43011
            if exchange_type == 'bitget':
                try:
                    # 组装请求体（按 v2 /mix/order/place-tpsl-order）
                    # 使用交易所内部 symbol id，如 BTCUSDT 而非 BTC/USDT:USDT
                    market_id = None
                    try:
                        if market:
                            market_id = market.get('id')
                    except Exception:
                        market_id = None
                    if not market_id:
                        # 简单回退：从合约符号粗略转换
                        market_id = contract_symbol.replace('/USDT:USDT', 'USDT').replace('/', '')

                    # 对数量做精度处理（Bitget TPSL API 要求 size 符合市场精度）
                    try:
                        if market:
                            amount_precision = market.get('precision', {}).get('amount')
                            if amount_precision is not None:
                                import decimal
                                if isinstance(amount_precision, int):
                                    # 整数：表示小数位数，直接 round
                                    amount = round(float(amount), amount_precision)
                                else:
                                    # 浮点数：表示步长，需要按步长取整
                                    amount = float(decimal.Decimal(str(amount)).quantize(
                                        decimal.Decimal(str(amount_precision)),
                                        rounding=decimal.ROUND_DOWN  # 向下取整，避免超过持仓数量
                                    ))
                    except Exception as prec_err:
                        logger.debug(f"{account_name} TPSL 数量精度处理失败: {prec_err}")
                    
                    import time
                    # 进一步通过 ccxt 的 amount_to_precision 计算 size 字符串，并规范去掉无意义小数
                    size_str = None
                    try:
                        if hasattr(client, 'amount_to_precision'):
                            ap = client.amount_to_precision(contract_symbol, amount)
                            size_str = str(ap)
                            if '.' in size_str:
                                size_str = size_str.rstrip('0').rstrip('.')
                    except Exception:
                        size_str = None
                    if not size_str:
                        # 回退：按整数向下取整（避免 40808 checkBDScale）
                        try:
                            size_str = str(int(float(amount)))
                        except Exception:
                            size_str = str(amount)
                    # Bitget TPSL 参数策略：先尝试不带 holdSide（实践证明更稳定）
                    # 如果失败，fallback 会尝试添加 holdSide
                    
                    hold_side = None
                    try:
                        hold_side = 'short' if side == 'buy' else 'long'
                    except Exception:
                        hold_side = None
                    
                    body = {
                        'marginCoin': 'USDT',
                        'productType': 'usdt-futures',
                        'symbol': market_id,
                        'planType': 'loss_plan',
                        'triggerPrice': str(stop_price),
                        'triggerType': 'mark_price',
                        'executePrice': '0',  # 市价执行
                        # 'holdSide': 移除，让 fallback 机制处理
                        'size': size_str,
                        'clientOid': f"sl_{int(time.time()*1000)}"
                    }
                    if hold_side:
                        body['holdSide'] = hold_side

                    # 优先尝试 ccxt 暴露的方法名（不同版本命名可能不同）
                    method_candidates = [
                        'v2PrivateMixPostOrderPlaceTpslOrder',
                        'privateMixPostOrderPlaceTpslOrder',
                        'v2PrivateMixOrderPostPlaceTpslOrder',
                    ]
                    response = None
                    last_err = None
                    for m in method_candidates:
                        fn = getattr(client, m, None)
                        if callable(fn):
                            try:
                                response = fn(body)
                                logger.debug(f"{account_name} TPSL 通过方法 {m} 成功")
                                break
                            except Exception as me:
                                last_err = me
                                logger.debug(f"{account_name} TPSL 方法 {m} 失败: {me}")
                                continue
                    if response is None:
                        # 尝试使用 ccxt 的 private_post 方法
                        try:
                            logger.debug(f"{account_name} 尝试 private_post TPSL: {body}")
                            # 尝试不同的 private_post 方法名格式
                            private_post_methods = [
                                'private_post_mix_v2_order_place_tpsl_order',
                                'privatePostMixV2OrderPlaceTpslOrder',
                                'private_post_v2_mix_order_place_tpsl_order',
                            ]
                            for method_name in private_post_methods:
                                method = getattr(client, method_name, None)
                                if callable(method):
                                    try:
                                        response = method(body)
                                        logger.debug(f"{account_name} TPSL 通过 {method_name} 成功: {response}")
                                        break
                                    except Exception as me:
                                        logger.debug(f"{account_name} TPSL 方法 {method_name} 失败: {me}")
                                        continue
                        except Exception as pe:
                            logger.debug(f"{account_name} private_post 方法尝试失败: {pe}")
                        
                        # 如果 private_post 也失败，使用直接 HTTP 请求
                        if response is None:
                            try:
                                import requests
                                import json
                                import hmac
                                import hashlib
                                import base64
                                from time import time
                                
                                timestamp = str(int(time() * 1000))
                                method = 'POST'
                                request_path = '/api/v2/mix/order/place-tpsl-order'
                                
                                # 构建请求体
                                body_str = json.dumps(body, separators=(',', ':'))
                                
                                # 构建签名字符串
                                message = timestamp + method + request_path + body_str
                                signature = base64.b64encode(
                                    hmac.new(
                                        client.secret.encode('utf-8'),
                                        message.encode('utf-8'),
                                        hashlib.sha256
                                    ).digest()
                                ).decode('utf-8')
                                
                                # 构建请求头
                                headers = {
                                    'ACCESS-KEY': client.apiKey,
                                    'ACCESS-SIGN': signature,
                                    'ACCESS-TIMESTAMP': timestamp,
                                    'ACCESS-PASSPHRASE': client.password,
                                    'Content-Type': 'application/json',
                                    'locale': 'en-US'
                                }
                                
                                # 直接使用 Bitget API base URL
                                api_base = 'https://api.bitget.com'
                                url = api_base + request_path
                                
                                logger.debug(f"{account_name} 直接 HTTP TPSL 请求: {url}, body: {body_str}")
                                resp = requests.post(url, headers=headers, data=body_str, timeout=10)
                                
                                # 记录响应内容以便诊断
                                try:
                                    resp_text = resp.text
                                    logger.debug(f"{account_name} TPSL HTTP 响应状态: {resp.status_code}, 响应内容: {resp_text}")
                                except:
                                    pass
                                
                                resp.raise_for_status()
                                response = resp.json()
                                logger.debug(f"{account_name} 直接 HTTP TPSL 响应: {response}")
                            except requests.exceptions.HTTPError as http_err:
                                # 记录详细的错误响应
                                error_detail = ""
                                error_status = None
                                try:
                                    if hasattr(http_err, 'response') and http_err.response is not None:
                                        error_status = http_err.response.status_code
                                        if hasattr(http_err.response, 'text'):
                                            error_detail = http_err.response.text
                                            logger.error(f"{account_name} TPSL HTTP 错误响应 ({error_status}): {error_detail}")
                                        if hasattr(http_err.response, 'json'):
                                            try:
                                                error_json = http_err.response.json()
                                                logger.error(f"{account_name} TPSL HTTP 错误 JSON: {error_json}")
                                            except:
                                                pass
                                except:
                                    pass
                                
                                logger.error(f"{account_name} 直接 HTTP TPSL 失败: {http_err}")
                                
                                # 如果返回 400 错误，可能是参数问题，优先处理 size 精度（40808），再尝试移除 executePrice/补充 holdSide
                                if error_status == 400:
                                    # Step A: 修正 size 精度（处理 40808 checkBDScale）
                                    try:
                                        need_fix = False
                                        ed = error_detail or ""
                                        if ("checkBDScale" in ed) or ("checkScale=" in ed) or ("\"code\":\"40808\"" in ed):
                                            need_fix = True
                                        if need_fix:
                                            body_size = body.copy()
                                            try:
                                                size_float = float(body_size.get('size', '0'))
                                                body_size['size'] = str(int(size_float))
                                            except Exception:
                                                pass
                                            body_str = json.dumps(body_size, separators=(',', ':'))
                                            message = timestamp + method + request_path + body_str
                                            signature = base64.b64encode(hmac.new(client.secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
                                            headers['ACCESS-SIGN'] = signature
                                            resp2 = requests.post(url, headers=headers, data=body_str, timeout=10)
                                            resp2.raise_for_status()
                                            response = resp2.json()
                                            logger.debug(f"{account_name} TPSL 调整 size 后成功: {response}")
                                    except Exception as fe1:
                                        logger.error(f"{account_name} TPSL 调整 size 后仍失败: {fe1}")

                                    if response is None:
                                        body_no_exec = body.copy()
                                        body_no_exec.pop('executePrice', None)
                                        try:
                                            body_str = json.dumps(body_no_exec, separators=(',', ':'))
                                            message = timestamp + method + request_path + body_str
                                            signature = base64.b64encode(hmac.new(client.secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
                                            headers['ACCESS-SIGN'] = signature
                                            resp2 = requests.post(url, headers=headers, data=body_str, timeout=10)
                                            resp2.raise_for_status()
                                            response = resp2.json()
                                        except Exception:
                                            pass

                                    if response is None and (
                                        ("holdSide" in (error_detail or "")) or
                                        ("\"code\":\"43011\"" in (error_detail or "")) or
                                        ("position direction cannot be empty" in (error_detail or "")) or
                                        ("\"code\":\"400172\"" in (error_detail or ""))
                                    ):
                                        # 如果因为 holdSide/持仓方向相关失败，尝试添加正确的 holdSide
                                        try:
                                            # 计算持仓方向
                                            hold_side = 'short' if side == 'buy' else 'long'
                                            body_with_hold = body.copy()
                                            body_with_hold['holdSide'] = hold_side
                                            body_str = json.dumps(body_with_hold, separators=(',', ':'))
                                            message = timestamp + method + request_path + body_str
                                            signature = base64.b64encode(hmac.new(client.secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
                                            headers['ACCESS-SIGN'] = signature
                                            resp2 = requests.post(url, headers=headers, data=body_str, timeout=10)
                                            resp2.raise_for_status()
                                            response = resp2.json()
                                        except Exception:
                                            pass
                                        if response is None:
                                            # 再尝试 holdSide='net'
                                            try:
                                                body_net = body.copy()
                                                body_net['holdSide'] = 'net'
                                                body_str = json.dumps(body_net, separators=(',', ':'))
                                                message = timestamp + method + request_path + body_str
                                                signature = base64.b64encode(hmac.new(client.secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()).decode('utf-8')
                                                headers['ACCESS-SIGN'] = signature
                                                resp2 = requests.post(url, headers=headers, data=body_str, timeout=10)
                                                resp2.raise_for_status()
                                                response = resp2.json()
                                            except Exception:
                                                pass
                                    else:
                                        raise http_err
                            except Exception as http_err:
                                logger.error(f"{account_name} 直接 HTTP TPSL 失败: {http_err}")
                                raise http_err

                    # 正常返回
                    oid = None
                    try:
                        if isinstance(response, dict):
                            oid = response.get('data', {}).get('orderId') or response.get('orderId') or response.get('id')
                    except Exception:
                        oid = None
                    return {
                        'status': 'success',
                        'order_id': oid,
                        'price': stop_price,
                        'amount': amount,
                        'order': response
                    }
                except Exception as be:
                    import traceback
                    logger.error(f"{account_name} Bitget TPSL 下单失败: {type(be).__name__}: {be}")
                    logger.error(f"{account_name} TPSL 异常详情:\n{traceback.format_exc()}")
                    try:
                        hold_side_val = body.get('holdSide', '未设置')
                        logger.error(f"{account_name} TPSL 请求参数: symbol={market_id}, holdSide={hold_side_val}, triggerPrice={stop_price}, size={amount}, productType={body.get('productType')}, body={body}")
                    except:
                        logger.error(f"{account_name} TPSL 请求参数获取失败")
                    # Bitget 专用下单失败则直接返回 None，避免通用 create_order 触发参数冲突
                    return None

            # 通用分支：退回 ccxt create_order 的通用 stopLossPrice 能力（非 Bitget 或兜底）
            # 仅传一个统一键，避免部分交易所 createOrder 参数冲突
            params = {
                'reduceOnly': True,
                'stopLossPrice': stop_price,
            }
            order = client.create_order(
                symbol=contract_symbol,
                type='market',
                side=side,
                amount=amount,
                price=None,
                params=params
            )

            return {
                'status': 'success',
                'order_id': order['id'],
                'price': stop_price,
                'amount': amount,
                'order': order
            }
            
        except Exception as e:
            logger.error(f"{account_name} 止损订单失败: {e}")
            return None
    
    def place_take_profit_order(self, account_name: str, symbol: str, side: str, 
                                amount: float, tp_price: float) -> Optional[Dict]:
        """
        设置止盈订单
        
        Args:
            account_name: 账户名称
            symbol: 交易对 (如 'BTC/USDT')
            side: 'buy' 或 'sell'
            amount: 数量
            tp_price: 止盈价格
            
        Returns:
            订单信息字典，失败返回None
        """
        if account_name not in self.clients:
            logger.error(f"账户 {account_name} 不存在")
            return None
        
        try:
            client = self.clients[account_name]
            account = self.accounts[account_name]
            exchange_type = account.exchange_type.lower()
            
            # 转换为合约符号
            contract_symbol = self._convert_to_contract_symbol(client, symbol)
            
            # 🔧 Bitget特定参数
            params = {
                'reduceOnly': True  # 只减仓
            }
            
            if exchange_type == 'bitget':
                params.update({
                    'marginCoin': 'USDT',
                    'productType': 'USDT-FUTURES'
                })
            
            order = retry_call(
                client.create_order,
                contract_symbol,
                'limit',
                side,
                amount,
                tp_price,
                retries=2,
                delay=0.5,
                logger=logger,
                op=f"{account_name}.create_order_tp",
                params=params,
            )
            
            return {
                'status': 'success',
                'order_id': order['id'],
                'price': tp_price,
                'amount': amount,
                'order': order
            }
            
        except Exception as e:
            logger.error(f"{account_name} 止盈订单失败: {e}")
            return None

# 全局客户端实例
multi_exchange_client = MultiExchangeClient()

