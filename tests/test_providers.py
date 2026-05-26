from mma.config import load_config
from mma.providers import provider_health


def test_provider_health_shape(tmp_path):
    config = load_config(tmp_path)
    health = provider_health(config)
    assert set(health) == {"ollama", "nvidia", "claude"}
    assert "configured" in health["nvidia"]
