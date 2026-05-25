from mma.config import load_config
from mma.db import Store
from mma.scheduler import run_pending


def test_scheduler_no_pending_tasks(tmp_path):
    config = load_config(tmp_path)
    Store(config.db_path).init()

    result = run_pending(tmp_path)

    assert result.attempted == 0
    assert result.results == []
