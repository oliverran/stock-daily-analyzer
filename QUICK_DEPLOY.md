# 快速部署指南

## 🚀 三种部署方式

### 1️⃣ 一键自动部署（推荐）

```bash
# 上传项目到服务器
scp -r stock-daily-analyzer user@your-server:/home/user/

# SSH登录服务器
ssh user@your-server

# 进入项目目录并运行部署脚本
cd /home/user/stock-daily-analyzer
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

**脚本会自动完成所有配置！**

### 2️⃣ Docker 快速部署

```bash
# 确保已安装Docker和Docker Compose
cd /home/user/stock-daily-analyzer/deploy/docker
chmod +x run.sh
./run.sh
```

### 3️⃣ 手动部署

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量（已完成）
cat .env  # 检查配置

# 4. 测试运行
python test_llm.py

# 5. 配置定时任务（以下时间按 cron 所用的主机时区解释）
crontab -e
# 添加: 30 15 * * 1-5 cd /path/to/project && venv/bin/python main.py >> /var/log/stock-analyzer/cron.log 2>&1
```

## 📋 部署后检查清单

- ✅ Python依赖已安装
- ✅ .env文件已配置API密钥
- ✅ 测试运行成功 (`python test_llm.py`)
- ✅ 定时任务已设置
- ✅ 日志目录已创建

## 🔍 常用命令

```bash
# 手动运行
cd /home/user/stock-daily-analyzer
source venv/bin/activate
python main.py

# 使用systemd服务
sudo systemctl start stock-analyzer
sudo systemctl status stock-analyzer

# 查看日志
tail -f /var/log/stock-analyzer/output.log
tail -f /var/log/stock-analyzer/cron.log

# Docker方式
docker-compose logs -f
docker-compose restart
```

## 📖 详细文档

查看完整部署文档：[DEPLOYMENT.md](./DEPLOYMENT.md)

## ⏰ 定时任务说明

示例配置在周一至周五 15:30 执行，**不等于仅在 A 股交易日执行**：cron 不识别交易所节假日，当前 `main.py` / `analyzer.py` 入口也没有交易日跳过逻辑。休市日仍可能分析旧行情并生成报告，需核对行情实际日期，不能将报告生成日期当作行情日期。

示例时间按 cron 所用的主机时区解释。先用 `date +'%Z %z'` 检查主机时区，并确认 cron 服务的时区配置：若为 `Asia/Shanghai`，`30 15 * * 1-5` 对应北京时间 15:30；若为 UTC，需使用 `30 7 * * 1-5` 才对应同一时刻。Docker 容器也需单独核对时区。

应用使用本地日期标记分析日期；仅调整触发时间不会自动改变应用时区。生产部署应另外接入交易日判断并验证行情新鲜度，详见[定时任务说明](./DEPLOYMENT.md#配置定时任务)。

修改运行时间：
```bash
crontab -e
```

## 🆘 遇到问题？

1. 查看日志文件定位问题
2. 确认API密钥配置正确
3. 检查Python依赖是否完整安装
4. 参考 DEPLOYMENT.md 的故障排查章节
