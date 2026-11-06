import argparse
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(prog="stock-analyzer", description="A-share daily analysis and quant research tools")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_demo = sub.add_parser("demo", help="Run an offline backtest with synthetic data; no API key needed")
    p_demo.add_argument("--out", default="reports/demo", help="Output directory (default: reports/demo)")

    p_daily_demo = sub.add_parser("demo-daily", help="Generate a daily report from fictional prices, offline")
    p_daily_demo.add_argument("--out", default="reports/daily-demo", help="Output directory (default: reports/daily-demo)")

    p_bt = sub.add_parser("backtest", help="Run a configured backtest using live data providers")
    p_bt.add_argument("--config", required=True, help="实验配置文件路径，例如 experiments/default_a_share_daily.json")
    p_bt.add_argument("--out", default="reports/experiments", help="输出目录")

    sub.add_parser("run-daily", help="Scan live A-share data and write a daily report")
    sub.add_parser("self-check", help="Check module imports; does not check API access or credentials")

    args = p.parse_args()

    if args.cmd == "demo-daily":
        from qf.daily_demo import DAILY_DEMO_WARNING, run_daily_demo

        print(DAILY_DEMO_WARNING)
        report_path = run_daily_demo(Path(args.out))
        print("Offline daily report complete: 4 fictional symbols, 80 weekday observations each.")
        for name in ("daily-report.txt", "inputs.csv", "analysis.json", "README.md", "README.en.md"):
            print(str(report_path.parent / name))
        return 0
    if args.cmd == "demo":
        from qf.demo import DEMO_WARNING, run_demo

        summary_path = run_demo(Path(args.out))
        print(DEMO_WARNING)
        print("Offline demo complete: 3 fictional symbols, 60 weekday observations.")
        for name in ("equity.csv", "holdings.csv", "summary.json", "equity.svg", "report.html"):
            print(str(summary_path.parent / name))
        print("Open report.html in your browser to view the synthetic results.")
        return 0
    if args.cmd == "backtest":
        from qf.experiment import run_experiment

        _, _, summary_path = run_experiment(Path(args.config), Path(args.out))
        print(str(summary_path))
        return 0
    if args.cmd == "run-daily":
        import main as daily

        return int(daily.main())
    if args.cmd == "self-check":
        import self_check

        return int(self_check.main())

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
