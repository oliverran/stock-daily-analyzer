我将为您创建一个全栈 Web 服务，让您可以直观地查看分析过程和结果。

### 1. 创建新分支
- 创建并切换到 `feature/web-ui-service` 分支。

### 2. 后端服务开发 (Python/FastAPI)
- **依赖**: 引入 `fastapi`, `uvicorn`, `sse-starlette` (用于实时日志推送)。
- **核心改造**:
    - 将 `main.py` 的全流程逻辑提取为 `ServiceRunner` 类。
    - 拦截 Python 的 `logging`，通过 Queue 实现 SSE 实时推送到前端。
    - 改造 `generate_report` 逻辑，使其返回结构化的 JSON 数据（包括回测数据、今日推荐列表、LLM 精选结果）。
- **API 接口**:
    - `POST /api/analyze`: 触发异步分析任务。
    - `GET /api/stream`: 建立 SSE 连接，实时接收分析日志。
    - `GET /api/latest-report`: 获取最新的分析结果（JSON 格式）。

### 3. 前端页面开发 (React + Tailwind)
- **初始化**: 在项目根目录下创建 `web` 目录，初始化一个轻量级的 React 项目。
- **界面设计**:
    - **顶部**: 标题栏与“开始分析”按钮。
    - **左侧/上方**: 实时日志控制台（Console），黑底绿字，展示后端推送的思考过程。
    - **右侧/下方**: 结果展示面板，包含三个 Tab 或卡片：
        1.  **历史回测**: 展示准确率、收益率等核心指标。
        2.  **今日推荐**: 表格展示各策略筛选出的股票（价格、RSI、量比）。
        3.  **LLM 智能精选**: 重点展示，包含股票名称、推荐理由（Markdown 渲染）。

### 4. 整合与运行
- 编写 `start_service.py` 脚本，一键启动后端 API 服务。
- 编写 `README_WEB.md` 说明如何启动前端和后端。

这个方案将把您的命令行工具升级为一个现代化的 Web 应用，既保留了核心的分析能力，又提供了更好的交互体验。
