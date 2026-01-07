import asyncio
import logging
import json
import queue
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

# 导入原有逻辑
from database import init_database, save_recommendations, get_overall_accuracy
from analyzer import run_daily_analysis
from backtester import run_backtest
from llm import llm_enabled, select_top_picks
from notifier import send_analysis_complete_notification
from config import BACKTEST_DAYS

# 创建一个全局的队列用于日志流
log_queue = queue.Queue()

class QueueHandler(logging.Handler):
    """自定义日志处理器，将日志放入队列"""
    def emit(self, record):
        try:
            msg = self.format(record)
            log_queue.put(msg)
        except Exception:
            self.handleError(record)

def setup_service_logging():
    """配置服务日志，添加 QueueHandler"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 避免重复添加 Handler
    for h in logger.handlers:
        if isinstance(h, QueueHandler):
            return logger
            
    queue_handler = QueueHandler()
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    queue_handler.setFormatter(formatter)
    logger.addHandler(queue_handler)
    return logger

class CustomJSONEncoder(json.JSONEncoder):
    """自定义 JSON 编码器，处理 DataFrame 和 numpy 类型"""
    def default(self, obj):
        # 优先处理 Pandas/Numpy 类型
        if isinstance(obj, (pd.DataFrame, pd.Series)):
            return obj.to_dict(orient='records')
        
        # 处理整数
        if isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
            
        # 处理浮点数 (包括 Python 原生 float 和 Numpy float)
        # 注意: 必须显式检查 float 类型，因为 json.dumps 默认不会将 float 传给 default 方法
        # 但如果是 np.float64 等类型，json.dumps 无法处理，会传给 default
        # 对于包含在 dict/list 中的原生 float('nan')，json.dumps 默认会输出 NaN，不符合 JSON 标准
        # 因此我们需要在调用 json.dumps 时设置 allow_nan=False 强制报错，或者自己清洗数据
        if isinstance(obj, (np.floating, np.float64, np.float32, float)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
            
        if isinstance(obj, np.ndarray):
            return obj.tolist()
            
        return super().default(obj)

# 辅助函数：递归清洗数据中的 NaN/Inf
def clean_data_for_json(data):
    if isinstance(data, dict):
        return {k: clean_data_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data_for_json(v) for v in data]
    elif isinstance(data, float):
        if np.isnan(data) or np.isinf(data):
            return None
        return data
    elif isinstance(data, (np.floating, np.float64, np.float32)):
         if np.isnan(data) or np.isinf(data):
            return None
         return float(data)
    elif isinstance(data, (np.integer, np.int64, np.int32)):
        return int(data)
    elif isinstance(data, np.ndarray):
        return clean_data_for_json(data.tolist())
    return data

async def run_analysis_service() -> Dict[str, Any]:
    """
    运行全流程分析并返回结构化数据
    (基于 main.py 改造，支持异步调用)
    """
    logger = setup_service_logging()
    logger.info("=" * 50)
    logger.info("WEB服务: 开始每日股票分析任务")
    logger.info("=" * 50)

    result_data = {
        "status": "failed",
        "backtest": None,
        "summary": None,
        "llm_picks": None,
        "timestamp": None
    }

    try:
        # 1. 初始化数据库
        init_database()
        logger.info("数据库初始化完成")
        await asyncio.sleep(0.1) # 让出时间片以便日志发送

        # 2. 运行回测
        logger.info(f"开始回测验证{BACKTEST_DAYS}天前的推荐...")
        backtest_result, _ = run_backtest()
        if backtest_result:
            logger.info(f"回测完成: 准确率 {backtest_result['accuracy_rate']:.0%}")
        else:
            logger.info("暂无历史数据可回测")
        
        # 序列化回测结果
        if backtest_result:
             # 先转 JSON 字符串处理 Numpy 类型，再反序列化，最后递归清洗 NaN
             temp_json = json.dumps(backtest_result, cls=CustomJSONEncoder)
             result_data["backtest"] = clean_data_for_json(json.loads(temp_json))
        else:
             result_data["backtest"] = None
             
        await asyncio.sleep(0.1)

        # 3. 运行今日分析
        logger.info("开始今日市场分析...")
        # run_daily_analysis 内部可能有耗时操作，但在 Web 服务中我们暂时同步运行
        # 如果非常耗时，应考虑放到 thread pool 中运行
        recommendations, summary = run_daily_analysis()
        logger.info(f"分析完成: 扫描{summary.get('total_scanned', 0)}只股票")
        
        # 序列化分析结果
        if summary:
             temp_json = json.dumps(summary, cls=CustomJSONEncoder)
             result_data["summary"] = clean_data_for_json(json.loads(temp_json))
        else:
             result_data["summary"] = None
             
        await asyncio.sleep(0.1)

        # 3.5 LLM智能精选
        llm_picks = {}
        if llm_enabled():
            logger.info("调用LLM生成类型内首选...")
            # select_top_picks 涉及网络请求
            llm_picks = select_top_picks(summary.get('recommendations', {}))
            if llm_picks:
                logger.info(f"LLM精选完成: {list(llm_picks.keys())}")
            else:
                logger.info("LLM未返回精选结果")
        
        # 序列化 LLM 结果
        temp_json = json.dumps(llm_picks, cls=CustomJSONEncoder)
        result_data["llm_picks"] = clean_data_for_json(json.loads(temp_json))
        await asyncio.sleep(0.1)

        # 4. 保存推荐到数据库
        if recommendations:
            saved_count = save_recommendations(recommendations)
            logger.info(f"保存{saved_count}条推荐记录")

        # 5. 标记成功
        result_data["status"] = "success"
        import datetime
        result_data["timestamp"] = datetime.datetime.now().isoformat()
        
        logger.info("每日分析任务全部完成!")
        # 强制将整个结果再进行一次彻底的 JSON 序列化/反序列化，确保无残留的复杂对象
        # 使用 clean_data_for_json 确保最终结果中没有 NaN
        return clean_data_for_json(result_data)

    except Exception as e:
        logger.error(f"分析过程出错: {e}", exc_info=True)
        result_data["error"] = str(e)
        return result_data
