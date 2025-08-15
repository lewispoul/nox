Nox API — Plan directeur, état d’avancement, et prompts Copilot par étapes
0) Vision et objectifs
But, mini plateforme « Nox API » sur Ubuntu 22.04, accessible en LAN ou via HTTPS, avec sandbox d’exécution, sécurité simple par Bearer token, service systemd durci, scripts de déploiement idempotents, tests reproductibles.

Exigences clés,

API FastAPI, endpoints, /health, /put, /run_py, /run_sh.

Sécurité, auth Bearer obligatoire, sandbox stricte, blacklist shell, timeouts, durcissement systemd, écoute locale si pas de proxy.

Déploiement idempotent, script qui crée l’utilisateur nox, l’arborescence, le venv, le service, les variables d’environnement, les tests.

Opérations, logs, diagnostics, tests curl, client Python minimal.

Réseau, reverse proxy optionnel, UFW cohérent.

Gouvernance, si changement non trivial, Copilot doit s’arrêter, produire un rapport, et attendre validation.

1) État actuel du 13 août 2025
OK, utilisateur nox et arborescence, /home/nox/nox/{api,sandbox,.venv}.

OK, nox_api.py fonctionnel, endpoints OK.

OK, service systemd nox-api actif sur 127.0.0.1:8080.

OK, auth Bearer via /etc/default/nox-api.

OK, tests, upload, run_py, run_sh.

A améliorer, durcissement, ProtectHome=read-only actuel, option future, déplacer venv vers /opt/nox/.venv puis remettre ProtectHome=yes.

A faire, reverse proxy, Caddy ou Nginx, et UFW.

2) Architecture cible
Processus, nox-api.service (User=nox), lance python3 -m uvicorn nox_api:app avec env depuis /etc/default/nox-api.

Sandbox, /home/nox/nox/sandbox autorisée en écriture via ReadWritePaths.

Code, /home/nox/nox/api/nox_api.py.

Venv, /home/nox/nox/.venv ou futur /opt/nox/.venv.

Reverse proxy, Caddy ou Nginx, écoute 80 et 443, upstream 127.0.0.1, forwarding du header Authorization.

3) Convention de travail avec Copilot
Chaque Étape ci dessous est un prompt unitaire à coller dans Copilot Chat.

Copilot doit exécuter et tester ce qu’il génère.

En cas de difficulté non triviale, par exemple changement lourd, Copilot s’arrête, rend un rapport, diffs, logs, erreurs, et attend validation.

4) Prompts Copilot par étapes
Étape 1, normaliser l’arborescence et le script d’installation
Prompt Copilot,

Contexte, standardiser le déploiement Nox API. Crée ou complète deploy/install_nox.sh idempotent. Contraintes, pas de chemins codés en dur sauf variables.
Tâches,

Créer l’utilisateur nox si absent, arborescence /home/nox/nox/{api,sandbox,logs} et droits.

Créer ou régénérer le venv sous /home/nox/nox/.venv, installer fastapi, uvicorn[standard], pydantic, python-multipart.

Écrire /etc/default/nox-api avec NOX_API_TOKEN, NOX_SANDBOX, NOX_TIMEOUT, NOX_BIND_ADDR, NOX_PORT.

Écrire nox-api.service durci, NoNewPrivileges, PrivateTmp, ProtectSystem=full, ProtectHome=read-only, ReadWritePaths sur la sandbox. ExecStart=/home/nox/nox/.venv/bin/python3 -m uvicorn nox_api:app --host ${NOX_BIND_ADDR} --port ${NOX_PORT}.

Déployer un api/nox_api.py minimal si absent.

Démarrer le service puis exécuter des tests, /health, upload, run_py, run_sh, et afficher les résultats.

Si un problème non trivial survient, s’arrêter et produire un rapport détaillé, journalctl, sorties commandes, patchs proposés.

Base de code à intégrer si api/nox_api.py est absent,
import os, subprocess, shlex, pathlib
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from pydantic import BaseModel
app = FastAPI()
NOX_TOKEN=os.getenv("NOX_API_TOKEN","").strip()
SANDBOX=pathlib.Path(os.getenv("NOX_SANDBOX","/home/nox/nox/sandbox")).resolve(); SANDBOX.mkdir(parents=True, exist_ok=True)
def auth(h:str|None):
    if not NOX_TOKEN: return
    if not h or not h.startswith("Bearer ") or h.split(" ",1)[1]!=NOX_TOKEN: raise HTTPException(401,"Unauthorized")
def join(rel:str)->pathlib.Path:
    p=(SANDBOX/rel.lstrip("/")).resolve()
    if SANDBOX not in p.parents and p!=SANDBOX: raise HTTPException(400,"Path escapes sandbox"); return p
@app.get('/health')
def health(): return {"status":"ok"}
@app.post('/put')
async def put(path:str, f:UploadFile=File(...), Authorization:str|None=Header(None)):
    auth(Authorization); d=join(path); d.parent.mkdir(parents=True,exist_ok=True); d.write_bytes(await f.read()); return {"saved":str(d)}
class RunPy(BaseModel): code:str; filename:str="run.py"
@app.post('/run_py')
def run_py(b:RunPy, Authorization:str|None=Header(None)):
    auth(Authorization); t=join(b.filename); t.parent.mkdir(parents=True,exist_ok=True); t.write_text(b.code)
    p=subprocess.run(["python3",str(t)],cwd=str(SANDBOX),capture_output=True,text=True,timeout=int(os.getenv("NOX_TIMEOUT","20")))
    return {"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
class RunSh(BaseModel): cmd:str
FORBIDDEN={"rm","reboot","shutdown","mkfs","dd","mount","umount","sudo"}
@app.post('/run_sh')
def run_sh(b:RunSh, Authorization:str|None=Header(None)):
    auth(Authorization); parts=shlex.split(b.cmd)
    if not parts: raise HTTPException(400,"Empty command")
    if parts[0] in FORBIDDEN: raise HTTPException(400,"Forbidden command")
    p=subprocess.run(parts,cwd=str(SANDBOX),capture_output=True,text=True,timeout=int(os.getenv("NOX_TIMEOUT","20")))
    return {"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
Étape 2, script de réparation et auto tests
Prompt Copilot,

Créer scripts/nox_repair.sh idempotent qui,

Arrête le service, vérifie le venv, réinstalle si corrompu.

Vérifie api/nox_api.py, non vide, importable, sinon restaure la version minimale.

Vérifie EnvironmentFile=/etc/default/nox-api et la présence de NOX_PORT et NOX_BIND_ADDR, sinon ajoute.

Force ExecStart=/home/nox/nox/.venv/bin/python3 -m uvicorn ....

Relance et exécute des auto tests clairs, health, put, run_py, run_sh, et en cas d’échec, affiche journalctl -u nox-api -n 50.

Si problème non trivial, s’arrêter et produire un rapport markdown dans logs/last_repair_report.md.
Ajouter une cible make repair dans un Makefile minimal.

Étape 3, durcissement, déplacer le venv vers /opt/nox/.venv et remettre ProtectHome=yes
Prompt Copilot,

Objectif, déplacer le venv pour autoriser ProtectHome=yes.
Tâches,

Script deploy/migrate_venv.sh qui crée /opt/nox/.venv, propriétaire nox:nox, réinstalle deps, met à jour ExecStart.

Mettre ProtectHome=yes dans l’unité systemd, conserver ReadWritePaths=/home/nox/nox/sandbox.

Redéployer, daemon-reload, restart, tests. Si échec, rollback automatique.

Rapport en cas d’anomalie.

Étape 4, reverse proxy Caddy et exemple Nginx
Prompt Copilot,

Créer deploy/Caddyfile.example et deploy/nginx_nox.conf.example.
Caddy, site 443 ou domaine, TLS auto, proxy vers 127.0.0.1, header Authorization conservé, limites de taille upload.
Nginx, server 80 et 443, proxy_set_header Authorization $http_authorization;, timeouts raisonnables.
Créer deploy/configure_ufw.sh qui ouvre 80 et 443 si proxy actif et ferme 8080.
Créer deploy/install_caddy.sh, installe Caddy, copie le Caddyfile, redémarre.
Tests, curl -I https://.../health, upload, run_py via HTTPS.
Rapport si émission de certificats échoue, ports, DNS.

Étape 5, client Python et tests automatiques
Prompt Copilot,

Créer clients/nox_client.py, classe NoxClient(base_url, token) avec health(), put(path, file), run_py(code, filename), run_sh(cmd).
Créer clients/tests_demo.py qui exécute la séquence complète et imprime un récapitulatif.
Fournir clients/requirements.txt minimal pour le client.
Ajouter make demo qui lance python3 clients/tests_demo.py.

Étape 6, journalisation, rotation, debugging
Prompt Copilot,

Créer deploy/logrotate-nox pour rotation de logs /var/log/nox-api/*.log si l’unité redirige les logs.
Étendre README.md, section troubleshooting, commandes systemd utiles, check list, token, port, venv, permissions, ProtectHome, ReadWritePaths.

Étape 7, qualité de vie
Prompt Copilot,

Créer scripts/noxctl en bash, offre, health, put <local> <relpath>, runpy <code|file>, runsh <cmd>, lecture du token depuis /etc/default/nox-api.
Ajouter complétion bash simple.
Ajouter make install-tools pour placer noxctl dans /usr/local/bin.

5) Check list de validation
systemctl status nox-api actif.

curl http://127.0.0.1:8080/health renvoie ok.

Upload et run_py et run_sh passent avec token.

UFW cohérent, local ou proxy.

Si venv en /opt/nox/.venv, ProtectHome=yes activé.

README et scripts à jour.

6) Règle d’arrêt Copilot
Si l’étape implique plus de 30 lignes modifiées sur des fichiers critiques, ou une régression aux tests, alors,

Stop.

Rapport détaillé, description, commandes, logs journalctl, diff git, patch minimal proposé.

Attendre validation.

7) Contraintes d’origine
Ne pas utiliser de chemins absolus codés en dur sauf variables.

Commentaires clairs.

Messages d’erreur utiles.

Aucune commande dangereuse côté /run_sh.

8) Vérifications attendues d’origine
systemctl status nox-api actif.

curl http://IP:8080/health renvoie ok.

Upload puis exécution d’un script Python simple.

UFW n’expose pas 8080 si reverse proxy actif.

Caddy ou Nginx répond sur le domaine si configuré.
# Nox API – Plan directeur, état d’avancement, et prompts Copilot par étapes

## 0) Vision et objectifs

**But**: mini‑plateforme "Nox API" sur Ubuntu 22.04 qui expose une sandbox d’exécution locale, sécurisée par token, extensible, pilotable depuis LAN via reverse‑proxy HTTPS, avec scripts d’installation, service systemd durci, et tests reproductibles.

**Exigences clés**:

* API FastAPI: `/health`, `/put`, `/run_py`, `/run_sh`.
* Sécurité: auth Bearer obligatoire, sandbox stricte, blacklist shell, timeouts, durcissement systemd, port local si pas de proxy.
* Déploiement idempotent: script qui crée user `nox`, arborescence, venv, service, variables d’environnement, tests.
* Opérations: logs, diagnostics, tests curl, client Python minimal.
* Réseau: reverse‑proxy (Caddy ou Nginx) optionnel, UFW cohérent.
* Gouvernance: si changement non trivial, **Copilot doit s’arrêter, produire un rapport** et attendre validation.

---

## 1) État actuel (13 août 2025)

* ✅ Utilisateur `nox` et arborescence `/home/nox/nox/{api,sandbox,.venv}` opérationnels.
* ✅ `nox_api.py` fonctionnel, endpoints OK.
* ✅ Service systemd `nox-api` actif sur `127.0.0.1:8080`.
* ✅ Auth Bearer via `/etc/default/nox-api`.
* ✅ Tests manuels: upload, run\_py, run\_sh OK.
* ⚠️ Durcissement: `ProtectHome=read-only` pour l’instant. Option future: déplacer venv dans `/opt/nox/.venv` puis remettre `ProtectHome=yes`.
* ⏳ Reverse‑proxy non encore posé. UFW à ajuster selon choix proxy.

---

## 2) Architecture cible (résumé)

* **Process**: `nox-api.service` (User=nox), lance `python3 -m uvicorn nox_api:app` avec env depuis `/etc/default/nox-api`.
* **Sandbox**: `/home/nox/nox/sandbox` lecture/écriture autorisée via `ReadWritePaths`.
* **Code**: `/home/nox/nox/api/nox_api.py`.
* **Venv**: `/home/nox/nox/.venv` (option: `/opt/nox/.venv`).
* **Proxy**: Caddy ou Nginx, écoute 80/443, upstream 127.0.0.1:8080, headers Authorization propagés.

---

## 3) Convention de travail avec Copilot

* Chaque **Étape** ci‑dessous est un **prompt unitaire** à coller dans Copilot Chat du repo.
* Copilot **doit exécuter/tester** ce qu’il génère.
* En cas de difficulté **non triviale** (modifs lourdes, migrations, refactor profond, impacts sécurité), Copilot **s’arrête**, rend un **rapport** (diffs, logs, commandes, erreurs), et **attend validation**.

---

## 4) Prompts Copilot par étapes (avec code inclus)

### Étape 1 — Normaliser l’arborescence et le script d’installation

**Prompt Copilot :**

> Contexte: Nous standardisons le déploiement de Nox API. Crée ou complète un script `deploy/install_nox.sh` idempotent. Contraintes: ne pas coder en dur autre chose que des variables. Le script doit:
>
> 1. Créer l’utilisateur `nox` si absent, l’arborescence `/home/nox/nox/{api,sandbox,logs}` et les droits.
> 2. Créer/recréer le venv sous `/home/nox/nox/.venv`, installer `fastapi`, `uvicorn[standard]`, `pydantic`, `python-multipart`.
> 3. Écrire `/etc/default/nox-api` avec `NOX_API_TOKEN`, `NOX_SANDBOX`, `NOX_TIMEOUT`, `NOX_BIND_ADDR`, `NOX_PORT`.
> 4. Écrire le service systemd `nox-api.service` avec durcissement (NoNewPrivileges, PrivateTmp, ProtectSystem=full, ProtectHome=read-only, ReadWritePaths pour la sandbox). Utiliser `ExecStart=/home/nox/nox/.venv/bin/python3 -m uvicorn nox_api:app --host ${NOX_BIND_ADDR} --port ${NOX_PORT}`.
> 5. Déployer un `api/nox_api.py` minimal fonctionnel si absent.
> 6. Démarrer le service, puis exécuter des **tests**: `/health`, upload, run\_py, run\_sh.
> 7. Si un problème non trivial survient, **arrêter** et produire un **rapport** détaillé avec logs `journalctl`, sortie des commandes, et patchs proposés.
>
> Base de code à intégrer si `api/nox_api.py` est absent:
>
> ```python
> import os, subprocess, shlex, pathlib
> from fastapi import FastAPI, UploadFile, File, HTTPException, Header
> from pydantic import BaseModel
> app = FastAPI()
> NOX_TOKEN=os.getenv("NOX_API_TOKEN","" ).strip()
> SANDBOX=pathlib.Path(os.getenv("NOX_SANDBOX","/home/nox/nox/sandbox")).resolve(); SANDBOX.mkdir(parents=True, exist_ok=True)
> def auth(h:str|None):
>     if not NOX_TOKEN: return
>     if not h or not h.startswith("Bearer ") or h.split(" ",1)[1]!=NOX_TOKEN: raise HTTPException(401,"Unauthorized")
> def join(rel:str)->pathlib.Path:
>     p=(SANDBOX/rel.lstrip("/")).resolve()
>     if SANDBOX not in p.parents and p!=SANDBOX: raise HTTPException(400,"Path escapes sandbox"); return p
> @app.get('/health')
> def health(): return {"status":"ok"}
> @app.post('/put')
> async def put(path:str, f:UploadFile=File(...), Authorization:str|None=Header(None)):
>     auth(Authorization); d=join(path); d.parent.mkdir(parents=True,exist_ok=True); d.write_bytes(await f.read()); return {"saved":str(d)}
> class RunPy(BaseModel): code:str; filename:str="run.py"
> @app.post('/run_py')
> def run_py(b:RunPy, Authorization:str|None=Header(None)):
>     auth(Authorization); t=join(b.filename); t.parent.mkdir(parents=True,exist_ok=True); t.write_text(b.code)
>     p=subprocess.run(["python3",str(t)],cwd=str(SANDBOX),capture_output=True,text=True,timeout=int(os.getenv("NOX_TIMEOUT","20")))
>     return {"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
> class RunSh(BaseModel): cmd:str
> FORBIDDEN={"rm","reboot","shutdown","mkfs","dd","mount","umount","sudo"}
> @app.post('/run_sh')
> def run_sh(b:RunSh, Authorization:str|None=Header(None)):
>     auth(Authorization); parts=shlex.split(b.cmd)
>     if not parts: raise HTTPException(400,"Empty command")
>     if parts[0] in FORBIDDEN: raise HTTPException(400,"Forbidden command")
>     p=subprocess.run(parts,cwd=str(SANDBOX),capture_output=True,text=True,timeout=int(os.getenv("NOX_TIMEOUT","20")))
>     return {"returncode":p.returncode,"stdout":p.stdout,"stderr":p.stderr}
> ```
>
> Livrables attendus: `deploy/install_nox.sh` exécutable, `api/nox_api.py` si manquant, `nox-api.service`, `/etc/default/nox-api`, et **sortie des tests**. Ne change pas des éléments en place qui fonctionnent déjà sans en justifier la nécessité.

---

### Étape 2 — Script de réparation/maintenance et auto‑tests

**Prompt Copilot :**

> Crée `scripts/nox_repair.sh` idempotent qui:
>
> 1. Arrête le service, vérifie l’existence du venv, le réinitialise si corrompu, réinstalle deps.
> 2. Vérifie l’intégrité de `api/nox_api.py` (non vide, importable), sinon restaure la version minimale fournie à l’Étape 1.
> 3. Vérifie `EnvironmentFile=/etc/default/nox-api` et que `NOX_PORT`, `NOX_BIND_ADDR` sont présents, sinon les ajoute.
> 4. Force `ExecStart=/home/nox/nox/.venv/bin/python3 -m uvicorn ...`.
> 5. Relance et exécute **auto‑tests** avec affichage clair (health, put, run\_py, run\_sh) et `journalctl -u nox-api -n 50` en cas d’échec.
> 6. Si problème non trivial, s’arrêter et produire **rapport** markdown dans `logs/last_repair_report.md`.
>
> Ajoute une cible `make repair` dans un `Makefile` minimal qui appelle ce script.

---

### Étape 3 — Durcissement: déplacer le venv vers `/opt/nox/.venv` et remettre `ProtectHome=yes`

**Prompt Copilot :**

> Objectif: déplacer le venv de `/home/nox/nox/.venv` vers `/opt/nox/.venv` pour autoriser `ProtectHome=yes`.
> Tâches:
>
> 1. Script de migration `deploy/migrate_venv.sh` qui crée `/opt/nox/.venv` (propriétaire `nox:nox`), réinstalle deps, et met à jour `ExecStart`.
> 2. Mettre `ProtectHome=yes` dans l’unité systemd, conserver `ReadWritePaths=/home/nox/nox/sandbox`.
> 3. Redéployer, `daemon-reload`, restart, et tests. Si échec, rollback automatique.
> 4. Rapport en cas d’anomalie.
>    Livrables: script + patch de l’unité + tests passants.

---

### Étape 4 — Reverse‑proxy Caddy (option Nginx en exemple)

**Prompt Copilot :**

> Créer `deploy/Caddyfile.example` et `deploy/nginx_nox.conf.example`:
>
> * Caddy: site `:443` ou domaine, TLS automatique, proxy vers `127.0.0.1:8080`, conservation header `Authorization`, limites de taille upload.
> * Nginx: server 80/443, `proxy_set_header Authorization $http_authorization;`, timeouts raisonnables.
> * `deploy/configure_ufw.sh` qui ouvre 80/443 si proxy actif et **ferme 8080**.
> * Script `deploy/install_caddy.sh` qui installe Caddy, copie le Caddyfile, et redémarre.
>   Tests: `curl -I https://.../health`, upload, run\_py via HTTPS.
>   Rapport si l’émission de certificats échoue (ports, DNS).

---

### Étape 5 — Client Python et tests automatiques

**Prompt Copilot :**

> Créer `clients/nox_client.py` avec une classe `NoxClient(base_url, token)` exposant `health()`, `put(path, file)`, `run_py(code, filename)`, `run_sh(cmd)`. Ajouter `clients/tests_demo.py` qui exécute la séquence complète et imprime un récapitulatif. Fournir un `requirements.txt` minimal pour le client.
> Ajouter une cible `make demo` qui lance `python3 clients/tests_demo.py`.

---

### Étape 6 — Journalisation, rotation, et debugging

**Prompt Copilot :**

> Créer `deploy/logrotate-nox` pour faire la rotation de `/var/log/nox-api/*.log` (si tu ajoutes une redirection dans l’unité). Ajouter une section de la doc "Troubleshooting" dans `README.md`: commandes systemd utiles, points de contrôle, et check‑list (token, port, venv, permissions, ProtectHome, ReadWritePaths).

---

### Étape 7 — Qualité de vie

**Prompt Copilot :**

> Créer `scripts/noxctl` (bash) qui offre: `health`, `put <local> <relpath>`, `runpy <code|file>`, `runsh <cmd>`, lecture du token depuis `/etc/default/nox-api`. Ajouter complétion bash simple. Ajouter `make install-tools` pour placer `noxctl` dans `/usr/local/bin`.

---

## 5) Check‑list de validation (à chaque merge)

* `systemctl status nox-api` actif.
* `curl http://127.0.0.1:8080/health` renvoie `ok`.
* Upload + `run_py` + `run_sh` passent avec token.
* UFW cohérent avec le mode (local ou proxy).
* Si venv en `/opt/nox/.venv`, unité avec `ProtectHome=yes`.
* README et scripts alignés avec la réalité.

---

## 6) Règle d’arrêt Copilot (impose à chaque étape)

* **Si** l’étape implique plus de 30 lignes modifiées sur des fichiers critiques (`nox_api.py`, service systemd, scripts deploy) **ou** une régression aux tests, **alors**:

  1. **Stop** l’automatisation.
  2. Génère un **rapport**: description du problème, commandes exécutées, logs `journalctl`, diff git, proposition de patch minimal.
  3. Attends explicitement la validation avant toute autre modification.

---

## 7) Notes

* Ne pas insérer d’em‑dashes dans les textes générés, sauf si nécessaire dans du code ou configs.
* Messages d’erreur informatifs, commentaires concis.
* Aucune commande dangereuse via `/run_sh`.
