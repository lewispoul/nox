# Session du 20 novembre 2026 : baseline laboratoire Windows

La reprise locale fonctionne dans `C:\Users\pouli\source\nox-pilot-fix`.
Base Git : `d2b1d47541f9713fe97a596caaadcd250cbd6ef5`, branche pilote de #101.
Travail proposé sur `codex/pilot-ci-baseline-20261120`.

## Problème et correction

Le test `tests/chemlab/ui/races.test.cjs` échouait sur le checkout CRLF Windows
avant d'exécuter ses scénarios : le remplacement du script supposait LF.
Normalisation uniquement dans la VM, puis vérification du scénario de réponse
tardive avec les deux conventions de fin de ligne. Aucun changement du script
UI livré. Les huit fichiers Python du pilote signalés par Black ont été formatés.

Le workflow laboratoire utilise désormais Windows et Linux, un shell Bash
avec arrêt sur erreur, des versions épinglées de Black/Flake8 et les contrôles
de style du pilote. Les pushes sur la branche pilote déclenchent aussi les tests.
Les workflows de lint globaux restent actifs et leur dette reste ouverte.

## Commandes et résultats locaux

Python 3.12.12, Node 26.13.1, données fictives et fixture publique uniquement.

| Commande | Résultat |
|---|---|
| `python -m black --workers 1 --check chemlab tests/chemlab` | 9 fichiers conformes |
| `python -m flake8 chemlab tests/chemlab` | Passe |
| `python -m pytest tests/chemlab -q` | 27 réussites, 1 avertissement Starlette/AnyIO |
| `node tests/chemlab/ui/app.test.cjs` | Passe |
| `node tests/chemlab/ui/races.test.cjs` | Passe, LF et CRLF inclus |
| `node chemlab/web/gascalc/tests.cjs` | 13 965 points passent |
| `node chemlab/web/gascalc/integration-tests.cjs` | DOM simulé passe |
| `npm ci --ignore-scripts --prefix nmr-spike` | 151 paquets installés, audit npm sans vulnérabilité signalée |
| `npm run fetch-fixture --prefix nmr-spike` | SHA-256 attendu confirmé |
| `npm test --prefix nmr-spike` | 8 192 paires FID comparées |
| `python -m chemlab.demo` | Six opérations réussies |
| `git diff --check` | Passe |

Les commandes Python utilisent l'environnement local `.venv-pilot`. Les versions
des dépendances directes du pilote restent inchangées; les transitives ne sont
pas encore verrouillées intégralement. Le moteur FID ancien présente toujours
l'axe non fini déjà documenté. Aucun test tactile ni serveur réseau lancé.

## Suite

Consulter la CI sur le commit de cette PR. La proposition de contrat artefacts
est dans #114. L'implémentation fichiers/artefacts reste le prochain lot produit.
Conserver une seule voie d'intégration pour les PR qui se recouvrent et traiter
la dette globale Black/Super-Linter séparément. Aucune fusion ni mise en service.
