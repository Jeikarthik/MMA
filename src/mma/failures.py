"""Failure classification and retry policy."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FailureClass(StrEnum):
    SYNTAX_ERROR = "syntax_error"
    TYPE_ERROR = "type_error"
    IMPORT_ERROR = "import_error"
    LOGIC_ERROR = "logic_error"
    SECURITY_VIOLATION = "security_violation"
    SECRET_LEAK = "secret_leak"
    PROVIDER_ERROR = "provider_error"
    PATCH_ERROR = "patch_error"
    VALIDATION_ERROR = "validation_error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FailureDiagnosis:
    failure_class: FailureClass
    root_cause: str
    retryable: bool
    escalate_to_nvidia: bool
    digest: str


def classify_failure(output: str, *, retry_count: int) -> FailureDiagnosis:
    """Classify deterministic failure output into a compact retry policy."""

    lower = output.lower()
    if "secret" in lower or "private key" in lower or "password" in lower:
        failure_class = FailureClass.SECRET_LEAK
        retryable = False
        escalate = True
        root = "possible secret exposure"
    elif "bandit" in lower or "security" in lower or "vulnerability" in lower:
        failure_class = FailureClass.SECURITY_VIOLATION
        retryable = True
        escalate = True
        root = "security validation failed"
    elif "syntaxerror" in lower or "compileall" in lower:
        failure_class = FailureClass.SYNTAX_ERROR
        retryable = True
        escalate = retry_count >= 2
        root = "syntax validation failed"
    elif "mypy" in lower or "type error" in lower:
        failure_class = FailureClass.TYPE_ERROR
        retryable = True
        escalate = True
        root = "type validation failed"
    elif "modulenotfounderror" in lower or "importerror" in lower:
        failure_class = FailureClass.IMPORT_ERROR
        retryable = True
        escalate = retry_count >= 2
        root = "import validation failed"
    elif "assert" in lower or "failed" in lower or "pytest" in lower:
        failure_class = FailureClass.LOGIC_ERROR
        retryable = True
        escalate = retry_count >= 2
        root = "test or logic validation failed"
    elif "api key" in lower or "provider" in lower or "ollama" in lower or "nvidia" in lower:
        failure_class = FailureClass.PROVIDER_ERROR
        retryable = True
        escalate = retry_count >= 2
        root = "model provider failed"
    elif "patch" in lower or "git apply" in lower or "unified diff" in lower:
        failure_class = FailureClass.PATCH_ERROR
        retryable = True
        escalate = retry_count >= 2
        root = "patch application failed"
    elif output.strip():
        failure_class = FailureClass.VALIDATION_ERROR
        retryable = True
        escalate = retry_count >= 2
        root = "validation failed"
    else:
        failure_class = FailureClass.UNKNOWN
        retryable = True
        escalate = retry_count >= 2
        root = "unknown failure"
    digest = compress_failure_digest(output, root_cause=root, failure_class=failure_class)
    return FailureDiagnosis(failure_class, root, retryable, escalate, digest)


def compress_failure_digest(
    output: str, *, root_cause: str, failure_class: FailureClass, max_chars: int = 300
) -> str:
    evidence = " ".join(line.strip() for line in output.splitlines() if line.strip())
    if len(evidence) > max_chars:
        evidence = evidence[: max_chars - 3] + "..."
    return f"{failure_class.value}: {root_cause}. Evidence: {evidence}"
