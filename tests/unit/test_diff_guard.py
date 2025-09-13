# file: tests/unit/test_diff_guard.py
import pytest

from agent.tools.codeedit import count_added_lines


def test_count_added_lines():
    """Test counting added lines in a diff."""
    patch = """--- a/test.py
+++ b/test.py
@@ -1,3 +1,5 @@
 line 1
+added line 1
 line 2
+added line 2
 line 3"""

    assert count_added_lines(patch) == 2


def test_large_diff_detection():
    """Test that large diffs are detected correctly."""
    # Create a synthetic diff with many added lines
    lines = ["--- a/test.py", "+++ b/test.py", "@@ -1,1 +1,1001 @@"]
    lines.extend([f"+added line {i}" for i in range(1000)])

    large_patch = "\n".join(lines)
    assert count_added_lines(large_patch) == 1000


def test_diff_guard_enforcement():
    """Test that the diff size guard works."""
    from agent.executor import apply_patch

    # Create a config with low limit
    cfg = {"policies": {"max_patch_size_lines": 5}}

    # Create a large patch
    large_patch = "\n".join([f"+line {i}" for i in range(10)])

    # Should exit with error - we test this by checking SystemExit is raised
    with pytest.raises(SystemExit) as exc_info:
        apply_patch(large_patch, [], cfg)

    assert exc_info.value.code == 1
