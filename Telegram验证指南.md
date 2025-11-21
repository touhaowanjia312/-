# 📱 Telegram 验证指南

## 问题：EOF when reading a line

### 为什么会出现这个错误？

当程序**首次连接** Telegram 时，需要输入验证码：
```
Please enter the code you received: 
```

但是如果程序在**后台运行**，就无法接收你的输入，导致：
```
ERROR: 机器人运行出错: EOF when reading a line
```

---

## ✅ 解决方案

### 方法1: 前台运行（推荐首次验证）

1. **关闭当前程序**
   ```powershell
   # 在 PowerShell 中运行
   taskkill /F /IM python.exe
   ```

2. **前台运行程序**
   ```powershell
   python gui_main.py
   ```
   
3. **在GUI中点击 "▶️ 启动监听"**

4. **切换到终端窗口**
   - 你会看到：`Please enter the code you received:`
   - 此时Telegram会发送验证码到你的手机

5. **输入验证码**
   - 在终端输入6位数字
   - 按回车

6. **验证成功！**
   - 程序会保存session文件
   - 以后不再需要验证

---

### 方法2: 使用已有的 Session 文件

如果你之前在其他地方验证过：

1. 找到 `trading_bot_session.session` 文件
2. 复制到程序目录 `c:\python\cypto11\`
3. 重新启动程序

---

## 🎯 验证流程详解

### 第一次运行
```
启动监听
  ↓
连接 Telegram
  ↓
需要验证！
  ↓
发送验证码到手机 📱
  ↓
在终端输入验证码
  ↓
验证成功 ✓
  ↓
保存 session 文件
  ↓
开始监听群组消息
```

### 以后运行
```
启动监听
  ↓
连接 Telegram
  ↓
检查到 session 文件 ✓
  ↓
自动登录
  ↓
开始监听群组消息
```

---

## 🔧 详细步骤（PowerShell）

### Step 1: 打开 PowerShell
```
1. 按 Win + X
2. 选择 "Windows PowerShell" 或 "终端"
3. 导航到程序目录：
   cd c:\python\cypto11
```

### Step 2: 停止后台进程
```powershell
taskkill /F /IM python.exe
```

### Step 3: 前台运行
```powershell
python gui_main.py
```

**重要：** 不要关闭这个终端窗口！

### Step 4: 在GUI操作
```
1. 打开GUI窗口（应该已经自动打开）
2. 点击左侧 "▶️ 启动监听" 按钮
3. 等待...
```

### Step 5: 切换到终端
```
你会看到：

INFO: 正在启动 Telegram 信号机器人...
INFO: Connecting to 149.154.167.92:443/TcpFull...
INFO: Connection complete!
Please enter the code you received: █
```

**这时候需要输入验证码！**

### Step 6: 输入验证码
```
1. 查看手机 Telegram
2. 收到6位验证码（例如：123456）
3. 在终端输入：123456
4. 按回车
```

### Step 7: 验证成功
```
INFO: 验证成功
INFO: 正在监听群组消息...
INFO: 机器人已启动
```

现在可以关闭终端，程序会继续在后台运行！

---

## 📂 Session 文件

### 文件位置
```
c:\python\cypto11\trading_bot_session.session
```

### 作用
- 保存 Telegram 登录状态
- 下次启动不需要验证
- 可以备份这个文件

### 如果丢失
- 重新运行验证流程
- 会生成新的 session 文件

---

## ⚠️ 常见错误

### 错误1: EOF when reading a line
**原因：** 程序在后台运行，无法输入验证码
**解决：** 使用方法1前台运行

### 错误2: Phone migrated to X
**不用担心！** 这是正常的：
```
INFO: Phone migrated to 4
INFO: Reconnecting to new data center 4
```
只是Telegram在切换数据中心，继续等待即可。

### 错误3: Invalid code
**原因：** 验证码输入错误或过期
**解决：** 重新点击 "启动监听"，获取新验证码

---

## 🚀 验证成功后

### 后台运行
验证成功后，以后可以直接后台运行：
```powershell
# 双击运行
start_gui.bat

# 或命令行后台运行
Start-Process python -ArgumentList "gui_main.py" -WindowStyle Hidden
```

### 自动监听
程序会：
- ✅ 自动连接 Telegram
- ✅ 监听配置的群组
- ✅ 识别交易信号
- ✅ 在多个交易所执行交易

---

## 📝 完整命令清单

### 停止程序
```powershell
taskkill /F /IM python.exe
```

### 前台运行（首次验证）
```powershell
python gui_main.py
```

### 后台运行（已验证）
```powershell
start_gui.bat
```

### 查看进程
```powershell
tasklist | findstr python
```

---

## 💡 建议

### 首次设置
1. ✅ 使用前台运行
2. ✅ 完成 Telegram 验证
3. ✅ 确认 session 文件已生成
4. ✅ 测试信号接收

### 日常使用
1. ✅ 直接后台运行
2. ✅ 查看GUI日志
3. ✅ 监控交易执行

---

**验证只需要一次！完成后就可以愉快地使用了！** 🎉

