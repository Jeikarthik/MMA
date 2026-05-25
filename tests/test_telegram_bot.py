from mma.services import MmaService
from mma.telegram_bot import handle_command


def test_telegram_start(tmp_path):
    response = handle_command(MmaService(tmp_path), "/start")
    assert "MMA ready" in response


def test_telegram_new_task_and_status(tmp_path):
    service = MmaService(tmp_path)

    created = handle_command(service, "/new_task Update README")
    status = handle_command(service, "/status")

    assert "Created task" in created
    assert "Update README" in status


def test_telegram_unknown_command(tmp_path):
    response = handle_command(MmaService(tmp_path), "/wat")
    assert "Unknown command" in response
