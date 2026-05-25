import pytest

from mma.patches import PatchError, extract_unified_diff


def test_extract_fenced_diff():
    text = """```diff
diff --git a/README.md b/README.md
--- a/README.md
+++ b/README.md
@@ -1 +1 @@
-old
+new
```"""
    assert extract_unified_diff(text).startswith("diff --git")


def test_rejects_non_patch_output():
    with pytest.raises(PatchError):
        extract_unified_diff("Here is the change.")
