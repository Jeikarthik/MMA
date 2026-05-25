"""Lightweight repository memory for context assembly."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path

from mma.db import Store, utc_now


TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".md",
    ".toml",
    ".json",
    ".yaml",
    ".yml",
    ".txt",
    ".css",
    ".html",
}

SKIP_DIRS = {".git", ".mma", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}


@dataclass(frozen=True)
class MemoryEntry:
    path: str
    sha256: str
    summary: str


def index_repo(store: Store, repo_root: Path) -> list[MemoryEntry]:
    """Index text files into compact summaries."""

    entries: list[MemoryEntry] = []
    for path in sorted(_iter_text_files(repo_root)):
        rel = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        summary = summarize_text(rel, text)
        with store.connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO repo_memory (path, sha256, summary, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (rel, digest, summary, utc_now()),
            )
        entries.append(MemoryEntry(rel, digest, summary))
    return entries


def search_memory(store: Store, query: str, limit: int = 5) -> list[MemoryEntry]:
    """Return simple keyword-ranked memory entries."""

    terms = [term.lower() for term in query.split() if term.strip()]
    with store.connect() as conn:
        rows = conn.execute("SELECT * FROM repo_memory").fetchall()
    ranked: list[tuple[int, MemoryEntry]] = []
    for row in rows:
        haystack = f"{row['path']} {row['summary']}".lower()
        score = sum(haystack.count(term) for term in terms)
        if score:
            ranked.append(
                (
                    score,
                    MemoryEntry(path=row["path"], sha256=row["sha256"], summary=row["summary"]),
                )
            )
    ranked.sort(key=lambda item: (-item[0], item[1].path))
    return [entry for _score, entry in ranked[:limit]]


def summarize_text(path: str, text: str) -> str:
    """Create a deterministic compact file summary."""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return f"{path}: empty file"
    heading = next((line.lstrip("# ").strip() for line in lines if line.startswith("#")), lines[0])
    symbols = [line for line in lines if line.startswith(("def ", "class ", "function ", "export "))]
    symbol_text = "; ".join(symbols[:5])
    if symbol_text:
        return f"{path}: {heading}. Symbols: {symbol_text}"
    body = " ".join(lines[:5])
    return f"{path}: {heading}. {body[:240]}"


def _iter_text_files(repo_root: Path):
    for path in repo_root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(repo_root).parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            yield path
