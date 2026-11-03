# A股每日分析助手

用 Python 扫描 A 股技术信号、生成研究日报，并通过独立的量化框架运行日频回测。LLM 新闻分析与候选股解读是可选功能。

**先运行离线演示，再接入真实数据。** 演示使用固定的虚构价格，无需 API Key；安装依赖后，运行演示不需要联网。

A-share daily research and backtesting in Python. Start with `stock-analyzer demo`: synthetic data, no API key, no market-data requests.

[快速开始](#快速开始) · [离线演示输出](#离线演示会生成什么) · [真实数据与日报](#接入真实数据) · [贡献指南](CONTRIBUTING.md) · [版本记录](CHANGELOG.md)

> 仅供学习和研究，不构成投资建议。演示结果来自合成数据，不能代表策略在真实市场的表现。项目不提供自动下单功能。

## 可以做什么

- **每日扫描**：按放量突破、趋势向好、超卖反弹等规则筛选候选股，生成文本日报并保存历史记录到 SQLite。
- **可选 LLM 分析**：通过火山方舟或兼容接口，结合新闻、基本面和历史异动信息生成候选股解读。需要自行配置服务凭据，可能产生 API 费用。
- **历史推荐回顾**：检查此前记录的推荐结果，与独立的组合回测功能区分开来。
- **量化研究框架 `qf`**：因子计算 → 截面打分 → TopK 等权组合 → 周频调仓 → 导出净值、持仓和指标。
- **本地运行与部署**：提供 CLI、部署脚本和 Docker 配置。macOS 支持系统通知，其他平台记录通知日志。

## 快速开始

需要 Git 和 Python 3.9+。首次安装需要联网下载依赖。

### macOS / Linux

```bash
git clone https://github.com/oliverran/stock-daily-analyzer.git
cd stock-daily-analyzer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
stock-analyzer demo
```

### Windows PowerShell

以下命令直接使用虚拟环境中的程序，无需修改 PowerShell 执行策略：

```powershell
git clone https://github.com/oliverran/stock-daily-analyzer.git
cd stock-daily-analyzer
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\stock-analyzer.exe demo
```

无需复制 `.env`，也无需配置 LLM。完成后会看到：

```text
Synthetic data only. Not historical market data or investment advice.
Offline demo complete: 3 fictional symbols, 60 weekday observations.
reports/demo/equity.csv
reports/demo/holdings.csv
reports/demo/summary.json
```

Windows 输出的路径分隔符可能为 `\`。后续命令若提示找不到 `stock-analyzer`，请先激活虚拟环境，或继续使用 `.\.venv\Scripts\stock-analyzer.exe`。

## 离线演示会生成什么

演示调用项目现有的 `DailyBacktester`，使用 `DEMO_A`、`DEMO_B`、`DEMO_C` 三个虚构标的的 60 条工作日数据。价格公式固定，不访问行情、新闻或 LLM 服务，也不写入日报数据库。

- `equity.csv`：按日期记录的模拟净值。
- `holdings.csv`：每日组合权重，`__CASH__` 表示现金。因子历史不足时保持现金。
- `summary.json`：明确标注合成数据来源，记录参数、总收益、年化收益、Sharpe 和最大回撤。

默认输出到 `reports/demo/`。可以用表格软件打开 CSV，或指定新目录保留不同结果：

```bash
stock-analyzer demo --out reports/my-demo
```

重复运行会覆盖所选目录内的同名演示文件。演示使用普通工作日而非交易所日历；价格、费用和交易约束均为示例设置，指标只用于理解输出格式。

## 接入真实数据

离线演示通过后，再根据需要选择下面的功能。两者均依赖外部数据服务，可能遇到超时、限流或数据缺失。`self-check` 只检查模块能否导入，**不验证 API 凭据或行情可用性**。

```bash
stock-analyzer self-check
stock-analyzer --help
```

### 1. 日报扫描

```bash
stock-analyzer run-daily
```

默认使用 AkShare / yfinance 获取行情。未设置 LLM 凭据时会跳过 LLM 分析，仍可运行量化筛选。输出包括：

- `reports/report_YYYY-MM-DD.txt`：日报。
- `stock_analysis.db`：本地历史记录。
- `logs/`：运行日志。

以上路径位于源码目录。默认筛选规则见 [`config.py`](config.py) 和 [`strategies.py`](strategies.py)。首次运行没有历史推荐可验证是正常情况；完整市场扫描的耗时取决于数据服务响应。

**可选：启用 LLM**

复制 `.env.example` 为 `.env`，将占位值替换为你自己的凭据：

```ini
ARK_API_KEY=your_api_key_here
ARK_MODEL_ID=your_model_endpoint_id
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
LLM_DEBUG=0
```

`ARK_MODEL_ID` 应填写你的服务可用的模型 / 推理接入点 ID。`ARK_BASE_URL` 是完整的 chat completions 地址。仅复制示例而不替换占位值会触发无效的 LLM 请求；不需要 LLM 时不要设置这些凭据。

`.env` 已被 Git 忽略。不要在 Issue、日志片段或提交中粘贴 API Key。使用其他兼容服务时需自行验证接口兼容性。

### 2. 组合回测

检查并调整 [`experiments/default_a_share_daily.json`](experiments/default_a_share_daily.json) 中的日期范围和股票池，再运行：

```bash
stock-analyzer backtest --config experiments/default_a_share_daily.json
```

也支持原有脚本入口：

```bash
python run_experiment.py --config experiments/default_a_share_daily.json
```

输出位于 `reports/experiments/<experiment_name>/`，包含 `equity.csv`、`holdings.csv` 和 `summary.json`。关键参数：

- `universe`：股票代码前缀、ST 过滤、股票数量上限。
- `data`：行情提供方、缓存目录、请求超时。
- `factors`：回看窗口与因子权重。
- `portfolio`：TopK 数量、单票权重上限。
- `trading`：简化的停牌、涨跌停、T+1 和印花税假设。
- `backtest`：日期区间、调仓频率、佣金、滑点、初始资金。

**研究边界**：在线实验使用运行时取得的股票池，不是历史时点股票池，存在幸存者偏差风险。交易约束和成本模型是简化实现，不应直接用于推断实盘收益；需要自行检查数据完整性、复权方式、成交假设及适用市场规则。离线演示也不能验证在线行情或 LLM 服务。

## 常见问题

- **找不到 `stock-analyzer`**：确认已在项目目录执行 `python -m pip install -e .`，且正在使用对应的虚拟环境。也可运行 `python -m qf.cli demo`。
- **`IMPORT_OK`，但在线运行失败**：自检只验证导入。先查看 `logs/`，检查网络、数据源响应及凭据；用 `stock-analyzer demo` 区分本地安装问题和外部服务问题。
- **日报没有候选股 / 没有历史回顾**：可能是筛选条件未命中、数据缺失或尚无历史记录，请结合日志判断，空结果不等于成功验证了全部数据源。
- **没有桌面通知**：非 macOS 平台会记录通知日志，不弹出系统通知。

## 开发与贡献

在已激活的虚拟环境中运行：

```bash
python -m pip install -e ".[dev]"
ruff check .
pytest -q
```

测试与演示不需要真实市场请求或 API Key。贡献方式见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全问题见 [SECURITY.md](SECURITY.md)。反馈运行问题时，请附上操作系统、Python 版本、执行命令和去除敏感信息后的错误信息。

如果这个项目对你的研究有帮助，欢迎点 Star，或分享你复现时发现的问题。请勿将合成演示指标当作真实业绩传播。

## 部署与项目结构

先在本地验证所需的在线流程，再配置定时运行：

- [快速部署指南](QUICK_DEPLOY.md)
- [完整部署文档](DEPLOYMENT.md)
- [`deploy/`](deploy/)：systemd、Supervisor、Docker 和定时任务示例。

主要代码：

```text
qf/                 因子、打分、组合、回测、离线演示和 CLI
experiments/        在线实验配置
tests/             单元测试与离线冒烟测试
analyzer.py         日报量化筛选
llm.py              可选 LLM 分析
attribution.py      历史异动检测与归因
backtester.py       历史推荐回顾
reporting.py        日报生成
config.py           日报参数
```

## 许可证

[MIT](LICENSE)。本项目仅供学习和研究使用，不构成任何投资建议。
