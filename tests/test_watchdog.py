from mma.config import load_config
from mma.db import Store
from mma.watchdog import run_watchdog


def test_watchdog_reports_no_stale_tasks(tmp_path):
    store = Store(load_config(tmp_path).db_path)
    store.init()

    report = run_watchdog(tmp_path)

    assert report.stale_tasks == []
