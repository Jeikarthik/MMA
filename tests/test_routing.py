from mma.config import load_config
from mma.db import Task
from mma.routing import choose_route


def make_task(**overrides):
    base = dict(
        id="1",
        title="Update docs",
        description="Add setup docs",
        type="doc",
        status="pending",
        risk="normal",
        validation_profile="docs",
        model_provider=None,
        model_name=None,
        retry_count=0,
        branch=None,
        commit_sha=None,
        files_modified=[],
        result_summary=None,
        error_log=None,
        failure_digest=None,
    )
    base.update(overrides)
    return Task(**base)


def test_simple_doc_routes_to_gemma4_local():
    route = choose_route(make_task(), load_config(), local_safe=True)
    assert route.provider == "local"
    assert "gemma4" in route.model


def test_critical_task_routes_to_nvidia():
    task = make_task(title="Fix auth token validation", type="code")
    route = choose_route(task, load_config(), local_safe=True)
    assert route.provider == "nvidia"


def test_local_failure_twice_routes_to_nvidia_for_non_critical():
    task = make_task(type="code", retry_count=2)
    route = choose_route(task, load_config(), local_safe=True)
    assert route.provider == "nvidia"


def test_unsafe_local_routes_to_nvidia():
    task = make_task(type="code")
    route = choose_route(task, load_config(), local_safe=False)
    assert route.provider == "nvidia"
