from mma.config import load_config
from mma.db import Store
from mma.memory import index_repo, search_memory


def test_index_and_search_memory(tmp_path):
    (tmp_path / "README.md").write_text("# Hello\nThis project uses NVIDIA routing.", encoding="utf-8")
    config = load_config(tmp_path)
    store = Store(config.db_path)
    store.init()

    entries = index_repo(store, tmp_path)

    assert len(entries) == 1
    matches = search_memory(store, "NVIDIA")
    assert matches[0].path == "README.md"
