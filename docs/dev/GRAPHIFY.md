# Graphify for NOx development

This optional tool maps the repository's code into a local knowledge graph.
It is separate from the FastAPI runtime and does not add a laboratory endpoint.
The integration pins `graphifyy[sql]==0.9.114` from
[Graphify-Labs](https://github.com/Graphify-Labs/graphify).
Upstream code inspected at `b582ad401aaef4378935ec6620e3b165ae8e03c1`.
The SQL extra supports the repository's database schemas.

## Windows PowerShell

Run from the NOx checkout, with Python 3.12 installed:

```powershell
py -3.12 -m venv .venv-graphify
.\.venv-graphify\Scripts\python.exe -m pip install -r tools/graphify/requirements.txt
.\.venv-graphify\Scripts\python.exe scripts/nox_graphify.py build
.\.venv-graphify\Scripts\python.exe scripts/nox_graphify.py query "ChemLab Store create_app"
.\.venv-graphify\Scripts\python.exe scripts/nox_graphify.py html
```

If using uv, replace the first two commands with:

```powershell
uv venv --python 3.12 .venv-graphify
uv pip install --python .venv-graphify/Scripts/python.exe -r tools/graphify/requirements.txt
```

## Linux/macOS

```bash
python3.12 -m venv .venv-graphify
.venv-graphify/bin/python -m pip install -r tools/graphify/requirements.txt
.venv-graphify/bin/python scripts/nox_graphify.py build
.venv-graphify/bin/python scripts/nox_graphify.py query 'ChemLab Store create_app'
.venv-graphify/bin/python scripts/nox_graphify.py html
```

The script resolves the checkout root, so queries also work from another current
directory when given the script's full path. Re-run build after source changes;
Graphify maintains its incremental cache. Query requires an existing graph.
Outputs live in `.run/graphify-out/`, including `graph.json`, analysis and cache.
The HTML command prints the viewer location. Generated graphs and environments
are ignored by Git; they can contain source snippets and local paths.

## Scope and limitations

Build always requests `--code-only` and one AST worker. It uses no LLM backend
or API key. Docs, papers and images receive no semantic extraction in this mode.
The first dependency installation requires Internet access. HTML exports may
reference external viewer assets; local extraction does not imply an offline
browser viewer. No hosted graph upload, global assistant configuration, MCP
server, agent skill or Git hook is installed by these repo commands.

`.graphifyignore` excludes runtime records, archives, virtual environments,
dependency trees, credentials and large generated datasets. It complements
Git ignore rules, not a guarantee that arbitrary new files contain no secrets.
Review files and exclusions before indexing a checkout with private additions.
Only the separate clean worktree was indexed during this integration; existing
uncommitted GasCalc work in the other checkout was preserved.

Edges carry Graphify's extraction/confidence metadata. Some relationships are
heuristic even in code-only mode. Treat results as navigation aids and confirm
them in source and tests; a graph is not evidence of scientific correctness or
working runtime behavior. The pinned upstream dependency has its own license
and notices; see its Apache-2.0 license and bundled legacy notices.

## Verification

```powershell
.\.venv-graphify\Scripts\python.exe -m unittest discover -s tests/tools -p test_graphify_policy.py
```

The policy test uses Graphify's real detector against synthetic source/data
files. GitHub's `Graphify local code graph` workflow runs that test, builds the
repository graph, queries it and exports HTML on Windows and Linux. Dependencies
are isolated from the pilot; transitive versions are not fully locked.
