from mma.assets import answer_asset_request, create_asset_request
from mma.config import load_config
from mma.db import Store
from mma.services import MmaService


def test_asset_request_blocks_and_resolution_returns_to_pending(tmp_path):
    config = load_config(tmp_path)
    store = Store(config.db_path)
    store.init()
    task = store.create_task(
        title="Configure deploy",
        description="Needs token",
        task_type="config",
        risk="normal",
        validation_profile="generic",
    )

    request_id = create_asset_request(store, task.id, "Need DEPLOY_TOKEN")
    assert store.get_task(task.id).status == "awaiting_assets"

    answer_asset_request(store, request_id, "provided out of band")
    assert store.get_task(task.id).status == "pending"


def test_service_blocks_task_when_assets_detected(tmp_path):
    service = MmaService(tmp_path)

    task = service.create_task(description="Configure deploy with API key", task_type="config")

    assert task["status"] == "awaiting_assets"
