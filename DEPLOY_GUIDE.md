# 服务器部署指南

## 📋 部署信息

- **服务器地址**: 47.250.142.117
- **用户**: root
- **远程路径**: /root/monitor_tpo

## 🚀 快速部署步骤

### 方法1: 使用自动部署脚本（推荐）

```bash
# 在本地项目目录运行
deploy.bat
```

脚本会自动上传所有必要文件到服务器。

### 方法2: 手动上传

如果自动脚本失败，可以使用以下命令手动上传：

```powershell
# 1. 创建远程目录（首次部署）
ssh root@47.250.142.117 "mkdir -p /root/monitor_tpo"

# 2. 上传 Python 文件
scp *.py root@47.250.142.117:/root/monitor_tpo/

# 3. 上传配置文件
scp config.yaml requirements.txt .env.example root@47.250.142.117:/root/monitor_tpo/

# 4. 上传文档
scp *.md root@47.250.142.117:/root/monitor_tpo/
```

### 方法3: 使用 SFTP（图形化界面）

如果不习惯命令行，可以使用 SFTP 客户端：
- **WinSCP** (推荐): https://winscp.net/
- **FileZilla**: https://filezilla-project.org/

连接信息：
- 协议: SFTP
- 主机: 47.250.142.117
- 端口: 22
- 用户名: root
- 密码: （你的服务器密码）

---

## 🔧 服务器端配置

上传完成后，SSH 登录服务器进行配置：

```bash
# 1. SSH 登录服务器
ssh root@47.250.142.117

# 2. 进入项目目录
cd /root/monitor_tpo

# 3. 安装 Python3 和 pip（如果还没有）
apt update
apt install -y python3 python3-pip python3-venv

# 4. 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 5. 安装依赖
pip install -r requirements.txt

# 6. 配置环境变量
cp .env.example .env
nano .env
# 编辑 Telegram Bot Token 和 Chat ID

# 7. 测试运行
python main.py
```

---

## 🔄 后续更新代码

当本地代码更新后，重新运行部署脚本即可：

```bash
# 在本地运行
deploy.bat
```

或手动上传修改的文件：

```bash
# 只上传某个文件
scp main.py root@47.250.142.117:/root/monitor_tpo/
```

---

## 🌟 让程序在后台持续运行

### 方法1: 使用 screen（简单）

```bash
# 创建新的 screen 会话
screen -S tpo_monitor

# 激活虚拟环境并运行
cd /root/monitor_tpo
source .venv/bin/activate
python main.py

# 按 Ctrl+A+D 退出 screen（程序继续运行）

# 重新连接到 screen
screen -r tpo_monitor

# 查看所有 screen 会话
screen -ls

# 停止程序
screen -r tpo_monitor
# 然后按 Ctrl+C
```

### 方法2: 使用 systemd（开机自启）

```bash
# 1. 创建服务文件
nano /etc/systemd/system/tpo_monitor.service
```

内容如下：

```ini
[Unit]
Description=TPO Trading Monitor Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/monitor_tpo
Environment="PATH=/root/monitor_tpo/.venv/bin"
ExecStart=/root/monitor_tpo/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 2. 启动服务
systemctl daemon-reload
systemctl start tpo_monitor
systemctl enable tpo_monitor  # 开机自启

# 3. 管理服务
systemctl status tpo_monitor   # 查看状态
systemctl stop tpo_monitor     # 停止
systemctl restart tpo_monitor  # 重启
systemctl logs -u tpo_monitor -f  # 查看日志
```

### 方法3: 使用 nohup（最简单）

```bash
# 在后台运行
cd /root/monitor_tpo
source .venv/bin/activate
nohup python main.py > output.log 2>&1 &

# 查看进程
ps aux | grep main.py

# 停止进程
kill <PID>
```

---

## 📊 查看日志

```bash
# 查看主日志
tail -f /root/monitor_tpo/logs/main.log

# 查看信号日志
tail -f /root/monitor_tpo/logs/signals.log

# 查看错误日志
tail -f /root/monitor_tpo/logs/errors.log
```

---

## 🔒 安全建议

1. **修改 SSH 端口**（可选）
   ```bash
   nano /etc/ssh/sshd_config
   # 将 Port 22 改为其他端口
   systemctl restart sshd
   ```

2. **配置防火墙**
   ```bash
   ufw allow 22/tcp  # 允许 SSH
   ufw enable
   ```

3. **使用 SSH 密钥登录**（更安全）
   ```bash
   # 在本地生成密钥（如果还没有）
   ssh-keygen -t rsa -b 4096
   
   # 上传公钥到服务器
   ssh-copy-id root@47.250.142.117
   ```

4. **保护 .env 文件**
   ```bash
   chmod 600 /root/monitor_tpo/.env
   ```

---

## ⚠️ 常见问题

### 问题1: ssh 或 scp 命令不存在

Windows 上需要安装 OpenSSH 客户端：
- 设置 → 应用 → 可选功能 → OpenSSH 客户端

或使用 Git Bash 中的命令。

### 问题2: 连接被拒绝

检查：
- 服务器 IP 是否正确
- SSH 服务是否运行（服务器端执行 `systemctl status sshd`）
- 防火墙是否阻止 22 端口

### 问题3: 权限被拒绝

确保：
- 使用正确的用户名和密码
- 有足够的权限访问目标目录

---

## 📞 技术支持

如果遇到问题，可以：
1. 检查本地和服务器的网络连接
2. 查看服务器日志: `/var/log/auth.log`
3. 检查防火墙设置

---

**最后更新**: 2025-12-11
