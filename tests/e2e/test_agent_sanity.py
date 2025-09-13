# file: tests/e2e/test_agent_sanity.py
import pathlib

import yaml


def test_backlog_exists_and_has_tasks():
    path = pathlib.Path("agent/tasks/backlog.yaml")
    assert path.exists(), "backlog.yaml missing"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) >= 1


def test_config_exists():
    path = pathlib.Path("agent/config.yaml")
    assert path.exists(), "agent/config.yaml missing"
