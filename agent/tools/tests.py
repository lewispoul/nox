# file: agent/tools/tests.py
from __future__ import annotations

import subprocess

_last_output = ""


def run_all() -> bool:
    global _last_output
    try:
        out = subprocess.check_output(
            "pytest -q", shell=True, text=True, stderr=subprocess.STDOUT
        )
        _last_output = out
        print(out)
        return True
    except subprocess.CalledProcessError as e:
        _last_output = e.output
        print(e.output)
        return False


def last_output() -> str:
    return _last_output
