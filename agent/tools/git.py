# file: agent/tools/git.py
from __future__ import annotations

import subprocess


def sh(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True).strip()


def create_branch(branch: str) -> None:
    try:
        sh(f"git checkout -b {branch}")
    except subprocess.CalledProcessError:
        # Branch already exists, just switch to it
        sh(f"git checkout {branch}")


def commit_all(msg: str) -> None:
    sh("git add -A")
    sh(f'git commit -m "{msg}"')


def open_pr(title: str, body: str) -> None:
    # Rely on GitHub CLI if available; otherwise print instructions.
    try:
        sh(f'gh pr create --title "{title}" --body "{body}"')
    except Exception:
        print("# gh not found. Open a PR manually via GitHub Web UI.")
        print("## PR TITLE:", title)
        print("## PR BODY:\n", body)
