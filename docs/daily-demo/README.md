# 研究日报样例 · 合成数据

[中文](README.md) | [English](README.en.md) | [项目首页](https://github.com/oliverran/stock-daily-analyzer/blob/main/README.md)

这份日报由项目现有的**技术指标计算 → 规则筛选 → 文本日报生成器**实际执行得到，
输入是虚构行情，不是当前市场日报。不是手写推荐，也没有伪造模型解读。

**数据来源：** [`qf/daily_demo.py`](https://github.com/oliverran/stock-daily-analyzer/blob/main/qf/daily_demo.py) 中的固定公式。
4 个虚构标的，各 80 条普通工作日观察，日期为 **2024-01-01 至 2024-04-19**。
报告日期固定为最后一条输入日期，不是运行当天。普通工作日不等于交易所交易日。
这些人工构造的价格用于展示分类，不用于证明筛选规则在真实市场有效。

## 直接看结果

原有日报生成器将候选股称为“推荐”，本页所有标的均为虚构。
没有读取历史推荐数据库，因此不编造准确率或收益；没有调用 LLM，因此不展示虚构的
“智能精选”。本样例不运行组合回测，也不会下单。量比采用当前成交量除以包含当日的
20 条观察平均成交量，和现有分析器保持一致。

```text
SYNTHETIC DAILY REPORT / 合成数据日报示例。Not live market data or investment advice. 不是实时行情、真实荐股或收益记录。
Source / 来源: qf/daily_demo.py; deterministic_synthetic; 2024-01-01..2024-04-19.
日期为固定样本日期，不是今日行情。无历史收益记录，无 LLM 解读。

============================================================
股票分析日报 - 2024-04-19
============================================================

【历史回测】
  暂无历史数据可回测

【今日推荐】
  扫描股票数: 4

  类型: 超卖反弹
    - 虚构样本 A(DEMO_A): ¥20.00 | RSI:44 | 量比:2.33

  类型: 趋势向好
    - 虚构样本 B(DEMO_B): ¥20.12 | RSI:56 | 量比:2.33

  类型: 放量突破
    - 虚构样本 C(DEMO_C): ¥20.38 | RSI:52 | 量比:2.33

============================================================
风险提示: 以上分析仅供参考，不构成投资建议。股市有风险，投资需谨慎。
============================================================
```

## 安装后复现

在仓库根目录完成[安装步骤](https://github.com/oliverran/stock-daily-analyzer/blob/main/README.md#快速开始)后运行：

```bash
stock-analyzer demo-daily --out reports/daily-demo
```

Windows 未激活虚拟环境时，使用 `.\.venv\Scripts\stock-analyzer.exe`。
用文本编辑器打开 `reports/daily-demo/daily-report.txt` 即可查看。
命令不请求行情、新闻或模型服务，也不写入日报数据库。重复运行会覆盖所选目录内
下列 5 个同名文件，需要保留旧结果时请换一个输出目录。

- [daily-report.txt](daily-report.txt)：带明确合成数据声明的实际日报输出。
- [inputs.csv](inputs.csv)：全部 320 条虚构收盘价和成交量输入。
- [analysis.json](analysis.json)：来源、日期、输入 SHA-256、参数、实际计算的
  指标、筛选分类和格式化候选记录。
- [README.md](README.md) 与 [README.en.md](README.en.md)：自动生成的中英文阅读说明。

更新仓库预览：`python scripts/update_daily_preview.py`。测试会重新生成并逐个核对文件。
所用生产代码见 [`analyzer.py`](https://github.com/oliverran/stock-daily-analyzer/blob/main/analyzer.py)、[`strategies.py`](https://github.com/oliverran/stock-daily-analyzer/blob/main/strategies.py)
和 [`reporting.py`](https://github.com/oliverran/stock-daily-analyzer/blob/main/reporting.py)。

[组合回测演示](https://github.com/oliverran/stock-daily-analyzer/blob/main/docs/demo/README.md)属于另一个流程。接入真实行情前请阅读
[`stock-analyzer run-daily` 的配置与研究边界](https://github.com/oliverran/stock-daily-analyzer/blob/main/README.md#接入真实数据)。
离线演示通过不代表在线服务可用，也不能验证信号的投资价值。
