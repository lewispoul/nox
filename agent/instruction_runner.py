"""Simple instruction bundle runner.

This module provides a minimal interface to load instruction bundles (JSON or
plain text) from a directory and execute them. It's intentionally small and
conservative: it supports running shell tasks and Python snippets.

Contract:
- Input: path to a bundle file or directory. Bundles are JSON with fields:
  - type: "shell" | "python" | "noop"
  - content: string to execute
  - metadata: optional dict
- Output: dict with keys: success(bool), stdout, stderr, returncode, metadata

Error modes: returns success=false with stderr populated.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict


def load_bundle(path: str) -> Dict[str, Any]:
    p = Path(path)
    if p.is_dir():
        # look for a bundle.json or instruction.json
        for candidate in (p / "bundle.json", p / "instruction.json"):
            if candidate.exists():
                p = candidate
                break
    if not p.exists():
        raise FileNotFoundError(f"Bundle not found: {path}")
    if p.suffix.lower() in (".json", ".jsonl"):
        return json.loads(p.read_text(encoding="utf-8"))
    # fallback: treat as plain text shell commands
    return {"type": "shell", "content": p.read_text(encoding="utf-8")}


def run_bundle(bundle: Dict[str, Any], timeout: int = 600) -> Dict[str, Any]:
    t = bundle.get("type", "shell")
    content = bundle.get("content", "")
    meta = bundle.get("metadata", {}) or {}

    if not content:
        return {
            "success": True,
            "stdout": "",
            "stderr": "",
            "returncode": 0,
            "metadata": meta,
        }

    if t == "noop":
        return {
            "success": True,
            "stdout": "NOOP",
            "stderr": "",
            "returncode": 0,
            "metadata": meta,
        }

    if t == "shell":
        # run via /bin/bash -c
        try:
            proc = subprocess.run(
                ["/bin/bash", "-lc", content],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
                "metadata": meta,
            }
        except subprocess.TimeoutExpired as e:
            return {
                "success": False,
                "stdout": e.stdout or "",
                "stderr": "timeout",
                "returncode": 124,
                "metadata": meta,
            }

    if t == "python":
        # run python snippet in a subprocess to isolate environment
        try:
            proc = subprocess.run(
                [sys.executable, "-c", content],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
                "metadata": meta,
            }
        except subprocess.TimeoutExpired as e:
            return {
                "success": False,
                "stdout": e.stdout or "",
                "stderr": "timeout",
                "returncode": 124,
                "metadata": meta,
            }

    return {
        "success": False,
        "stdout": "",
        "stderr": f"Unknown bundle type: {t}",
        "returncode": 2,
        "metadata": meta,
    }


def run_path(path: str, timeout: int = 600) -> Dict[str, Any]:
    b = load_bundle(path)
    return run_bundle(b, timeout=timeout)
