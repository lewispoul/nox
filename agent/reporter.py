# file: agent/reporter.py
from __future__ import annotations


def summarize_run(task, plan, patch_ok: bool, tests_ok: bool, test_output: str) -> str:
    lines = []
    lines.append(f"### Task\n- {task.get('id')} — {task.get('title')}")
    lines.append("### Plan")
    lines.append(f"```json\n{plan}\n```")
    lines.append("### Tests")
    lines.append("```\n" + (test_output[-2000:] if test_output else "no output") + "\n```")
    lines.append("### Status")
    lines.append(f"- Patch applied: {'yes' if patch_ok else 'no'}")
    lines.append(f"- Tests passed: {'yes' if tests_ok else 'no'}")
    lines.append("### Risks\n- See policies.md and plan.risks")
    return "\n\n".join(lines)
