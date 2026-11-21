"""Exercise repository exclusions with Graphify's real file detector."""

from pathlib import Path
import tempfile
import unittest

from graphify.detect import detect

ROOT = Path(__file__).resolve().parents[2]


class GraphifyPolicyTests(unittest.TestCase):
    def test_local_data_and_dependencies_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            # Windows runners may expose TEMP through an 8.3 alias. Graphify
            # resolves paths; use the same canonical root for comparisons.
            root = Path(directory).resolve()
            (root / ".graphifyignore").write_bytes(
                (ROOT / ".graphifyignore").read_bytes()
            )
            included = ["chemlab/app.py", "api/main.py", "nox/jobs/storage.py"]
            excluded = [
                ".venv-graphify/site-packages/example.py",
                ".run/private.py",
                "data/experiment.py",
                "logs/session.py",
                "archive/old.py",
                "node_modules/lib/index.js",
                "docs-interactive/node_modules/lib/index.js",
                "chemlab/web/gascalc/data.json",
                "k8s/secrets.yaml",
                ".env",
            ]
            for name in included + excluded:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("value = 1\n", encoding="utf-8")
            files = detect(root)["files"]
            found = {
                Path(path).relative_to(root).as_posix()
                for group in files.values()
                for path in group
            }
            self.assertTrue(set(included).issubset(found), found)
            self.assertFalse(set(excluded) & found, found)


if __name__ == "__main__":
    unittest.main()
