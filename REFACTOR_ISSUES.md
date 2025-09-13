# Issues Refactor à créer - NOX Repository Hygiene

Selon le triage dans `triage_nox.md`, voici les issues à créer avec les labels [refactor, hygiene] :

## 1. Refactor: requirements-phase2.txt
**Description:** Consolider requirements-phase2.txt dans pyproject.toml
**Problème:** Duplication des dépendances entre plusieurs fichiers requirements
**Solution:** Migrer toutes les dépendances vers pyproject.toml avec des groupes optionnels

## 2. Refactor: agent/tools/**
**Description:** Restructurer agent/tools pour préparer nox_core
**Problème:** Interface publique non définie, manque de tests et types
**Solution:** Créer une interface publique claire, ajouter types et tests

## 3. Refactor: ai/**
**Description:** Isoler interfaces AI et ajouter tests et types
**Problème:** Interfaces AI non clairement définies, manque de tests
**Solution:** Séparer les interfaces, ajouter type hints et tests unitaires

## 4. Refactor: .github/workflows/**
**Description:** Homogénéiser les workflows CI/CD
**Problème:** Workflows hétérogènes, duplication de code
**Solution:** Standardiser avec le workflow python-ci, réutiliser les actions

## 5. Refactor: scripts/*.sh
**Description:** Documenter et sécuriser les scripts shell
**Problème:** Scripts sans documentation, vérifications d'environnement manquantes
**Solution:** Ajouter documentation, vérifications d'env, gestion d'erreurs

---

## Commandes GitHub CLI pour créer les issues

```bash
gh issue create --title "Refactor: requirements-phase2.txt" --label "refactor,hygiene" --body "Consolider requirements-phase2.txt dans pyproject.toml pour éviter la duplication des dépendances."

gh issue create --title "Refactor: agent/tools/**" --label "refactor,hygiene" --body "Restructurer agent/tools/ pour préparer l'extraction de nox_core avec interface publique claire, types et tests."

gh issue create --title "Refactor: ai/**" --label "refactor,hygiene" --body "Isoler les interfaces AI, ajouter tests unitaires et type hints pour améliorer la maintenabilité."

gh issue create --title "Refactor: .github/workflows/**" --label "refactor,hygiene" --body "Homogénéiser les workflows CI/CD en utilisant le workflow python-ci standard et réduire la duplication."

gh issue create --title "Refactor: scripts/*.sh" --label "refactor,hygiene" --body "Documenter les scripts shell, ajouter des vérifications d'environnement et améliorer la gestion d'erreurs."
```

---
*Ces issues sont créées dans le cadre de l'initiative d'hygiène du référentiel NOX (stage 1).*