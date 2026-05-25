from mma.scout import detect_validation_profile, scout_task


def test_scout_marks_auth_as_high_risk(tmp_path):
    result = scout_task(tmp_path, "Fix auth token validation", "code")
    assert result.risk == "high"


def test_detect_docs_profile_for_readme(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'", encoding="utf-8")
    assert detect_validation_profile(tmp_path, "Update README", "doc") == "docs"


def test_detect_frontend_profile_for_package_json(tmp_path):
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    assert detect_validation_profile(tmp_path, "Add UI", "code") == "frontend"


def test_scout_detects_assets(tmp_path):
    result = scout_task(tmp_path, "Configure deploy with API key and logo", "config")
    assert set(result.missing_assets) >= {"api_key", "design", "deployment"}
