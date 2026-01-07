import unittest
from unittest.mock import MagicMock, patch
import json
import numpy as np
import pandas as pd
from datetime import date
from service_runner import CustomJSONEncoder

class TestCustomJSONEncoder(unittest.TestCase):
    def test_numpy_types(self):
        encoder = CustomJSONEncoder()
        
        # Test int types
        self.assertEqual(encoder.default(np.int64(10)), 10)
        self.assertEqual(encoder.default(np.int32(20)), 20)
        
        # Test float types
        self.assertEqual(encoder.default(np.float64(10.5)), 10.5)
        self.assertEqual(encoder.default(np.float32(20.5)), 20.5)
        
        # Test NaN/Inf - 注意：CustomJSONEncoder 现在在 default 中处理 float 类型
        # 但如果是直接调用 default(np.nan)，因为 np.nan 是 float 类型，
        # 如果 CustomJSONEncoder.default 逻辑正确，应该能返回 None
        self.assertIsNone(encoder.default(np.nan))
        self.assertIsNone(encoder.default(np.inf))
        
        # Test ndarray
        self.assertEqual(encoder.default(np.array([1, 2, 3])), [1, 2, 3])

    def test_pandas_types(self):
        encoder = CustomJSONEncoder()
        df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
        self.assertEqual(
            encoder.default(df),
            [{'a': 1, 'b': 3}, {'a': 2, 'b': 4}]
        )

class TestServiceRunnerMock(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.mock_analyzer_patcher = patch('service_runner.run_daily_analysis')
        self.mock_backtester_patcher = patch('service_runner.run_backtest')
        self.mock_llm_patcher = patch('service_runner.select_top_picks')
        self.mock_db_patcher = patch('service_runner.init_database')
        
        self.mock_run_daily = self.mock_analyzer_patcher.start()
        self.mock_run_backtest = self.mock_backtester_patcher.start()
        self.mock_select_picks = self.mock_llm_patcher.start()
        self.mock_init_db = self.mock_db_patcher.start()

    def tearDown(self):
        self.mock_analyzer_patcher.stop()
        self.mock_backtester_patcher.stop()
        self.mock_llm_patcher.stop()
        self.mock_db_patcher.stop()

    def test_json_serialization_flow(self):
        """测试完整的数据流序列化"""
        # 构造包含 numpy 类型的复杂数据
        mock_summary = {
            'total_scanned': np.int64(100),
            'recommendations': {
                'TypeA': [
                    {'name': 'StockA', 'price': np.float64(10.5), 'rsi': np.nan},
                    {'name': 'StockB', 'ma_values': np.array([1, 2, 3])}
                ]
            }
        }
        
        # 模拟数据
        data = {
            "status": "success",
            "summary": mock_summary,
            "timestamp": date.today().isoformat()
        }
        
        # 尝试序列化
        from service_runner import clean_data_for_json
        try:
            # 模拟 service_runner 中的两步处理：先 dumps+loads，再 clean
            json_str = json.dumps(data, cls=CustomJSONEncoder)
            temp_result = json.loads(json_str)
            result = clean_data_for_json(temp_result)
            
            # 验证转换结果
            self.assertEqual(result['summary']['total_scanned'], 100)
            self.assertEqual(result['summary']['recommendations']['TypeA'][0]['price'], 10.5)
            self.assertIsNone(result['summary']['recommendations']['TypeA'][0]['rsi'])
            self.assertEqual(result['summary']['recommendations']['TypeA'][1]['ma_values'], [1, 2, 3])
            print("JSON 序列化测试通过")
        except Exception as e:
            self.fail(f"JSON 序列化失败: {e}")

if __name__ == '__main__':
    unittest.main()
