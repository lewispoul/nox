# Session du 20 novembre 2026 : baseline laboratoire Windows

## Suite : intégration Graphify

Branche `codex/graphify-integration-20261120`, empilée sur la réparation #115.
Worktree séparé `C:\Users\pouli\source\nox-graphify` pour préserver les
modifications GasCalc non committées du checkout existant.

Ajout d'un outil développeur facultatif, `graphifyy[sql]==0.9.114`, isolé du
runtime NOx. Le script `scripts/nox_graphify.py` construit un graphe de code
local, le recherche et exporte HTML. La politique `.graphifyignore` exclut les
données/runtime, secrets, archives, dépendances et grandes données générées.
Aucune installation de skill global, MCP, hook Git ou backend LLM.

Validation Windows Python 3.12.12 : installation facultative réussie; test
`python -m unittest discover -s tests/tools -p test_graphify_policy.py` réussi;
build initial puis incrémental réussis. Après installation du parseur SQL,
le graphe contient 4 918 nœuds et 7 833 liens. La recherche
`python scripts/nox_graphify.py query "ChemLab Store create_app"` retrouve
Store, create_app et les routes/tests associés. L'export HTML est présent sous
`.run/graphify-out/graph.html` (3 935 846 octets lors du contrôle).
Aucune source des dossiers exclus archive/data/logs/.run/.venv n'est présente
dans les nœuds contrôlés. Black et Flake8 passent sur les deux nouveaux scripts
Python. La CI Windows/Linux est ajoutée; consulter son résultat sur la PR.
Guide : [docs/dev/GRAPHIFY.md](dev/GRAPHIFY.md).

Le premier run CI Linux passe. Windows a exposé un chemin TEMP avec alias 8.3
(`RUNNER~1`) : le test comparait cet alias au chemin long résolu par Graphify.
La racine temporaire du test est désormais résolue avant comparaison; aucune
exclusion ni assertion n'est retirée. Consulter le run du commit corrigé.

Limites : graphe de navigation de code, pas extraction sémantique de documents,
preuve d'exécution NOx ou validation scientifique. Dépendances transitives non
verrouillées intégralement. L'HTML peut référencer des ressources externes.
Le graphe généré reste local et ignoré par Git. Aucun merge ni déploiement.

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
