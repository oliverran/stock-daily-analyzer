import asyncio
import json
import logging
from typing import Dict
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from service_runner import run_analysis_service, log_queue, setup_service_logging

# 初始化日志配置
setup_service_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Stock Daily Analyzer API")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局变量存储最新的分析结果
latest_result = {}

@app.get("/")
async def root():
    return {"message": "Stock Analyzer Service is Running"}

@app.post("/api/analyze")
async def start_analysis():
    """触发分析任务 (异步运行)"""
    logger.info("收到分析请求，启动后台任务...")
    
    # 清空之前的日志队列 (可选)
    while not log_queue.empty():
        log_queue.get()
        
    # 异步运行分析
    asyncio.create_task(run_analysis_task())
    return {"status": "started", "message": "Analysis task started"}

async def run_analysis_task():
    """后台运行分析并更新结果"""
    global latest_result
    result = await run_analysis_service()
    latest_result = result
    # 发送一个特殊的日志消息表示结束
    log_queue.put("Done")

@app.get("/api/stream")
async def stream_logs(request: Request):
    """SSE 接口：实时推送日志"""
    async def event_generator():
        try:
            # 发送连接成功消息
            yield {"event": "log", "data": "正在连接日志流..."}
            
            while True:
                # 如果客户端断开连接，停止生成
                if await request.is_disconnected():
                    logger.info("Client disconnected from stream")
                    break
                    
                # 非阻塞获取日志
                while not log_queue.empty():
                    msg = log_queue.get_nowait()
                    if msg == "Done":
                        yield {"event": "status", "data": "finished"}
                    else:
                        yield {"event": "log", "data": msg}
                
                # 发送心跳注释，防止连接因空闲超时
                yield {"comment": "ping"}
                # 缩短 sleep 时间，提高响应速度，减少超时风险
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
             logger.info("Stream cancelled")
        except Exception as e:
            logger.error(f"Stream error: {e}")

    # 禁用各种超时限制
    return EventSourceResponse(
        event_generator(),
        ping=15,  # sse-starlette 内置 ping 间隔
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" # 禁用 Nginx 缓冲（如果存在）
        }
    )

@app.get("/api/latest-report")
async def get_latest_report():
    """获取最新的分析结果"""
    return latest_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
