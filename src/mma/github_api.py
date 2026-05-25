"""Minimal GitHub API helpers for PR workflow."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from urllib import error, request


class GitHubError(RuntimeError):
    """Raised when GitHub automation fails."""


@dataclass(frozen=True)
class PullRequest:
    number: int
    url: str
    title: str


def create_pull_request(
    *,
    repo_full_name: str,
    head: str,
    base: str,
    title: str,
    body: str,
    token: str | None = None,
) -> PullRequest:
    """Create a GitHub pull request using the REST API."""

    api_token = token or os.getenv("GITHUB_TOKEN")
    if not api_token:
        raise GitHubError("GITHUB_TOKEN is not configured")
    payload = {"head": head, "base": base, "title": title, "body": body}
    url = f"https://api.github.com/repos/{repo_full_name}/pulls"
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "User-Agent": "mma-orchestrator",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        raise GitHubError(f"failed to create pull request: {exc}") from exc
    return PullRequest(number=int(data["number"]), url=data["html_url"], title=data["title"])


def build_pr_body(*, summary: str, validation: str, risks: str = "None known.") -> str:
    """Build a deterministic PR body."""

    return f"""## Summary
{summary}

## Validation
{validation}

## Risks
{risks}
"""
