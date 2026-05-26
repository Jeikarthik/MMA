from mma.prompts import ENGINEERING_SYSTEM_PROMPT, TASK_PROMPT_RULES


def test_engineering_prompt_enforces_needs_context_and_diff():
    assert "NEEDS_CONTEXT" in ENGINEERING_SYSTEM_PROMPT
    assert "unified git diff" in ENGINEERING_SYSTEM_PROMPT
    assert "production-quality" in ENGINEERING_SYSTEM_PROMPT


def test_task_prompt_rules_are_strict():
    joined = "\n".join(TASK_PROMPT_RULES)
    assert "diff must apply cleanly" in joined
    assert "Build for real MVP/product use" in joined
