import pytest

from mma.config import load_config
from mma.dag import DagTask, create_dag, validate_dag
from mma.db import Store


def test_validate_dag_rejects_cycle():
    tasks = [
        DagTask(key="a", title="A", description="A", depends_on=("b",)),
        DagTask(key="b", title="B", description="B", depends_on=("a",)),
    ]
    with pytest.raises(ValueError, match="cycle"):
        validate_dag(tasks)


def test_create_dag_and_ready_tasks(tmp_path):
    config = load_config(tmp_path)
    store = Store(config.db_path)
    store.init()

    ids = create_dag(
        store,
        [
            DagTask(key="a", title="A", description="A"),
            DagTask(key="b", title="B", description="B", depends_on=("a",)),
        ],
    )

    ready = store.ready_tasks()
    assert [task.id for task in ready] == [ids["a"]]
