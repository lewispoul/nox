# Placeholder for copilot_prompt_nox.md
# Copilot Prompt – NOX (hygiene stage 1)

Contexte
Tu travailles dans le dépôt NOX sur une branche dédiée. Utilise `triage_nox.md` comme vérité terrain.

Objectifs
1) Générer `docs/INDEX.md` qui liste uniquement les documents KEEP.
2) Déplacer les éléments ARCHIVE vers `docs/legacy/` en conservant l’arborescence.
3) Créer `.pre-commit-config.yaml` avec ruff, black, isort, mypy, detect-secrets.
4) Ajouter `.github/workflows/python-ci.yml` basé sur un workflow standard Python: lint, type-check, tests avec coverage, build Docker, Trivy, SBOM Syft, Grype, upload artefacts.
5) Ouvrir des issues pour chaque entrée REFACTOR avec titre “Refactor: <chemin>”.
6) Ouvrir une PR intitulée “chore, repo hygiene and docs consolidation, stage 1” avec une checklist.

Détails d’implémentation
- `docs/INDEX.md` doit contenir des liens relatifs fonctionnels.
- `docs/legacy/` ne remplace pas, on ne supprime rien.
- `.pre-commit-config.yaml` complet, compatible Python 3.11, propose la commande `pre-commit install`.
- Le workflow CI doit sortir les artefacts `coverage.xml`, `trivy.json`, `sbom.json`, `grype.json`.
- Si des workflows existants font doublon, ne pas les supprimer, les laisser vivre en parallèle pour cette PR.

Critères d’acceptation
- CI verte sur la PR.
- Hooks pre-commit exécutables.
- INDEX propre et `docs/legacy/` présent.
- Issues de refactor ouvertes.

Quand tu es prêt, propose le diff complet des fichiers à créer ou modifier, puis applique et commite.
