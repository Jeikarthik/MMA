from mma.services import MmaService


def test_service_create_dag(tmp_path):
    service = MmaService(tmp_path)

    ids = service.create_dag(
        [
            {"key": "a", "title": "A", "description": "A"},
            {"key": "b", "title": "B", "description": "B", "depends_on": ["a"]},
        ]
    )

    assert set(ids) == {"a", "b"}
