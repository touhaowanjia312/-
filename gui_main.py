"""
Telegram 群组信号跟单程序 - GUI 版本
高级全面的图形用户界面
"""

import sys
import asyncio
import threading
import queue
from datetime import datetime
from typing import Optional
import customtkinter as ctk
from tkinter import scrolledtext, messagebox, ttk
import logging
from io import StringIO
import traceback
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from telegram_client import TelegramSignalBot
from signal_parser import SignalParser
from exchange_client import ExchangeClient
from multi_exchange_client import multi_exchange_client
from config import Config
from gui_multi_exchange import ExchangeManagementWindow
from database import trading_db
from statistics import trading_stats
import order_manager

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置主题
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class TextHandler(logging.Handler):
    """自定义日志处理器，将日志输出到 GUI"""
    
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.queue = queue.Queue()
        
    def emit(self, record):
        msg = self.format(record)
        self.queue.put(msg)

class TradingBotGUI(ctk.CTk):
    """主 GUI 应用"""
    
    def __init__(self):
        super().__init__()
        
        # 窗口配置
        self.title("Telegram 群组信号跟单程序 v1.0")
        self.geometry("1500x950")  # 增加窗口大小
        
        # 设置最小窗口大小
        self.minsize(1200, 700)
        
        # 应用状态
        self.bot: Optional[TelegramSignalBot] = None
        self.bot_thread: Optional[threading.Thread] = None
        self.is_running = False
        self.exchange: Optional[ExchangeClient] = None
        self.multi_exchange = multi_exchange_client  # 多交易所客户端
        self.signal_parser = SignalParser()
        
        # 统计数据
        self.stats = {
            'total_signals': 0,
            'executed_trades': 0,
            'total_profit': 0.0,
            'win_rate': 0.0
        }
        
        # 创建界面
        self.create_widgets()
        
        # 配置日志
        self.setup_logging()
        
        # 启动更新循环
        self.update_log_display()
        self.update_stats_display()
        
    def create_widgets(self):
        """创建所有界面组件"""
        
        # 创建左侧面板
        self.create_left_panel()
        
        # 创建右侧面板
        self.create_right_panel()
        
    def create_left_panel(self):
        """创建左侧控制面板"""
        left_frame = ctk.CTkFrame(self, width=400)
        left_frame.pack(side="left", fill="both", padx=10, pady=10)
        
        # 标题
        title_label = ctk.CTkLabel(
            left_frame,
            text="🤖 交易机器人控制台",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=20)
        
        # 状态指示器
        self.status_frame = ctk.CTkFrame(left_frame)
        self.status_frame.pack(fill="x", padx=20, pady=10)
        
        self.status_label = ctk.CTkLabel(
            self.status_frame,
            text="● 未运行",
            font=ctk.CTkFont(size=16),
            text_color="gray"
        )
        self.status_label.pack(pady=10)
        
        # 控制按钮
        button_frame = ctk.CTkFrame(left_frame)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        self.start_button = ctk.CTkButton(
            button_frame,
            text="▶ 启动机器人",
            command=self.start_bot,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_button.pack(pady=5, fill="x")
        
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="■ 停止机器人",
            command=self.stop_bot,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_button.pack(pady=5, fill="x")
        
        # 统计信息
        self.create_stats_section(left_frame)
        
        # 账户信息
        self.create_account_section(left_frame)
        
        # 配置部分
        self.create_config_section(left_frame)
        
        # 主题切换
        theme_frame = ctk.CTkFrame(left_frame)
        theme_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(theme_frame, text="主题:").pack(side="left", padx=5)
        self.theme_switch = ctk.CTkSwitch(
            theme_frame,
            text="深色模式",
            command=self.toggle_theme
        )
        self.theme_switch.pack(side="left", padx=5)
        self.theme_switch.select()
        
    def create_stats_section(self, parent):
        """创建统计信息部分"""
        stats_frame = ctk.CTkFrame(parent)
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            stats_frame,
            text="📊 统计信息",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # 统计项
        self.total_signals_label = ctk.CTkLabel(
            stats_frame,
            text="识别信号: 0",
            font=ctk.CTkFont(size=12)
        )
        self.total_signals_label.pack(pady=2)
        
        self.executed_trades_label = ctk.CTkLabel(
            stats_frame,
            text="执行交易: 0",
            font=ctk.CTkFont(size=12)
        )
        self.executed_trades_label.pack(pady=2)
        
        self.total_profit_label = ctk.CTkLabel(
            stats_frame,
            text="总盈亏: $0.00",
            font=ctk.CTkFont(size=12)
        )
        self.total_profit_label.pack(pady=2)
        
        self.win_rate_label = ctk.CTkLabel(
            stats_frame,
            text="胜率: 0%",
            font=ctk.CTkFont(size=12)
        )
        self.win_rate_label.pack(pady=2)
        
    def create_account_section(self, parent):
        """创建账户信息部分"""
        account_frame = ctk.CTkFrame(parent)
        account_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            account_frame,
            text="💰 账户余额",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        self.balance_label = ctk.CTkLabel(
            account_frame,
            text="USDT: --",
            font=ctk.CTkFont(size=14)
        )
        self.balance_label.pack(pady=5)
        
        refresh_btn = ctk.CTkButton(
            account_frame,
            text="🔄 刷新余额",
            command=self.refresh_balance,
            height=30
        )
        refresh_btn.pack(pady=5)
        
    def create_config_section(self, parent):
        """创建配置部分"""
        # 使用可滚动框架
        config_frame = ctk.CTkScrollableFrame(parent, height=400)
        config_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ctk.CTkLabel(
            config_frame,
            text="⚙️ 配置",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # 交易开关
        self.trading_enabled_var = ctk.BooleanVar(value=Config.TRADING_ENABLED)
        trading_switch = ctk.CTkSwitch(
            config_frame,
            text="启用交易",
            variable=self.trading_enabled_var,
            command=self.toggle_trading
        )
        trading_switch.pack(pady=5)
        
        # 测试网开关
        self.testnet_var = ctk.BooleanVar(value=Config.EXCHANGE_TESTNET)
        testnet_switch = ctk.CTkSwitch(
            config_frame,
            text="使用测试网",
            variable=self.testnet_var
        )
        testnet_switch.pack(pady=5)
        
        # 风险百分比
        ctk.CTkLabel(config_frame, text="风险百分比:").pack(pady=(10, 0))
        self.risk_slider = ctk.CTkSlider(
            config_frame,
            from_=0.1,
            to=5.0,
            number_of_steps=49
        )
        self.risk_slider.set(Config.RISK_PERCENTAGE)
        self.risk_slider.pack(pady=5, padx=10, fill="x")
        
        self.risk_label = ctk.CTkLabel(
            config_frame,
            text=f"{Config.RISK_PERCENTAGE:.1f}%"
        )
        self.risk_label.pack()
        
        self.risk_slider.configure(command=self.update_risk_label)
        
    def create_right_panel(self):
        """创建右侧面板"""
        right_frame = ctk.CTkFrame(self)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        # 创建标签页
        self.tabview = ctk.CTkTabview(right_frame)
        self.tabview.pack(fill="both", expand=True)
        
        # 日志标签页
        self.log_tab = self.tabview.add("📝 实时日志")
        self.create_log_tab()
        
        # 信号测试标签页
        self.test_tab = self.tabview.add("🧪 信号测试")
        self.create_test_tab()
        
        # 统计分析标签页
        self.stats_tab = self.tabview.add("📊 统计分析")
        self.create_stats_tab()
        
        # 交易历史标签页
        self.history_tab = self.tabview.add("📈 交易历史")
        self.create_history_tab()
        
        # 设置标签页
        self.settings_tab = self.tabview.add("⚙️ 详细设置")
        self.create_settings_tab()
        
    def create_log_tab(self):
        """创建日志标签页"""
        log_frame = ctk.CTkFrame(self.log_tab)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap="word",
            font=("Consolas", 10),
            bg="#1e1e1e",
            fg="#ffffff",
            insertbackground="white"
        )
        self.log_text.pack(fill="both", expand=True)
        
        # 清除日志按钮
        clear_btn = ctk.CTkButton(
            log_frame,
            text="清除日志",
            command=self.clear_log,
            height=30
        )
        clear_btn.pack(pady=5)
        
    def create_test_tab(self):
        """创建信号测试标签页"""
        test_frame = ctk.CTkFrame(self.test_tab)
        test_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            test_frame,
            text="输入交易信号进行测试：",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10)
        
        # 输入框
        self.test_input = ctk.CTkTextbox(test_frame, height=150)
        self.test_input.pack(fill="x", padx=10, pady=5)
        self.test_input.insert("1.0", "🔥 LONG BTC/USDT\nEntry: 42000\nStop Loss: 41000\nTake Profit: 43000\nLeverage: 10x")
        
        # 测试按钮
        test_btn = ctk.CTkButton(
            test_frame,
            text="🧪 测试解析",
            command=self.test_signal_parsing,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        test_btn.pack(pady=10)
        
        # 结果显示
        ctk.CTkLabel(
            test_frame,
            text="解析结果：",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=10)
        
        self.test_result = ctk.CTkTextbox(test_frame, height=300)
        self.test_result.pack(fill="both", expand=True, padx=10, pady=5)
        
    def create_history_tab(self):
        """创建交易历史标签页"""
        history_frame = ctk.CTkFrame(self.history_tab)
        history_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            history_frame,
            text="📈 交易历史记录",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # 创建表格
        columns = ("时间", "交易对", "方向", "价格", "数量", "状态")
        self.history_tree = ttk.Treeview(history_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=100)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        
        self.history_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 刷新按钮
        refresh_btn = ctk.CTkButton(
            history_frame,
            text="🔄 刷新",
            command=self.refresh_history,
            height=30
        )
        refresh_btn.pack(pady=10)
        
        # 初始加载
        self.refresh_history()

    def create_stats_tab(self):
        container = ctk.CTkFrame(self.stats_tab)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 顶部控制区
        controls = ctk.CTkFrame(container)
        controls.pack(fill="x", pady=5)
        
        ctk.CTkLabel(controls, text="账户:").pack(side="left", padx=5)
        self.account_var = ctk.StringVar(value="全部账户")
        self.account_menu = ctk.CTkOptionMenu(
            controls,
            variable=self.account_var,
            values=["全部账户"] + list(self.multi_exchange.clients.keys())
        )
        self.account_menu.pack(side="left", padx=5)
        
        ctk.CTkLabel(controls, text="天数:").pack(side="left", padx=(15, 5))
        self.stats_days_entry = ctk.CTkEntry(controls, width=80)
        self.stats_days_entry.insert(0, "30")
        self.stats_days_entry.pack(side="left", padx=5)
        
        ctk.CTkButton(controls, text="🔄 刷新统计", command=self.refresh_stats, height=32).pack(side="left", padx=10)
        ctk.CTkButton(controls, text="⬇ 导出CSV", command=self.export_stats_csv, height=32).pack(side="left", padx=5)

        # 风控状态区
        risk_controls = ctk.CTkFrame(container)
        risk_controls.pack(fill="x", pady=5)
        ctk.CTkLabel(risk_controls, text="🛡 风险状态").pack(side="left", padx=5)
        ctk.CTkButton(risk_controls, text="🔄 刷新风控", command=self.refresh_risk_status, height=28).pack(side="left", padx=5)
        ctk.CTkButton(risk_controls, text="✅ 解除冷却", command=self.risk_manual_enable, height=28).pack(side="left", padx=5)
        ctk.CTkButton(risk_controls, text="♻ 重置统计", command=self.risk_reset, height=28).pack(side="left", padx=5)
        
        self.risk_summary = ctk.CTkTextbox(container, height=110)
        self.risk_summary.pack(fill="x", padx=5, pady=(0, 10))
        
        # 摘要区
        self.stats_summary = ctk.CTkTextbox(container, height=160)
        self.stats_summary.pack(fill="x", padx=5, pady=10)
        
        # 图表区
        self.chart_frame = ctk.CTkFrame(container)
        self.chart_frame.pack(fill="both", expand=True)
        self.pnl_canvas = None
        
        # 初次加载
        self.refresh_stats()
        self.refresh_risk_status()

    def refresh_stats(self):
        try:
            acct_label = self.account_var.get() if hasattr(self, 'account_var') else "全部账户"
            account = None if acct_label in (None, "", "全部账户") else acct_label
            try:
                days = int(self.stats_days_entry.get()) if hasattr(self, 'stats_days_entry') else 30
            except Exception:
                days = 30
            perf = trading_stats.get_account_performance(account, days)
            summary = perf.get('summary', {}) or {}
            metrics = perf.get('metrics', {}) or {}
            lines = []
            lines.append("【基本统计】")
            lines.append(f"总交易: {summary.get('total_trades', 0)}  盈利: {summary.get('winning_trades', 0)}  亏损: {summary.get('losing_trades', 0)}  胜率: {summary.get('win_rate', 0):.2f}%")
            lines.append("")
            lines.append("【盈亏统计】")
            lines.append(f"总盈亏: {summary.get('total_pnl', 0):.2f}  平均盈亏: {summary.get('average_pnl', 0):.2f}  最大盈: {summary.get('largest_win', 0):.2f}  最大亏: {summary.get('largest_loss', 0):.2f}  盈亏比: {summary.get('profit_factor', 0):.2f}")
            if metrics:
                lines.append("")
                lines.append("【风险指标】")
                lines.append(f"最大回撤: {metrics.get('max_drawdown', 0):.2f}  夏普: {metrics.get('sharpe_ratio', 0):.2f}  平均持仓(h): {metrics.get('avg_holding_time_hours', 0):.2f}  手续费: {metrics.get('total_fees', 0):.2f}  ROI: {metrics.get('roi', 0):.2f}%")
            txt = "\n".join(lines)
            self.stats_summary.delete("1.0", "end")
            self.stats_summary.insert("1.0", txt)
            
            # 绘制 PnL 曲线
            curve = trading_stats.generate_pnl_curve(account, days)
            if self.pnl_canvas:
                try:
                    self.pnl_canvas.get_tk_widget().destroy()
                except Exception:
                    pass
                self.pnl_canvas = None
            fig = Figure(figsize=(8, 4), dpi=100)
            ax = fig.add_subplot(111)
            if curve:
                xs = [i for i, _ in enumerate(curve)]
                ys = [d.get('cumulative_pnl', 0) for d in curve]
                ax.plot(xs, ys, label='累计盈亏')
                ax.set_title('累计盈亏曲线')
                ax.set_xlabel('交易序号(时间序)')
                ax.set_ylabel('累计PnL')
                ax.grid(True, alpha=0.3)
                ax.legend()
            else:
                ax.text(0.5, 0.5, '暂无已关闭交易，无法生成曲线', ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')
            self.pnl_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            self.pnl_canvas.draw()
            self.pnl_canvas.get_tk_widget().pack(fill="both", expand=True)
        except Exception as e:
            logging.error(f"刷新统计失败: {e}")

    def export_stats_csv(self):
        try:
            acct_label = self.account_var.get() if hasattr(self, 'account_var') else "全部账户"
            account = None if acct_label in (None, "", "全部账户") else acct_label
            import datetime as _dt
            fname = f"trades_export_{(account or 'all')}_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            ok = trading_stats.export_to_csv(account, fname)
            messagebox.showinfo("导出CSV", f"导出{'成功' if ok else '失败'}: {fname}")
        except Exception as e:
            logging.error(f"导出CSV失败: {e}")

    def refresh_risk_status(self):
        try:
            acct_label = self.account_var.get() if hasattr(self, 'account_var') else "全部账户"
            account = None if acct_label in (None, "", "全部账户") else acct_label
            lines = []
            rm = risk_manager if 'risk_manager' in globals() else None
            if not rm:
                lines.append("风控未初始化（启动机器人后可用）")
            else:
                from datetime import datetime as _dt
                def fmt_state(s: dict):
                    try:
                        enabled = s.get('trading_enabled')
                        cd = s.get('cooldown_until')
                        remain = 0
                        if cd:
                            try:
                                dt = cd if isinstance(cd, _dt) else _dt.fromisoformat(str(cd))
                                remain = max(0, int((dt - _dt.now()).total_seconds() // 60))
                            except Exception:
                                remain = 0
                        state = ("启用" if enabled else f"冷却{remain}分")
                        return state
                    except Exception:
                        return "-"
                if account:
                    s = rm.get_risk_status(account)
                    if not s:
                        lines.append(f"{account}: 无数据")
                    else:
                        lines.append(f"{account}  状态:{fmt_state(s)}  日PnL:{s.get('daily_pnl',0):.2f}  总PnL:{s.get('total_pnl',0):.2f}  日亏%:{s.get('daily_loss_pct',0):.2f}%  总亏%:{s.get('total_loss_pct',0):.2f}%  连亏:{s.get('consecutive_losses',0)}  连胜:{s.get('consecutive_wins',0)}  持仓:{s.get('open_positions_count',0)}")
                else:
                    stats = rm.get_all_risk_status()
                    agg_daily = 0.0
                    agg_total = 0.0
                    for name, s in (stats or {}).items():
                        agg_daily += float(s.get('daily_pnl', 0) or 0)
                        agg_total += float(s.get('total_pnl', 0) or 0)
                        lines.append(f"{name}  状态:{fmt_state(s)}  日PnL:{s.get('daily_pnl',0):.2f}  总PnL:{s.get('total_pnl',0):.2f}  连亏:{s.get('consecutive_losses',0)}  连胜:{s.get('consecutive_wins',0)}  持仓:{s.get('open_positions_count',0)}")
                    lines.append("")
                    lines.append(f"合计  日PnL:{agg_daily:.2f}  总PnL:{agg_total:.2f}")
            txt = "\n".join(lines)
            self.risk_summary.delete("1.0", "end")
            self.risk_summary.insert("1.0", txt)
        except Exception as e:
            logging.error(f"刷新风控失败: {e}")

    def risk_manual_enable(self):
        try:
            rm = risk_manager if 'risk_manager' in globals() else None
            if not rm:
                return
            acct_label = self.account_var.get() if hasattr(self, 'account_var') else "全部账户"
            account = None if acct_label in (None, "", "全部账户") else acct_label
            if account:
                try:
                    rm.manually_enable_trading(account)
                except Exception:
                    pass
            else:
                try:
                    for name in list(self.multi_exchange.clients.keys()):
                        try:
                            rm.manually_enable_trading(name)
                        except Exception:
                            continue
                except Exception:
                    pass
            self.refresh_risk_status()
        except Exception as e:
            logging.error(f"解除冷却失败: {e}")

    def risk_reset(self):
        try:
            rm = risk_manager if 'risk_manager' in globals() else None
            if not rm:
                return
            acct_label = self.account_var.get() if hasattr(self, 'account_var') else "全部账户"
            account = None if acct_label in (None, "", "全部账户") else acct_label
            if account:
                try:
                    rm.reset_account(account)
                except Exception:
                    pass
            else:
                try:
                    for name in list(self.multi_exchange.clients.keys()):
                        try:
                            rm.reset_account(name)
                        except Exception:
                            continue
                except Exception:
                    pass
            self.refresh_risk_status()
        except Exception as e:
            logging.error(f"重置统计失败: {e}")

    def refresh_history(self):
        try:
            # 清空表格
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            # 读取最近100条订单
            with trading_db.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT created_at, symbol, side, price, amount, status FROM orders ORDER BY created_at DESC LIMIT 100")
                rows = cur.fetchall()
                for row in rows:
                    t = row["created_at"] if isinstance(row["created_at"], str) else str(row["created_at"]) if row["created_at"] is not None else ""
                    sym = row["symbol"] or ""
                    side = row["side"] or ""
                    price = f"{row['price']:.8f}" if row["price"] is not None else ""
                    amount = f"{row['amount']:.8f}" if row["amount"] is not None else ""
                    status = row["status"] or ""
                    self.add_trade_to_history(t, sym, side.upper(), price, amount, status)
        except Exception as e:
            logging.error(f"加载历史失败: {e}")
        
    def create_settings_tab(self):
        """创建详细设置标签页"""
        # 使用可滚动框架
        settings_frame = ctk.CTkScrollableFrame(self.settings_tab)
        settings_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Telegram 设置
        telegram_frame = ctk.CTkFrame(settings_frame)
        telegram_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            telegram_frame,
            text="Telegram 配置",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)
        
        self.api_id_entry = self.create_setting_entry(telegram_frame, "API ID:", Config.TELEGRAM_API_ID or "")
        self.api_hash_entry = self.create_setting_entry(telegram_frame, "API Hash:", Config.TELEGRAM_API_HASH or "")
        self.phone_entry = self.create_setting_entry(telegram_frame, "手机号:", Config.TELEGRAM_PHONE or "")
        self.group_id_entry = self.create_setting_entry(telegram_frame, "群组ID:", Config.TELEGRAM_GROUP_ID or "")
        
        # 交易所设置
        exchange_frame = ctk.CTkFrame(settings_frame)
        exchange_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            exchange_frame,
            text="交易所配置",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(pady=5)
        
        self.exchange_entry = self.create_setting_entry(exchange_frame, "交易所:", Config.EXCHANGE_NAME or "binance")
        self.api_key_entry = self.create_setting_entry(exchange_frame, "API Key:", Config.EXCHANGE_API_KEY or "", show="*")
        self.api_secret_entry = self.create_setting_entry(exchange_frame, "API Secret:", Config.EXCHANGE_API_SECRET or "", show="*")
        
        # TP/SL 高级设置
        tpsl_frame = ctk.CTkFrame(settings_frame)
        tpsl_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(
            tpsl_frame,
            text="🎯 止盈止损(TP/SL)设置",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=5)
        
        # 分批止盈设置
        tp_config_frame = ctk.CTkFrame(tpsl_frame)
        tp_config_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(tp_config_frame, text="分批止盈设置 (TP1, TP2, TP3):").pack(anchor="w", pady=2)
        
        tp_row1 = ctk.CTkFrame(tp_config_frame)
        tp_row1.pack(fill="x", pady=2)
        ctk.CTkLabel(tp_row1, text="TP1 利润%:", width=80).pack(side="left", padx=2)
        self.tp1_profit = ctk.CTkEntry(tp_row1, width=60, placeholder_text="2")
        self.tp1_profit.pack(side="left", padx=2)
        ctk.CTkLabel(tp_row1, text="仓位%:", width=60).pack(side="left", padx=2)
        self.tp1_portion = ctk.CTkEntry(tp_row1, width=60, placeholder_text="30")
        self.tp1_portion.pack(side="left", padx=2)
        
        tp_row2 = ctk.CTkFrame(tp_config_frame)
        tp_row2.pack(fill="x", pady=2)
        ctk.CTkLabel(tp_row2, text="TP2 利润%:", width=80).pack(side="left", padx=2)
        self.tp2_profit = ctk.CTkEntry(tp_row2, width=60, placeholder_text="4")
        self.tp2_profit.pack(side="left", padx=2)
        ctk.CTkLabel(tp_row2, text="仓位%:", width=60).pack(side="left", padx=2)
        self.tp2_portion = ctk.CTkEntry(tp_row2, width=60, placeholder_text="30")
        self.tp2_portion.pack(side="left", padx=2)
        
        tp_row3 = ctk.CTkFrame(tp_config_frame)
        tp_row3.pack(fill="x", pady=2)
        ctk.CTkLabel(tp_row3, text="TP3 利润%:", width=80).pack(side="left", padx=2)
        self.tp3_profit = ctk.CTkEntry(tp_row3, width=60, placeholder_text="6")
        self.tp3_profit.pack(side="left", padx=2)
        ctk.CTkLabel(tp_row3, text="仓位%:", width=60).pack(side="left", padx=2)
        self.tp3_portion = ctk.CTkEntry(tp_row3, width=60, placeholder_text="40")
        self.tp3_portion.pack(side="left", padx=2)
        
        # 止损和追踪止损
        sl_config_frame = ctk.CTkFrame(tpsl_frame)
        sl_config_frame.pack(fill="x", padx=10, pady=5)
        
        sl_row = ctk.CTkFrame(sl_config_frame)
        sl_row.pack(fill="x", pady=2)
        ctk.CTkLabel(sl_row, text="默认止损 %:", width=100).pack(side="left", padx=5)
        self.default_sl = ctk.CTkEntry(sl_row, width=80, placeholder_text="2.0")
        self.default_sl.pack(side="left", padx=5)
        
        # 追踪止损开关
        self.trailing_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            sl_config_frame,
            text="启用追踪止损",
            variable=self.trailing_var
        ).pack(anchor="w", pady=2)
        
        trail_row = ctk.CTkFrame(sl_config_frame)
        trail_row.pack(fill="x", pady=2)
        ctk.CTkLabel(trail_row, text="追踪止损 %:", width=100).pack(side="left", padx=5)
        self.trailing_percent = ctk.CTkEntry(trail_row, width=80, placeholder_text="2.0")
        self.trailing_percent.pack(side="left", padx=5)
        
        # 保本后是否停止追踪止损
        self.stop_trailing_after_be_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            sl_config_frame,
            text="保本后停止追踪止损",
            variable=self.stop_trailing_after_be_var
        ).pack(anchor="w", pady=2)
        
        # 保本止损开关
        self.breakeven_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            sl_config_frame,
            text="启用保本止损（盈利后移动止损到成本价）",
            variable=self.breakeven_var
        ).pack(anchor="w", pady=2)
        
        breakeven_row = ctk.CTkFrame(sl_config_frame)
        breakeven_row.pack(fill="x", pady=2)
        ctk.CTkLabel(breakeven_row, text="触发盈利 %:", width=100).pack(side="left", padx=5)
        self.breakeven_trigger = ctk.CTkEntry(breakeven_row, width=80, placeholder_text="1.0")
        self.breakeven_trigger.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            tpsl_frame,
            text="💡 这些设置将自动应用于所有新的交易信号",
            text_color="gray",
            font=ctk.CTkFont(size=10)
        ).pack(pady=5)
        
        # 多交易所管理按钮
        multi_exchange_frame = ctk.CTkFrame(settings_frame)
        multi_exchange_frame.pack(fill="x", padx=10, pady=20)
        
        ctk.CTkLabel(
            multi_exchange_frame,
            text="💼 多交易所账户管理",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=5)
        
        ctk.CTkLabel(
            multi_exchange_frame,
            text="管理多个交易所账户，为每个账户设置独立的:\n• 杠杆倍数  • 风险参数  • 仓位计算模式",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).pack(pady=5)
        
        ctk.CTkButton(
            multi_exchange_frame,
            text="🚀 打开多交易所管理界面",
            command=self.open_multi_exchange_window,
            height=45,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#FF6B35",
            hover_color="#D84315"
        ).pack(fill="x", padx=20, pady=10)
        
        # 保存按钮
        save_btn = ctk.CTkButton(
            settings_frame,
            text="💾 保存配置到 .env",
            command=self.save_config,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        save_btn.pack(pady=20)
        
    def create_setting_entry(self, parent, label_text, default_value, show=None):
        """创建设置输入项并返回entry对象"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(frame, text=label_text, width=120).pack(side="left", padx=5)
        entry = ctk.CTkEntry(frame, placeholder_text=default_value, show=show)
        entry.pack(side="left", fill="x", expand=True, padx=5)
        entry.insert(0, default_value)
        
        return entry  # 返回entry以便后续访问
    
    def setup_logging(self):
        """设置日志系统"""
        self.text_handler = TextHandler(self.log_text)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.text_handler.setFormatter(formatter)
        
        logger = logging.getLogger()
        logger.addHandler(self.text_handler)
        logger.setLevel(logging.INFO)
        
    def update_log_display(self):
        """更新日志显示"""
        while not self.text_handler.queue.empty():
            msg = self.text_handler.queue.get()
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
        
        self.after(100, self.update_log_display)
    
    def update_stats_display(self):
        """更新统计信息显示"""
        self.total_signals_label.configure(text=f"识别信号: {self.stats['total_signals']}")
        self.executed_trades_label.configure(text=f"执行交易: {self.stats['executed_trades']}")
        self.total_profit_label.configure(text=f"总盈亏: ${self.stats['total_profit']:.2f}")
        self.win_rate_label.configure(text=f"胜率: {self.stats['win_rate']:.1f}%")
        
        self.after(1000, self.update_stats_display)
    
    def start_bot(self):
        """启动机器人"""
        if self.is_running:
            messagebox.showwarning("警告", "机器人已在运行中！")
            return
        
        try:
            Config.validate()
        except ValueError as e:
            messagebox.showerror("配置错误", f"配置验证失败：{e}")
            return
        
        self.is_running = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_label.configure(text="● 运行中", text_color="green")
        
        # 在新线程中启动机器人
        self.bot_thread = threading.Thread(target=self.run_bot_async, daemon=True)
        self.bot_thread.start()
        
        # 启动监控任务
        self.start_monitoring()
        
        logging.info("✓ 机器人已启动")
    
    def run_bot_async(self):
        """在异步环境中运行机器人"""
        try:
            self.bot = TelegramSignalBot()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.start())
        except Exception as e:
            logging.error(f"机器人运行出错: {e}")
            try:
                logging.error(traceback.format_exc())
            except Exception:
                pass
            self.is_running = False
    
    def start_monitoring(self):
        """启动监控任务"""
        try:
            # 创建持仓管理器实例并设置为全局变量
            logger.info("🔧 创建PositionManager实例...")
            order_manager.position_manager = order_manager.PositionManager(self.multi_exchange)
            self.position_manager = order_manager.position_manager
            logger.info(f"🔧 PositionManager创建成功: {order_manager.position_manager}")
            
            # 在新线程中启动监控循环
            logger.info("🔧 启动监控线程...")
            self.monitor_thread = threading.Thread(target=self.run_monitoring_async, daemon=True)
            self.monitor_thread.start()
            logging.info("✓ 持仓监控已启动")
        except Exception as e:
            logging.error(f"启动监控失败: {e}")
            import traceback
            logging.error(f"详细错误信息: {traceback.format_exc()}")
    
    def run_monitoring_async(self):
        """在异步环境中运行监控"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # 创建监控任务
            async def monitoring_loop():
                while True:
                    try:
                        if order_manager.position_manager:
                            order_manager.position_manager.monitor_positions()
                    except Exception as e:
                        logging.error(f"监控持仓出错: {e}")
                    await asyncio.sleep(3)
            
            loop.run_until_complete(monitoring_loop())
        except Exception as e:
            logging.error(f"监控循环出错: {e}")
    
    def stop_monitoring(self):
        """停止监控任务"""
        try:
            if hasattr(self, 'monitor_thread') and self.monitor_thread.is_alive():
                # 由于是守护线程，会自动停止
                logging.info("✓ 持仓监控已停止")
        except Exception as e:
            logging.error(f"停止监控失败: {e}")
    
    def stop_bot(self):
        """停止机器人"""
        if not self.is_running:
            messagebox.showwarning("警告", "机器人未在运行！")
            return
        
        self.is_running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text="● 已停止", text_color="red")
        
        if self.bot:
            self.bot.stop()
        
        # 停止监控任务
        self.stop_monitoring()
        
        logging.info("✓ 机器人已停止")
    
    def _format_balance(self, balance: float) -> str:
        """
        格式化余额显示
        对于小额余额显示更多小数位
        """
        if balance >= 1.0:
            return f"{balance:.2f}"
        elif balance >= 0.01:
            return f"{balance:.4f}"
        elif balance >= 0.0001:
            return f"{balance:.6f}"
        else:
            return f"{balance:.8f}"
    
    def refresh_balance(self):
        """刷新账户余额"""
        # 使用多交易所客户端
        if len(self.multi_exchange.clients) > 0:
            # 获取详细余额
            detailed_balances = self.multi_exchange.get_all_balances_detailed()
            if detailed_balances:
                total = 0.0
                balance_text = ""
                
                for name, bal_info in detailed_balances.items():
                    total += bal_info['total']
                    
                    # 显示格式：账户名: 总额 (现货: xxx, 合约: xxx)
                    if bal_info['futures'] is None:
                        # 统一账户
                        balance_text += f"{name}: {self._format_balance(bal_info['total'])} (统一)\n"
                    else:
                        # 分离账户 - 始终显示现货和合约
                        balance_text += f"{name}: {self._format_balance(bal_info['total'])} "
                        balance_text += f"(💵 现货: {self._format_balance(bal_info['spot'])}, "
                        balance_text += f"📊 合约: {self._format_balance(bal_info['futures'])})\n"
                
                # 添加总计
                final_text = f"💰 总计: {self._format_balance(total)} USDT\n\n{balance_text}"
                self.balance_label.configure(text=final_text.strip())
                logging.info(f"余额已更新: {len(detailed_balances)} 个账户")
            else:
                self.balance_label.configure(text="USDT: 获取失败")
        else:
            # 回退到单交易所
            if not self.exchange:
                self.exchange = ExchangeClient()
            
            if self.exchange.initialized:
                balance = self.exchange.get_balance('USDT')
                if balance is not None:
                    formatted = self._format_balance(balance)
                    self.balance_label.configure(text=f"USDT: {formatted}")
                    logging.info(f"余额更新: {formatted} USDT")
                else:
                    self.balance_label.configure(text="USDT: 获取失败")
            else:
                messagebox.showwarning("警告", "请先在多交易所管理中配置账户")
    
    def test_signal_parsing(self):
        """测试信号解析"""
        message = self.test_input.get("1.0", "end-1c")
        
        if not message.strip():
            messagebox.showwarning("警告", "请输入信号内容")
            return
        
        signal = self.signal_parser.parse(message)
        
        result = ""
        if signal:
            result = f"✓ 解析成功！\n\n"
            result += f"信号类型: {signal.signal_type.value}\n"
            result += f"交易对: {signal.symbol}\n"
            if signal.entry_price:
                result += f"入场价格: {signal.entry_price}\n"
            if signal.stop_loss:
                result += f"止损: {signal.stop_loss}\n"
            if signal.take_profit:
                result += f"止盈: {signal.take_profit}\n"
            if signal.leverage:
                result += f"杠杆: {signal.leverage}x\n"
            
            self.stats['total_signals'] += 1
        else:
            result = "✗ 未能识别有效的交易信号\n\n"
            result += "请检查信号格式是否正确。\n"
            result += "支持的格式示例：\n"
            result += "LONG BTC/USDT\n"
            result += "Entry: 42000\n"
            result += "Stop Loss: 41000\n"
            result += "Take Profit: 43000"
        
        self.test_result.delete("1.0", "end")
        self.test_result.insert("1.0", result)
        
        logging.info(f"信号测试: {'成功' if signal else '失败'}")
    
    def add_trade_to_history(self, time, symbol, trade_type, price, amount, status):
        """添加交易到历史记录"""
        self.history_tree.insert("", "end", values=(time, symbol, trade_type, price, amount, status))
    
    def clear_log(self):
        """清除日志"""
        self.log_text.delete("1.0", "end")
        logging.info("日志已清除")
    
    def toggle_theme(self):
        """切换主题"""
        if self.theme_switch.get():
            ctk.set_appearance_mode("dark")
        else:
            ctk.set_appearance_mode("light")
    
    def toggle_trading(self):
        """切换交易开关"""
        Config.TRADING_ENABLED = self.trading_enabled_var.get()
        status = "已启用" if Config.TRADING_ENABLED else "已禁用"
        logging.info(f"交易状态: {status}")
    
    def update_risk_label(self, value):
        """更新风险标签"""
        self.risk_label.configure(text=f"{float(value):.1f}%")
        Config.RISK_PERCENTAGE = float(value)
    
    def save_config(self):
        """保存配置"""
        try:
            import os
            from pathlib import Path
            
            # 创建配置字典
            config_data = {
                # Telegram 配置
                'TELEGRAM_API_ID': self.api_id_entry.get(),
                'TELEGRAM_API_HASH': self.api_hash_entry.get(),
                'TELEGRAM_PHONE': self.phone_entry.get(),
                'TELEGRAM_GROUP_ID': self.group_id_entry.get(),
                
                # 交易所配置
                'EXCHANGE_NAME': self.exchange_entry.get(),
                'EXCHANGE_API_KEY': self.api_key_entry.get(),
                'EXCHANGE_API_SECRET': self.api_secret_entry.get(),
                
                # TP/SL 配置
                'USE_SIGNAL_TPSL': 'true',  # 优先使用信号中的TP/SL
                'TP1_PROFIT': self.tp1_profit.get() or '2.0',
                'TP1_PORTION': self.tp1_portion.get() or '30.0',
                'TP2_PROFIT': self.tp2_profit.get() or '4.0',
                'TP2_PORTION': self.tp2_portion.get() or '30.0',
                'TP3_PROFIT': self.tp3_profit.get() or '6.0',
                'TP3_PORTION': self.tp3_portion.get() or '40.0',
                'DEFAULT_STOP_LOSS': self.default_sl.get() or '2.0',
                'TRAILING_STOP_ENABLED': 'true' if self.trailing_var.get() else 'false',
                'TRAILING_STOP_PERCENT': self.trailing_percent.get() or '2.0',
                'STOP_TRAILING_AFTER_BREAKEVEN': 'true' if self.stop_trailing_after_be_var.get() else 'false',
                'BREAKEVEN_ENABLED': 'true' if self.breakeven_var.get() else 'false',
                'BREAKEVEN_TRIGGER': self.breakeven_trigger.get() or '1.0',
            }
            
            # 写入 .env 文件
            env_path = Path('.env')
            env_lines = []
            
            # 读取现有内容（如果存在）
            existing_keys = set()
            if env_path.exists():
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            key = line.split('=')[0].strip()
                            if key in config_data:
                                existing_keys.add(key)
                                env_lines.append(f"{key}={config_data[key]}")
                            else:
                                env_lines.append(line)
                        else:
                            env_lines.append(line)
            
            # 添加新的配置项
            for key, value in config_data.items():
                if key not in existing_keys:
                    env_lines.append(f"{key}={value}")
            
            # 保存到文件
            with open(env_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(env_lines))
            
            # 同时保存到 config.json 用于 TP/SL 配置
            import json
            config_json_path = Path('tpsl_config.json')
            tpsl_config = {
                'use_signal_tpsl': True,  # 优先使用信号中的TP/SL
                'additional_tps': [  # 额外的止盈点（在信号TP之后）
                    {
                        'profit_percent': float(config_data['TP1_PROFIT']),
                        'portion_percent': float(config_data['TP1_PORTION'])
                    },
                    {
                        'profit_percent': float(config_data['TP2_PROFIT']),
                        'portion_percent': float(config_data['TP2_PORTION'])
                    },
                    {
                        'profit_percent': float(config_data['TP3_PROFIT']),
                        'portion_percent': float(config_data['TP3_PORTION'])
                    }
                ],
                'default_stop_loss_percent': float(config_data['DEFAULT_STOP_LOSS']),
                'trailing_stop': {
                    'enabled': config_data['TRAILING_STOP_ENABLED'] == 'true',
                    'percent': float(config_data['TRAILING_STOP_PERCENT'])
                },
                'breakeven': {
                    'enabled': config_data['BREAKEVEN_ENABLED'] == 'true',
                    'trigger_percent': float(config_data['BREAKEVEN_TRIGGER'])
                },
                'stop_trailing_after_breakeven': config_data.get('STOP_TRAILING_AFTER_BREAKEVEN', 'false') == 'true'
            }
            
            with open(config_json_path, 'w', encoding='utf-8') as f:
                json.dump(tpsl_config, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("成功", 
                "✅ 配置已保存！\n\n"
                "保存位置：\n"
                "• .env (基础配置)\n"
                "• tpsl_config.json (止盈止损配置)\n\n"
                "配置说明：\n"
                "✓ 优先使用信号中的止盈止损\n"
                "✓ TP1/TP2/TP3 作为额外的分批止盈\n"
                "✓ 重启程序后生效")
            
            logger.info("✓ 配置已保存到 .env 和 tpsl_config.json")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存配置失败：{e}")
            logger.error(f"保存配置失败: {e}")
    
    def open_multi_exchange_window(self):
        """打开多交易所管理窗口"""
        try:
            # 创建新窗口
            exchange_window = ExchangeManagementWindow(self)
            exchange_window.focus()
            logger.info("✓ 多交易所管理窗口已打开")
        except Exception as e:
            messagebox.showerror("错误", f"打开多交易所管理窗口失败：{e}")
            logger.error(f"打开多交易所管理窗口失败: {e}")
    
    def on_closing(self):
        """关闭窗口时"""
        if self.is_running:
            if messagebox.askokcancel("退出", "机器人正在运行，确定要退出吗？"):
                self.stop_bot()
                self.destroy()
        else:
            self.destroy()

def main():
    """主函数"""
    app = TradingBotGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()

