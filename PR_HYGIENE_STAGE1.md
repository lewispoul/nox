# PR: Repository Hygiene and Documentation Consolidation - Stage 1

## Description
Cette PR implémente la première étape de l'initiative d'hygiène du référentiel NOX selon le master brief. L'objectif est d'unifier l'organisation de la documentation, d'améliorer la CI, et de préparer l'extraction future de `nox_core`.

## Changements effectués

### 📚 Documentation
- ✅ **Créé `docs/INDEX.md`** - Index centralisé référençant uniquement la documentation active
- ✅ **Créé `docs/legacy/`** - Répertoire pour la documentation archivée
- ✅ **Déplacé les documents obsolètes** vers `docs/legacy/` (rapports de session, progression, jalons)
- ✅ **Conservé l'historique** - Aucun document supprimé, seulement déplacé

### 🔧 CI/CD et outils de développement
- ✅ **Workflow CI standardisé** - Créé `.github/workflows/python-ci.yml` avec :
  - Lint (ruff, black, isort)
  - Type checking (mypy)
  - Tests avec couverture
  - Build Docker
  - Scans de sécurité (Trivy)
  - SBOM (Syft) et vulnérabilités (Grype)
  - Upload d'artefacts
- ✅ **Pre-commit hooks** - `.pre-commit-config.yaml` déjà présent et configuré
- ✅ **Template d'issues** - Template pour les tâches de refactoring

### 📋 Planification du refactoring
- ✅ **Issues Refactor préparées** - `REFACTOR_ISSUES.md` liste les tâches selon `triage_nox.md`
- ✅ **Template d'issues** - Template standardisé pour les tâches de refactoring

## Structure après changements

```
docs/
├── INDEX.md                    # ✨ Nouveau - Index centralisé
├── legacy/                     # ✨ Nouveau - Documentation archivée
│   ├── README.md              # ✨ Nouveau - Explication du contenu
│   ├── session-reports/       # 📦 Déplacé
│   ├── progress-reports/      # 📦 Déplacé
│   ├── milestone-reports/     # 📦 Déplacé
│   └── ...                    # 📦 Autres rapports déplacés
├── README.md                  # ✅ Conservé
├── architecture/              # ✅ Conservé
└── ...                        # ✅ Autres docs actives

.github/workflows/
├── python-ci.yml              # ✨ Nouveau - Workflow CI standardisé
├── agent-nightly.yml          # ✅ Conservé
├── cd.yml                     # ✅ Conservé
└── ...                        # ✅ Autres workflows conservés

REFACTOR_ISSUES.md              # ✨ Nouveau - Liste des issues à créer
```

## Critères d'acceptation ✅

- [x] `docs/INDEX.md` présent et référence les documents actifs
- [x] `docs/legacy/` créé avec documentation archivée
- [x] Liens dans `docs/INDEX.md` vérifiés et fonctionnels
- [x] `.pre-commit-config.yaml` présent (déjà existant et configuré)
- [x] Workflow CI avec tous les composants requis (lint, tests, Docker, scans)
- [x] Artefacts CI configurés (coverage.xml, trivy.json, sbom.json, grype.json)
- [x] Issues "Refactor" préparées pour les éléments du triage

## Prochaines étapes

Les issues suivantes doivent être créées avec les labels `[refactor, hygiene]` :

1. **Refactor: requirements-phase2.txt** - Consolider dans pyproject.toml
2. **Refactor: agent/tools/**** - Préparer l'extraction de nox_core
3. **Refactor: ai/**** - Isoler interfaces, ajouter tests et types
4. **Refactor: .github/workflows/**** - Homogénéiser les workflows
5. **Refactor: scripts/*.sh** - Documenter et sécuriser

## Impact

- ✅ **Zero breaking changes** - Aucun changement de fonctionnalité
- ✅ **Documentation mieux organisée** - Plus facile de trouver l'information
- ✅ **CI standardisée** - Workflow uniforme avec sécurité renforcée
- ✅ **Préparation du refactoring** - Base solide pour les étapes suivantes

## Tests

Le workflow CI incluant les tests peut être déclenché automatiquement sur cette PR pour vérifier que tout fonctionne correctement.

---

*Cette PR fait partie de l'initiative d'hygiène de la suite NOX visant à unifier l'hygiène, la CI, la documentation et préparer l'extraction de `nox_core`.*