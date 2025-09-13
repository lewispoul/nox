# Placeholder for triage_nox.md
# Triage NOX – KEEP, REFACTOR, ARCHIVE

Utiliser cette liste comme vérité terrain. Ce tri est basé sur l’inventaire du dépôt et sur des heuristiques de stabilité.

## KEEP (conserver tel quel)
- README.md
- PROJECT_STRUCTURE.md
- MasterPlan
- Dockerfile
- docker-compose.yml
- docker-compose.dev.yml
- docker-compose.xtb.yml
- pyproject.toml
- requirements.txt
- dev-requirements.txt
- pytest.ini
- Makefile
- redis-cluster.yml
- agent/executor.py
- agent/planner.py
- agent/reporter.py
- agent/instruction_runner.py
- agent/policies.md
- agent/tools/tests.py
- .github/workflows/agent-nightly.yml
- .github/workflows/cd.yml
- .github/workflows/deploy-pi.yml
- .github/workflows/docker-build.yml

## REFACTOR (garder mais réorganiser, typer, tester, consolider)
- requirements-phase2.txt  → consolider dans pyproject.toml
- agent/tools/**           → futurs modules de `nox_core` avec interface publique documentée
- ai/**                    → isoler interfaces, ajouter tests et types
- .github/workflows/**     → homogénéiser les jobs, utiliser le workflow standard python-ci
- scripts/*.sh             → documenter usages, ajouter vérifs d’environnement

Actions attendues
- Ouvrir une issue “Refactor: <chemin>” pour chaque entrée, labels [refactor, hygiene].
- Ajouter des tests unitaires et type hints.

## ARCHIVE (déplacer vers docs/legacy, ne pas supprimer)
- .github/workflows-backup/**
- **/ci.yml.broken
- docs/*session* reports*, *progress* reports*, *milestone* reports*
- anciens guides spécifiques non utilisés, si doublons avec README ou INDEX

Règles
- Créer `docs/legacy/` et y déplacer les éléments ci-dessus en conservant l’arborescence relative.
- Mettre à jour `docs/INDEX.md` pour ne référencer que KEEP.
