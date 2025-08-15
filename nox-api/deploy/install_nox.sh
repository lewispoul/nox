#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Nox API - Script d'installation idempotent
# Conforme à docs/planning/COPILOT_PLAN.md - Étape 1
# =============================================================================

echo "[NOX] Début d'installation Nox API"

# Paramètres de configuration
NOX_USER=nox
NOX_GROUP=nox
NOX_HOME=/home/$NOX_USER
NOX_ROOT=$NOX_HOME/nox
NOX_API_DIR=$NOX_ROOT/api
NOX_SANDBOX_DIR=$NOX_ROOT/sandbox
NOX_LOGS_DIR=$NOX_ROOT/logs
NOX_VENV_DIR=$NOX_ROOT/.venv
ENV_FILE=/etc/default/nox-api
SYSTEMD_SERVICE=/etc/systemd/system/nox-api.service

# Variables pour les tests
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_FILE=$(mktemp)

echo "[NOX] Configuration: utilisateur=$NOX_USER, racine=$NOX_ROOT"

# =============================================================================
# 1. Arrêter le service existant si présent
# =============================================================================
echo "[NOX] Arrêt du service existant..."
sudo systemctl stop nox-api 2>/dev/null || echo "[NOX] Service non actif"

# =============================================================================
# 2. Création utilisateur et arborescence
# =============================================================================
echo "[NOX] Création utilisateur et arborescence..."

if ! id "$NOX_USER" &>/dev/null; then
    echo "[NOX] Création de l'utilisateur $NOX_USER"
    sudo useradd -m -s /bin/bash "$NOX_USER"
else
    echo "[NOX] Utilisateur $NOX_USER existe déjà"
fi

# Création de l'arborescence complète
sudo mkdir -p "$NOX_API_DIR" "$NOX_SANDBOX_DIR" "$NOX_LOGS_DIR"
sudo chown -R $NOX_USER:$NOX_GROUP "$NOX_ROOT"
sudo chmod 755 "$NOX_ROOT" "$NOX_API_DIR" "$NOX_LOGS_DIR"
sudo chmod 775 "$NOX_SANDBOX_DIR"

echo "[NOX] Arborescence créée: $NOX_ROOT/{api,sandbox,logs}"

# =============================================================================
# 3. Installation du venv et des dépendances
# =============================================================================
echo "[NOX] Configuration de l'environnement virtuel..."

# Suppression du venv existant s'il est corrompu
if [[ -d "$NOX_VENV_DIR" ]]; then
    echo "[NOX] Test du venv existant..."
    if ! sudo -u $NOX_USER bash -c "source $NOX_VENV_DIR/bin/activate && python3 -c 'import fastapi, uvicorn'" 2>/dev/null; then
        echo "[NOX] Venv corrompu, suppression..."
        sudo rm -rf "$NOX_VENV_DIR"
    else
        echo "[NOX] Venv existant fonctionnel"
    fi
fi

# Création/recréation du venv
if [[ ! -d "$NOX_VENV_DIR" ]]; then
    echo "[NOX] Création du nouvel environnement virtuel..."
    sudo -u $NOX_USER bash -c "
        python3 -m venv $NOX_VENV_DIR
        source $NOX_VENV_DIR/bin/activate
        pip install --upgrade pip
        pip install fastapi uvicorn[standard] pydantic python-multipart
    "
    echo "[NOX] Dépendances installées: fastapi, uvicorn[standard], pydantic, python-multipart"
fi

# =============================================================================
# 4. Configuration des variables d'environnement
# =============================================================================
echo "[NOX] Configuration des variables d'environnement..."

if [[ ! -f "$ENV_FILE" ]]; then
    echo "[NOX] Création de $ENV_FILE"
    {
        echo "NOX_API_TOKEN=$(openssl rand -hex 16)"
        echo "NOX_SANDBOX=$NOX_SANDBOX_DIR"
        echo "NOX_TIMEOUT=20"
        echo "NOX_BIND_ADDR=127.0.0.1"
        echo "NOX_PORT=8080"
    } | sudo tee "$ENV_FILE" >/dev/null
    sudo chmod 600 "$ENV_FILE"
    echo "[NOX] Variables d'environnement créées"
else
    echo "[NOX] Fichier d'environnement existant conservé"
    # Vérification des variables requises
    for var in NOX_API_TOKEN NOX_SANDBOX NOX_TIMEOUT NOX_BIND_ADDR NOX_PORT; do
        if ! sudo grep -q "^$var=" "$ENV_FILE"; then
            echo "[NOX] AVERTISSEMENT: Variable $var manquante dans $ENV_FILE"
        fi
    done
fi

# =============================================================================
# 5. Déploiement du code API (version de production si absent)
# =============================================================================
echo "[NOX] Déploiement du code API..."

if [[ ! -f "$NOX_API_DIR/nox_api.py" ]]; then
    echo "[NOX] Création de $NOX_API_DIR/nox_api.py"
    cat <<'PYTHON_CODE' | sudo tee "$NOX_API_DIR/nox_api.py" >/dev/null
import os, io, json, subprocess, shlex, tempfile, pathlib
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from pydantic import BaseModel, Field

app = FastAPI()

NOX_TOKEN   = os.getenv("NOX_API_TOKEN", "").strip()
SANDBOX     = pathlib.Path(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox")).resolve()
TIMEOUT_SEC = int(os.getenv("NOX_TIMEOUT", "20"))

SANDBOX.mkdir(parents=True, exist_ok=True)

def check_auth(auth: str | None):
    if not NOX_TOKEN:
        return
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized")
    if auth.removeprefix("Bearer ").strip() != NOX_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

def safe_join(relpath: str) -> pathlib.Path:
    p = (SANDBOX / relpath.lstrip("/")).resolve()
    if SANDBOX not in p.parents and p != SANDBOX:
        raise HTTPException(status_code=400, detail="Path escapes sandbox")
    return p

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/put")
async def put_file(path: str, f: UploadFile = File(...), authorization: str | None = Header(default=None, alias="Authorization")):
    check_auth(authorization)
    dest = safe_join(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = await f.read()
    dest.write_bytes(data)
    return {"saved": str(dest)}

class RunPy(BaseModel):
    code: str
    filename: str = Field(default="run.py")

@app.post("/run_py")
def run_py(body: RunPy, authorization: str | None = Header(default=None, alias="Authorization")):
    check_auth(authorization)
    target = safe_join(body.filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.code)
    try:
        proc = subprocess.run(
            ["python3", str(target)],
            cwd=str(SANDBOX),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SEC
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Timeout")
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

FORBIDDEN = {"rm", "reboot", "shutdown", "mkfs", "dd", "mount", "umount", "kill", "pkill", "sudo"}
class RunSh(BaseModel):
    cmd: str

@app.post("/run_sh")
def run_sh(body: RunSh, authorization: str | None = Header(default=None, alias="Authorization")):
    check_auth(authorization)
    parts = shlex.split(body.cmd)
    if not parts:
        raise HTTPException(status_code=400, detail="Empty command")
    if parts[0] in FORBIDDEN:
        raise HTTPException(status_code=400, detail="Forbidden command")
    try:
        proc = subprocess.run(parts, cwd=str(SANDBOX), capture_output=True, text=True, timeout=TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Timeout")
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
PYTHON_CODE

    sudo chown $NOX_USER:$NOX_GROUP "$NOX_API_DIR/nox_api.py"
    sudo chmod 644 "$NOX_API_DIR/nox_api.py"
    echo "[NOX] Code API déployé"
else
    echo "[NOX] Code API existant conservé"
    # Vérification de l'intégrité du fichier
    if [[ ! -s "$NOX_API_DIR/nox_api.py" ]]; then
        echo "[NOX] ERREUR: nox_api.py existe mais est vide"
        exit 1
    fi
fi

# =============================================================================
# 6. Configuration du service systemd avec durcissement
# =============================================================================
echo "[NOX] Configuration du service systemd..."

cat <<EOF | sudo tee "$SYSTEMD_SERVICE" >/dev/null
[Unit]
Description=Nox API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$NOX_USER
Group=$NOX_GROUP
EnvironmentFile=$ENV_FILE
WorkingDirectory=$NOX_API_DIR
ExecStart=$NOX_VENV_DIR/bin/python3 -m uvicorn nox_api:app --host \${NOX_BIND_ADDR} --port \${NOX_PORT}
Restart=on-failure
RestartSec=10

# Durcissement sécurité
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=$NOX_SANDBOX_DIR $NOX_LOGS_DIR
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

[Install]
WantedBy=multi-user.target
EOF

echo "[NOX] Service systemd configuré avec durcissement sécurité"

# =============================================================================
# 7. Activation du service
# =============================================================================
echo "[NOX] Activation du service..."

sudo systemctl daemon-reload
sudo systemctl enable nox-api
sudo systemctl start nox-api

# Attendre que le service soit prêt
echo "[NOX] Attente du démarrage du service..."
for i in {1..10}; do
    if systemctl is-active --quiet nox-api; then
        echo "[NOX] Service démarré avec succès"
        break
    fi
    if [[ $i -eq 10 ]]; then
        echo "[NOX] ERREUR: Le service n'a pas démarré dans les temps"
        echo "[NOX] Logs du service:"
        sudo journalctl -u nox-api -n 20 --no-pager
        exit 1
    fi
    sleep 2
done

# Attendre que l'API soit réellement disponible
echo "[NOX] Vérification de la disponibilité de l'API..."
for i in {1..15}; do
    if curl -s --max-time 2 http://127.0.0.1:8080/health >/dev/null 2>&1; then
        echo "[NOX] API disponible"
        break
    fi
    if [[ $i -eq 15 ]]; then
        echo "[NOX] ERREUR: API non disponible après démarrage"
        sudo journalctl -u nox-api -n 20 --no-pager
        exit 1
    fi
    sleep 1
done

# =============================================================================
# 8. Tests de validation
# =============================================================================
echo "[NOX] === TESTS DE VALIDATION ==="

# Récupération du token pour les tests
NOX_TOKEN=$(sudo grep "^NOX_API_TOKEN=" "$ENV_FILE" | cut -d= -f2)
if [[ -z "$NOX_TOKEN" ]]; then
    echo "[NOX] ERREUR: Token non trouvé"
    exit 1
fi

TEST_PASSED=0
TEST_TOTAL=0

# Test 1: Health check
echo "[NOX] Test 1/4: /health"
((TEST_TOTAL++))
HEALTH_RESPONSE=$(curl -s -w "|||%{http_code}" http://127.0.0.1:8080/health)
if [[ "$HEALTH_RESPONSE" == *"|||200" ]]; then
    HTTP_CODE="200"
    RESPONSE_BODY=${HEALTH_RESPONSE%|||*}
else
    HTTP_CODE="ERROR"
    RESPONSE_BODY="$HEALTH_RESPONSE"
fi

if [[ "$HTTP_CODE" == "200" ]] && [[ "$RESPONSE_BODY" == *"ok"* ]]; then
    echo "[NOX] ✓ Test /health: SUCCESS ($RESPONSE_BODY)"
    ((TEST_PASSED++))
else
    echo "[NOX] ✗ Test /health: FAILED (HTTP $HTTP_CODE: $RESPONSE_BODY)"
fi

# Test 2: Upload file
echo "[NOX] Test 2/4: /put"
((TEST_TOTAL++))
echo "Test content" > "$TEST_FILE"
UPLOAD_RESPONSE=$(curl -s -w "|||%{http_code}" \
    -H "Authorization: Bearer $NOX_TOKEN" \
    -X POST "http://127.0.0.1:8080/put?path=test.txt" \
    -F "f=@$TEST_FILE")

if [[ "$UPLOAD_RESPONSE" == *"|||200" ]]; then
    HTTP_CODE="200"
    RESPONSE_BODY=${UPLOAD_RESPONSE%|||*}
else
    HTTP_CODE="ERROR"
    RESPONSE_BODY="$UPLOAD_RESPONSE"
fi

if [[ "$HTTP_CODE" == "200" ]] && [[ "$RESPONSE_BODY" == *"saved"* ]]; then
    echo "[NOX] ✓ Test /put: SUCCESS"
    ((TEST_PASSED++))
else
    echo "[NOX] ✗ Test /put: FAILED (HTTP $HTTP_CODE: $RESPONSE_BODY)"
fi

# Test 3: Run Python code
echo "[NOX] Test 3/4: /run_py"
((TEST_TOTAL++))
RUNPY_RESPONSE=$(curl -s -w "|||%{http_code}" \
    -H "Authorization: Bearer $NOX_TOKEN" \
    -H "Content-Type: application/json" \
    -X POST "http://127.0.0.1:8080/run_py" \
    -d '{"code": "print(\"Hello from Nox Python!\")"}')

if [[ "$RUNPY_RESPONSE" == *"|||200" ]]; then
    HTTP_CODE="200"
    RESPONSE_BODY=${RUNPY_RESPONSE%|||*}
else
    HTTP_CODE="ERROR"
    RESPONSE_BODY="$RUNPY_RESPONSE"
fi

if [[ "$HTTP_CODE" == "200" ]] && [[ "$RESPONSE_BODY" == *"Hello from Nox Python!"* ]]; then
    echo "[NOX] ✓ Test /run_py: SUCCESS"
    ((TEST_PASSED++))
else
    echo "[NOX] ✗ Test /run_py: FAILED (HTTP $HTTP_CODE: $RESPONSE_BODY)"
fi

# Test 4: Run shell command
echo "[NOX] Test 4/4: /run_sh"
((TEST_TOTAL++))
RUNSH_RESPONSE=$(curl -s -w "|||%{http_code}" \
    -H "Authorization: Bearer $NOX_TOKEN" \
    -H "Content-Type: application/json" \
    -X POST "http://127.0.0.1:8080/run_sh" \
    -d '{"cmd": "echo Hello from Nox Shell"}')

if [[ "$RUNSH_RESPONSE" == *"|||200" ]]; then
    HTTP_CODE="200"
    RESPONSE_BODY=${RUNSH_RESPONSE%|||*}
else
    HTTP_CODE="ERROR" 
    RESPONSE_BODY="$RUNSH_RESPONSE"
fi

if [[ "$HTTP_CODE" == "200" ]] && [[ "$RESPONSE_BODY" == *"Hello from Nox Shell"* ]]; then
    echo "[NOX] ✓ Test /run_sh: SUCCESS"
    ((TEST_PASSED++))
else
    echo "[NOX] ✗ Test /run_sh: FAILED (HTTP $HTTP_CODE: $RESPONSE_BODY)"
fi

# Nettoyage
rm -f "$TEST_FILE"

# =============================================================================
# 9. Rapport final
# =============================================================================
echo ""
echo "[NOX] === RAPPORT D'INSTALLATION ==="
echo "[NOX] Tests réussis: $TEST_PASSED/$TEST_TOTAL"

# Status du service
SERVICE_STATUS=$(systemctl is-active nox-api)
echo "[NOX] Status du service: $SERVICE_STATUS"

if [[ "$SERVICE_STATUS" == "active" ]] && [[ $TEST_PASSED -eq $TEST_TOTAL ]]; then
    echo "[NOX] ✓ INSTALLATION RÉUSSIE"
    echo "[NOX] API disponible sur http://127.0.0.1:8080"
    echo "[NOX] Token: $NOX_TOKEN"
    echo "[NOX] Sandbox: $NOX_SANDBOX_DIR"
    exit 0
else
    echo "[NOX] ✗ INSTALLATION ÉCHOUÉE"
    echo "[NOX] Logs du service:"
    sudo journalctl -u nox-api -n 20 --no-pager
    
    if [[ $TEST_PASSED -lt $TEST_TOTAL ]]; then
        echo "[NOX] Tests échoués: $((TEST_TOTAL - TEST_PASSED))/$TEST_TOTAL"
    fi
    exit 1
fi
