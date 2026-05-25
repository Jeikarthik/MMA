from mma.capabilities import list_capabilities, register_capability
from mma.config import load_config
from mma.db import Store


def test_mutating_capability_requires_approval(tmp_path):
    config = load_config(tmp_path)
    store = Store(config.db_path)
    store.init()

    register_capability(
        store,
        name="browser-qa",
        adapter_type="browser",
        permissions={"external_tool"},
    )

    capability = list_capabilities(store)[0]
    assert capability.requires_approval


def test_read_only_capability_does_not_require_approval(tmp_path):
    config = load_config(tmp_path)
    store = Store(config.db_path)
    store.init()

    register_capability(store, name="repo-inspect", adapter_type="native", permissions=set())

    capability = list_capabilities(store)[0]
    assert not capability.requires_approval
