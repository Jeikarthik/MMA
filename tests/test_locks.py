import pytest

from mma.config import load_config
from mma.db import Store
from mma.locks import LockError, acquire_file_locks, release_file_locks


def test_file_lock_conflict(tmp_path):
    store = Store(load_config(tmp_path).db_path)
    store.init()
    acquire_file_locks(store, "task-1", ["a.py"])
    with pytest.raises(LockError):
        acquire_file_locks(store, "task-2", ["a.py"])


def test_file_lock_release(tmp_path):
    store = Store(load_config(tmp_path).db_path)
    store.init()
    acquire_file_locks(store, "task-1", ["a.py"])
    release_file_locks(store, "task-1")
    acquire_file_locks(store, "task-2", ["a.py"])
