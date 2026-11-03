from unittest.mock import Mock

import main as daily_main
from config import BACKTEST_DAYS


def test_main_runs_daily_pipeline_without_external_services(monkeypatch, tmp_path):
    logger = Mock()
    report_path = tmp_path / "daily_report.md"
    summary = {"total_scanned": 0, "counts": {}, "recommendations": {}}
    mocks = {
        "setup_logging": Mock(return_value=logger),
        "init_database": Mock(),
        "run_backtest": Mock(return_value=(None, "")),
        "run_daily_analysis": Mock(return_value=([], summary)),
        "llm_enabled": Mock(return_value=False),
        "select_top_picks": Mock(),
        "save_recommendations": Mock(),
        "generate_report": Mock(return_value="Daily report"),
        "save_report": Mock(return_value=report_path),
        "get_overall_accuracy": Mock(return_value=None),
        "send_analysis_complete_notification": Mock(),
        "send_error_notification": Mock(),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(daily_main, name, mock)

    assert daily_main.main() == 0

    logger.info.assert_any_call(f"开始回测验证{BACKTEST_DAYS}天前的推荐...")
    mocks["run_backtest"].assert_called_once_with()
    mocks["run_daily_analysis"].assert_called_once_with()
    mocks["generate_report"].assert_called_once_with(None, [], summary, {})
    mocks["save_report"].assert_called_once_with("Daily report")
    mocks["send_analysis_complete_notification"].assert_called_once_with(0, None, str(report_path))
    mocks["select_top_picks"].assert_not_called()
    mocks["save_recommendations"].assert_not_called()
    mocks["send_error_notification"].assert_not_called()
