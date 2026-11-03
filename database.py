"""
Stock Daily Analyzer - Database Module
"""
import sqlite3
from datetime import date
from typing import List, Dict, Optional
from contextlib import contextmanager

from config import DB_PATH


@contextmanager
def get_connection():
    """获取数据库连接的上下文管理器"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database():
    """初始化数据库表结构"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 每日推荐表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL,
                ticker TEXT NOT NULL,
                name TEXT NOT NULL,
                sector TEXT,
                recommendation_type TEXT NOT NULL,
                price_at_recommend REAL NOT NULL,
                rsi REAL,
                macd_signal TEXT,
                volume_ratio REAL,
                confidence TEXT,
                reasoning TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, ticker)
            )
        ''')

        # 价格跟踪表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS price_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recommendation_id INTEGER NOT NULL,
                date DATE NOT NULL,
                close_price REAL NOT NULL,
                change_pct REAL NOT NULL,
                FOREIGN KEY (recommendation_id) REFERENCES daily_recommendations(id),
                UNIQUE(recommendation_id, date)
            )
        ''')

        # 回测结果表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date DATE NOT NULL UNIQUE,
                backtest_date DATE NOT NULL,
                total_recommendations INTEGER NOT NULL,
                correct_count INTEGER NOT NULL,
                neutral_count INTEGER NOT NULL,
                wrong_count INTEGER NOT NULL,
                accuracy_rate REAL NOT NULL,
                avg_return REAL NOT NULL,
                best_pick TEXT,
                best_return REAL,
                worst_pick TEXT,
                worst_return REAL,
                summary TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_recommendations_date ON daily_recommendations(date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tracking_date ON price_tracking(date)')


def save_recommendation(recommendation: Dict) -> int:
    """保存单条推荐记录"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO daily_recommendations
            (date, ticker, name, sector, recommendation_type, price_at_recommend,
             rsi, macd_signal, volume_ratio, confidence, reasoning)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            recommendation['date'],
            recommendation['ticker'],
            recommendation['name'],
            recommendation.get('sector'),
            recommendation['recommendation_type'],
            recommendation['price'],
            recommendation.get('rsi'),
            recommendation.get('macd_signal'),
            recommendation.get('volume_ratio'),
            recommendation.get('confidence', '中'),
            recommendation.get('reasoning')
        ))
        return cursor.lastrowid


def save_recommendations(recommendations: List[Dict]) -> int:
    """批量保存推荐记录"""
    count = 0
    for rec in recommendations:
        try:
            save_recommendation(rec)
            count += 1
        except Exception as e:
            print(f"保存推荐失败 {rec.get('name')}: {e}")
    return count


def get_recommendations_by_date(target_date: date) -> List[Dict]:
    """获取指定日期的推荐记录"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM daily_recommendations WHERE date = ?
        ''', (target_date.isoformat(),))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_recommendations_for_backtest(days_ago: int) -> List[Dict]:
    """获取N天前的推荐记录用于回测"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM daily_recommendations
            WHERE date = date('now', ? || ' days')
        ''', (f'-{days_ago}',))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def save_price_tracking(recommendation_id: int, track_date: date,
                        close_price: float, change_pct: float):
    """保存价格跟踪记录"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO price_tracking
            (recommendation_id, date, close_price, change_pct)
            VALUES (?, ?, ?, ?)
        ''', (recommendation_id, track_date.isoformat(), close_price, change_pct))


def save_backtest_result(result: Dict):
    """保存回测结果"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO backtest_results
            (date, backtest_date, total_recommendations, correct_count, neutral_count,
             wrong_count, accuracy_rate, avg_return, best_pick, best_return,
             worst_pick, worst_return, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            result['date'],
            result['backtest_date'],
            result['total_recommendations'],
            result['correct_count'],
            result['neutral_count'],
            result['wrong_count'],
            result['accuracy_rate'],
            result['avg_return'],
            result.get('best_pick'),
            result.get('best_return'),
            result.get('worst_pick'),
            result.get('worst_return'),
            result.get('summary')
        ))


def get_latest_backtest_results(limit: int = 10) -> List[Dict]:
    """获取最近的回测结果"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM backtest_results
            ORDER BY date DESC LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_overall_accuracy() -> Optional[float]:
    """获取总体准确率"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                SUM(correct_count) as total_correct,
                SUM(total_recommendations) as total_recs
            FROM backtest_results
        ''')
        row = cursor.fetchone()
        if row and row['total_recs'] and row['total_recs'] > 0:
            return row['total_correct'] / row['total_recs']
        return None


if __name__ == "__main__":
    # 初始化数据库
    init_database()
    print(f"数据库初始化完成: {DB_PATH}")
