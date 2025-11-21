import asyncio
import logging

# Prepare DB before importing trade_executor
import database

# Use a test database file to avoid polluting production data
TEST_DB = "test_trading_history.db"
database.trading_db = database.TradingDatabase(TEST_DB)

from signal_parser import TradingSignal, SignalType
import order_manager
from trade_executor import TradeExecutor
import trade_executor as te_mod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("integration_test")


class DummyRisk:
    def can_open_trade(self, account, tv):
        logger.info(f"[DummyRisk] can_open_trade account={account} tv={tv}")
        return True, ""

    def record_trade(self, account, pnl, closed=False):
        logger.info(f"[DummyRisk] record_trade account={account} pnl={pnl:.4f} closed={closed}")


class FakeMultiExchange:
    def __init__(self):
        self.clients = {"acc1": object()}
        self.accounts = {"acc1": type("Cfg", (), {"default_leverage": 5})()}
        self.positions = {"acc1": {}}
        self.order_status = {}
        self.next_order_id = 1

    # Pricing
    def get_current_price(self, account_name, symbol):
        return 100.0

    # Position helpers
    def get_position(self, account_name, symbol):
        return self.positions.get(account_name, {}).get(symbol)

    def list_open_positions(self, account_name):
        pos = self.positions.get(account_name, {})
        out = []
        for sym, p in pos.items():
            if float(p.get("contracts", 0)) > 0:
                q = dict(p)
                q["symbol"] = sym
                out.append(q)
        return out

    # Sizing
    def calculate_position_size(self, account_name, symbol, entry_price):
        return 1.0

    # Orders
    def place_market_order(self, account_name, symbol, side, amount):
        price = 100.0
        self.positions.setdefault(account_name, {})[symbol] = {
            "contracts": float(amount),
            "side": "long" if side == "buy" else "short",
            "entry_price": price,
        }
        oid = f"OID{self.next_order_id}"; self.next_order_id += 1
        return {"status": "success", "order_id": oid, "price": price, "amount": amount}

    def place_stop_loss_order(self, account_name, symbol, side, amount, stop_price):
        oid = f"OID{self.next_order_id}"; self.next_order_id += 1
        return {"status": "placed", "order_id": oid, "stop": stop_price}

    def place_take_profit_order(self, account_name, symbol, side, amount, tp_price):
        oid = f"OID{self.next_order_id}"; self.next_order_id += 1
        self.order_status[oid] = "open"
        return {"status": "placed", "order_id": oid, "price": tp_price, "amount": amount}

    def fetch_order_status(self, account_name, symbol, order_id):
        st = self.order_status.get(order_id)
        if st is None:
            return None
        return {"status": st}

    def cancel_open_reduce_only_orders(self, account_name, symbol):
        # Nothing to cancel in fake
        return 0

    def close_position(self, account_name, symbol):
        p = self.positions.get(account_name, {}).get(symbol)
        if not p or float(p.get("contracts", 0)) <= 0:
            return False
        # market close
        p["contracts"] = 0.0
        return True


async def main():
    # Inject dummy risk manager into executor module
    te_mod.risk_manager = DummyRisk()

    # Setup fake exchange and position manager
    fake = FakeMultiExchange()
    order_manager.init_position_manager(fake)

    executor = TradeExecutor(fake)

    # Build a LONG signal without explicit entry price (use market)
    sig = TradingSignal(
        signal_type=SignalType.LONG,
        symbol="BTC/USDT",
        entry_price=None,
        stop_loss=None,
        take_profit=[110.0],  # price-based TP1
        leverage=5,
        raw_message="测试 LONG 信号 第一止盈 110"
    )

    # Execute on multi-exchange path (fake has one account)
    await executor._execute_multi_exchange(sig)

    # Mark all TP orders as closed to trigger TP1 monitor path
    for k in list(fake.order_status.keys()):
        fake.order_status[k] = "closed"

    # Allow monitor task to run
    await asyncio.sleep(0.2)

    # Close position and verify DB PnL
    pos = fake.get_position("acc1", "BTC/USDT")
    if pos:
        # simulate full close in exchange
        pos["contracts"] = 0.0

    # Fetch open trade and close it with exit price
    open_trades = database.trading_db.get_trades(account_name="acc1", limit=1, status="open")
    if not open_trades:
        logger.error("No open trades found for verification")
        return
    t = open_trades[0]
    trade_id = t["id"]
    entry = float(t["entry_price"] or 100.0)
    size = float(t["position_size"] or 1.0)
    lev = int(t["leverage"] or 1)
    exit_price = 110.0
    expected_pnl = (exit_price - entry) * size * lev if t["side"] == "buy" else (entry - exit_price) * size * lev
    database.trading_db.close_trade(trade_id, exit_price)

    closed = database.trading_db.get_trades(account_name="acc1", limit=1, status="closed")
    if not closed:
        logger.error("No closed trades after close_trade")
        return
    ct = closed[0]
    logger.info(f"Closed trade: id={ct['id']} pnl={ct['pnl']:.4f} exit={ct['exit_price']}")
    logger.info(f"Expected pnl: {expected_pnl:.4f}")


if __name__ == "__main__":
    asyncio.run(main())
