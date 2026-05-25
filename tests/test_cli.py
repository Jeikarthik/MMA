from mma.cli import main


def test_cli_init_and_status(tmp_path, capsys):
    assert main(["--repo", str(tmp_path), "init"]) == 0
    assert main(["--repo", str(tmp_path), "status"]) == 0
    output = capsys.readouterr().out
    assert "initialized" in output


def test_cli_new_task(tmp_path, capsys):
    assert main(["--repo", str(tmp_path), "init"]) == 0
    assert main(["--repo", str(tmp_path), "new-task", "Update docs", "--type", "doc"]) == 0
    assert main(["--repo", str(tmp_path), "status"]) == 0
    output = capsys.readouterr().out
    assert "Update docs" in output


def test_cli_lists_seeded_capabilities(tmp_path, capsys):
    assert main(["--repo", str(tmp_path), "init"]) == 0
    assert main(["--repo", str(tmp_path), "capabilities"]) == 0
    output = capsys.readouterr().out
    assert "repo-inspect" in output
    assert "browser-qa" in output


def test_cli_missing_secret_returns_error(tmp_path):
    assert main(["--repo", str(tmp_path), "init"]) == 0
    try:
        result = main(["--repo", str(tmp_path), "get-secret", "NOPE"])
    except Exception:
        result = 1
    assert result == 1
