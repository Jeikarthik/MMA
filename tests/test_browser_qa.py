import os

import pytest

from mma.browser_qa import BrowserQaError, run_browser_qa


def test_browser_qa_requires_command(tmp_path, monkeypatch):
    monkeypatch.delenv("MMA_BROWSER_QA_COMMAND", raising=False)
    with pytest.raises(BrowserQaError):
        run_browser_qa(tmp_path)


def test_browser_qa_runs_configured_command(tmp_path, monkeypatch):
    monkeypatch.setenv("MMA_BROWSER_QA_COMMAND", "python -c \"print('ok')\"")
    assert "ok" in run_browser_qa(tmp_path)
