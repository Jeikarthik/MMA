from mma.failures import FailureClass, classify_failure


def test_classify_secret_leak_escalates_without_retry():
    diagnosis = classify_failure("detect-secrets found private key", retry_count=1)
    assert diagnosis.failure_class == FailureClass.SECRET_LEAK
    assert not diagnosis.retryable
    assert diagnosis.escalate_to_nvidia


def test_classify_pytest_failure_escalates_after_second_failure():
    first = classify_failure("pytest failed assertion", retry_count=1)
    second = classify_failure("pytest failed assertion", retry_count=2)
    assert first.failure_class == FailureClass.LOGIC_ERROR
    assert not first.escalate_to_nvidia
    assert second.escalate_to_nvidia
