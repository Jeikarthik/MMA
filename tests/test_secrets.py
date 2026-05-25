import sys

import pytest

from mma.config import load_config
from mma.db import Store
from mma.secrets import load_credential, protect_secret, store_credential, unprotect_secret


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
def test_dpapi_round_trip():
    encrypted = protect_secret("secret-value")
    assert encrypted != "secret-value"
    assert unprotect_secret(encrypted) == "secret-value"


@pytest.mark.skipif(sys.platform != "win32", reason="DPAPI is Windows-only")
def test_store_and_load_credential(tmp_path):
    config = load_config(tmp_path)
    store = Store(config.db_path)
    store.init()

    store_credential(store, "NVIDIA_API_KEY", "abc123")

    assert load_credential(store, "NVIDIA_API_KEY") == "abc123"
