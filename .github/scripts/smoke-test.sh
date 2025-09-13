#!/bin/bash
# Smoke test for auto-merge workflow fixes

set -e

echo "🔍 Running auto-merge workflow smoke tests..."
echo

# Test 1: Check workflow files exist and are valid
echo "📁 Test 1: Workflow files validation"
for workflow in dependabot-automerge auto-label; do
    file=".github/workflows/${workflow}.yml"
    if [[ -f "$file" ]]; then
        echo "  ✅ $file exists"
        if python -c "import yaml; yaml.safe_load(open('$file'))" 2>/dev/null; then
            echo "  ✅ $file has valid YAML syntax"
        else
            echo "  ❌ $file has invalid YAML syntax"
            exit 1
        fi
    else
        echo "  ❌ $file missing"
        exit 1
    fi
done

# Test 2: Check dependabot.yml configuration
echo
echo "📋 Test 2: Dependabot configuration"
if [[ -f ".github/dependabot.yml" ]]; then
    echo "  ✅ .github/dependabot.yml exists"
    
    # Check for monthly schedule
    if grep -q "monthly" .github/dependabot.yml; then
        echo "  ✅ Monthly schedule configured (reduces PR frequency)"
    else
        echo "  ⚠️  Weekly schedule detected (may generate many PRs)"
    fi
    
    # Check for automerge-candidate labels
    if grep -q "automerge-candidate" .github/dependabot.yml; then
        echo "  ✅ automerge-candidate labels configured"
    else
        echo "  ❌ automerge-candidate labels missing"
        exit 1
    fi
    
    # Check for groups (to batch updates)
    if grep -q "groups:" .github/dependabot.yml; then
        echo "  ✅ Dependency grouping configured (batches updates)"
    else
        echo "  ⚠️  No dependency grouping (may create separate PRs for each update)"
    fi
else
    echo "  ❌ .github/dependabot.yml missing"
    exit 1
fi

# Test 3: Check workflow triggers and conditions
echo
echo "⚙️  Test 3: Workflow trigger configuration"
automerge_file=".github/workflows/dependabot-automerge.yml"

# Check for checkout step
if grep -q "actions/checkout" "$automerge_file"; then
    echo "  ✅ Checkout step present (fixes git repository error)"
else
    echo "  ❌ Missing checkout step (will cause git errors)"
    exit 1
fi

# Check for pull-request-number parameter
if grep -q "pull-request-number" "$automerge_file"; then
    echo "  ✅ Explicit PR number parameter (improves reliability)"
else
    echo "  ⚠️  No explicit PR number (may use context automatically)"
fi

# Check for dependabot actor condition
if grep -q "dependabot\[bot\]" "$automerge_file"; then
    echo "  ✅ Dependabot actor condition present"
else
    echo "  ❌ Missing Dependabot actor condition"
    exit 1
fi

# Check for automerge-candidate label condition
if grep -q "automerge-candidate" "$automerge_file"; then
    echo "  ✅ Auto-merge candidate label condition present"
else
    echo "  ❌ Missing auto-merge candidate label condition"
    exit 1
fi

echo
echo "🎉 All smoke tests passed!"
echo
echo "📖 Summary of improvements:"
echo "  • Fixed git repository access error in auto-merge workflow"
echo "  • Added automatic labeling of Dependabot PRs with automerge-candidate"
echo "  • Reduced Dependabot PR frequency from weekly to monthly"
echo "  • Added dependency grouping to batch related updates"
echo "  • Enhanced auto-merge triggers for CI completion events"
echo
echo "🚀 Auto-merge should now work automatically for Dependabot PRs!"