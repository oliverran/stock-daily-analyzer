import importlib


def main() -> int:
    modules = [
        "config",
        "database",
        "analyzer",
        "backtester",
        "llm",
        "notifier",
        "reporting",
        "log_setup",
        "strategies",
        "qf.config",
        "qf.universe",
        "qf.data",
        "qf.factors",
        "qf.scoring",
        "qf.portfolio",
        "qf.metrics",
        "qf.backtest",
        "qf.experiment",
        "qf.trading",
        "qf.cli",
    ]
    failures = []
    for m in modules:
        try:
            importlib.import_module(m)
        except Exception as e:
            failures.append((m, repr(e)))
    if failures:
        for m, err in failures:
            print(f"IMPORT_FAIL {m}: {err}")
        return 1
    print("IMPORT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
