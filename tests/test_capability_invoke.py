from mma.capabilities import invoke_capability, seed_default_capabilities
from mma.config import load_config
from mma.db import Store


def test_invoke_browser_qa_requires_approval(tmp_path):
    store = Store(load_config(tmp_path).db_path)
    store.init()
    seed_default_capabilities(store)

    result = invoke_capability(store, tmp_path, name="browser-qa", arguments={})

    assert result["status"] == "awaiting_approval"


def test_invoke_repo_inspect_indexes(tmp_path):
    (tmp_path / "README.md").write_text("# Hello", encoding="utf-8")
    store = Store(load_config(tmp_path).db_path)
    store.init()
    seed_default_capabilities(store)

    result = invoke_capability(store, tmp_path, name="repo-inspect", arguments={})

    assert result["status"] == "complete"
    assert result["indexed"] == 1
