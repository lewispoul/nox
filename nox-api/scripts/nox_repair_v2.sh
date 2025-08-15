#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Nox API - Script de réparation et maintenance (Version Robuste)
# Conforme à docs/planning/COPILOT_PLAN.md - Étape 2
# =============================================================================

# Configuration des paramètres
NOX_USER=nox
NOX_GROUP=nox
NOX_HOME=/home/$NOX_USER
NOX_ROOT=$NOX_HOME/nox
NOX_API_DIR=$NOX_ROOT/api
NOX_SANDBOX_DIR=$NOX_ROOT/sandbox
NOX_LOGS_DIR=$NOX_ROOT/logs
NOX_VENV_DIR=$NOX_ROOT/.venv
ENV_FILE=/etc/default/nox-api
SERVICE_FILE=/etc/systemd/system/nox-api.service
REPORT_FILE="$NOX_LOGS_DIR/last_repair_report.md"

# Variables pour le suivi
REPAIRS_MADE=()
ISSUES_FOUND=()
START_TIME=$(date)

echo "=========================================="
echo "NOX REPAIR - Réparation et maintenance"
echo "Début: $START_TIME"
echo "=========================================="

# =============================================================================
# Fonctions utilitaires
# =============================================================================

log_repair() {
    local message="$1"
    echo "✓ RÉPARÉ: $message"
    REPAIRS_MADE+=("$message")
}

log_issue() {
    local message="$1"
    echo "⚠ ISSUE: $message"
    ISSUES_FOUND+=("$message")
}

check_and_repair_user() {
    echo "--- Vérification utilisateur ---"
    if ! id "$NOX_USER" &>/dev/null; then
        echo "Création utilisateur $NOX_USER..."
        sudo useradd -m -s /bin/bash "$NOX_USER"
        log_repair "Utilisateur $NOX_USER créé"
    else
        echo "Utilisateur $NOX_USER: OK"
    fi
}

check_and_repair_structure() {
    echo "--- Vérification arborescence ---"
    local created=false
    
    for dir in "$NOX_API_DIR" "$NOX_SANDBOX_DIR" "$NOX_LOGS_DIR"; do
        if [[ ! -d "$dir" ]]; then
            echo "Création $dir..."
            sudo mkdir -p "$dir"
            created=true
        fi
    done
    
    if [[ "$created" == "true" ]]; then
        log_repair "Arborescence créée/corrigée"
    fi
    
    # Correction permissions
    sudo chown -R $NOX_USER:$NOX_GROUP "$NOX_ROOT"
    sudo chmod 755 "$NOX_ROOT" "$NOX_API_DIR" "$NOX_LOGS_DIR"
    sudo chmod 775 "$NOX_SANDBOX_DIR"
    
    echo "Arborescence: OK"
}

check_and_repair_venv() {
    echo "--- Vérification venv ---"
    local need_repair=false
    
    if [[ ! -x "$NOX_VENV_DIR/bin/python3" ]]; then
        need_repair=true
        log_issue "Venv manquant ou cassé"
    else
        # Test imports
        if ! sudo -u $NOX_USER bash -c "source $NOX_VENV_DIR/bin/activate && python3 -c 'import fastapi, uvicorn'" 2>/dev/null; then
            need_repair=true
            log_issue "Dépendances venv manquantes"
        fi
    fi
    
    if [[ "$need_repair" == "true" ]]; then
        echo "Réparation du venv..."
        sudo rm -rf "$NOX_VENV_DIR" 2>/dev/null || true
        sudo -u $NOX_USER python3 -m venv "$NOX_VENV_DIR"
        sudo -u $NOX_USER bash -c "
            source $NOX_VENV_DIR/bin/activate
            pip install --upgrade pip
            pip install fastapi uvicorn[standard] pydantic python-multipart
        "
        log_repair "Venv recréé avec dépendances"
    else
        echo "Venv: OK"
    fi
}

check_and_repair_api() {
    echo "--- Vérification code API ---"
    local need_repair=false
    
    if [[ ! -f "$NOX_API_DIR/nox_api.py" ]] || [[ ! -s "$NOX_API_DIR/nox_api.py" ]]; then
        need_repair=true
        log_issue "Fichier API manquant ou vide"
    else
        # Test syntaxe
        if ! sudo -u $NOX_USER bash -c "source $NOX_VENV_DIR/bin/activate && python3 -m py_compile $NOX_API_DIR/nox_api.py" 2>/dev/null; then
            need_repair=true
            log_issue "Erreur de syntaxe dans l'API"
        fi
    fi
    
    if [[ "$need_repair" == "true" ]]; then
        echo "Restauration du code API..."
        [[ -f "$NOX_API_DIR/nox_api.py" ]] && sudo mv "$NOX_API_DIR/nox_api.py" "$NOX_API_DIR/nox_api.py.backup.$(date +%s)"
        
        # Code API minimal mais fonctionnel
        cat <<'PYTHON_CODE' | sudo tee "$NOX_API_DIR/nox_api.py" >/dev/null
import os, subprocess, shlex, pathlib
from fastapi import FastAPI, UploadFile, File, HTTPException, Header
from pydantic import BaseModel

app = FastAPI()

NOX_TOKEN = os.getenv("NOX_API_TOKEN", "").strip()
SANDBOX = pathlib.Path(os.getenv("NOX_SANDBOX", "/home/nox/nox/sandbox")).resolve()
TIMEOUT_SEC = int(os.getenv("NOX_TIMEOUT", "20"))

SANDBOX.mkdir(parents=True, exist_ok=True)

def check_auth(auth):
    if not NOX_TOKEN:
        return
    if not auth or not auth.startswith("Bearer ") or auth.split(" ", 1)[1] != NOX_TOKEN:
        raise HTTPException(401, "Unauthorized")

def safe_join(relpath):
    p = (SANDBOX / relpath.lstrip("/")).resolve()
    if SANDBOX not in p.parents and p != SANDBOX:
        raise HTTPException(400, "Path escapes sandbox")
    return p

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/put")
async def put_file(path: str, f: UploadFile = File(...), authorization: str = Header(None, alias="Authorization")):
    check_auth(authorization)
    dest = safe_join(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(await f.read())
    return {"saved": str(dest)}

class RunPy(BaseModel):
    code: str
    filename: str = "run.py"

@app.post("/run_py")
def run_py(body: RunPy, authorization: str = Header(None, alias="Authorization")):
    check_auth(authorization)
    target = safe_join(body.filename)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body.code)
    proc = subprocess.run(["python3", str(target)], cwd=str(SANDBOX), 
                         capture_output=True, text=True, timeout=TIMEOUT_SEC)
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}

class RunSh(BaseModel):
    cmd: str

FORBIDDEN = {"rm", "reboot", "shutdown", "mkfs", "dd", "mount", "umount", "sudo"}

@app.post("/run_sh")
def run_sh(body: RunSh, authorization: str = Header(None, alias="Authorization")):
    check_auth(authorization)
    parts = shlex.split(body.cmd)
    if not parts or parts[0] in FORBIDDEN:
        raise HTTPException(400, "Empty or forbidden command")
    proc = subprocess.run(parts, cwd=str(SANDBOX), capture_output=True, 
                         text=True, timeout=TIMEOUT_SEC)
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
PYTHON_CODE

        sudo chown $NOX_USER:$NOX_GROUP "$NOX_API_DIR/nox_api.py"
        sudo chmod 644 "$NOX_API_DIR/nox_api.py"
        log_repair "Code API restauré"
    else
        echo "Code API: OK"
    fi
}

check_and_repair_env() {
    echo "--- Vérification variables d'environnement ---"
    local need_repair=false
    
    if [[ ! -f "$ENV_FILE" ]]; then
        need_repair=true
        log_issue "Fichier environnement manquant"
    else
        for var in NOX_API_TOKEN NOX_SANDBOX NOX_TIMEOUT NOX_BIND_ADDR NOX_PORT; do
            if ! sudo grep -q "^$var=" "$ENV_FILE"; then
                need_repair=true
                log_issue "Variable manquante: $var"
            fi
        done
    fi
    
    if [[ "$need_repair" == "true" ]]; then
        echo "Réparation fichier environnement..."
        [[ -f "$ENV_FILE" ]] && sudo cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%s)"
        
        {
            echo "NOX_API_TOKEN=$(openssl rand -hex 16)"
            echo "NOX_SANDBOX=$NOX_SANDBOX_DIR"
            echo "NOX_TIMEOUT=20"
            echo "NOX_BIND_ADDR=127.0.0.1"
            echo "NOX_PORT=8080"
        } | sudo tee "$ENV_FILE" >/dev/null
        
        sudo chmod 600 "$ENV_FILE"
        log_repair "Fichier environnement restauré"
    else
        echo "Variables d'environnement: OK"
    fi
}

check_and_repair_service() {
    echo "--- Vérification service systemd ---"
    local need_repair=false
    
    if [[ ! -f "$SERVICE_FILE" ]]; then
        need_repair=true
        log_issue "Service systemd manquant"
    else
        if ! sudo grep -q "ExecStart=$NOX_VENV_DIR" "$SERVICE_FILE"; then
            need_repair=true
            log_issue "Chemin ExecStart incorrect"
        fi
    fi
    
    if [[ "$need_repair" == "true" ]]; then
        echo "Réparation service systemd..."
        [[ -f "$SERVICE_FILE" ]] && sudo cp "$SERVICE_FILE" "$SERVICE_FILE.backup.$(date +%s)"
        
        cat <<EOF | sudo tee "$SERVICE_FILE" >/dev/null
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

# Durcissement sécurité
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=full
ProtectHome=read-only
ReadWritePaths=$NOX_SANDBOX_DIR $NOX_LOGS_DIR

[Install]
WantedBy=multi-user.target
EOF
        
        log_repair "Service systemd restauré"
    else
        echo "Service systemd: OK"
    fi
}

restart_and_test() {
    echo "--- Redémarrage et tests ---"
    
    # Arrêt du service
    sudo systemctl stop nox-api 2>/dev/null || true
    
    # Rechargement et démarrage
    sudo systemctl daemon-reload
    sudo systemctl enable nox-api
    sudo systemctl start nox-api
    
    # Attendre que le service soit prêt
    echo "Attente démarrage..."
    for i in {1..10}; do
        if systemctl is-active --quiet nox-api; then
            break
        fi
        if [[ $i -eq 10 ]]; then
            echo "✗ ÉCHEC: Service ne démarre pas"
            sudo journalctl -u nox-api -n 10 --no-pager
            return 1
        fi
        sleep 2
    done
    
    # Attendre que l'API réponde
    echo "Test API..."
    for i in {1..10}; do
        if curl -s --max-time 2 http://127.0.0.1:8080/health >/dev/null 2>&1; then
            echo "✓ API disponible"
            return 0
        fi
        sleep 1
    done
    
    echo "⚠ API non disponible après redémarrage"
    return 1
}

generate_report() {
    echo "--- Génération du rapport ---"
    
    sudo mkdir -p "$(dirname "$REPORT_FILE")"
    
    cat <<EOF | sudo tee "$REPORT_FILE" >/dev/null
# Rapport de réparation Nox API

**Date**: $(date)
**Début**: $START_TIME
**Fin**: $(date)

## Résumé

- **Réparations**: ${#REPAIRS_MADE[@]}
- **Issues**: ${#ISSUES_FOUND[@]}
- **Service**: $(systemctl is-active nox-api 2>/dev/null || echo "non disponible")
- **API**: $(curl -s http://127.0.0.1:8080/health >/dev/null 2>&1 && echo "disponible" || echo "non disponible")

## Détails des réparations

$(for repair in "${REPAIRS_MADE[@]}"; do echo "- ✓ $repair"; done)

## Issues identifiées

$(for issue in "${ISSUES_FOUND[@]}"; do echo "- ⚠ $issue"; done)

## Tests basiques

- Health check: $(curl -s http://127.0.0.1:8080/health >/dev/null 2>&1 && echo "✅ OK" || echo "❌ FAIL")

## État du système

### Service
\`\`\`
$(systemctl status nox-api --no-pager 2>/dev/null || echo "Service non disponible")
\`\`\`

### Logs récents
\`\`\`
$(sudo journalctl -u nox-api -n 10 --no-pager 2>/dev/null || echo "Logs non disponibles")
\`\`\`
EOF
    
    sudo chown $NOX_USER:$NOX_GROUP "$REPORT_FILE" 2>/dev/null || true
    echo "Rapport sauvé: $REPORT_FILE"
}

# =============================================================================
# Exécution principale
# =============================================================================

# Phase 1: Arrêt du service
echo "Arrêt du service pour maintenance..."
sudo systemctl stop nox-api 2>/dev/null || true

# Phase 2: Vérifications et réparations
check_and_repair_user
check_and_repair_structure
check_and_repair_venv
check_and_repair_api
check_and_repair_env
check_and_repair_service

# Phase 3: Redémarrage et tests
if restart_and_test; then
    echo "✓ Redémarrage réussi"
else
    echo "⚠ Problème au redémarrage"
fi

# Phase 4: Rapport
generate_report

# Résumé final
echo ""
echo "=========================================="
echo "RÉPARATION TERMINÉE"
echo "Réparations: ${#REPAIRS_MADE[@]}"
echo "Issues: ${#ISSUES_FOUND[@]}"
echo "Service: $(systemctl is-active nox-api 2>/dev/null || echo 'non disponible')"
echo "Rapport: $REPORT_FILE"
echo "=========================================="

if [[ ${#REPAIRS_MADE[@]} -gt 0 ]]; then
    echo "🔧 Des réparations ont été effectuées"
fi

if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then
    echo "🎉 API fonctionnelle"
    exit 0
else
    echo "⚠ API non disponible - consulter les logs"
    exit 1
fi
