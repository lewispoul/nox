# file: agent/tools/shell.py
from __future__ import annotations

import subprocess


def run(cmd: str, timeout: int = 600) -> int:
    print(f"$ {cmd}")
    proc = subprocess.Popen(cmd, shell=True)
    try:
        return proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        return 124
