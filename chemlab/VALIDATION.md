# Validation du pilote — 19 novembre 2026 (America/Toronto)

Base NOX examinée : `779e80fbeb10665c7996c3d70574ebe625c647dc`.
Le dépôt privé `thesis_ai` a été consulté via GitHub pour définir le format de
passages; son pipeline sémantique et son corpus n’ont pas été exécutés ni copiés.

## Résultats

- `python -m pytest tests/chemlab -q` : **14 réussites**.
- `python -m chemlab.demo` : six opérations API terminées, dont mesure simulée,
  note en brouillon, journal filtré, calcul 900 g / 1 000 mL et recherche sourcée.
- Quatre tests NOX ciblés ont d’abord réussi avec les versions récentes installées.
  Avec FastAPI 0.110.3, Pydantic 2.6.4 et HTTPX 0.27.2, ils donnent **2 réussites,
  2 échecs**, indépendamment des tests ChemLab. Ces mêmes échecs ont été reproduits
  sur la base NOX sans les nouveaux fichiers.
- Aucune preuve d’exécution de matériel réel, de XTB réel, de recherche sémantique,
  de serveur Redis réel ou de déploiement multi-utilisateur.

## Échecs NOX existants à traiter séparément

Commande :

```bash
JOBS_FORCE_LOCAL=1 python -m pytest tests/test_api_minimal.py tests/e2e/test_e2e_hermetic_jobs.py -q
```

1. `test_jobs_flow` attend `pending` mais reçoit `queued` ou `running`.
2. `test_e2e_xtb_with_mock_runner` ne retrouve pas les artefacts cube attendus.

Le comportement varie avec les dépendances et l’exécution asynchrone; aucun
changement de ces routes ou de leurs attentes n’est inclus dans le pilote.

Deux avertissements de dépréciation proviennent des dépendances multipart et
AnyIO/Starlette dans l’environnement de validation. La suite complète NOX n’a
pas été lancée. La recherche documentaire a été validée sur des fixtures
fictives conformes au schéma consulté, pas sur le corpus privé de l’utilisateur.
