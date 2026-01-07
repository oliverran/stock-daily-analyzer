# Stock Daily Analyzer - Web Service

这是一个基于 FastAPI 和 React 的现代化 Web 界面，用于可视化运行 A 股分析工具。

## 功能特性

*   **可视化控制台**: 实时展示后端分析日志（SSE流式传输），清晰呈现思考过程。
*   **交互式仪表盘**:
    *   **LLM 智能精选**: 卡片式展示大模型推荐的最优标的及深度理由。
    *   **今日推荐**: 表格化展示各策略选出的股票及核心指标。
    *   **历史回测**: 图形化展示准确率、收益率及胜负分布。

## 快速开始

### 1. 启动后端服务

确保您已在项目根目录下，并安装了依赖：

```bash
pip install fastapi uvicorn sse-starlette
```

运行启动脚本：

```bash
python3 server.py
```

服务将运行在 `http://localhost:8000`。

### 2. 启动前端页面

进入 `web` 目录并启动开发服务器：

```bash
cd web
npm run dev
```

浏览器访问 `http://localhost:5173` 即可看到界面。

## API 接口说明

*   `POST /api/analyze`: 触发后台分析任务。
*   `GET /api/stream`: 获取实时日志流 (Server-Sent Events)。
*   `GET /api/latest-report`: 获取最近一次分析的完整结果 (JSON)。

## 开发说明

*   后端逻辑位于 `service_runner.py` (业务逻辑封装) 和 `server.py` (API 定义)。
*   前端代码位于 `web/src/App.jsx`。
