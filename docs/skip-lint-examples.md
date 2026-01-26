# Skip Lint Action - Usage Examples

This document demonstrates how to use the skip lint feature in the python-ci.yml workflow.

## Method 1: Commit Message

Include `[skip lint]` or `[no lint]` in your commit message:

```bash
# Example 1: Quick documentation fix
git commit -m "docs: update README [skip lint]"
git push

# Example 2: Work in progress commit
git commit -m "WIP: refactoring auth module [no lint]"
git push

# Example 3: Urgent hotfix
git commit -m "fix: critical security patch [skip lint]"
git push
```

## Method 2: Manual Workflow Dispatch

1. Go to GitHub Actions tab in your repository
2. Select "Python CI" workflow
3. Click "Run workflow" button
4. Check the "Skip lint action" checkbox
5. Click "Run workflow"

## When to Skip Lint

✅ **Good Use Cases:**
- Urgent hotfixes that need quick deployment
- Work-in-progress commits to development branches
- Documentation-only changes
- When linting issues are being addressed in a separate PR
- Emergency security patches

❌ **Avoid Skipping Lint When:**
- Making production-ready changes
- Submitting pull requests for review
- Adding new features (unless it's WIP)
- Modifying critical code paths

## What Happens When Lint is Skipped

When you skip lint, the CI workflow will:

1. ✅ Skip the code quality checks:
   - Black formatting
   - isort import sorting
   - flake8 linting
   - Security scanning (Bandit, Safety, pip-audit)

2. ✅ Still run tests:
   - Unit tests with coverage
   - Integration tests
   - Database and Redis service tests

3. ✅ Show a note in the CI summary:
   - "ℹ️ Note: Code quality checks were skipped"

## Testing the Feature

You can test this feature by running:

```bash
# Run the test suite
pytest tests/test_workflow_skip_lint.py -v

# This will verify:
# - Workflow syntax is valid
# - Skip lint input is properly configured
# - Code quality job has proper skip conditions
# - Test job handles skipped lint correctly
# - SBOM job works with skipped lint
# - CI summary acknowledges skipped lint
```

## Example Workflow Run

### With Lint (Default)
```
✅ Code Quality & Security
✅ Run Tests
✅ Generate SBOM
✅ CI Summary
```

### With Lint Skipped
```
⏭️ Code Quality & Security (skipped)
✅ Run Tests
✅ Generate SBOM
✅ CI Summary (with note: "Code quality checks were skipped")
```

## Reverting to Normal

Simply commit without the skip markers to resume normal linting:

```bash
git commit -m "refactor: cleanup auth module"
git push
# This will run all lint checks
```
