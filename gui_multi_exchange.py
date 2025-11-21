"""
多交易所管理 GUI 窗口
"""

import customtkinter as ctk
from tkinter import messagebox, ttk
from multi_exchange_config import ExchangeAccount, multi_exchange_config
from multi_exchange_client import multi_exchange_client
import logging

logger = logging.getLogger(__name__)

class ExchangeManagementWindow(ctk.CTkToplevel):
    """交易所管理窗口"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("交易所账户管理")
        self.geometry("1000x700")
        
        # 当前选中的账户
        self.selected_account_name = None
        self.editing_account = None
        
        # 创建界面
        self.create_widgets()
        
        # 加载现有账户
        self.refresh_accounts_list()
    
    def create_widgets(self):
        """创建界面组件"""
        
        # 左侧账户列表
        left_frame = ctk.CTkFrame(self, width=300)
        left_frame.pack(side="left", fill="both", padx=10, pady=10)
        
        ctk.CTkLabel(
            left_frame,
            text="💼 交易所账户列表",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=10)
        
        # 账户列表框
        list_frame = ctk.CTkFrame(left_frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.accounts_listbox = ctk.CTkTextbox(list_frame, height=400)
        self.accounts_listbox.pack(fill="both", expand=True)
        
        # 按钮
        btn_frame = ctk.CTkFrame(left_frame)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkButton(
            btn_frame,
            text="➕ 添加账户",
            command=self.add_account,
            fg_color="green",
            hover_color="darkgreen"
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame,
            text="✏️ 编辑账户",
            command=self.edit_account
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame,
            text="🗑️ 删除账户",
            command=self.delete_account,
            fg_color="red",
            hover_color="darkred"
        ).pack(fill="x", pady=2)
        
        ctk.CTkButton(
            btn_frame,
            text="🔄 刷新列表",
            command=self.refresh_accounts_list
        ).pack(fill="x", pady=2)
        
        # 右侧详细配置
        self.create_config_panel()
    
    def create_config_panel(self):
        """创建配置面板"""
        right_frame = ctk.CTkScrollableFrame(self)
        right_frame.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(
            right_frame,
            text="⚙️ 账户配置",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=10)
        
        # 基本信息
        basic_frame = ctk.CTkFrame(right_frame)
        basic_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(basic_frame, text="基本信息", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        self.name_entry = self.create_entry(basic_frame, "账户名称:", "如: 币安主账户")
        
        exchange_frame = ctk.CTkFrame(basic_frame)
        exchange_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(exchange_frame, text="交易所类型:", width=120).pack(side="left", padx=5)
        self.exchange_combo = ctk.CTkComboBox(
            exchange_frame,
            values=["binance", "okx", "bybit", "huobi", "bitget", "gate", "kucoin"]
        )
        self.exchange_combo.pack(side="left", fill="x", expand=True, padx=5)
        
        self.api_key_entry = self.create_entry(basic_frame, "API Key:", "", show="*")
        self.api_secret_entry = self.create_entry(basic_frame, "API Secret:", "", show="*")
        self.password_entry = self.create_entry(basic_frame, "Password:", "可选（bitget/okx需要）", show="*")
        
        # 网络设置
        network_frame = ctk.CTkFrame(basic_frame)
        network_frame.pack(fill="x", padx=10, pady=5)
        
        self.testnet_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(network_frame, text="使用测试网", variable=self.testnet_var).pack(side="left", padx=5)
        
        self.enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(network_frame, text="启用此账户", variable=self.enabled_var).pack(side="left", padx=5)
        
        # 交易参数
        trading_frame = ctk.CTkFrame(right_frame)
        trading_frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(trading_frame, text="交易参数", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=5)
        
        # 杠杆倍数
        leverage_frame = ctk.CTkFrame(trading_frame)
        leverage_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(leverage_frame, text="默认杠杆倍数:", width=120).pack(side="left", padx=5)
        self.leverage_slider = ctk.CTkSlider(leverage_frame, from_=1, to=125, number_of_steps=124)
        self.leverage_slider.set(10)
        self.leverage_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.leverage_label = ctk.CTkLabel(leverage_frame, text="10x", width=50)
        self.leverage_label.pack(side="left", padx=5)
        self.leverage_slider.configure(command=self.update_leverage_label)
        
        # 仓位设置方式
        position_mode_frame = ctk.CTkFrame(trading_frame)
        position_mode_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(position_mode_frame, text="仓位计算方式:", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        
        self.position_mode_var = ctk.StringVar(value="risk")
        
        risk_radio = ctk.CTkRadioButton(
            position_mode_frame,
            text="风险百分比模式",
            variable=self.position_mode_var,
            value="risk",
            command=self.toggle_position_mode
        )
        risk_radio.pack(anchor="w", padx=20, pady=2)
        
        margin_radio = ctk.CTkRadioButton(
            position_mode_frame,
            text="固定保证金模式",
            variable=self.position_mode_var,
            value="margin",
            command=self.toggle_position_mode
        )
        margin_radio.pack(anchor="w", padx=20, pady=2)
        
        # 风险百分比设置
        self.risk_frame = ctk.CTkFrame(trading_frame)
        self.risk_frame.pack(fill="x", padx=10, pady=5)
        
        risk_pct_frame = ctk.CTkFrame(self.risk_frame)
        risk_pct_frame.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(risk_pct_frame, text="风险百分比:", width=120).pack(side="left", padx=5)
        self.risk_slider = ctk.CTkSlider(risk_pct_frame, from_=0.1, to=10.0, number_of_steps=99)
        self.risk_slider.set(1.0)
        self.risk_slider.pack(side="left", fill="x", expand=True, padx=5)
        self.risk_label = ctk.CTkLabel(risk_pct_frame, text="1.0%", width=50)
        self.risk_label.pack(side="left", padx=5)
        self.risk_slider.configure(command=self.update_risk_label)
        
        self.default_size_entry = self.create_entry(self.risk_frame, "默认仓位大小:", "0.01")
        self.max_size_entry = self.create_entry(self.risk_frame, "最大仓位限制:", "0.1")
        
        # 固定保证金设置
        self.margin_frame = ctk.CTkFrame(trading_frame)
        
        self.margin_entry = self.create_entry(self.margin_frame, "保证金金额 (USDT):", "100")
        
        ctk.CTkLabel(
            self.margin_frame,
            text="💡 实际仓位 = 保证金 × 杠杆 ÷ 价格",
            text_color="gray"
        ).pack(pady=5)
        
        # 初始显示风险模式
        self.toggle_position_mode()
        
        # 保存按钮
        save_frame = ctk.CTkFrame(right_frame)
        save_frame.pack(fill="x", padx=10, pady=20)
        
        self.save_button = ctk.CTkButton(
            save_frame,
            text="💾 保存账户",
            command=self.save_account,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="green",
            hover_color="darkgreen"
        )
        self.save_button.pack(fill="x")
    
    def create_entry(self, parent, label_text, placeholder, show=None):
        """创建输入框"""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(frame, text=label_text, width=120).pack(side="left", padx=5)
        entry = ctk.CTkEntry(frame, placeholder_text=placeholder, show=show)
        entry.pack(side="left", fill="x", expand=True, padx=5)
        
        return entry
    
    def update_leverage_label(self, value):
        """更新杠杆标签"""
        self.leverage_label.configure(text=f"{int(float(value))}x")
    
    def update_risk_label(self, value):
        """更新风险标签"""
        self.risk_label.configure(text=f"{float(value):.1f}%")
    
    def toggle_position_mode(self):
        """切换仓位计算模式"""
        if self.position_mode_var.get() == "risk":
            self.risk_frame.pack(fill="x", padx=10, pady=5)
            self.margin_frame.pack_forget()
        else:
            self.margin_frame.pack(fill="x", padx=10, pady=5)
            self.risk_frame.pack_forget()
    
    def refresh_accounts_list(self):
        """刷新账户列表"""
        self.accounts_listbox.delete("1.0", "end")
        
        if len(multi_exchange_config) == 0:
            self.accounts_listbox.insert("1.0", "暂无账户\n\n点击 '添加账户' 开始配置")
            return
        
        for i, account in enumerate(multi_exchange_config, 1):
            status = "✓ 启用" if account.enabled else "✗ 禁用"
            network = "测试网" if account.testnet else "正式网"
            mode = "保证金" if account.use_margin_amount else "风险%"
            
            text = f"[{i}] {account.name}\n"
            text += f"    交易所: {account.exchange_type}\n"
            text += f"    状态: {status} | {network}\n"
            text += f"    杠杆: {account.default_leverage}x\n"
            text += f"    模式: {mode}\n"
            
            if account.use_margin_amount:
                text += f"    保证金: {account.margin_amount} USDT\n"
            else:
                text += f"    风险: {account.risk_percentage}%\n"
            
            text += f"    ─────────────────\n"
            
            self.accounts_listbox.insert("end", text)
        
        # 添加提示
        self.accounts_listbox.insert("end", "\n💡 提示：点击上方按钮选择账户进行编辑或删除")
    
    def add_account(self):
        """添加新账户"""
        self.clear_form()
        self.save_button.configure(text="💾 添加账户")
    
    def edit_account(self):
        """编辑选中的账户"""
        if len(multi_exchange_config) == 0:
            messagebox.showwarning("提示", "没有可编辑的账户")
            return
        
        # 创建选择对话框
        from tkinter import simpledialog
        
        names = [acc.name for acc in multi_exchange_config]
        choice_text = "\n".join([f"{i+1}. {name}" for i, name in enumerate(names)])
        
        result = simpledialog.askstring(
            "选择账户",
            f"请输入要编辑的账户编号：\n\n{choice_text}"
        )
        
        if result:
            try:
                idx = int(result) - 1
                if 0 <= idx < len(names):
                    account = multi_exchange_config.get_account(names[idx])
                    if account:
                        self.load_account_to_form(account)
                        self.editing_account = account.name
                        self.save_button.configure(text="💾 更新账户")
                        messagebox.showinfo("提示", f"已加载 '{account.name}' 的配置，修改后点击保存")
                else:
                    messagebox.showerror("错误", "无效的编号")
            except ValueError:
                messagebox.showerror("错误", "请输入数字")
    
    def delete_account(self):
        """删除账户"""
        if len(multi_exchange_config) == 0:
            messagebox.showwarning("提示", "没有可删除的账户")
            return
        
        from tkinter import simpledialog
        
        names = [acc.name for acc in multi_exchange_config]
        choice_text = "\n".join([f"{i+1}. {name}" for i, name in enumerate(names)])
        
        result = simpledialog.askstring(
            "删除账户",
            f"⚠️ 请输入要删除的账户编号：\n\n{choice_text}"
        )
        
        if result:
            try:
                idx = int(result) - 1
                if 0 <= idx < len(names):
                    account_name = names[idx]
                    
                    if messagebox.askyesno("确认删除", f"确定要删除账户 '{account_name}' 吗？"):
                        # 从配置中删除
                        multi_exchange_config.remove_account(account_name)
                        multi_exchange_config.save_to_file()
                        
                        # 从客户端中删除
                        from multi_exchange_client import multi_exchange_client
                        multi_exchange_client.remove_exchange(account_name)
                        
                        messagebox.showinfo("成功", f"账户 '{account_name}' 已删除")
                        self.refresh_accounts_list()
                        self.clear_form()
                else:
                    messagebox.showerror("错误", "无效的编号")
            except ValueError:
                messagebox.showerror("错误", "请输入数字")
    
    def save_account(self):
        """保存账户"""
        try:
            name = self.name_entry.get()
            if not name:
                messagebox.showerror("错误", "请输入账户名称")
                return
            
            api_key = self.api_key_entry.get()
            api_secret = self.api_secret_entry.get()
            
            if not api_key or not api_secret:
                messagebox.showerror("错误", "请输入 API Key 和 Secret")
                return
            
            # 检查是否是更新
            if self.editing_account and self.editing_account != name:
                # 账户名称改变了，需要先删除旧的
                multi_exchange_config.remove_account(self.editing_account)
                from multi_exchange_client import multi_exchange_client
                multi_exchange_client.remove_exchange(self.editing_account)
            
            # 创建账户对象
            account = ExchangeAccount(
                name=name,
                exchange_type=self.exchange_combo.get(),
                api_key=api_key,
                api_secret=api_secret,
                password=self.password_entry.get() or "",  # API密码（可选）
                testnet=self.testnet_var.get(),
                enabled=self.enabled_var.get(),
                default_leverage=int(self.leverage_slider.get()),
                default_position_size=float(self.default_size_entry.get() or "0.01"),
                max_position_size=float(self.max_size_entry.get() or "0.1"),
                risk_percentage=float(self.risk_slider.get()),
                use_margin_amount=(self.position_mode_var.get() == "margin"),
                margin_amount=float(self.margin_entry.get() or "100")
            )
            
            # 如果是更新，先删除旧的
            if self.editing_account:
                multi_exchange_config.remove_account(name)
                from multi_exchange_client import multi_exchange_client
                multi_exchange_client.remove_exchange(name)
            
            # 添加到配置
            multi_exchange_config.add_account(account)
            multi_exchange_config.save_to_file()
            
            # 初始化交易所客户端
            from multi_exchange_client import multi_exchange_client
            multi_exchange_client.add_exchange(account)
            
            action = "更新" if self.editing_account else "保存"
            messagebox.showinfo("成功", f"账户 '{name}' 已{action}并初始化！")
            
            # 重置编辑状态
            self.editing_account = None
            self.save_button.configure(text="💾 保存账户")
            
            # 刷新列表
            self.refresh_accounts_list()
            self.clear_form()
            
        except ValueError as e:
            messagebox.showerror("错误", f"输入格式错误: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
            logger.error(f"保存账户失败: {e}")
    
    def clear_form(self):
        """清空表单"""
        self.name_entry.delete(0, "end")
        self.api_key_entry.delete(0, "end")
        self.api_secret_entry.delete(0, "end")
        self.password_entry.delete(0, "end")  # 清空password
        self.exchange_combo.set("binance")
        self.testnet_var.set(True)
        self.enabled_var.set(True)
        self.leverage_slider.set(10)
        self.risk_slider.set(1.0)
        self.default_size_entry.delete(0, "end")
        self.default_size_entry.insert(0, "0.01")
        self.max_size_entry.delete(0, "end")
        self.max_size_entry.insert(0, "0.1")
        self.margin_entry.delete(0, "end")
        self.margin_entry.insert(0, "100")
        self.position_mode_var.set("risk")
        self.toggle_position_mode()
        self.editing_account = None
        self.save_button.configure(text="💾 保存账户")
    
    def load_account_to_form(self, account: ExchangeAccount):
        """加载账户信息到表单"""
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, account.name)
        
        self.exchange_combo.set(account.exchange_type)
        
        self.api_key_entry.delete(0, "end")
        self.api_key_entry.insert(0, account.api_key)
        
        self.api_secret_entry.delete(0, "end")
        self.api_secret_entry.insert(0, account.api_secret)
        
        self.password_entry.delete(0, "end")
        if hasattr(account, 'password') and account.password:
            self.password_entry.insert(0, account.password)
        
        self.testnet_var.set(account.testnet)
        self.enabled_var.set(account.enabled)
        
        self.leverage_slider.set(account.default_leverage)
        
        self.default_size_entry.delete(0, "end")
        self.default_size_entry.insert(0, str(account.default_position_size))
        
        self.max_size_entry.delete(0, "end")
        self.max_size_entry.insert(0, str(account.max_position_size))
        
        self.risk_slider.set(account.risk_percentage)
        
        self.margin_entry.delete(0, "end")
        self.margin_entry.insert(0, str(account.margin_amount))
        
        if account.use_margin_amount:
            self.position_mode_var.set("margin")
        else:
            self.position_mode_var.set("risk")
        
        self.toggle_position_mode()

