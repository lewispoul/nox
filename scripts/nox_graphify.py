"""Build/query the optional local code graph using a separate Python environment."""

import argparse
import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / ".run" / "graphify-out" / "graph.json"
VERSION = "0.9.114"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build", help="Local code AST extraction; no LLM backend")
    query = commands.add_parser("query", help="Search the existing local graph")
    query.add_argument("question")
    commands.add_parser("html", help="Export an interactive HTML graph")
    args = parser.parse_args()
    try:
        installed = importlib.metadata.version("graphifyy")
    except importlib.metadata.PackageNotFoundError:
        parser.error("Install tools/graphify/requirements.txt in .venv-graphify first.")
    if installed != VERSION:
        parser.error(f"Expected graphifyy {VERSION}, found {installed}.")
    # Keep outputs inside the checkout even when a parent shell sets an override.
    env = dict(os.environ, GRAPHIFY_OUT="graphify-out", PYTHONUTF8="1")
    command = [sys.executable, "-m", "graphify"]
    if args.command == "build":
        command += [
            "extract",
            str(ROOT),
            "--code-only",
            "--max-workers",
            "1",
            "--out",
            str(ROOT / ".run"),
        ]
    else:
        if not GRAPH.is_file():
            parser.error("No graph yet. Run the build command first.")
        if args.command == "query":
            command += ["query", args.question, "--graph", str(GRAPH)]
        else:
            command += ["export", "html", "--graph", str(GRAPH)]
    result = subprocess.run(command, cwd=ROOT, env=env, check=False)
    if result.returncode:
        return result.returncode
    if args.command == "build" and not GRAPH.is_file():
        parser.error("Graphify exited without producing the expected graph.json.")
    if args.command == "html":
        print(f"Viewer: {GRAPH.with_name('graph.html')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
