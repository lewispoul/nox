#!/usr/bin/env python3
"""Debug patch format issues."""

import subprocess
import tempfile

# Create a simple test patch that should work
test_patch = """diff --git a/test_file.py b/test_file.py
index 1234567..abcdefg 100644
--- a/test_file.py
+++ b/test_file.py
@@ -1,3 +1,5 @@
 import json
 
 def test():
+    # Added comment
+    print("hello")
     pass
"""


def test_patch_format():
    """Test if a basic patch can be applied."""
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """import json

def test():
    pass
"""
        )
        temp_file = f.name

    # Create patch file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".patch", delete=False) as f:
        f.write(test_patch)
        patch_file = f.name

    # Try to apply patch
    try:
        result = subprocess.run(
            ["git", "apply", "--check", patch_file],
            cwd="/tmp",
            capture_output=True,
            text=True,
        )
        print(f"Patch check result: {result.returncode}")
        print(f"Stdout: {result.stdout}")
        print(f"Stderr: {result.stderr}")

    except Exception as e:
        print(f"Error testing patch: {e}")


if __name__ == "__main__":
    test_patch_format()
