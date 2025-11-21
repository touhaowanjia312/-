# GUI 版本安装指南

## 📋 系统要求

- **Python**: 3.8 或更高版本
- **操作系统**: Windows 10+, macOS 10.14+, Linux (Ubuntu 18.04+)
- **内存**: 至少 2GB RAM
- **屏幕**: 推荐分辨率 1280x720 或更高

## 🚀 快速安装（3步）

### 第一步：安装 Python 依赖

```bash
pip install -r requirements.txt
```

**如果遇到问题**，可以分步安装：

```bash
# 基础依赖
pip install telethon python-dotenv ccxt requests

# GUI 依赖
pip install customtkinter pillow matplotlib
```

### 第二步：配置环境变量

复制配置示例：
```bash
# Windows
copy config.example.txt .env

# Linux/Mac
cp config.example.txt .env
```

编辑 `.env` 文件，至少填入 Telegram 配置：
```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+86xxxxxxxxxx
TELEGRAM_GROUP_ID=@your_group
```

### 第三步：启动 GUI

**Windows:**
```bash
# 方法 1: 双击
start_gui.bat

# 方法 2: 命令行
python gui_main.py
```

**Linux/Mac:**
```bash
# 添加执行权限（首次）
chmod +x start_gui.sh

# 启动
./start_gui.sh

# 或直接运行
python3 gui_main.py
```

## 🔧 详细安装步骤

### Windows 系统

#### 1. 安装 Python

1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.8+ 安装包
3. **重要**: 勾选 "Add Python to PATH"
4. 点击 "Install Now"

#### 2. 验证安装

打开命令提示符（CMD）：
```bash
python --version
pip --version
```

应该显示版本号，如 `Python 3.11.0`

#### 3. 安装依赖

```bash
cd C:\python\cypto11
pip install -r requirements.txt
```

#### 4. 常见问题

**问题 1: pip 不是内部命令**
```bash
# 解决方法
python -m pip install -r requirements.txt
```

**问题 2: 安装 customtkinter 失败**
```bash
# 尝试
pip install --upgrade pip
pip install customtkinter
```

**问题 3: 缺少 Visual C++ 构建工具**
- 安装 Visual Studio Build Tools
- 或使用预编译版本：`pip install --prefer-binary`

### macOS 系统

#### 1. 安装 Python

使用 Homebrew（推荐）：
```bash
# 安装 Homebrew（如果没有）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装 Python
brew install python@3.11
```

#### 2. 安装依赖

```bash
cd ~/cypto11
pip3 install -r requirements.txt
```

#### 3. 常见问题

**问题 1: tkinter 未安装**
```bash
brew install python-tk@3.11
```

**问题 2: SSL 证书问题**
```bash
/Applications/Python\ 3.11/Install\ Certificates.command
```

### Linux 系统（Ubuntu/Debian）

#### 1. 安装 Python 和依赖

```bash
sudo apt update
sudo apt install python3 python3-pip python3-tk
```

#### 2. 安装程序依赖

```bash
cd ~/cypto11
pip3 install -r requirements.txt
```

#### 3. 常见问题

**问题 1: tkinter 相关错误**
```bash
sudo apt install python3-tk
```

**问题 2: pillow 依赖问题**
```bash
sudo apt install python3-pil python3-pil.imagetk
```

## ✅ 验证安装

运行测试脚本验证所有模块是否正确安装：

```bash
python test_signal_parser.py
```

如果成功运行并显示测试结果，说明基础安装成功。

## 🎨 首次启动 GUI

### 1. 启动程序

```bash
python gui_main.py
```

### 2. 界面说明

启动后你会看到：
- **左侧**：控制面板（启动/停止、统计、配置）
- **右侧**：标签页（日志、测试、历史、设置）
- **状态**: 顶部显示 "● 未运行"

### 3. 功能测试

在不配置 API 的情况下，可以测试：

**测试信号解析**：
1. 点击 "🧪 信号测试" 标签
2. 输入或使用默认信号
3. 点击 "🧪 测试解析"
4. 查看结果

### 4. 配置 Telegram（首次使用）

1. 获取 Telegram API：https://my.telegram.org/apps
2. 点击 "⚙️ 详细设置" 标签
3. 填入 API ID、API Hash、手机号、群组ID
4. 返回主界面，点击 "▶ 启动机器人"
5. **重要**: 在终端窗口（不是GUI）输入验证码

## 🐛 故障排除

### 问题 1: 点击启动后无响应

**诊断**：
1. 查看终端窗口是否有输出
2. 检查 `.env` 文件是否配置
3. 查看 "📝 实时日志" 标签

**解决**：
- 确保配置文件完整
- 查看日志中的错误提示
- 在终端窗口输入验证码（如果需要）

### 问题 2: GUI 窗口无法打开

**可能原因**：
1. customtkinter 未正确安装
2. tkinter 未安装（Linux）
3. 显示问题

**解决**：
```bash
# 重新安装 GUI 依赖
pip uninstall customtkinter
pip install customtkinter

# Linux 用户
sudo apt install python3-tk
```

### 问题 3: 字体显示异常

**Windows**:
- 确保系统安装了 Consolas 字体

**Linux**:
```bash
sudo apt install fonts-liberation
```

**macOS**:
- 通常无需额外配置

### 问题 4: 主题显示不正常

**解决**：
- 尝试切换主题（深色/浅色）
- 更新 customtkinter：`pip install --upgrade customtkinter`

### 问题 5: 无法连接 Telegram

**检查**：
1. 网络连接
2. API ID 和 Hash 是否正确
3. 手机号格式（需要包含国家代码，如 +86）
4. 是否需要代理（中国大陆用户）

**代理设置**：
修改 `telegram_client.py`，在创建客户端时添加代理：
```python
self.client = TelegramClient(
    'trading_bot_session',
    Config.TELEGRAM_API_ID,
    Config.TELEGRAM_API_HASH,
    proxy=('socks5', 'localhost', 1080)  # 根据你的代理配置
)
```

### 问题 6: 交易所连接失败

**检查**：
1. API Key 和 Secret 是否正确
2. API 权限是否启用
3. 是否选择了正确的网络（测试网/正式网）
4. IP 白名单设置

**测试连接**：
在 Python 中测试：
```python
from exchange_client import ExchangeClient
client = ExchangeClient()
balance = client.get_balance('USDT')
print(f"余额: {balance}")
```

## 📊 性能优化

### 减少内存使用

1. **定期清除日志**
   - 日志过多会占用内存
   - 定期点击 "清除日志"

2. **关闭不需要的标签页**
   - 只保持当前使用的标签打开

3. **调整更新频率**
   - 修改 `gui_main.py` 中的更新间隔

### 提高响应速度

1. **使用 SSD**
   - 程序运行在 SSD 上会更快

2. **关闭其他程序**
   - 释放系统资源

3. **升级 Python**
   - 使用最新版 Python 3.11+

## 🔄 更新程序

### 更新代码
```bash
git pull origin main
```

### 更新依赖
```bash
pip install --upgrade -r requirements.txt
```

### 清除缓存
```bash
# 删除 __pycache__ 文件夹
rm -rf __pycache__

# Windows
rmdir /s /q __pycache__
```

## 🆘 获取帮助

如果问题仍未解决：

1. **查看文档**
   - README.md - 完整文档
   - GUI_README.md - GUI 使用说明
   - QUICKSTART.md - 快速入门

2. **查看日志**
   - GUI 的 "实时日志" 标签
   - 终端窗口的输出

3. **检查配置**
   - 验证 .env 文件
   - 运行 `python test_signal_parser.py`

4. **提交 Issue**
   - 访问 GitHub 仓库
   - 提交详细的问题描述和错误日志

## 🎉 成功标志

如果你看到以下内容，说明安装成功：

✅ GUI 窗口正常打开  
✅ 界面布局完整  
✅ 可以切换标签页  
✅ 信号测试功能正常  
✅ 日志显示正常  

现在可以开始配置并使用程序了！

---

**下一步**：查看 [GUI_README.md](GUI_README.md) 了解如何使用 GUI 版本。

