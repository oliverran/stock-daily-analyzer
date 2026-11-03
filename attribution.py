"""
Stock Daily Analyzer - Attribution Module
历史股价异动检测与归因分析
基于用户文档 "个股页长期股价异动AI归因Ready.docx" 实现简化逻辑
"""
import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import List, Dict
from config import get_yfinance_ticker

logger = logging.getLogger(__name__)

def detect_abnormal_movements(code: str, days: int = 90) -> List[Dict]:
    """
    检测个股在过去N天内的异动区间 (滑动窗口版)
    
    规则依据:
    1. 短期窗口 (10天):
       - 相对斜率 >= 1% (关注速度)
       - 相对斜率 = [(最高价 - 最低价) / 最低价] / 时间跨度 × 100%
       - 最高最低点之间 > 3个交易日
    
    2. 长期窗口 (90天):
       - 振幅 >= 20% (关注幅度)
       - 振幅 = (最高价 - 最低价) / 最低价 * 100%
       - 最高最低点之间 > 15个交易日
       
    Args:
        code: 股票代码
        days: 回溯天数 (默认90天用于长期窗口，同时也包含短期窗口的数据)
        
    Returns:
        List[Dict]: 异动区间列表
    """
    ticker = get_yfinance_ticker(code)
    try:
        # 获取足够长的历史数据 (90天 + 缓冲)
        start_date = (datetime.now() - timedelta(days=days + 20)).strftime('%Y-%m-%d')
        df = yf.download(ticker, start=start_date, progress=False)
        
        if df.empty or len(df) < 15:
            logger.warning(f"Insufficient history data for {code}")
            return []
            
        closes = df['Close']
        if isinstance(closes, pd.DataFrame):
            closes = closes.iloc[:, 0]
            
        movements = []
        
        # --- 长期窗口检测 (90天) ---
        # 简化处理：直接在整个days范围内寻找最大振幅，如果超过20%且时间跨度足够，则认定为长期异动
        # 这相当于一个固定的大窗口检测
        
        # 1. 长期振幅检测
        long_term_window = closes[-days:] if len(closes) > days else closes
        if len(long_term_window) > 15:
            l_max_idx = long_term_window.idxmax()
            l_min_idx = long_term_window.idxmin()
            l_max_val = long_term_window.max()
            l_min_val = long_term_window.min()
            
            # 计算振幅
            l_amplitude = (l_max_val - l_min_val) / l_min_val
            
            # 计算时间跨度 (交易日数量)
            # 获取索引位置
            l_p1 = long_term_window.index.get_loc(l_max_idx)
            l_p2 = long_term_window.index.get_loc(l_min_idx)
            l_span = abs(l_p1 - l_p2)
            
            if l_amplitude >= 0.20 and l_span > 15:
                # 确定方向
                if l_min_idx < l_max_idx:
                    m_type = "rise"
                    start, end = l_min_idx, l_max_idx
                else:
                    m_type = "fall"
                    start, end = l_max_idx, l_min_idx
                    
                movements.append({
                    "window": "long_term",
                    "type": m_type,
                    "start_date": start.strftime('%Y-%m-%d'),
                    "end_date": end.strftime('%Y-%m-%d'),
                    "amplitude": float(l_amplitude),
                    "days_span": int(l_span),
                    "desc": f"长期{('上涨' if m_type == 'rise' else '下跌')} (振幅{l_amplitude:.1%})"
                })

        # --- 短期窗口检测 (10天滑动) ---
        # 滑动窗口：从过去90天开始，每10天为一个窗口
        # 为了避免过多重叠，步长设为 5
        
        short_movements = []
        window_size = 10
        step = 5
        
        for i in range(0, len(closes) - window_size + 1, step):
            window = closes.iloc[i : i + window_size]
            
            w_max_idx = window.idxmax()
            w_min_idx = window.idxmin()
            w_max_val = window.max()
            w_min_val = window.min()
            
            w_p1 = window.index.get_loc(w_max_idx)
            w_p2 = window.index.get_loc(w_min_idx)
            w_span = abs(w_p1 - w_p2)
            
            if w_span > 3:
                # 相对斜率计算: [(最高 - 最低) / 最低] / 跨度
                # 注意：这里跨度是指两个极值点之间的交易日天数，而不是窗口大小
                slope = ((w_max_val - w_min_val) / w_min_val) / w_span
                
                if slope >= 0.01: # 斜率 >= 1%
                    if w_min_idx < w_max_idx:
                        m_type = "rise"
                        start, end = w_min_idx, w_max_idx
                    else:
                        m_type = "fall"
                        start, end = w_max_idx, w_min_idx
                    
                    # 避免重复：检查是否被包含在长期异动中
                    is_covered = False
                    for m in movements:
                        # 简单检查日期重叠
                        if m['start_date'] <= start.strftime('%Y-%m-%d') and m['end_date'] >= end.strftime('%Y-%m-%d'):
                            is_covered = True
                            break
                    
                    if not is_covered:
                         short_movements.append({
                            "window": "short_term",
                            "type": m_type,
                            "start_date": start.strftime('%Y-%m-%d'),
                            "end_date": end.strftime('%Y-%m-%d'),
                            "amplitude": float((w_max_val - w_min_val) / w_min_val),
                            "slope": float(slope),
                            "days_span": int(w_span),
                            "desc": f"短期快速{('拉升' if m_type == 'rise' else '下跌')} (日均斜率{slope:.1%})"
                        })
        
        # 合并结果
        movements.extend(short_movements)
        # 简单去重：如果多个短期异动非常接近，只保留最剧烈的
        # (这里暂略复杂去重逻辑，只按时间排序)
        movements.sort(key=lambda x: x['start_date'])
        
        return movements
        
    except Exception as e:
        logger.error(f"Error detecting movements for {code}: {e}")
        return []

def format_movements_for_llm(movements: List[Dict], limit: int = 5) -> str:
    """
    格式化异动信息供 LLM 使用
    
    Args:
        movements: 异动列表
        limit: 限制返回的最近异动数量，避免上下文过长
    """
    if not movements:
        return "近期（3个月内）无显著股价异动（长期振幅<20%且无短期剧烈波动）。"
    
    # 按结束时间倒序排列，取最近的N条
    sorted_movements = sorted(movements, key=lambda x: x['end_date'], reverse=True)
    recent_movements = sorted_movements[:limit]
    
    # 再次按时间正序排列，方便阅读
    recent_movements.sort(key=lambda x: x['start_date'])
        
    desc = f"近期股价异动记录（筛选最近{len(recent_movements)}次）：\n"
    for m in recent_movements:
        desc += f"- [{m['window']}] {m['start_date']} 至 {m['end_date']}: {m['desc']}\n"
    return desc
