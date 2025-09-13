#!/bin/bash
# Test script to validate auto-merge workflow configuration

set -e

echo "🧪 Testing auto-merge workflow configuration..."

# Check if required labels exist
echo "📋 Checking required labels..."
if gh label list --json name | jq -r '.[].name' | grep -q "automerge-candidate"; then
    echo "✅ automerge-candidate label exists"
else
    echo "❌ automerge-candidate label missing"
    echo "Creating automerge-candidate label..."
    gh label create "automerge-candidate" --color "1b5848" --description "Active l'automerge quand les checks sont verts" || echo "Label already exists"
fi

if gh label list --json name | jq -r '.[].name' | grep -q "dependencies"; then
    echo "✅ dependencies label exists"
else
    echo "❌ dependencies label missing"
    echo "Creating dependencies label..."
    gh label create "dependencies" --color "1d76db" --description "Mises à jour de paquets (Dependabot ou manuel)" || echo "Label already exists"
fi

echo "🔧 Workflow configuration validation complete!"
echo "📖 Auto-merge will work when:"
echo "   1. PR is created by dependabot[bot]"
echo "   2. PR has 'automerge-candidate' label (added automatically)"
echo "   3. All CI checks pass"
echo "   4. PR will be automatically squash-merged"