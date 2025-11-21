# 🔄 GUI 重启说明

## ✅ 已完成的修改

### 1. 添加 Password 输入框
```python
# gui_multi_exchange.py 第117行
self.password_entry = self.create_entry(
    basic_frame, 
    "Password:", 
    "可选（bitget/okx需要）", 
    show="*"
)
```

### 2. 更新 ExchangeAccount 类
```python
# multi_exchange_config.py
class ExchangeAccount:
    def __init__(self, ..., password: str = "", ...):
        self.password = password
```

### 3. 更新客户端配置
```python
# multi_exchange_client.py
if account.password and account.password.strip():
    config['password'] = account.password.strip()
```

---

## 🎯 现在界面应该显示

打开 **"🚀 多交易所管理界面"** 后，右侧表单应该显示：

```
⚙️ 账户配置
━━━━━━━━━━━━━━━━━━━━

基本信息
  账户名称: [___________]
  
  交易所类型: [bitget ▼]
  
  API Key: [**************]
  
  API Secret: [**************]
  
  Password: [可选（bitget/okx需要）]  ← 新增！
  
  ☑ 使用测试网
  ☑ 启用此账户

交易参数
  默认杠杆倍数: [======⚪====] 10x
  
  ... 其他设置 ...
```

---

## 💡 如何填写

### Bitget 账户
```
1. 点击 "✏️ 编辑账户"
2. 选择 bitget 账户（编号 1）
3. 找到 "Password:" 输入框
4. 填写你的 Bitget Passphrase
5. 点击 "💾 更新账户"
```

### 从零创建 Bitget 账户
```
1. 点击 "➕ 添加账户"
2. 填写：
   账户名称: Bitget主账户
   交易所类型: bitget
   API Key: bg_xxxxx
   API Secret: xxxxxx
   Password: 你的Passphrase  ← 重要！
3. 保存
```

---

## ⚠️ 如果还是看不到

### 原因可能是：
1. **程序没有完全重启**
   - 关闭所有 Python 进程
   - 重新运行 `python gui_main.py`

2. **缓存问题**
   - 删除 `__pycache__` 目录
   - 重新启动程序

3. **代码没有保存**
   - 确保所有文件都已保存
   - 检查文件修改时间

---

## 🔧 手动重启步骤

### Windows
```powershell
# 1. 关闭所有 Python 进程
taskkill /F /IM python.exe

# 2. 等待 2 秒
Start-Sleep -Seconds 2

# 3. 重新启动
python gui_main.py
```

### 或者直接
```
1. 关闭 GUI 窗口
2. 在终端按 Ctrl+C
3. 重新运行: python gui_main.py
```

---

## ✅ 验证 Password 字段

### 检查步骤：
```
1. 打开程序
2. 点击 "🚀 多交易所管理界面"
3. 点击 "➕ 添加账户"
4. 在右侧表单向下滚动
5. 应该看到：
   API Key: [**************]
   API Secret: [**************]
   Password: [可选（bitget/okx需要）]  ← 这一行
```

---

## 🎯 如果仍然没有显示

请执行以下操作：

### 1. 清理并重启
```bash
# 删除缓存
rm -rf __pycache__
rm -rf gui_multi_exchange.pyc

# 重启
python gui_main.py
```

### 2. 验证代码
```python
# 查看 gui_multi_exchange.py 第 115-120 行
# 应该包含：
self.api_key_entry = self.create_entry(basic_frame, "API Key:", "", show="*")
self.api_secret_entry = self.create_entry(basic_frame, "API Secret:", "", show="*")
self.password_entry = self.create_entry(basic_frame, "Password:", "可选（bitget/okx需要）", show="*")
```

### 3. 检查日志
查看终端输出，确认没有错误：
```
INFO: 成功连接到 bitget (bitget)  ← 应该看到这个
```

而不是：
```
ERROR: bitget requires "password" credential  ← 如果看到这个，说明password没传入
```

---

## 📱 截图对比

### 修改前：
```
API Key: [**************]
API Secret: [**************]
☑ 使用测试网
☑ 启用此账户
```

### 修改后（应该显示）：
```
API Key: [**************]
API Secret: [**************]
Password: [可选（bitget/okx需要）]  ← 新增
☑ 使用测试网
☑ 启用此账户
```

---

**如果重启后还是看不到，请告诉我，我会进一步检查！** 🔍

