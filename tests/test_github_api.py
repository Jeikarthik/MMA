from mma.github_api import build_pr_body


def test_build_pr_body_contains_required_sections():
    body = build_pr_body(summary="Changed docs.", validation="pytest passed.")

    assert "## Summary" in body
    assert "Changed docs." in body
    assert "## Validation" in body
    assert "pytest passed." in body
    assert "## Risks" in body
