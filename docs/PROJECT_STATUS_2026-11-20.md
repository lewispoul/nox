# État NOx au 20 novembre 2026

Lot `codex/experiment-artifacts-20261120` sur #115 : stockage/API artefacts
implémentés; 58 tests pilote locaux passent. [Contrat](../chemlab/ARTIFACTS.md).
Interface de fichiers et sauvegarde GasCalc restent à réaliser.

Le pilote laboratoire assemblé est sur `codex/chemlab-local-foundation` (#101),
distinct de `main`. Le premier lot et GasCalc sont intégrés à cette branche.
Les PR de modules et de Copilot qui se recouvrent demandent une revue avant merge.

La réparation `codex/pilot-ci-baseline-20261120` reproduit les tests localement
sur Windows, corrige l'instrumentation CRLF du test de courses et ajoute Windows
à la CI laboratoire. Les tests locaux du pilote, GasCalc et FID passent.
Voir [le rapport de session](SESSION_SUMMARY_2026-11-20.md) pour les preuves.
Les dettes de lint globales restent ouvertes; aucune validation globale du dépôt
ni du traitement RMN complet n'est revendiquée.

Prochaine priorité produit : fichiers et artefacts immuables rattachés aux
expériences, puis intégration GasCalc. Contrat proposé dans #114. Téléphone réel,
FT/ppm/phase/intégration, matériel réel et accès réseau restent non validés.
