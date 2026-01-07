"""
Stock Daily Analyzer - Backtest Module
回测验证历史推荐的准确性
"""
import warnings
warnings.filterwarnings('ignore')

import yfinance as yf
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple

from config import BACKTEST_DAYS, CORRECT_THRESHOLD, WRONG_THRESHOLD, DATA_TIMEOUT
from database import (
    get_recommendations_for_backtest,
    save_backtest_result,
    save_price_tracking,
    get_overall_accuracy
)

logger = logging.getLogger(__name__)


class Backtester:
    """回测验证器"""

    def __init__(self, days_ago: int = BACKTEST_DAYS):
        self.days_ago = days_ago
        self.today = date.today()
        self.backtest_date = self.today - timedelta(days=days_ago)

    def get_current_price(self, ticker: str) -> Optional[float]:
        """获取股票当前价格"""
        try:
            stock = yf.Ticker(ticker)
            data = stock.history(period="5d", timeout=DATA_TIMEOUT)
            if not data.empty:
                return data['Close'].iloc[-1]
        except Exception as e:
            pass
        return None

    def calculate_return(self, recommend_price: float, current_price: float) -> float:
        """计算收益率"""
        return (current_price - recommend_price) / recommend_price

    def evaluate_recommendation(self, rec: Dict) -> Dict:
        """评估单条推荐"""
        ticker = rec['ticker']
        recommend_price = rec['price_at_recommend']

        current_price = self.get_current_price(ticker)
        if current_price is None:
            return {
                'id': rec['id'],
                'ticker': ticker,
                'name': rec['name'],
                'recommend_price': recommend_price,
                'current_price': None,
                'return_pct': None,
                'result': 'unknown',
                'error': '无法获取当前价格'
            }

        return_pct = self.calculate_return(recommend_price, current_price)

        # 判断结果
        if return_pct > CORRECT_THRESHOLD:
            result = 'correct'
        elif return_pct < WRONG_THRESHOLD:
            result = 'wrong'
        else:
            result = 'neutral'

        # 保存价格跟踪
        try:
            save_price_tracking(
                recommendation_id=rec['id'],
                track_date=self.today,
                close_price=current_price,
                change_pct=return_pct
            )
        except Exception as e:
            pass

        return {
            'id': rec['id'],
            'ticker': ticker,
            'name': rec['name'],
            'sector': rec.get('sector', ''),
            'recommendation_type': rec['recommendation_type'],
            'recommend_price': recommend_price,
            'current_price': current_price,
            'return_pct': return_pct,
            'result': result,
        }

    def run_backtest(self) -> Optional[Dict]:
        """运行回测"""
        logger.info(f"\n{'='*50}")
        logger.info(f"回测验证 - 验证 {self.days_ago} 天前({self.backtest_date})的推荐")
        logger.info(f"{'='*50}\n")

        # 获取历史推荐
        recommendations = get_recommendations_for_backtest(self.days_ago)

        if not recommendations:
            logger.info(f"没有找到 {self.days_ago} 天前的推荐记录")
            return None

        logger.info(f"找到 {len(recommendations)} 条推荐记录，开始验证...")

        # 评估每条推荐
        results = []
        for rec in recommendations:
            eval_result = self.evaluate_recommendation(rec)
            results.append(eval_result)
            status = "✓" if eval_result['result'] == 'correct' else (
                "✗" if eval_result['result'] == 'wrong' else "-"
            )
            if eval_result['return_pct'] is not None:
                logger.info(f"  [{status}] {eval_result['name']}: {eval_result['return_pct']:+.2%}")

        # 统计结果
        valid_results = [r for r in results if r['return_pct'] is not None]
        if not valid_results:
            logger.info("没有有效的回测结果")
            return None

        correct_count = sum(1 for r in valid_results if r['result'] == 'correct')
        neutral_count = sum(1 for r in valid_results if r['result'] == 'neutral')
        wrong_count = sum(1 for r in valid_results if r['result'] == 'wrong')
        total = len(valid_results)

        accuracy_rate = correct_count / total if total > 0 else 0
        avg_return = sum(r['return_pct'] for r in valid_results) / total if total > 0 else 0

        # 找出最佳和最差
        sorted_by_return = sorted(valid_results, key=lambda x: x['return_pct'], reverse=True)
        best = sorted_by_return[0] if sorted_by_return else None
        worst = sorted_by_return[-1] if sorted_by_return else None

        # 生成总结
        if accuracy_rate >= 0.7:
            summary = f"表现优秀！准确率{accuracy_rate:.0%}，平均收益{avg_return:+.2%}"
        elif accuracy_rate >= 0.5:
            summary = f"表现一般，准确率{accuracy_rate:.0%}，平均收益{avg_return:+.2%}"
        else:
            summary = f"表现欠佳，准确率{accuracy_rate:.0%}，平均收益{avg_return:+.2%}，需要优化策略"

        backtest_result = {
            'date': self.today.isoformat(),
            'backtest_date': self.backtest_date.isoformat(),
            'total_recommendations': total,
            'correct_count': correct_count,
            'neutral_count': neutral_count,
            'wrong_count': wrong_count,
            'accuracy_rate': accuracy_rate,
            'avg_return': avg_return,
            'best_pick': best['name'] if best else None,
            'best_return': best['return_pct'] if best else None,
            'worst_pick': worst['name'] if worst else None,
            'worst_return': worst['return_pct'] if worst else None,
            'summary': summary,
            'details': results,
        }

        # 保存回测结果
        try:
            save_backtest_result(backtest_result)
        except Exception as e:
            logger.error(f"保存回测结果失败: {e}")

        return backtest_result

    def format_backtest_report(self, result: Dict) -> str:
        """格式化回测报告"""
        if not result:
            return "暂无回测数据"

        lines = [
            f"【历史回测】验证{self.days_ago}天前推荐",
            f"  - 验证日期: {result['backtest_date']}",
            f"  - 推荐数量: {result['total_recommendations']}只",
            f"  - 正确: {result['correct_count']}只 | 一般: {result['neutral_count']}只 | 错误: {result['wrong_count']}只",
            f"  - 准确率: {result['accuracy_rate']:.0%}",
            f"  - 平均收益: {result['avg_return']:+.2%}",
        ]

        if result.get('best_pick'):
            lines.append(f"  - 最佳: {result['best_pick']} ({result['best_return']:+.2%})")
        if result.get('worst_pick'):
            lines.append(f"  - 最差: {result['worst_pick']} ({result['worst_return']:+.2%})")

        lines.append(f"  - 评价: {result['summary']}")

        return '\n'.join(lines)


def run_backtest(days_ago: int = BACKTEST_DAYS) -> Tuple[Optional[Dict], str]:
    """运行回测的便捷函数"""
    backtester = Backtester(days_ago)
    result = backtester.run_backtest()
    report = backtester.format_backtest_report(result)
    return result, report


if __name__ == "__main__":
    result, report = run_backtest()
    print(f"\n{report}")

    overall = get_overall_accuracy()
    if overall:
        print(f"\n总体历史准确率: {overall:.0%}")
