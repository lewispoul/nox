# Placeholder for copilot_master_brief.md
# Copilot Master Brief – NOX Suite

## Contexte et objectif
Tu agis en tant qu’assistant d’ingénierie pour 5 dépôts: NOX, Pinox, IAM, IAM-pi, IAM 2.0. Le but est d’unifier l’hygiène, la CI, la doc, normaliser l’API, et dégager un noyau factorisé `nox_core`.

## Rôles cibles
- NOX, moteur agent factorisé, expose une API publique stable, fournit les tools génériques fs, git, shell, tests.
- IAM 2.0, agent stable et industrialisable avec API OpenAPI.
- Pinox, orchestrateur et UI, dépend de nox_core et de l’API IAM 2.0.
- IAM 1.x et IAM-pi, archives et annexes d’environnement.

## Tâches standard à exécuter dans chaque dépôt
1. Créer `docs/INDEX.md` qui référence uniquement les documents à garder.
2. Déplacer les docs obsolètes vers `docs/legacy/` sans supprimer.
3. Ajouter `.pre-commit-config.yaml` et proposer `pre-commit install`.
4. Ajouter un workflow CI `.github/workflows/python-ci.yml` avec lint, mypy, tests, build Docker, scans Trivy, SBOM Syft, Grype, upload artefacts.
5. Ouvrir une PR “chore, repo hygiene and docs consolidation, stage 1”, joindre un diff propre et la checklist.

## Spécifique à NOX
- S’appuyer sur `triage_nox.md` comme vérité terrain pour KEEP, REFACTOR, ARCHIVE.
- Après l’hygiène, proposer une PR d’extraction d’un paquet Python `nox_core` avec interface publique claire et tests.

## Spécifique à IAM 2.0
- Générer OpenAPI, publier `openapi.json` en artefact CI.
- Ajouter des tests contractuels Schemathesis qui échouent si 5xx.

## Contraintes et bonnes pratiques
- Aucune fuite de secrets.
- Changements idempotents et PRs petites mais complètes.
- Conserver l’historique: on déplace en `docs/legacy/`, on ne supprime pas.

## Style de réponse attendu
- Avant de modifier des fichiers, proposer le plan et l’arborescence.
- Afficher les diffs et les nouveaux contenus.
- Proposer la commande Git correspondante si utile.
- Utiliser le ton clair, précis, sans jargon inutile.

## Critères d’acceptation généraux (PR d’hygiène)
- `docs/INDEX.md` présent, `docs/legacy/` créé, liens OK.
- `.pre-commit-config.yaml` présent, hooks exécutables.
- CI verte, artefacts `coverage.xml`, `trivy.json`, `sbom.json`, `grype.json` disponibles.
- Issues “Refactor” ouvertes pour les éléments de la section REFACTOR du triage.

Fin du brief.
