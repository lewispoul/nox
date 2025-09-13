# file: tests/e2e/test_dry_run.py
import json
import os
import unittest.mock

from agent.executor import run_once


def test_dry_run_with_mocked_llm():
    """Test dry-run mode with mocked LLM response."""
    # Set a test API key
    os.environ["OPENAI_API_KEY"] = "test"

    # Mock the OpenAI response
    test_response = {
        "rationale": "Test dry run",
        "files_to_edit": [],
        "tests_to_add": [],
        "commands_to_run": ["pytest -q"],
        "risks": ["Test only"],
        "expected_outputs": ["No changes"],
        "patch": "",
    }

    # Use direct function call instead of subprocess to allow proper mocking
    with unittest.mock.patch("agent.executor.call_llm") as mock_llm:
        mock_llm.return_value = json.dumps(test_response)

        # Mock preflight_checks to avoid git checks in test
        with unittest.mock.patch("agent.executor.preflight_checks"):
            # Capture stdout for verification
            import io
            import sys

            old_stdout = sys.stdout
            captured_output = io.StringIO()
            sys.stdout = captured_output

            try:
                result = run_once(dry_run=True)
                assert result, "Dry run should return True"

                # Check that dry-run output was produced
                output = captured_output.getvalue()
                assert "DRY RUN MODE" in output
                assert "Test dry run" in output
            finally:
                sys.stdout = old_stdout
