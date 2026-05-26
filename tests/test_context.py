from mma.config import load_config
from mma.context import assemble_context
from mma.db import Store
from mma.memory import index_repo


def test_context_includes_memory(tmp_path):
    (tmp_path / "README.md").write_text("# MMA\nNVIDIA routing details", encoding="utf-8")
    config = load_config(tmp_path)
    store = Store(config.db_path)
    store.init()
    index_repo(store, tmp_path)
    task = store.create_task(
        title="Update NVIDIA docs",
        description="Mention NVIDIA routing",
        task_type="doc",
        risk="normal",
        validation_profile="docs",
    )

    context = assemble_context(store, task)

    assert "Relevant repo memory" in context.prompt
    assert context.summaries_used == ["README.md"]
