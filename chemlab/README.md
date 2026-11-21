# ChemLab Assistant — pilote local NOX

Première base exécutable, distincte de l’API de calcul NOX. Le pilote ajoute un
registre d’appareils simulés, un journal SQLite, des notes en brouillon, un calcul
d’inventaire et un pont documentaire vers un export local `thesis_ai`.
Aucun matériel, moteur de calcul, modèle IA ou service externe n’est appelé.

## Exécuter

Depuis la racine du dépôt, Python 3.11+ :

```bash
python -m venv .venv
. .venv/bin/activate
pip install 'fastapi>=0.110,<0.111' 'pydantic>=2.6,<2.7' 'uvicorn>=0.35,<0.36' 'httpx>=0.27,<0.28'
python -m chemlab.demo
```

La démo crée des données fictives dans un répertoire temporaire, utilise l’API
sans ouvrir de port, puis supprime ses fichiers temporaires. Pour conserver les
observations et servir l’API sur **la boucle locale uniquement** :

```bash
export CHEMLAB_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export CHEMLAB_DB=.run/chemlab.sqlite3
uvicorn chemlab.app:create_app --factory --host 127.0.0.1 --port 8090
```

Dans un second terminal, utiliser le même jeton :

```bash
curl -H "Authorization: Bearer $CHEMLAB_TOKEN" http://127.0.0.1:8090/health
curl -H "Authorization: Bearer $CHEMLAB_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"id":"balance-demo","name":"Balance simulée","location":"Banc fictif","capability":"mass.read_stable"}' \
  http://127.0.0.1:8090/devices
```

Le jeton est commun à ce pilote mono-utilisateur, pas une identité individuelle.
Pas de CORS, de documentation interactive publique ni de route de commande
physique. Ne pas exposer ce pilote sur un LAN ou Internet : l’authentification
multi-utilisateur, TLS et les permissions par expérience restent à intégrer.
Le système d’exploitation doit protéger le jeton, le fichier SQLite et les exports.

## Contrats de la première version

| Route | Fonction |
| --- | --- |
| `GET /health` | Mode simulation et nombre de passages chargés |
| `GET/POST /devices` | Registre immuable par identifiant, adaptateur `simulated` uniquement |
| `POST /observations` | Mesure liée à une expérience, unité et stabilité contrôlées |
| `POST /notes` | Note manuelle `draft_local`, sans écriture dans un cahier externe |
| `GET /events?experiment_id=DEMO-001&limit=100` | Journal filtré, limite maximale 500 |
| `POST /inventory/calculate` | Masse nette et volume facultatif, décimaux renvoyés comme chaînes |
| `GET /literature/search?q=stable%20mass&limit=5` | Passages, source, page connue, score lexical et empreinte d’export |

Observation :

```json
{"event_id":"reading-1","device_id":"balance-demo","experiment_id":"DEMO-001","value":12.5,"unit":"g","stable":true,"observed_at":"2026-01-01T12:00:00Z"}
```

Capacités : `temperature.read` accepte `degC`; `mass.read_stable` accepte `g`
avec `stable=true`. L’adaptateur est simulé et les événements de mesure portent
`source=simulated`. `observed_at` doit inclure un fuseau; `recorded_at` est généré
par le serveur en UTC. L’expérience est une étiquette de regroupement, pas encore
une entité vérifiée contre un cahier. Aucun statut ne prétend que l’appareil réel
est connecté, calibré ou en ligne.

Même `event_id` et même contenu normalisé : résultat initial retourné, y compris
après redémarrage. Même identifiant avec un autre contenu : HTTP 409. La clé est
partagée entre notes et observations. Les transactions SQLite sérialisent les
réessais concurrents. Pas de modification ni suppression des événements par l’API.

Calcul d’inventaire :

```json
{"gross_g":"1240","tare_g":"340","density_g_ml":"0.9","tare_kind":"estimated"}
```

Résultat de référence : 900 g et 1 000 mL. Cette référence a été calculée avec
Wolfram lors de la conception du portail; le code fonctionne sans Wolfram.
La densité est fournie par l’utilisateur et aucune incertitude n’est évaluée.
Sans densité, aucun volume n’est produit. Une tare estimée reste explicitement
estimée. Ceci n’implémente pas encore un inventaire de bouteilles ni des commandes.

## Utiliser `thesis_ai` sans copier son corpus

Le dépôt privé `lewispoul/thesis_ai` reste indépendant. Ses fichiers de recherche,
son README et son dossier de reprise ont servi à définir ce pont; aucun code du
dépôt privé ni aucun contenu de thèse n’a été copié dans NOX.

1. Construire l’index dans `thesis_ai` avec ses propres commandes et dépendances.
2. Sélectionner **un export autorisé pour l’utilisateur local** `data/index/records.jsonl`.
3. Avant le démarrage du pilote :

```bash
export CHEMLAB_LITERATURE_INDEX=/chemin/autorise/thesis_ai/data/index/records.jsonl
```

Chaque ligne doit être un objet avec `source_name` et `text` non vides.
`page_number` est un entier positif facultatif (`page` est accepté en repli).
Les métadonnées supplémentaires sont ignorées; les chemins de PDF ne sont jamais
ouverts. Une ligne invalide fait échouer explicitement le chargement.
Le fichier est lu une seule fois au démarrage, avec une limite pilote de 20 Mo.
Redémarrer après modification de l’export. La réponse porte son SHA-256 et une
référence de ligne stable dans cet export précis. Les pages inconnues restent nulles.

Le classement est la couverture des mots de la question, **pas** une similarité
sémantique ni une probabilité de justesse. Aucun modèle n’est téléchargé, aucune
réponse n’est générée et aucune procédure n’est déclarée approuvée. La recherche
sémantique, le reranking et les réponses de `thesis_ai` ne sont pas encore branchés.
Un export ne doit contenir que les documents autorisés pour ce pilote unique :
il n’y a pas de contrôle d’accès par document ni de séparation entre utilisateurs.

## Validation

```bash
pip install 'pytest>=8.2,<9' 'pytest-asyncio>=0.26,<0.27' fakeredis dramatiq redis python-multipart
python -m pytest tests/chemlab -q
JOBS_FORCE_LOCAL=1 python -m pytest tests/test_api_minimal.py tests/e2e/test_e2e_hermetic_jobs.py -q
python -m chemlab.demo
```

La suite vérifie persistance, réessais concurrents, conflits d’identifiants,
unités, stabilité, authentification, absence de commandes physiques, calculs et
citations de l’export documentaire. Les essais NOX existants utilisent un runner
simulé et ne prouvent pas l’exécution de XTB ou de matériel réel.

## Suite bornée

- Ajouter un contrat d’adaptateur et un premier capteur sur banc d’essai.
- Introduire les expériences, identités et permissions avant un usage partagé.
- Relier le moteur de recherche sémantique `thesis_ai` derrière une interface dédiée.
- Évaluer la réutilisation des tâches NOX pour les calculs longs; ne pas relier
  les commandes physiques à l’agent d’exécution Python/shell.
- Compléter inventaire par contenant, provenance de densité, expiration et bons
  de commande en brouillon; puis interfaces tactiles et dictée.
