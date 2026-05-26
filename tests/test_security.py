import subprocess

import pytest

from mma.security import SecurityError, scan_files_for_secrets, scan_text_for_secrets


def test_scan_text_for_secrets_detects_assignment():
    findings = scan_text_for_secrets('API_KEY="super-secret-value"')
    assert findings


def test_scan_files_for_secrets_raises(tmp_path):
    (tmp_path / "bad.py").write_text('TOKEN="super-secret-value"', encoding="utf-8")
    with pytest.raises(SecurityError):
        scan_files_for_secrets(tmp_path, ["bad.py"])


def test_git_commit_secret_scan_blocks(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "a@b.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=tmp_path, check=True)
    (tmp_path / "bad.py").write_text('PASSWORD="super-secret-value"', encoding="utf-8")
    subprocess.run(["git", "add", "bad.py"], cwd=tmp_path, check=True)
    from mma.security import run_staged_secret_scan

    with pytest.raises(SecurityError):
        run_staged_secret_scan(tmp_path)
