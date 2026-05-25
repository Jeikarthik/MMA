from pathlib import Path

from mma.mcp_server import JsonRpcServer
from mma.services import MmaService


def test_mcp_lists_tools(tmp_path: Path):
    service = MmaService(tmp_path)
    service.init()
    server = JsonRpcServer(service)

    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})

    assert response["result"]["tools"]
    assert {tool["name"] for tool in response["result"]["tools"]} >= {
        "submit_task",
        "run_task",
        "get_project_status",
        "rollback_task",
        "submit_dag",
    }


def test_mcp_submit_task(tmp_path: Path):
    service = MmaService(tmp_path)
    service.init()
    server = JsonRpcServer(service)

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "submit_task",
                "arguments": {"description": "Update docs", "task_type": "doc"},
            },
        }
    )

    text = response["result"]["content"][0]["text"]
    assert "Update docs" in text
