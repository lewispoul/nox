# file: agent/executor.py
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from agent.planner import build_planner_prompt, parse_planner_json
from agent.reporter import summarize_run
from agent.tools import codeedit, fs, git, tests


def apply_changes_via_files(changes, allowlist) -> str:
    """
    Write files per 'changes' and return a valid unified diff string produced by git.
    Does not commit. Leaves changes staged.
    """
    # allowlist check
    for ch in changes:
        p = ch.get("path", "")
        if not any(
            p.startswith(prefix.rstrip("*").rstrip("/")) for prefix in allowlist
        ):
            raise RuntimeError(f"Change touches disallowed path: {p}")

    # write/delete files
    for ch in changes:
        action = ch.get("action", "create_or_update")
        path = Path(ch["path"])
        if action in ("create_or_update", "create", "update"):
            path.parent.mkdir(parents=True, exist_ok=True)
            content = ch.get("content", "")
            path.write_text(content, encoding="utf-8", newline="\n")
        elif action == "delete":
            if path.exists():
                path.unlink()

    # stage and generate diff from index
    subprocess.check_call("git add -A", shell=True)
    diff = subprocess.check_output(
        "git diff --cached --unified=3", shell=True, text=True
    )
    return diff


def load_config():
    try:
        import yaml as _yaml

        return _yaml.safe_load(fs.read("agent/config.yaml")) or {}
    except Exception:
        return {}


def redact(text: str) -> str:
    """Redact secrets and keys from text to prevent leakage."""
    # Redact OpenAI API keys (broader pattern)
    text = re.sub(r"sk-[A-Za-z0-9_-]{20,}", "sk-***REDACTED***", text)
    # Redact environment variable assignments
    text = re.sub(r"(OPENAI_API_KEY\s*=\s*)(.+)", r"\1***REDACTED***", text)
    text = re.sub(r"(GITHUB_TOKEN\s*=\s*)(.+)", r"\1***REDACTED***", text)
    # Redact any other common secret patterns
    text = re.sub(r"(Bearer\s+)[A-Za-z0-9_-]{20,}", r"\1***REDACTED***", text)
    return text


def preflight_checks() -> None:
    """Run preflight checks to ensure safe operation."""
    # Check if on main branch
    try:
        current_branch = subprocess.check_output(
            "git rev-parse --abbrev-ref HEAD", shell=True, text=True
        ).strip()
        # Allow overriding the main-branch safeguard using an env var for controlled deployments
        allow_on_main = os.getenv("NOX_AGENT_ALLOW_ON_MAIN", "0")
        if current_branch == "main" and allow_on_main != "1":
            print(
                "ERROR: Agent cannot run on main branch. Switch to a feature branch or set NOX_AGENT_ALLOW_ON_MAIN=1 to override."
            )
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("ERROR: Failed to check current branch")
        sys.exit(1)

    # Check if working tree is dirty
    try:
        status = subprocess.check_output(
            "git status --porcelain", shell=True, text=True
        ).strip()
        allow_dirty = os.getenv("NOX_AGENT_ALLOW_DIRTY", "0")
        if status and allow_dirty != "1":
            print(
                "ERROR: Working tree is dirty. Commit or stash changes before running agent or set NOX_AGENT_ALLOW_DIRTY=1 to override."
            )
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("ERROR: Failed to check git status")
        sys.exit(1)


def call_llm(prompt: str) -> str:
    """
    If NOX_PLAN_FILE is set, return its contents (offline plan injection).
    Otherwise call OpenAI as usual.
    """
    plan_file = os.getenv("NOX_PLAN_FILE")
    if plan_file:
        return Path(plan_file).read_text(encoding="utf-8")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are the Nox Planner. Output only compact JSON as per planner.py spec.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=2000,
    )
    return resp.choices[0].message.content


def apply_patch(patch: str, allowlist, cfg) -> bool:
    """Apply patch with size and scope validation."""
    if not patch.strip():
        return False

    # Check patch size
    max_lines = cfg.get("policies", {}).get("max_patch_size_lines", 1200)
    added_lines = codeedit.count_added_lines(patch)
    if added_lines > max_lines:
        print(f"ERROR: Patch too large ({added_lines} lines > {max_lines} limit)")
        sys.exit(1)

    codeedit.check_unified_diff(patch)
    if not codeedit.only_in_allowed_paths(patch, allowlist):
        raise RuntimeError("Patch touches files outside allowlist.")

    # Ensure directories exist for new files
    codeedit.ensure_directories_for_new_files(patch)

    # Simple application via 'git apply' to keep it robust
    from subprocess import check_call

    try:
        Path(".agent_patch.diff").write_text(patch, encoding="utf-8")
        check_call("git apply --whitespace=nowarn .agent_patch.diff", shell=True)
        return True
    finally:
        try:
            Path(".agent_patch.diff").unlink()
        except Exception:
            pass


def run_once(dry_run: bool = False, no_pr: bool = False) -> bool:
    """Run a single agent cycle."""
    preflight_checks()

    cfg = load_config()
    task = fs.pick_task("agent/tasks/backlog.yaml")
    ctx = fs.read_context(task)
    prompt = build_planner_prompt(
        ctx["task_yaml"], ctx["repo_tree"], ctx["file_snippets"]
    )

    plan_text = call_llm(prompt)
    plan = plan_text
    try:
        plan_json = parse_planner_json(plan_text)
        plan = json.dumps(plan_json, indent=2)
    except Exception as e:
        print(f"ERROR: Failed to parse planner JSON: {e}")
        if dry_run:
            sys.exit(1)
        plan_json = {"changes": []}

    # New file-ops approach with backward compatibility
    allowlist = cfg.get("files_allowlist", [])
    patch_text = ""

    if "changes" in plan_json and plan_json["changes"]:
        # Preferred new path: write files, stage, generate diff
        patch_text = apply_changes_via_files(plan_json["changes"], allowlist)
    elif plan_json.get("patch"):
        # Backward compatibility: show patch for visibility,
        # but DO NOT git-apply (it's brittle). Leave 'patch_text' as-is for display only.
        patch_text = str(plan_json["patch"])

    # size guard
    max_added = int(cfg.get("policies", {}).get("max_patch_size_lines", 1200))
    if isinstance(patch_text, str):
        added_lines = sum(
            1
            for ln in patch_text.splitlines()
            if ln.startswith("+") and not ln.startswith("+++")
        )
        if added_lines > max_added:
            raise RuntimeError(f"Patch exceeds size cap ({added_lines} > {max_added}).")

    if dry_run:
        print("=== DRY RUN MODE ===")
        print("Plan:")
        print(redact(json.dumps(plan_json, indent=2)))
        print("\nProposed diff:")
        print(patch_text)
        return True

    # Real run:
    branch = f"{cfg.get('branch_prefix','agent/')}{task.get('id','task')}"
    git.create_branch(branch)

    # If we used 'changes', the index is already staged. If we only had 'patch' and no 'changes',
    # there's nothing staged; in that case we simply won't commit.
    if isinstance(patch_text, str) and patch_text.strip() and "changes" in plan_json:
        git.commit_all(f"agent: apply changes for {task.get('id')}")

    tests_ok = tests.run_all()

    if not no_pr:
        report = redact(summarize_run(task, plan, True, tests_ok, tests.last_output()))
        git.open_pr(title=f"agent: {task.get('id')} {task.get('title')}", body=report)

    return tests_ok


def main():
    ap = argparse.ArgumentParser(description="Nox Agent - Safe AI-powered code changes")
    ap.add_argument("--once", action="store_true", help="Run a single cycle")
    ap.add_argument(
        "--dry-run", action="store_true", help="Plan and show diff without applying"
    )
    ap.add_argument(
        "--no-pr", action="store_true", help="Apply patch but skip PR creation"
    )
    args = ap.parse_args()

    try:
        if args.once or not args.dry_run:  # default behavior or explicit --once
            success = run_once(dry_run=args.dry_run, no_pr=args.no_pr)
            sys.exit(0 if success else 1)
        else:
            # one-shot by default for bootstrap to avoid infinite loops in CI
            success = run_once(dry_run=args.dry_run, no_pr=args.no_pr)
            sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nAgent interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
