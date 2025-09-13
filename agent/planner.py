# file: agent/planner.py
from __future__ import annotations

import json
import textwrap
from typing import Any, Dict

PROMPT_TEMPLATE = textwrap.dedent(
    """\
System: You are the Nox Planner. Output ONLY compact JSON with keys:
- rationale: short reasoning
- changes: list of objects {{path, action, content}}. action ∈ {{"create_or_update","delete"}}.
- tests_to_add: list of test file paths
- commands_to_run: list of shell commands (pytest etc.)
- risks: short bullet list
- expected_outputs: short bullet list

Rules:
- Edit only within the task scope paths.
- Provide FULL file contents in 'content' for any create_or_update action.
- Do NOT output diffs. Do NOT wrap lines. Use Unix newlines.
- Keep total output concise; omit unnecessary commentary.

User:
Task:
{task_yaml}

Repo tree (trimmed):
{repo_tree}

Key file snippets:
{file_snippets}

Current test output (if any):
{test_output}
"""
)


def build_planner_prompt(
    task_yaml: str, repo_tree: str, file_snippets: str, test_output: str = ""
) -> str:
    return PROMPT_TEMPLATE.format(
        task_yaml=task_yaml.strip(),
        repo_tree=repo_tree.strip(),
        file_snippets=file_snippets.strip(),
        test_output=test_output.strip(),
    )


def parse_planner_json(text: str) -> Dict[str, Any]:
    # Be lenient: find the first { ... } block.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Planner did not return JSON.")
    raw = text[start : end + 1]
    return json.loads(raw)
