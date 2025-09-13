# file: agent/tools/fs.py
from __future__ import annotations

import os
import pathlib
from typing import Any, Dict

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    p = ROOT / path
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(path: str, content: str) -> None:
    p = ROOT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def list_tree(base: str = ".", max_depth: int = 3) -> str:
    base_path = (ROOT / base).resolve()
    out = []
    for root, dirs, files in os.walk(base_path):
        depth = len(pathlib.Path(root).relative_to(base_path).parts)
        if depth > max_depth:
            continue
        rel_root = str(pathlib.Path(root).relative_to(ROOT))
        out.append(rel_root + "/")
        for name in sorted(files):
            out.append(str(pathlib.Path(root, name).relative_to(ROOT)))
    return "\n".join(out)


def pick_task(backlog_path: str) -> Dict[str, Any]:
    import yaml as _yaml

    data = _yaml.safe_load(read(backlog_path)) or []
    if not data:
        raise RuntimeError("No tasks in backlog.")
    # naive: pick highest priority then first
    prio_order = {"high": 0, "medium": 1, "low": 2}
    data.sort(key=lambda t: prio_order.get(t.get("priority", "medium"), 1))
    return data[0]


def read_context(task: Dict[str, Any]) -> Dict[str, Any]:
    scope_paths = task.get("scope", {}).get("paths", [])
    snippets = []
    for path in scope_paths:
        try:
            snippets.append(f"### {path}\n" + read(path)[:4000])
        except Exception:
            continue
    return {
        "task_yaml": yaml.safe_dump(task, sort_keys=False),
        "repo_tree": list_tree("."),
        "file_snippets": "\n\n".join(snippets),
    }
