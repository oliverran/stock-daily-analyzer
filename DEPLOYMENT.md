# 服务器部署指南

本文档详细说明如何将 Stock Daily Analyzer 部署到生产服务器。

## 目录

- [方案一：使用部署脚本（推荐）](#方案一使用部署脚本推荐)
- [方案二：手动部署](#方案二手动部署)
- [方案三：Docker部署](#方案三docker部署)
- [配置定时任务](#配置定时任务)
- [监控与维护](#监控与维护)

---

## 方案一：使用部署脚本（推荐）

### 一键部署

```bash
# 1. 上传项目到服务器
scp -r stock-daily-analyzer user@your-server:/home/user/

# 2. 登录服务器
ssh user@your-server

# 3. 进入项目目录
cd stock-daily-analyzer

# 4. 给部署脚本添加执行权限
chmod +x deploy/deploy.sh

# 5. 运行部署脚本
./deploy/deploy.sh
```

脚本会自动完成：
- ✅ 检查系统依赖
- ✅ 创建项目目录和日志目录
- ✅ 复制项目文件
- ✅ 创建Python虚拟环境
- ✅ 安装依赖包
- ✅ 配置环境变量
- ✅ 设置systemd服务
- ✅ 配置定时任务
- ✅ 执行测试运行

### 自定义安装路径

```bash
# 指定安装目录
INSTALL_DIR=/opt/stock-analyzer ./deploy/deploy.sh

# 指定其他Python版本
PYTHON_BIN=python3.11 ./deploy/deploy.sh
```

---

## 方案二：手动部署

### 1. 准备服务器环境

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
sudo yum update -y                      # CentOS/RHEL

# 安装Python 3.9+
sudo apt install python3 python3-pip python3-venv  # Ubuntu/Debian
sudo yum install python3 python3-pip               # CentOS/RHEL

# 安装Git
sudo apt install git  # Ubuntu/Debian
sudo yum install git  # CentOS/RHEL
```

### 2. 创建项目目录

```bash
# 创建项目目录
mkdir -p ~/stock-daily-analyzer
cd ~/stock-daily-analyzer

# 创建日志目录
sudo mkdir -p /var/log/stock-analyzer
sudo chown $USER:$USER /var/log/stock-analyzer
```

### 3. 上传项目文件

```bash
# 方法1: 使用Git克隆
git clone https://github.com/yourusername/stock-daily-analyzer.git
cd stock-daily-analyzer

# 方法2: 使用scp上传
# 在本地执行:
scp -r /path/to/stock-daily-analyzer user@server:/home/user/
```

### 4. 创建虚拟环境

```bash
cd ~/stock-daily-analyzer

# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

### 5. 配置环境变量

```bash
# 创建.env文件
cat > .env << EOF
ARK_API_KEY=your_actual_api_key
ARK_MODEL_ID=your_actual_model_id
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
EOF

# 设置文件权限
chmod 600 .env
```

### 6. 测试运行

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行测试
python test_llm.py

# 完整运行
python main.py
```

---

## 方案三：Docker部署

### 前置要求

```bash
# 安装Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装Docker Compose
sudo apt install docker-compose  # Ubuntu/Debian
sudo yum install docker-compose  # CentOS/RHEL

# 将当前用户添加到docker组
sudo usermod -aG docker $USER
newgrp docker
```

### 使用Docker部署

```bash
# 1. 进入Docker部署目录
cd deploy/docker

# 2. 确保.env文件已配置（在项目根目录）
cat ../../.env

# 3. 给运行脚本添加执行权限
chmod +x run.sh

# 4. 构建并运行
./run.sh

# 或者手动执行
docker-compose build
docker-compose up -d
```

### Docker常用命令

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 停止容器
docker-compose down

# 重启容器
docker-compose restart

# 进入容器
docker-compose exec stock-analyzer bash

# 清理并重建
docker-compose down -v
docker-compose up -d --build
```

---

## 配置定时任务

### 调度边界与时区

- 以下规则只筛选周一至周五，不识别 A 股交易所节假日，不能称作“每个交易日”。当前 `main.py` 调用 `run_daily_analysis()`，`analyzer.py` 中没有按交易日跳过执行的检查；休市日仍可能分析上一交易日行情。
- cron 示例按 cron 服务所用的主机时区解释。用 `date +'%Z %z'` 检查主机时区，并核对 cron 服务配置；Docker 容器需单独检查。下例在 `Asia/Shanghai` 时区对应北京时间 15:30 / 20:00；UTC 主机应分别改为 `30 7 * * 1-5` / `0 12 * * 1-5`。不同 cron 实现对 `CRON_TZ` 的支持不同，不应直接假定可用。
- 应用以本地 `date.today()` 标记分析日期，报告生成日期不代表行情日期。生产运行需另加交易日判断，并核对最新行情的日期和完整性；延后运行也不保证数据源已更新。本指南没有配置交易所日历或数据新鲜度保护。

### 使用Cron（推荐）

```bash
# 编辑crontab
crontab -e

# 添加以下内容（周一至周五15:30，按 cron 服务时区）
30 15 * * 1-5 cd /home/user/stock-daily-analyzer && /home/user/stock-daily-analyzer/venv/bin/python /home/user/stock-daily-analyzer/main.py >> /var/log/stock-analyzer/cron.log 2>&1

# 或者周一至周五20:00执行（仍需检查行情是否已更新）
0 20 * * 1-5 cd /home/user/stock-daily-analyzer && /home/user/stock-daily-analyzer/venv/bin/python /home/user/stock-daily-analyzer/main.py >> /var/log/stock-analyzer/cron.log 2>&1

# 查看定时任务
crontab -l
```

### 使用systemd timer

下例显式使用 `Asia/Shanghai` 调度，避免主机时区不同导致触发时间偏移；它不会设置 Python 进程的本地时区，也不会识别交易所休市日。`Persistent=true` 会在计时器重新启用时补触发停机期间错过的任务，补触发可能发生在周末或休市日。

可在安装前只解析日历表达式（不会创建或运行任务）：

```bash
systemd-analyze calendar 'Mon..Fri *-*-* 15:30:00 Asia/Shanghai'
```

```bash
# 创建timer文件
sudo nano /etc/systemd/system/stock-analyzer.timer

# 添加以下内容
[Unit]
Description=Stock Daily Analyzer Timer
Requires=stock-analyzer.service

[Timer]
OnCalendar=Mon..Fri *-*-* 15:30:00 Asia/Shanghai
Persistent=true

[Install]
WantedBy=timers.target

# 启用并启动timer
sudo systemctl daemon-reload
sudo systemctl enable stock-analyzer.timer
sudo systemctl start stock-analyzer.timer

# 查看timer状态
sudo systemctl status stock-analyzer.timer
sudo systemctl list-timers
```

---

## 监控与维护

### 查看日志

```bash
# 查看输出日志
tail -f /var/log/stock-analyzer/output.log

# 查看错误日志
tail -f /var/log/stock-analyzer/error.log

# 查看cron日志
tail -f /var/log/stock-analyzer/cron.log

# 查看系统日志
sudo journalctl -u stock-analyzer -f
```

### 手动运行

```bash
# 方法1: 直接运行
cd ~/stock-daily-analyzer
source venv/bin/activate
python main.py

# 方法2: 使用systemd
sudo systemctl start stock-analyzer

# 方法3: 使用Docker
docker-compose run --rm stock-analyzer
```

### 更新代码

```bash
# Git更新
cd ~/stock-daily-analyzer
git pull origin main

# 激活虚拟环境
source venv/bin/activate

# 更新依赖
pip install -r requirements.txt --upgrade

# 重启服务
sudo systemctl restart stock-analyzer
```

### 备份数据

```bash
# 备份数据库和报告
tar -czf stock-analyzer-backup-$(date +%Y%m%d).tar.gz \
    ~/stock-daily-analyzer/*.db \
    ~/stock-daily-analyzer/reports/ \
    ~/stock-daily-analyzer/.env

# 定期备份脚本
cat > ~/backup-stock-analyzer.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=~/backups
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/stock-analyzer-$(date +%Y%m%d-%H%M%S).tar.gz \
    ~/stock-daily-analyzer/*.db \
    ~/stock-daily-analyzer/reports/ \
    ~/stock-daily-analyzer/.env
# 保留最近7天的备份
find $BACKUP_DIR -name "stock-analyzer-*.tar.gz" -mtime +7 -delete
EOF

chmod +x ~/backup-stock-analyzer.sh

# 添加到crontab（每天凌晨2点备份）
# 2 0 * * * ~/backup-stock-analyzer.sh
```

### 性能监控

```bash
# 监控进程资源使用
top -p $(pgrep -f "python.*main.py")

# 查看内存使用
ps aux | grep "python.*main.py"

# 磁盘空间检查
df -h ~/stock-daily-analyzer
du -sh ~/stock-daily-analyzer/*
```

### 故障排查

#### 程序无法启动

```bash
# 1. 检查Python环境
which python
python --version

# 2. 检查依赖
source venv/bin/activate
pip list

# 3. 检查环境变量
cat .env

# 4. 手动运行查看错误
python main.py
```

#### API调用失败

```bash
# 1. 检查网络连接
ping ark.cn-beijing.volces.com

# 2. 测试API
python test_llm.py

# 3. 检查API密钥
cat .env | grep ARK_API_KEY
```

#### 定时任务不执行

```bash
# 1. 检查cron服务
sudo systemctl status cron

# 2. 查看cron日志
sudo tail -f /var/log/syslog | grep CRON

# 3. 测试cron命令
cd /home/user/stock-daily-analyzer && /home/user/stock-daily-analyzer/venv/bin/python /home/user/stock-daily-analyzer/main.py
```

---

## 安全建议

1. **保护API密钥**
   ```bash
   # 设置.env文件权限
   chmod 600 .env
   
   # 确保不被Git跟踪
   echo ".env" >> .gitignore
   ```

2. **限制日志文件大小**
   ```bash
   # 使用logrotate
   sudo nano /etc/logrotate.d/stock-analyzer
   
   # 添加以下内容
   /var/log/stock-analyzer/*.log {
       daily
       rotate 7
       compress
       delaycompress
       notifempty
       create 0644 user user
   }
   ```

3. **设置防火墙**（如果需要远程访问）
   ```bash
   sudo ufw allow 22/tcp  # SSH
   sudo ufw enable
   ```

---

## 常见问题

**Q: 如何修改运行时间？**
A: 编辑crontab或systemd timer配置文件，修改时间参数。

**Q: 数据库文件存储在哪里？**
A: 默认在项目根目录下，文件名为 `stock_analysis.db`

**Q: 如何查看历史报告？**
A: 报告保存在 `reports/` 目录下，按日期命名。

**Q: 程序占用资源过高怎么办？**
A: 可以在systemd服务配置中调整资源限制（MemoryMax、CPUQuota）

---

## 联系支持

如遇到问题，请：
1. 查看日志文件
2. 参考本文档的故障排查章节
3. 提交Issue到GitHub仓库

---

**祝部署顺利！📈**
