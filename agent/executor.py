# file: agent/executor.py
from __future__ import annotations
import argparse, json, yaml, os, re, subprocess, sys
from pathlib import Path
from agent.tools import fs, git, shell, tests, codeedit
from agent.planner import build_planner_prompt, parse_planner_json
from agent.reporter import summarize_run

def load_config():
    try:
        import yaml as _yaml
        return _yaml.safe_load(fs.read("agent/config.yaml")) or {}
    except Exception:
        return {}

def redact(text: str) -> str:
    """Redact secrets and keys from text to prevent leakage."""
    # Redact OpenAI API keys
    text = re.sub(r"sk-[A-Za-z0-9]{10,}", "sk-***REDACTED***", text)
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
        if current_branch == "main":
            print("ERROR: Agent cannot run on main branch. Switch to a feature branch.")
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("ERROR: Failed to check current branch")
        sys.exit(1)
    
    # Check if working tree is dirty
    try:
        status = subprocess.check_output(
            "git status --porcelain", shell=True, text=True
        ).strip()
        if status:
            print("ERROR: Working tree is dirty. Commit or stash changes before running agent.")
            sys.exit(1)
    except subprocess.CalledProcessError:
        print("ERROR: Failed to check git status")
        sys.exit(1)

def call_llm(prompt: str) -> str:
    """Call OpenAI API with the planner prompt."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are the Nox Planner. Output only JSON per planner.py spec."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=2000
        )
        
        return response.choices[0].message.content
    except ImportError:
        raise RuntimeError("openai package not installed. Run: pip install openai")
    except Exception as e:
        raise RuntimeError(f"OpenAI API call failed: {e}")

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
    
    # Simple application via 'git apply' to keep it robust
    from subprocess import check_call, CalledProcessError
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
    prompt = build_planner_prompt(ctx["task_yaml"], ctx["repo_tree"], ctx["file_snippets"])

    plan_text = call_llm(prompt)
    plan = plan_text
    try:
        plan_json = parse_planner_json(plan_text)
        plan = json.dumps(plan_json, indent=2)
    except Exception as e:
        print(f"ERROR: Failed to parse planner JSON: {e}")
        if dry_run:
            sys.exit(1)
        plan_json = {"patch": ""}

    if dry_run:
        # Dry-run: print redacted plan and diff, then exit
        print("=== DRY RUN MODE ===")
        print("Plan:")
        print(redact(plan))
        print("\nProposed diff:")
        print(redact(plan_json.get("patch", "")))
        return True

    branch = f"{cfg.get('branch_prefix','agent/')}{task.get('id','task')}"
    git.create_branch(branch)

    patch_ok = apply_patch(plan_json.get("patch",""), cfg.get("files_allowlist", []), cfg)
    if patch_ok:
        git.commit_all(f"agent: apply patch for {task.get('id')}")

    tests_ok = tests.run_all()
    
    if not no_pr:
        report = redact(summarize_run(task, plan, patch_ok, tests_ok, tests.last_output()))
        git.open_pr(title=f"agent: {task.get('id')} {task.get('title')}", body=report)
    
    return tests_ok

def main():
    ap = argparse.ArgumentParser(description="Nox Agent - Safe AI-powered code changes")
    ap.add_argument("--once", action="store_true", help="Run a single cycle")
    ap.add_argument("--dry-run", action="store_true", help="Plan and show diff without applying")
    ap.add_argument("--no-pr", action="store_true", help="Apply patch but skip PR creation")
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
