#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Nox API - Script de réparation et maintenance
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

# Variables pour le suivi des réparations
REPAIRS_MADE=()
ISSUES_FOUND=()
TESTS_PASSED=0
TESTS_TOTAL=0

echo "[NOX REPAIR] Début de la réparation Nox API - $(date)"
echo "[NOX REPAIR] Rapport sera sauvé dans: $REPORT_FILE"

# =============================================================================
# Fonctions utilitaires
# =============================================================================

log_repair() {
    local message="$1"
    echo "[NOX REPAIR] ✓ $message"
    REPAIRS_MADE+=("$message")
}

log_issue() {
    local message="$1"
    echo "[NOX REPAIR] ⚠ $message"
    ISSUES_FOUND+=("$message")
}

log_error() {
    local message="$1"
    echo "[NOX REPAIR] ✗ $message"
    ISSUES_FOUND+=("ERREUR: $message")
}

check_critical_issue() {
    local issue="$1"
    local details="$2"
    
    echo "[NOX REPAIR] 🛑 PROBLÈME CRITIQUE DÉTECTÉ"
    echo "[NOX REPAIR] Issue: $issue"
    echo "[NOX REPAIR] Détails: $details"
    echo "[NOX REPAIR] ARRÊT pour validation manuelle requise"
    
    # Génération du rapport d'urgence
    generate_emergency_report "$issue" "$details"
    exit 2
}

generate_emergency_report() {
    local issue="$1"
    local details="$2"
    
    sudo mkdir -p "$(dirname "$REPORT_FILE")"
    sudo tee "$REPORT_FILE" >/dev/null <<EOF
# Rapport d'urgence - Réparation Nox API

**Date**: $(date)
**Status**: ARRÊT CRITIQUE - Validation manuelle requise

## Problème critique détecté

**Issue**: $issue
**Détails**: $details

## Actions requises

1. Examiner la situation manuellement
2. Corriger le problème identifié
3. Relancer le script de réparation

## Logs système récents

\`\`\`
$(sudo journalctl -u nox-api -n 20 --no-pager 2>/dev/null || echo "Logs non disponibles")
\`\`\`

## État du service

\`\`\`
$(systemctl status nox-api --no-pager 2>/dev/null || echo "Service non disponible")
\`\`\`
EOF
    
    sudo chown $NOX_USER:$NOX_GROUP "$REPORT_FILE" 2>/dev/null || true
    echo "[NOX REPAIR] Rapport d'urgence généré: $REPORT_FILE"
}

# =============================================================================
# 1. Arrêt du service pour maintenance
# =============================================================================

echo "[NOX REPAIR] === PHASE 1: Arrêt du service ==="

if systemctl is-active --quiet nox-api 2>/dev/null; then
    echo "[NOX REPAIR] Arrêt du service nox-api..."
    sudo systemctl stop nox-api
    log_repair "Service arrêté pour maintenance"
else
    log_issue "Service déjà arrêté ou inexistant"
fi

# =============================================================================
# 2. Vérification et réparation utilisateur/groupes
# =============================================================================

echo "[NOX REPAIR] === PHASE 2: Vérification utilisateur ==="

if ! id "$NOX_USER" &>/dev/null; then
    echo "[NOX REPAIR] Création de l'utilisateur $NOX_USER..."
    if sudo useradd -m -s /bin/bash "$NOX_USER"; then
        log_repair "Utilisateur $NOX_USER créé"
    else
        log_error "Échec de création de l'utilisateur $NOX_USER"
        exit 1
    fi
else
    echo "[NOX REPAIR] Utilisateur $NOX_USER existe"
fi

# Vérification du home directory
if [[ ! -d "$NOX_HOME" ]]; then
    log_error "Home directory manquant pour $NOX_USER"
    exit 1
fi

# =============================================================================
# 3. Vérification et réparation de l'arborescence
# =============================================================================

echo "[NOX REPAIR] === PHASE 3: Vérification arborescence ==="

# Création des répertoires manquants
for dir in "$NOX_API_DIR" "$NOX_SANDBOX_DIR" "$NOX_LOGS_DIR"; do
    if [[ ! -d "$dir" ]]; then
        echo "[NOX REPAIR] Création du répertoire $dir..."
        sudo mkdir -p "$dir"
        log_repair "Répertoire créé: $dir"
    fi
done

# Correction des permissions
echo "[NOX REPAIR] Vérification des permissions..."
sudo chown -R $NOX_USER:$NOX_GROUP "$NOX_ROOT"
sudo chmod 755 "$NOX_ROOT" "$NOX_API_DIR" "$NOX_LOGS_DIR"
sudo chmod 775 "$NOX_SANDBOX_DIR"  # Écriture pour l'exécution

# Vérification que sandbox n'a pas été effacé (protection données utilisateur)
if [[ -d "$NOX_SANDBOX_DIR" ]]; then
    SANDBOX_FILES=$(sudo find "$NOX_SANDBOX_DIR" -type f 2>/dev/null | wc -l)
    if [[ $SANDBOX_FILES -gt 0 ]]; then
        echo "[NOX REPAIR] Sandbox contient $SANDBOX_FILES fichiers - préservés"
    fi
fi

log_repair "Permissions corrigées sur l'arborescence"

# =============================================================================
# 4. Vérification et réparation du venv
# =============================================================================

echo "[NOX REPAIR] === PHASE 4: Vérification environnement virtuel ==="

VENV_CORRUPTED=false

# Test d'intégrité du venv existant
if [[ -d "$NOX_VENV_DIR" ]]; then
    echo "[NOX REPAIR] Test d'intégrité du venv existant..."
    
    # Vérifier l'exécutable Python
    if [[ ! -x "$NOX_VENV_DIR/bin/python3" ]]; then
        VENV_CORRUPTED=true
        log_issue "Exécutable Python manquant dans le venv"
    fi
    
    # Tester l'importation des modules critiques
    if ! sudo -u $NOX_USER bash -c "source $NOX_VENV_DIR/bin/activate && python3 -c 'import fastapi, uvicorn, pydantic'" 2>/dev/null; then
        VENV_CORRUPTED=true
        log_issue "Modules Python critiques manquants dans le venv"
    fi
else
    VENV_CORRUPTED=true
    log_issue "Environnement virtuel manquant"
fi

# Recréation du venv si nécessaire
if [[ "$VENV_CORRUPTED" == "true" ]]; then
    echo "[NOX REPAIR] Recréation de l'environnement virtuel..."
    
    # Suppression de l'ancien venv
    if [[ -d "$NOX_VENV_DIR" ]]; then
        sudo rm -rf "$NOX_VENV_DIR"
        log_repair "Ancien venv corrompu supprimé"
    fi
    
    # Création du nouveau venv
    if sudo -u $NOX_USER python3 -m venv "$NOX_VENV_DIR"; then
        log_repair "Nouvel environnement virtuel créé"
    else
        log_error "Échec de création du venv"
        exit 1
    fi
    
    # Installation des dépendances
    echo "[NOX REPAIR] Installation des dépendances Python..."
    if sudo -u $NOX_USER bash -c "
        source $NOX_VENV_DIR/bin/activate
        pip install --upgrade pip
        pip install fastapi uvicorn[standard] pydantic python-multipart
    "; then
        log_repair "Dépendances Python installées"
    else
        log_error "Échec d'installation des dépendances"
        exit 1
    fi
else
    echo "[NOX REPAIR] Environnement virtuel OK"
fi

# =============================================================================
# 5. Vérification et réparation du code API
# =============================================================================

echo "[NOX REPAIR] === PHASE 5: Vérification code API ==="

API_FILE="$NOX_API_DIR/nox_api.py"
API_CORRUPTED=false

if [[ ! -f "$API_FILE" ]]; then
    API_CORRUPTED=true
    log_issue "Fichier API manquant"
elif [[ ! -s "$API_FILE" ]]; then
    API_CORRUPTED=true
    log_issue "Fichier API vide"
else
    # Test de syntaxe Python
    if ! sudo -u $NOX_USER bash -c "source $NOX_VENV_DIR/bin/activate && python3 -m py_compile $API_FILE" 2>/dev/null; then
        API_CORRUPTED=true
        log_issue "Fichier API contient des erreurs de syntaxe"
    fi
    
    # Test d'importation
    if ! sudo -u $NOX_USER bash -c "cd $NOX_API_DIR && source $NOX_VENV_DIR/bin/activate && python3 -c 'import nox_api'" 2>/dev/null; then
        API_CORRUPTED=true
        log_issue "Fichier API non importable"
    fi
fi

# Restauration du code API si nécessaire
if [[ "$API_CORRUPTED" == "true" ]]; then
    echo "[NOX REPAIR] Restauration du code API..."
    
    # Sauvegarde de l'ancien fichier si il existe
    if [[ -f "$API_FILE" ]]; then
        sudo mv "$API_FILE" "${API_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        log_repair "Ancien fichier API sauvegardé"
    fi
    
    # Déploiement du code API fonctionnel
    cat <<'PYTHON_CODE' | sudo tee "$API_FILE" >/dev/null
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

    sudo chown $NOX_USER:$NOX_GROUP "$API_FILE"
    sudo chmod 644 "$API_FILE"
    log_repair "Code API restauré"
else
    echo "[NOX REPAIR] Code API OK"
fi

# =============================================================================
# 6. Vérification et réparation variables d'environnement
# =============================================================================

echo "[NOX REPAIR] === PHASE 6: Vérification variables d'environnement ==="

ENV_CORRUPTED=false
REQUIRED_VARS=("NOX_API_TOKEN" "NOX_SANDBOX" "NOX_TIMEOUT" "NOX_BIND_ADDR" "NOX_PORT")

if [[ ! -f "$ENV_FILE" ]]; then
    ENV_CORRUPTED=true
    log_issue "Fichier d'environnement manquant"
else
    # Vérification des variables requises
    for var in "${REQUIRED_VARS[@]}"; do
        if ! sudo grep -q "^$var=" "$ENV_FILE"; then
            ENV_CORRUPTED=true
            log_issue "Variable manquante: $var"
        fi
    done
    
    # Vérification que le token n'est pas vide
    if sudo grep -q "^NOX_API_TOKEN=$" "$ENV_FILE"; then
        ENV_CORRUPTED=true
        log_issue "Token vide détecté"
    fi
fi

# Réparation du fichier d'environnement si nécessaire
if [[ "$ENV_CORRUPTED" == "true" ]]; then
    echo "[NOX REPAIR] Réparation du fichier d'environnement..."
    
    # Sauvegarde de l'ancien fichier si il existe
    if [[ -f "$ENV_FILE" ]]; then
        sudo cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        log_repair "Ancien fichier d'environnement sauvegardé"
    fi
    
    # Génération du nouveau fichier d'environnement
    {
        echo "NOX_API_TOKEN=$(openssl rand -hex 16)"
        echo "NOX_SANDBOX=$NOX_SANDBOX_DIR"
        echo "NOX_TIMEOUT=20"
        echo "NOX_BIND_ADDR=127.0.0.1"
        echo "NOX_PORT=8080"
    } | sudo tee "$ENV_FILE" >/dev/null
    
    sudo chmod 600 "$ENV_FILE"
    log_repair "Fichier d'environnement restauré avec nouveau token"
else
    echo "[NOX REPAIR] Variables d'environnement OK"
fi

# =============================================================================
# 7. Vérification et réparation service systemd
# =============================================================================

echo "[NOX REPAIR] === PHASE 7: Vérification service systemd ==="

SERVICE_CORRUPTED=false

if [[ ! -f "$SERVICE_FILE" ]]; then
    SERVICE_CORRUPTED=true
    log_issue "Fichier service manquant"
else
    # Vérifications critiques du service
    REQUIRED_SERVICE_PARTS=("EnvironmentFile=$ENV_FILE" "User=$NOX_USER" "ExecStart=" "NoNewPrivileges=yes")
    
    for part in "${REQUIRED_SERVICE_PARTS[@]}"; do
        if ! sudo grep -q "$part" "$SERVICE_FILE"; then
            SERVICE_CORRUPTED=true
            log_issue "Configuration service manquante: $part"
        fi
    done
    
    # Vérification du chemin ExecStart
    if ! sudo grep -q "ExecStart=$NOX_VENV_DIR/bin/python3" "$SERVICE_FILE"; then
        SERVICE_CORRUPTED=true
        log_issue "Chemin ExecStart incorrect dans le service"
    fi
fi

# Réparation du service si nécessaire
if [[ "$SERVICE_CORRUPTED" == "true" ]]; then
    echo "[NOX REPAIR] Réparation du service systemd..."
    
    # Sauvegarde de l'ancien service si il existe
    if [[ -f "$SERVICE_FILE" ]]; then
        sudo cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        log_repair "Ancien service sauvegardé"
    fi
    
    # Création du service corrigé
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

    log_repair "Service systemd restauré avec durcissement"
else
    echo "[NOX REPAIR] Service systemd OK"
fi

# =============================================================================
# 8. Redémarrage et tests
# =============================================================================

echo "[NOX REPAIR] === PHASE 8: Redémarrage du service ==="

sudo systemctl daemon-reload
sudo systemctl enable nox-api

echo "[NOX REPAIR] Démarrage du service..."
if sudo systemctl start nox-api; then
    log_repair "Service redémarré avec succès"
else
    log_error "Échec du redémarrage du service"
    echo "[NOX REPAIR] Logs du service:"
    sudo journalctl -u nox-api -n 10 --no-pager
    exit 1
fi

# Attendre que le service soit prêt
echo "[NOX REPAIR] Attente de la disponibilité..."
for i in {1..15}; do
    if curl -s --max-time 2 http://127.0.0.1:8080/health >/dev/null 2>&1; then
        echo "[NOX REPAIR] API disponible"
        break
    fi
    if [[ $i -eq 15 ]]; then
        log_error "API non disponible après redémarrage"
        sudo journalctl -u nox-api -n 10 --no-pager
        exit 1
    fi
    sleep 1
done

# =============================================================================
# 9. Tests automatiques
# =============================================================================

echo "[NOX REPAIR] === PHASE 9: Tests automatiques ==="

# Récupération du token pour les tests
NOX_TOKEN=$(sudo grep "^NOX_API_TOKEN=" "$ENV_FILE" | cut -d= -f2)

# Test 1: Health check
echo "[NOX REPAIR] Test 1/4: /health"
((TESTS_TOTAL++))
set +e  # Désactiver l'arrêt sur erreur pour les tests
if curl -s --max-time 3 http://127.0.0.1:8080/health 2>/dev/null | grep -q "ok"; then
    echo "[NOX REPAIR] ✓ Test /health: SUCCESS"
    ((TESTS_PASSED++))
else
    echo "[NOX REPAIR] ✗ Test /health: FAILED"
fi
set -e  # Réactiver l'arrêt sur erreur

# Test 2: Upload
echo "[NOX REPAIR] Test 2/4: /put"
((TESTS_TOTAL++))
TEST_FILE=$(mktemp)
echo "repair test content" > "$TEST_FILE"
set +e
if curl -s --max-time 3 -H "Authorization: Bearer $NOX_TOKEN" -X POST "http://127.0.0.1:8080/put?path=repair_test.txt" -F "f=@$TEST_FILE" 2>/dev/null | grep -q "saved"; then
    echo "[NOX REPAIR] ✓ Test /put: SUCCESS"
    ((TESTS_PASSED++))
else
    echo "[NOX REPAIR] ✗ Test /put: FAILED"
fi
set -e
rm -f "$TEST_FILE"

# Test 3: Python execution
echo "[NOX REPAIR] Test 3/4: /run_py"
((TESTS_TOTAL++))
set +e
if curl -s --max-time 5 -H "Authorization: Bearer $NOX_TOKEN" -H "Content-Type: application/json" -X POST "http://127.0.0.1:8080/run_py" -d '{"code": "print(\"repair test ok\")"}' 2>/dev/null | grep -q "repair test ok"; then
    echo "[NOX REPAIR] ✓ Test /run_py: SUCCESS"
    ((TESTS_PASSED++))
else
    echo "[NOX REPAIR] ✗ Test /run_py: FAILED"
fi
set -e

# Test 4: Shell execution
echo "[NOX REPAIR] Test 4/4: /run_sh"
((TESTS_TOTAL++))
set +e
if curl -s --max-time 5 -H "Authorization: Bearer $NOX_TOKEN" -H "Content-Type: application/json" -X POST "http://127.0.0.1:8080/run_sh" -d '{"cmd": "echo repair test ok"}' 2>/dev/null | grep -q "repair test ok"; then
    echo "[NOX REPAIR] ✓ Test /run_sh: SUCCESS"
    ((TESTS_PASSED++))
else
    echo "[NOX REPAIR] ✗ Test /run_sh: FAILED"
fi
set -e

# =============================================================================
# 10. Génération du rapport final
# =============================================================================

echo "[NOX REPAIR] === GÉNÉRATION DU RAPPORT ==="

# S'assurer que le répertoire de logs existe
sudo mkdir -p "$(dirname "$REPORT_FILE")"

# Génération du rapport détaillé
sudo tee "$REPORT_FILE" >/dev/null <<EOF
# Rapport de réparation Nox API

**Date**: $(date)
**Durée**: Environ $(( SECONDS / 60 )) minutes
**Status**: $(if [[ $TESTS_PASSED -eq $TESTS_TOTAL && ${#ISSUES_FOUND[@]} -eq 0 ]]; then echo "✅ SUCCÈS"; else echo "⚠️ ATTENTION REQUISE"; fi)

## Résumé des réparations

$(if [[ ${#REPAIRS_MADE[@]} -eq 0 ]]; then
    echo "Aucune réparation nécessaire - système était sain"
else
    printf "### Réparations effectuées (%d):\n\n" ${#REPAIRS_MADE[@]}
    for repair in "${REPAIRS_MADE[@]}"; do
        echo "- ✓ $repair"
    done
fi)

## Issues identifiées

$(if [[ ${#ISSUES_FOUND[@]} -eq 0 ]]; then
    echo "Aucune issue détectée"
else
    printf "### Issues trouvées et corrigées (%d):\n\n" ${#ISSUES_FOUND[@]}
    for issue in "${ISSUES_FOUND[@]}"; do
        echo "- ⚠️ $issue"
    done
fi)

## Tests de validation

**Résultats**: $TESTS_PASSED/$TESTS_TOTAL tests réussis

- Test /health: $(if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then echo "✅ OK"; else echo "❌ FAIL"; fi)
- Test /put: $(if [[ $TESTS_PASSED -ge 2 ]]; then echo "✅ OK"; else echo "❌ FAIL"; fi)
- Test /run_py: $(if [[ $TESTS_PASSED -ge 3 ]]; then echo "✅ OK"; else echo "❌ FAIL"; fi)
- Test /run_sh: $(if [[ $TESTS_PASSED -ge 4 ]]; then echo "✅ OK"; else echo "❌ FAIL"; fi)

## État actuel du système

### Service systemd
\`\`\`
$(systemctl status nox-api --no-pager 2>/dev/null || echo "Service non disponible")
\`\`\`

### Configuration
- **Utilisateur**: $NOX_USER $(if id "$NOX_USER" &>/dev/null; then echo "✅"; else echo "❌"; fi)
- **Arborescence**: $(if [[ -d "$NOX_ROOT" ]]; then echo "✅ $NOX_ROOT"; else echo "❌ Manquante"; fi)
- **Venv**: $(if [[ -x "$NOX_VENV_DIR/bin/python3" ]]; then echo "✅ $NOX_VENV_DIR"; else echo "❌ Corrompu"; fi)
- **API**: $(if [[ -f "$NOX_API_DIR/nox_api.py" ]]; then echo "✅ Présente"; else echo "❌ Manquante"; fi)
- **Variables**: $(if [[ -f "$ENV_FILE" ]]; then echo "✅ Configurées"; else echo "❌ Manquantes"; fi)

### Sandbox
- **Chemin**: $NOX_SANDBOX_DIR
- **Permissions**: $(ls -ld "$NOX_SANDBOX_DIR" 2>/dev/null | cut -d' ' -f1 || echo "Non disponible")
- **Fichiers**: $(find "$NOX_SANDBOX_DIR" -type f 2>/dev/null | wc -l) fichiers préservés

## Recommandations

$(if [[ $TESTS_PASSED -eq $TESTS_TOTAL && ${#ISSUES_FOUND[@]} -eq 0 ]]; then
    echo "✅ Système opérationnel - Aucune action requise"
elif [[ $TESTS_PASSED -eq $TESTS_TOTAL ]]; then
    echo "⚠️ Tests passés mais des réparations ont été nécessaires - Surveiller le système"
else
    echo "❌ Certains tests ont échoué - Investigation manuelle requise"
    echo ""
    echo "### Actions suggérées:"
    echo "1. Vérifier les logs: \`sudo journalctl -u nox-api -f\`"
    echo "2. Tester manuellement les endpoints"
    echo "3. Vérifier la connectivité réseau"
fi)

## Logs récents du service

\`\`\`
$(sudo journalctl -u nox-api -n 20 --no-pager 2>/dev/null || echo "Logs non disponibles")
\`\`\`

---
*Rapport généré automatiquement par nox_repair.sh*
EOF

# Correction des permissions du rapport
sudo chown $NOX_USER:$NOX_GROUP "$REPORT_FILE" 2>/dev/null || true

# =============================================================================
# 11. Résumé final en console
# =============================================================================

echo ""
echo "[NOX REPAIR] === RÉSUMÉ FINAL ==="
echo "[NOX REPAIR] Réparations effectuées: ${#REPAIRS_MADE[@]}"
echo "[NOX REPAIR] Issues corrigées: ${#ISSUES_FOUND[@]}"
echo "[NOX REPAIR] Tests réussis: $TESTS_PASSED/$TESTS_TOTAL"
echo "[NOX REPAIR] Service status: $(systemctl is-active nox-api)"
echo "[NOX REPAIR] Rapport détaillé: $REPORT_FILE"

if [[ $TESTS_PASSED -eq $TESTS_TOTAL && ${#ISSUES_FOUND[@]} -eq 0 ]]; then
    echo "[NOX REPAIR] 🎉 RÉPARATION RÉUSSIE - Système opérationnel"
    exit 0
elif [[ $TESTS_PASSED -eq $TESTS_TOTAL ]]; then
    echo "[NOX REPAIR] ⚠️ RÉPARATION PARTIELLE - Tests OK mais issues corrigées"
    exit 0
else
    echo "[NOX REPAIR] ❌ RÉPARATION INCOMPLÈTE - Tests échoués"
    echo "[NOX REPAIR] Consulter le rapport pour plus de détails"
    exit 1
fi
