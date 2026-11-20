# NOx — lancer le premier lot local

Python 3.11+ et Node.js pour les tests JavaScript. Depuis la racine du dépôt :

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r chemlab/requirements-pilot.txt
export CHEMLAB_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
export CHEMLAB_DB=.run/chemlab.sqlite3
uvicorn chemlab.app:create_app --factory --host 127.0.0.1 --port 8090
```

Ouvrir `http://127.0.0.1:8090/ui/` et saisir le jeton défini dans ce terminal.
Pour afficher le jeton dans votre propre terminal : `printenv CHEMLAB_TOKEN`.
Ne pas le publier dans une capture, un commit ou une conversation.

Créer un projet, créer une expérience, la sélectionner, écrire une note puis
relire le journal. Le statut confirmé de la note est **brouillon local**; rien
n'est écrit dans FindMolecule. Un redémarrage du serveur conserve la base SQLite.
Le jeton de la page est effacé lors d'un rechargement et doit être saisi de nouveau.
Les brouillons non confirmés restent seulement en mémoire; ne pas fermer la page
avant de résoudre un échec d'envoi.

## Mobile et réseau

La mise en page vise téléphone et PC; ce serveur écoute uniquement sur la boucle
locale. Le téléphone ne peut donc pas joindre le serveur du PC avec `127.0.0.1`.
Un déploiement LAN séparé (TLS, authentification, sauvegardes et politique d'accès)
reste à préparer et à tester. Ce lot n'ouvre aucun accès au laptop à distance.
GasCalc peut aussi être ouvert seul via son fichier HTML sans API ni réseau.

## Tests

```bash
python -m pytest tests/chemlab -q
node chemlab/web/gascalc/tests.cjs
node chemlab/web/gascalc/integration-tests.cjs
```

Voir `docs/nox/VALIDATION.md`, `chemlab/web/README.md` et
`docs/nox/NMR_FID_SPIKE.md` pour le périmètre réel, les tests UI et la preuve FID.
Le présent lot ne revendique pas une validation de toute l'ancienne suite NOX,
du matériel réel, de XTB réel ou d'une application mobile installée.

## Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r chemlab/requirements-pilot.txt
$env:CHEMLAB_TOKEN = & .\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
$env:CHEMLAB_DB = '.run/chemlab.sqlite3'
.\.venv\Scripts\python.exe -m uvicorn chemlab.app:create_app --factory --host 127.0.0.1 --port 8090
```

Dans un second terminal, utiliser le jeton du premier terminal pour l'interface;
il peut y être consulté avec `$env:CHEMLAB_TOKEN` avant le lancement du serveur.
L'affichage est local au terminal de l'utilisateur, pas dans un journal partagé.
