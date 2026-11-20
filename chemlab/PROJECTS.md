# NOx — registre des projets et expériences

Le pilote possède un registre SQLite local, persistant et mono-utilisateur.
Toutes les routes ci-dessous exigent le même jeton Bearer que les observations.

| Route | Contrat |
| --- | --- |
| `GET /projects` | Liste des projets, triée par identifiant |
| `POST /projects` | `{ "id": "OLED", "name": "OLED project" }` |
| `GET /experiments` | Liste des expériences, triée par identifiant |
| `GET /experiments?project_id=OLED` | Filtre exact par projet |
| `POST /experiments` | `{ "id": "LPP-26-050", "project_id": "OLED", "name": "Test synthesis" }` |
| `GET /experiments/LPP-26-050` | Une expérience, ou HTTP 404 |

Identifiants : lettres ASCII, chiffres, tirets et tirets bas; longueur maximale
64 pour un projet, 80 pour une expérience. Les noms ont 1 à 120 caractères.
Les champs inconnus sont refusés. La création d'une expérience exige un projet
enregistré (sinon HTTP 404).

Une nouvelle soumission identique renvoie l'enregistrement initial, y compris
après redémarrage. Un identifiant réutilisé avec un contenu différent renvoie
HTTP 409 : ce n'est pas une mise à jour. Les créations concurrentes sont
sérialisées par SQLite; aucune route de modification ou suppression n'est ajoutée.
L'ouverture d'une base pilote existante ajoute les tables, sans supprimer ses
appareils ni événements.

## Compatibilité et limites

Les anciennes notes et observations continuent d'accepter un `experiment_id`
non enregistré. Ce champ demeure une étiquette de regroupement pour ces routes;
il n'est pas encore une relation obligatoire vers le registre. Aucune expérience
n'est créée automatiquement à partir d'anciens événements. Une interface peut
choisir des expériences du registre, mais l'API historique ne l'impose pas.

Ce registre ne fournit pas encore d'échantillons, de fichiers analytiques, de
contrôle d'accès par projet ni de synchronisation avec FindMolecule. Il ne modifie
pas les limites du pilote : local, mono-utilisateur et appareils simulés.

## Validation

`python -m pytest tests/chemlab/test_projects.py tests/chemlab/test_pilot.py -q`

Vérifie persistance, conflits, projet inconnu, filtrage exact, refus des entrées
invalides, authentification, réessais concurrents et compatibilité des notes.
