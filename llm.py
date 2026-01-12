import os
import json
from typing import Dict, List, Optional
import yfinance as yf
import akshare as ak
import requests
import numpy as np
from config import get_yfinance_ticker
from attribution import detect_abnormal_movements, format_movements_for_llm


def _clean_env(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    return v.strip()


import logging

# 获取 logger
logger = logging.getLogger(__name__)

def llm_enabled() -> bool:
    key = _clean_env(os.environ.get("ARK_API_KEY") or os.environ.get("VOLC_API_KEY"))
    model = _clean_env(os.environ.get("ARK_MODEL_ID") or os.environ.get("VOLC_MODEL_ID"))
    return bool(key and model)


def _to_jsonable(v):
    if v is None:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        try:
            if np.isnan(v):
                return None
        except Exception:
            pass
        return float(v)
    return v


def get_stock_news_safe(code: str, limit: int = 3) -> List[str]:
    """
    Safely fetch stock news using akshare with error handling.
    
    Args:
        code: 6-digit stock code (e.g., "600519")
        limit: Number of news headlines to return
    
    Returns:
        List of news titles
    """
    try:
        # akshare expects a 6-digit code for this function
        # Ensure code is a string of 6 digits, remove suffix if any
        code_str = str(code)
        clean_code = code_str.split(".")[0] if "." in code_str else code_str
        
        # Fetch news dataframe
        news_df = ak.stock_news_em(symbol=clean_code)
        
        if news_df is None or news_df.empty:
            return []
            
        # Extract titles, taking the most recent ones
        # Use .get to avoid KeyError if column name changes
        titles = news_df.get('新闻标题')
        if titles is None:
             return []
        
        return titles.tolist()[:limit]
        
    except Exception:
        # Silently fail as this is optional context
        return []


def _gather_stock_context(stock: Dict) -> Dict:
    ticker = get_yfinance_ticker(stock["code"])
    stock_name = stock.get("name", "Unknown")
    meta = {}
    
    # 1. Fetch news from akshare (preferred for A-shares)
    # 增加获取数量以便筛选 (从 3 增加到 10)
    raw_news = get_stock_news_safe(stock["code"], limit=10)
    
    # 2. LLM 智能筛选新闻 (Top 3)
    if llm_enabled() and raw_news:
        news_titles = _filter_news_with_llm(stock_name, raw_news)
    else:
        news_titles = raw_news[:3]

    # 3. 历史股价异动检测与归因
    attribution_summary = "无历史归因信息"
    if llm_enabled():
        # 检测异动
        movements = detect_abnormal_movements(stock["code"], days=90)
        movements_desc = format_movements_for_llm(movements)
        # 生成归因总结
        attribution_summary = _summarize_attribution_with_llm(stock_name, movements_desc, raw_news)

    # 4. Fetch other meta info from yfinance
    try:
        t = yf.Ticker(ticker)
        fi = getattr(t, "fast_info", None)
        if fi:
            meta["market_cap"] = getattr(fi, "market_cap", None)
            meta["pe_ratio"] = getattr(fi, "trailing_pe", None)
            meta["dividend_yield"] = getattr(fi, "dividend_yield", None)
        info = getattr(t, "info", {}) or {}
        sector = info.get("sector")
        industry = info.get("industry")
        if sector:
            meta["sector"] = sector
        if industry:
            meta["industry"] = industry
    except Exception:
        pass

    return {
        "code": _to_jsonable(stock.get("code")),
        "name": _to_jsonable(stock.get("name")),
        "ticker": _to_jsonable(ticker),
        "price": _to_jsonable(stock.get("price")),
        "rsi": _to_jsonable(stock.get("rsi")),
        "weekly_change": _to_jsonable(stock.get("weekly_change")),
        "daily_change": _to_jsonable(stock.get("daily_change")),
        "vol_ratio": _to_jsonable(stock.get("vol_ratio")),
        "macd_golden_cross": _to_jsonable(stock.get("macd_golden_cross")),
        "ma_bullish": _to_jsonable(stock.get("ma_bullish")),
        "meta": {k: _to_jsonable(v) for k, v in meta.items()},
        "news": news_titles,
        "history_attribution": attribution_summary,
    }


def _build_prompt(rec_type: str, contexts: List[Dict]) -> str:
    safe_contexts = []
    for c in contexts:
        safe_contexts.append({k: _to_jsonable(v) if k != "meta" else {mk: _to_jsonable(mv) for mk, mv in v.items()} for k, v in c.items()})
    return (
        "你是资深交易助理。给定同一类型的候选股票，请综合以下三个维度进行深度分析，选择一只最值得买入的股票：\n"
        "1. **量化信号**：分析RSI、MACD、均线形态、量比等技术指标的有效性。\n"
        "2. **异动归因**：参考'history_attribution'字段，评估该股的历史股性、主力资金意图及上涨逻辑的持续性。\n"
        "3. **市场情绪**：结合新闻资讯，判断当前是否有明确的宏观或行业利好催化。\n\n"
        "请给出简洁、逻辑严密且具有可操作性的推荐理由。必须输出JSON格式："
        '{"ticker":"...", "name":"...", "reason":"..."}。'
        f"\n选股策略类型:{rec_type}。\n候选股票池:{json.dumps(safe_contexts, ensure_ascii=False)}"
    )


def _call_ark(prompt: str) -> Optional[Dict]:
    api_key = _clean_env(os.environ.get("ARK_API_KEY") or os.environ.get("VOLC_API_KEY"))
    model_id = _clean_env(os.environ.get("ARK_MODEL_ID") or os.environ.get("VOLC_MODEL_ID"))
    base_url = _clean_env(os.environ.get("ARK_BASE_URL")) or "https://ark.cn-beijing.volces.com/api/v3/chat/completions"
    if not api_key or not model_id:
        return None
    
    if os.environ.get("LLM_DEBUG") == "1":
        key_len = len(api_key)
        prefix_ok = api_key.lower().startswith("ak-")
        logger.info(f"ARK_ENV_CHECK key_len={key_len}, prefix_ok={prefix_ok}, model_id={model_id}, base_url={base_url}")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": "输出仅限JSON。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 800,
        "response_format": {"type": "json_object"},
    }
    
    # 记录发送给 LLM 的 Prompt (截取前500字符以防过长)
    logger.info(f"LLM_REQUEST_PROMPT_PREVIEW: {prompt[:500]}...")
    if os.environ.get("LLM_DEBUG") == "1":
        logger.info(f"LLM_FULL_PROMPT: {prompt}")

    try:
        # Increase timeout to 60s to avoid ReadTimeout on complex queries
        resp = requests.post(base_url, headers=headers, data=json.dumps(payload), timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        # 记录 LLM 的原始响应
        if os.environ.get("LLM_DEBUG") == "1":
            logger.info(f"ARK_RAW_RESPONSE={json.dumps(data, ensure_ascii=False)[:2000]}")
            
        choices = data.get("choices") or data.get("data", {}).get("choices") or []
        if not choices:
            logger.warning("LLM returned no choices")
            return None
            
        content = (
            choices[0].get("message", {}).get("content")
            or choices[0].get("content")
            or ""
        )
        content = content.strip()
        
        # 记录 LLM 返回的内容
        logger.info(f"LLM_RESPONSE_CONTENT: {content}")
        
        if content.startswith("```"):
            try:
                fence_start = content.find("{")
                fence_end = content.rfind("}")
                if fence_start != -1 and fence_end != -1 and fence_end > fence_start:
                    content = content[fence_start : fence_end + 1]
            except Exception:
                pass
        try:
            parsed = json.loads(content)
        except Exception:
            start = content.find("{")
            end = content.rfind("}")
            if start != -1 and end != -1 and end > start:
                parsed = json.loads(content[start : end + 1])
            else:
                logger.error(f"Failed to parse LLM JSON: {content}")
                return None
        return parsed
             
    except requests.RequestException as e:
        logger.error(f"ARK_HTTP_ERROR: {e}")
        if os.environ.get("LLM_DEBUG") == "1":
            try:
                if e.response is not None:
                    logger.error(f"ARK_HTTP_STATUS={e.response.status_code}")
                    body = e.response.text or ""
                    logger.error(f"ARK_HTTP_BODY={body[:1000]}")
            except Exception:
                pass
        return None
    except Exception as e:
        logger.error(f"ARK_GENERIC_ERROR: {e}")
        return None
    return None


def _filter_news_with_llm(stock_name: str, news_list: List[str]) -> List[str]:
    """
    使用 LLM 对新闻进行筛选，选出 Top 3
    """
    if not news_list:
        return []
        
    prompt = (
        f"你是金融助手。请从以下关于【{stock_name}】的新闻中，筛选出对股价影响最大、时效性最强、相关性最高的 3 条新闻。"
        "请对选出的新闻进行一句话概括。必须输出JSON格式：{\"top_news\": [\"概括1\", \"概括2\", \"概括3\"]}"
        f"\n新闻列表：\n{json.dumps(news_list, ensure_ascii=False)}"
    )
    
    result = _call_ark(prompt)
    if result and "top_news" in result and isinstance(result["top_news"], list):
        return result["top_news"]
    
    # 如果调用失败或格式不对，回退到取前3条
    return news_list[:3]


def _summarize_attribution_with_llm(stock_name: str, movements_desc: str, news_list: List[str]) -> str:
    """
    使用 LLM 生成历史归因总结
    """
    if "无显著股价异动" in movements_desc:
        return "近期股价波动较小，无显著历史异动。"
        
    prompt = (
        f"你是金融分析师。股票【{stock_name}】{movements_desc}"
        f"结合以下近期新闻（作为参考）：{json.dumps(news_list[:5], ensure_ascii=False)}。"
        "请从宏观、行业、个股三个维度，简要分析上述历史异动的原因（如果新闻不足以解释历史，请基于一般性的技术面或行业逻辑进行推测）。"
        "必须输出JSON格式：{\"summary\": \"归因总结...\"}"
    )
    
    result = _call_ark(prompt)
    if result and "summary" in result:
        return result["summary"]
    
    return "无法生成归因总结。"


def _fallback_pick(rec_type: str, contexts: List[Dict]) -> Optional[Dict]:
    if not contexts:
        return None
    def safe(v, default=0.0):
        return v if isinstance(v, (int, float)) else default
    def headlines(c):
        ns = c.get("news") or []
        return " | ".join(ns[:2]) if ns else ""
    pick = contexts[0]
    if rec_type == "放量突破":
        pick = sorted(contexts, key=lambda c: (safe(c.get("daily_change")), safe(c.get("vol_ratio"))), reverse=True)[0]
        h = headlines(pick)
        reason = f"规则回退: 日涨幅{safe(pick.get('daily_change')):.2%}, 量比{safe(pick.get('vol_ratio')):.2f}" + (f"; 新闻: {h}" if h else "")
    elif rec_type == "趋势向好":
        pick = sorted(contexts, key=lambda c: (bool(c.get("ma_bullish")), safe(c.get("weekly_change"))), reverse=True)[0]
        h = headlines(pick)
        reason = f"规则回退: 均线多头, 周涨幅{safe(pick.get('weekly_change')):.2%}" + (f"; 新闻: {h}" if h else "")
    elif rec_type == "超卖反弹":
        pick = sorted(contexts, key=lambda c: (not bool(c.get("macd_golden_cross")), safe(c.get("rsi"))))[0]
        h = headlines(pick)
        reason = f"规则回退: RSI{safe(pick.get('rsi')):.0f}偏低, MACD向好" + (f"; 新闻: {h}" if h else "")
    else:
        reason = "规则回退: 综合信号最优"
    return {"ticker": pick.get("ticker"), "name": pick.get("name"), "reason": reason}


def select_top_picks(recommendations_by_type: Dict[str, List[Dict]]) -> Dict[str, Dict]:
    if not llm_enabled():
        return {}
    result: Dict[str, Dict] = {}
    for rec_type, stocks in recommendations_by_type.items():
        if not stocks:
            continue
        contexts = [_gather_stock_context(s) for s in stocks]
        prompt = _build_prompt(rec_type, contexts)
        best = _call_ark(prompt)
        if best:
            result[rec_type] = best
        else:
            fallback = _fallback_pick(rec_type, contexts)
            if fallback:
                result[rec_type] = fallback
    return result
