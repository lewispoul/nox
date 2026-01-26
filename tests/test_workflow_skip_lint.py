#!/usr/bin/env python3
"""
Test to verify GitHub Actions workflow skip lint functionality

This test validates that the python-ci.yml workflow properly supports
skipping lint checks via workflow inputs and commit messages.
"""

import yaml
import pytest
from pathlib import Path


@pytest.fixture
def workflow():
    """Load the python-ci.yml workflow"""
    workflow_path = Path(__file__).parent.parent / ".github" / "workflows" / "python-ci.yml"
    with open(workflow_path, "r") as f:
        return yaml.safe_load(f)


def test_workflow_syntax_valid(workflow):
    """Test that the workflow YAML is syntactically valid"""
    assert workflow is not None
    assert "name" in workflow
    assert "jobs" in workflow


def test_workflow_dispatch_has_skip_lint_input(workflow):
    """Test that workflow_dispatch has skip_lint input"""
    # Note: 'on' is parsed as True in YAML (boolean alias)
    triggers = workflow.get(True, {})
    assert "workflow_dispatch" in triggers, "workflow_dispatch trigger missing"
    
    workflow_dispatch = triggers["workflow_dispatch"]
    if workflow_dispatch is not None:
        inputs = workflow_dispatch.get("inputs", {})
        assert "skip_lint" in inputs, "skip_lint input missing"
        assert inputs["skip_lint"]["type"] == "boolean", "skip_lint should be boolean"
        assert inputs["skip_lint"]["default"] is False, "skip_lint should default to False"


def test_code_quality_job_has_skip_conditions(workflow):
    """Test that code-quality job has proper skip conditions"""
    code_quality = workflow["jobs"]["code-quality"]
    assert "if" in code_quality, "code-quality job missing 'if' condition"
    
    condition = code_quality["if"]
    # Check that all skip conditions are present
    assert "skip_lint" in condition, "skip_lint input check missing"
    assert "[skip lint]" in condition, "[skip lint] commit message check missing"
    assert "[no lint]" in condition, "[no lint] commit message check missing"


def test_test_job_handles_skipped_lint(workflow):
    """Test that test job runs even if code-quality is skipped"""
    test_job = workflow["jobs"]["test"]
    
    # Test job depends on code-quality
    assert "needs" in test_job, "test job missing 'needs'"
    assert "code-quality" in test_job["needs"], "test job should depend on code-quality"
    
    # Test job should handle skipped code-quality
    assert "if" in test_job, "test job missing 'if' condition"
    condition = test_job["if"]
    assert "skipped" in condition, "test job doesn't handle skipped code-quality"
    assert "always()" in condition, "test job should use always() to run after skip"


def test_sbom_job_handles_skipped_lint(workflow):
    """Test that SBOM job properly depends on test results, not lint"""
    sbom_job = workflow["jobs"]["sbom"]
    
    assert "needs" in sbom_job
    assert "test" in sbom_job["needs"]
    
    # SBOM should check test result, allowing lint to be skipped
    condition = sbom_job["if"]
    assert "test.result" in condition, "SBOM should check test results"


def test_ci_summary_acknowledges_skipped_lint(workflow):
    """Test that CI summary properly reports when lint is skipped"""
    ci_summary = workflow["jobs"]["ci-summary"]
    
    # Find the step that reports results
    report_step = None
    for step in ci_summary["steps"]:
        if "CI Summary Report" in step.get("name", ""):
            report_step = step
            break
    
    assert report_step is not None, "CI Summary Report step not found"
    
    # Check that the report mentions skipped lint
    run_script = report_step["run"]
    assert "skipped" in run_script.lower(), "CI summary should mention skipped status"
