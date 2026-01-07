"""
Stock Daily Analyzer - Core Analysis Module
支持全市场A股扫描（除创业板外）
"""
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import yfinance as yf
import akshare as ak
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import logging

from config import (
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT, RSI_OVERSOLD_SCREEN,
    MACD_FAST, MACD_SLOW, MACD_SIGNAL,
    BOLLINGER_PERIOD, BOLLINGER_STD, MA_PERIODS,
    DATA_PERIOD, DATA_TIMEOUT, SECTOR_STOCKS,
    MAX_RECOMMENDATIONS_PER_TYPE, MIN_VOLUME_RATIO,
    get_yfinance_ticker, is_valid_stock
)

logger = logging.getLogger(__name__)

class StockAnalyzer:
    """A股市场分析器"""

    def __init__(self):
        self.stock_list = []
        self.analysis_date = date.today()

    def get_all_stocks(self) -> List[Tuple[str, str]]:
        """获取所有A股股票列表（除创业板外）"""
        try:
            # 使用akshare获取A股列表
            df = ak.stock_zh_a_spot_em()
            stocks = []
            for _, row in df.iterrows():
                code = row['代码']
                name = row['名称']
                # 过滤创业板和ST股票
                if is_valid_stock(code) and 'ST' not in name:
                    stocks.append((code, name))
            logger.info(f"获取到 {len(stocks)} 只有效股票（排除创业板和ST）")
            return stocks
        except Exception as e:
            logger.error(f"获取股票列表失败: {e}")
            # 降级使用配置的热门股票
            return self._get_sector_stocks()

    def _get_sector_stocks(self) -> List[Tuple[str, str]]:
        """从配置获取板块股票"""
        stocks = []
        for sector, codes in SECTOR_STOCKS.items():
            for code in codes:
                stocks.append((code, f"{sector}股票"))
        return stocks

    def fetch_stock_data(self, code: str, period: str = DATA_PERIOD) -> Optional[pd.DataFrame]:
        """获取单只股票数据"""
        try:
            ticker = get_yfinance_ticker(code)
            stock = yf.Ticker(ticker)
            data = stock.history(period=period, timeout=DATA_TIMEOUT)
            if data.empty or len(data) < 20:
                return None
            return data
        except Exception as e:
            return None

    def calculate_rsi(self, prices: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_macd(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算MACD指标"""
        ema_fast = prices.ewm(span=MACD_FAST, adjust=False).mean()
        ema_slow = prices.ewm(span=MACD_SLOW, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=MACD_SIGNAL, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def calculate_bollinger(self, prices: pd.Series) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """计算布林带"""
        middle = prices.rolling(window=BOLLINGER_PERIOD).mean()
        std = prices.rolling(window=BOLLINGER_PERIOD).std()
        upper = middle + (std * BOLLINGER_STD)
        lower = middle - (std * BOLLINGER_STD)
        return upper, middle, lower

    def analyze_single_stock(self, code: str, name: str) -> Optional[Dict]:
        """分析单只股票"""
        data = self.fetch_stock_data(code)
        if data is None:
            return None

        try:
            close = data['Close']
            volume = data['Volume']

            current_price = close.iloc[-1]
            prev_close = close.iloc[-2]
            daily_change = (current_price - prev_close) / prev_close

            # RSI
            rsi = self.calculate_rsi(close)
            rsi_current = rsi.iloc[-1]

            # MACD
            macd_line, signal_line, histogram = self.calculate_macd(close)
            macd_current = macd_line.iloc[-1]
            signal_current = signal_line.iloc[-1]
            hist_current = histogram.iloc[-1]
            hist_prev = histogram.iloc[-2]

            # 判断MACD金叉/死叉
            macd_bullish = macd_current > signal_current
            macd_golden_cross = (macd_line.iloc[-2] <= signal_line.iloc[-2]) and macd_bullish
            macd_improving = hist_current > hist_prev

            # 布林带
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger(close)
            bb_upper_current = bb_upper.iloc[-1]
            bb_middle_current = bb_middle.iloc[-1]
            bb_lower_current = bb_lower.iloc[-1]

            # 均线
            ma_values = {}
            for period in MA_PERIODS:
                if len(close) >= period:
                    ma_values[f'ma{period}'] = close.rolling(window=period).mean().iloc[-1]

            # 均线多头排列
            ma_bullish = False
            if all(f'ma{p}' in ma_values for p in [5, 10, 20]):
                ma_bullish = ma_values['ma5'] > ma_values['ma10'] > ma_values['ma20']

            # 成交量
            vol_current = volume.iloc[-1]
            vol_avg = volume.rolling(window=20).mean().iloc[-1]
            vol_ratio = vol_current / vol_avg if vol_avg > 0 else 1

            # 周涨跌
            week_ago_price = close.iloc[-5] if len(close) >= 5 else close.iloc[0]
            weekly_change = (current_price - week_ago_price) / week_ago_price

            # 获取板块分类
            sector = self._get_sector(code)

            return {
                'code': code,
                'name': name,
                'sector': sector,
                'price': current_price,
                'daily_change': daily_change,
                'weekly_change': weekly_change,
                'rsi': rsi_current,
                'macd_bullish': macd_bullish,
                'macd_golden_cross': macd_golden_cross,
                'macd_improving': macd_improving,
                'ma_bullish': ma_bullish,
                'above_bb_mid': current_price > bb_middle_current,
                'below_bb_upper': current_price < bb_upper_current,
                'below_bb_lower': current_price < bb_lower_current,
                'vol_ratio': vol_ratio,
                'ma_values': ma_values,
            }
        except Exception as e:
            return None

    def _get_sector(self, code: str) -> str:
        """获取股票所属板块"""
        for sector, codes in SECTOR_STOCKS.items():
            if code in codes or code.replace(".SS", "").replace(".SZ", "") in codes:
                return sector
        return "其他"

    def scan_market(self, max_stocks: int = None) -> List[Dict]:
        """扫描全市场"""
        stocks = self.get_all_stocks()
        if max_stocks:
            stocks = stocks[:max_stocks]

        logger.info(f"开始扫描 {len(stocks)} 只股票...")
        results = []
        failed = 0

        # 使用线程池并行获取数据
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_stock = {
                executor.submit(self.analyze_single_stock, code, name): (code, name)
                for code, name in stocks
            }

            for i, future in enumerate(as_completed(future_to_stock)):
                code, name = future_to_stock[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                    else:
                        failed += 1
                except Exception as e:
                    failed += 1

                # 进度显示
                if (i + 1) % 100 == 0:
                    logger.info(f"进度: {i + 1}/{len(stocks)}, 成功: {len(results)}, 失败: {failed}")

        logger.info(f"扫描完成: 成功 {len(results)}, 失败 {failed}")
        return results

    def screen_oversold_rebound(self, stocks: List[Dict]) -> List[Dict]:
        """
        筛选类型A: 超卖反弹型
        条件: RSI < 45 且 MACD向好
        """
        candidates = [
            s for s in stocks
            if s['rsi'] < RSI_OVERSOLD_SCREEN
            and s['macd_bullish']
            and not np.isnan(s['rsi'])
        ]
        # 按RSI从低到高排序
        candidates.sort(key=lambda x: x['rsi'])
        return candidates[:MAX_RECOMMENDATIONS_PER_TYPE]

    def screen_trending_up(self, stocks: List[Dict]) -> List[Dict]:
        """
        筛选类型B: 趋势向好型
        条件: 均线多头排列 + MACD向好 + RSI在40-70之间
        """
        candidates = [
            s for s in stocks
            if s['ma_bullish']
            and s['macd_bullish']
            and 40 < s['rsi'] < 70
            and not np.isnan(s['rsi'])
        ]
        # 按周涨幅排序
        candidates.sort(key=lambda x: x['weekly_change'], reverse=True)
        return candidates[:MAX_RECOMMENDATIONS_PER_TYPE]

    def screen_volume_breakout(self, stocks: List[Dict]) -> List[Dict]:
        """
        筛选类型C: 放量突破型
        条件: 量比 > 1.5 且 日涨幅 > 1% 且 RSI < 75
        """
        candidates = [
            s for s in stocks
            if s['vol_ratio'] > MIN_VOLUME_RATIO
            and s['daily_change'] > 0.01
            and s['rsi'] < 75
            and not np.isnan(s['rsi'])
        ]
        # 按日涨幅排序
        candidates.sort(key=lambda x: x['daily_change'], reverse=True)
        return candidates[:MAX_RECOMMENDATIONS_PER_TYPE]

    def generate_recommendations(self, stocks: List[Dict]) -> Dict[str, List[Dict]]:
        """生成推荐列表"""
        return {
            '超卖反弹': self.screen_oversold_rebound(stocks),
            '趋势向好': self.screen_trending_up(stocks),
            '放量突破': self.screen_volume_breakout(stocks),
        }

    def format_recommendation(self, stock: Dict, rec_type: str) -> Dict:
        """格式化为数据库存储格式"""
        reasoning_parts = []

        if rec_type == '超卖反弹':
            reasoning_parts.append(f"RSI={stock['rsi']:.0f}处于超卖区")
            if stock['macd_golden_cross']:
                reasoning_parts.append("MACD金叉")
            elif stock['macd_bullish']:
                reasoning_parts.append("MACD多头")

        elif rec_type == '趋势向好':
            reasoning_parts.append("均线多头排列")
            reasoning_parts.append(f"RSI={stock['rsi']:.0f}适中")
            reasoning_parts.append(f"周涨幅{stock['weekly_change']:.1%}")

        elif rec_type == '放量突破':
            reasoning_parts.append(f"量比{stock['vol_ratio']:.2f}")
            reasoning_parts.append(f"日涨幅{stock['daily_change']:.1%}")

        # 置信度
        confidence = "中"
        if stock.get('macd_golden_cross'):
            confidence = "高"
        elif stock['rsi'] < 30 or stock['rsi'] > 70:
            confidence = "高" if rec_type == '超卖反弹' else "低"

        return {
            'date': self.analysis_date.isoformat(),
            'ticker': get_yfinance_ticker(stock['code']),
            'name': stock['name'],
            'sector': stock['sector'],
            'recommendation_type': rec_type,
            'price': stock['price'],
            'rsi': stock['rsi'],
            'macd_signal': 'bullish' if stock['macd_bullish'] else 'bearish',
            'volume_ratio': stock['vol_ratio'],
            'confidence': confidence,
            'reasoning': '; '.join(reasoning_parts),
        }

    def run_analysis(self, max_stocks: int = None) -> Tuple[List[Dict], Dict]:
        """
        运行完整分析流程

        Returns:
            recommendations: 格式化的推荐列表（用于存储）
            summary: 分析摘要（用于显示）
        """
        logger.info(f"\n{'='*50}")
        logger.info(f"开始A股市场分析 - {self.analysis_date}")
        logger.info(f"{'='*50}\n")

        # 1. 扫描市场
        all_stocks = self.scan_market(max_stocks)

        if not all_stocks:
            logger.warning("未获取到任何股票数据")
            return [], {}

        # 2. 生成推荐
        recommendations_by_type = self.generate_recommendations(all_stocks)

        # 3. 格式化推荐
        all_recommendations = []
        for rec_type, stocks in recommendations_by_type.items():
            for stock in stocks:
                formatted = self.format_recommendation(stock, rec_type)
                all_recommendations.append(formatted)

        # 4. 生成摘要
        summary = {
            'date': self.analysis_date.isoformat(),
            'total_scanned': len(all_stocks),
            'recommendations': recommendations_by_type,
            'counts': {k: len(v) for k, v in recommendations_by_type.items()},
        }

        return all_recommendations, summary


def run_daily_analysis(max_stocks: int = None) -> Tuple[List[Dict], Dict]:
    """运行每日分析的便捷函数"""
    analyzer = StockAnalyzer()
    return analyzer.run_analysis(max_stocks)


if __name__ == "__main__":
    # 测试运行（限制股票数量以加快测试）
    recommendations, summary = run_daily_analysis(max_stocks=100)

    print(f"\n{'='*50}")
    print("分析结果摘要")
    print(f"{'='*50}")
    print(f"扫描股票数: {summary.get('total_scanned', 0)}")
    print(f"推荐数量: {summary.get('counts', {})}")

    for rec_type, stocks in summary.get('recommendations', {}).items():
        print(f"\n【{rec_type}】")
        for s in stocks[:3]:
            print(f"  {s['name']}({s['code']}): ¥{s['price']:.2f} RSI:{s['rsi']:.0f}")
