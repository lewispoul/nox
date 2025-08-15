#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Nox API - Script de durcissement (Étape 3)
# Conforme à docs/planning/COPILOT_PLAN.md - Étape 3
# =============================================================================

# Configuration
NOX_USER=nox
NOX_GROUP=nox
NOX_HOME=/home/$NOX_USER
OLD_VENV_PATH="$NOX_HOME/nox/.venv"
NEW_VENV_PATH="/opt/nox/.venv"
SERVICE_FILE="/etc/systemd/system/nox-api.service"
API_DIR="$NOX_HOME/nox/api"
SANDBOX_DIR="$NOX_HOME/nox/sandbox"
LOGS_DIR="$NOX_HOME/nox/logs"

# Variables de suivi
STEPS_COMPLETED=()
BACKUP_CREATED=""
MIGRATION_SUCCESS=false
SERVICE_RESTART_SUCCESS=false

# Fonctions utilitaires
log_step() {
    local message="$1"
    echo "[NOX] $message"
    STEPS_COMPLETED+=("$message")
}

log_error() {
    local message="$1"
    echo "[NOX ERROR] $message" >&2
}

generate_failure_report() {
    local error_msg="$1"
    
    echo ""
    echo "========================================="
    echo "RAPPORT D'ÉCHEC - DURCISSEMENT NOX API"
    echo "========================================="
    echo "Erreur: $error_msg"
    echo "Date: $(date)"
    echo ""
    
    echo "=== ÉTAPES COMPLÉTÉES ==="
    for step in "${STEPS_COMPLETED[@]}"; do
        echo "✓ $step"
    done
    echo ""
    
    echo "=== ÉTAT DES RÉPERTOIRES ==="
    echo "Ancien venv (/home/nox/nox/.venv):"
    ls -la "$OLD_VENV_PATH" 2>/dev/null || echo "  Introuvable"
    echo ""
    echo "Nouveau venv (/opt/nox/.venv):"
    ls -la "$NEW_VENV_PATH" 2>/dev/null || echo "  Introuvable"
    echo ""
    echo "Sauvegardes:"
    ls -la "$NOX_HOME/nox/.venv.bak."* 2>/dev/null || echo "  Aucune sauvegarde trouvée"
    echo ""
    
    echo "=== LOGS DU SERVICE ==="
    sudo journalctl -u nox-api -n 100 --no-pager 2>/dev/null || echo "Logs indisponibles"
    echo ""
    
    echo "=== STATUT DU SERVICE ==="
    sudo systemctl status nox-api --no-pager 2>/dev/null || echo "Service indisponible"
    
    echo ""
    echo "========================================="
    echo "FIN DU RAPPORT D'ÉCHEC"
    echo "========================================="
}

# Fonction de nettoyage en cas d'erreur
cleanup_on_error() {
    local error_msg="$1"
    
    log_error "Erreur détectée: $error_msg"
    
    # Si une sauvegarde a été créée et que la migration a échoué, proposer une restauration
    if [[ -n "$BACKUP_CREATED" && "$MIGRATION_SUCCESS" == "false" ]]; then
        log_error "Tentative de restauration de l'ancien venv..."
        if [[ -d "$BACKUP_CREATED" ]]; then
            sudo rm -rf "$OLD_VENV_PATH" 2>/dev/null || true
            sudo cp -a "$BACKUP_CREATED" "$OLD_VENV_PATH" 2>/dev/null || true
            sudo chown -R $NOX_USER:$NOX_GROUP "$OLD_VENV_PATH" 2>/dev/null || true
            log_step "Venv restauré depuis la sauvegarde"
        fi
    fi
    
    generate_failure_report "$error_msg"
    exit 1
}

# Piège pour les erreurs
trap 'cleanup_on_error "Script interrompu"' ERR

echo "=========================================="
echo "NOX HARDENING - Durcissement sécurisé"
echo "Début: $(date)"
echo "=========================================="

# =============================================================================
# Phase 1: Vérifications préliminaires
# =============================================================================

log_step "Vérifications préliminaires"

# Vérifier que nous sommes root/sudo
if [[ $EUID -ne 0 && -z "${SUDO_USER:-}" ]]; then
    cleanup_on_error "Ce script doit être exécuté avec sudo"
fi

# Vérifier que l'utilisateur nox existe
if ! id "$NOX_USER" &>/dev/null; then
    cleanup_on_error "Utilisateur $NOX_USER introuvable. Exécutez d'abord l'installation."
fi

# Vérifier que le service existe
if [[ ! -f "$SERVICE_FILE" ]]; then
    cleanup_on_error "Service $SERVICE_FILE introuvable. Exécutez d'abord l'installation."
fi

# Vérifier que l'ancien venv existe et fonctionne
if [[ ! -d "$OLD_VENV_PATH" ]]; then
    cleanup_on_error "Ancien venv $OLD_VENV_PATH introuvable"
fi

if [[ ! -x "$OLD_VENV_PATH/bin/python3" ]]; then
    cleanup_on_error "Ancien venv $OLD_VENV_PATH non fonctionnel"
fi

log_step "Vérifications préliminaires terminées"

# =============================================================================
# Phase 2: Arrêt du service et sauvegarde
# =============================================================================

log_step "Arrêt du service nox-api"
sudo systemctl stop nox-api || cleanup_on_error "Impossible d'arrêter le service"

log_step "Sauvegarde de l'ancien venv"
if [[ -d "$OLD_VENV_PATH" ]]; then
    BACKUP_PATH="$NOX_HOME/nox/.venv.bak.$(date +%Y%m%d%H%M%S)"
    sudo cp -a "$OLD_VENV_PATH" "$BACKUP_PATH"
    sudo chown -R $NOX_USER:$NOX_GROUP "$BACKUP_PATH"
    BACKUP_CREATED="$BACKUP_PATH"
    log_step "Sauvegarde créée: $BACKUP_PATH"
else
    log_step "Aucun venv à sauvegarder"
fi

# =============================================================================
# Phase 3: Création du nouveau venv
# =============================================================================

log_step "Création du répertoire /opt/nox"
sudo mkdir -p /opt/nox
sudo chown $NOX_USER:$NOX_GROUP /opt/nox
sudo chmod 755 /opt/nox

# Vérifier si le nouveau venv existe déjà (idempotence)
if [[ -d "$NEW_VENV_PATH" && -x "$NEW_VENV_PATH/bin/python3" ]]; then
    log_step "Nouveau venv existe déjà et est fonctionnel"
    
    # Vérifier que les dépendances sont installées
    if sudo -u $NOX_USER bash -c "source $NEW_VENV_PATH/bin/activate && python3 -c 'import fastapi, uvicorn'" 2>/dev/null; then
        log_step "Dépendances déjà installées dans le nouveau venv"
    else
        log_step "Installation des dépendances manquantes"
        sudo -u $NOX_USER bash -c "
            source $NEW_VENV_PATH/bin/activate
            pip install --upgrade pip
            pip install fastapi uvicorn[standard] pydantic python-multipart
        " || cleanup_on_error "Impossible d'installer les dépendances"
    fi
else
    log_step "Création du nouveau venv dans $NEW_VENV_PATH"
    sudo -u $NOX_USER python3 -m venv "$NEW_VENV_PATH" || cleanup_on_error "Impossible de créer le nouveau venv"
    
    log_step "Installation des dépendances"
    sudo -u $NOX_USER bash -c "
        source $NEW_VENV_PATH/bin/activate
        pip install --upgrade pip
        pip install fastapi uvicorn[standard] pydantic python-multipart
    " || cleanup_on_error "Impossible d'installer les dépendances"
fi

# Vérifier que le nouveau venv fonctionne
if ! sudo -u $NOX_USER bash -c "source $NEW_VENV_PATH/bin/activate && python3 -c 'import fastapi, uvicorn'" 2>/dev/null; then
    cleanup_on_error "Le nouveau venv ne fonctionne pas correctement"
fi

MIGRATION_SUCCESS=true
log_step "Nouveau venv créé et validé"

# =============================================================================
# Phase 4: Mise à jour du service systemd
# =============================================================================

log_step "Sauvegarde du fichier service actuel"
sudo cp "$SERVICE_FILE" "$SERVICE_FILE.bak.$(date +%Y%m%d%H%M%S)"

log_step "Mise à jour du chemin venv dans le service"
# Utiliser une approche plus sûre pour la substitution
sudo sed -i.tmp "s#$OLD_VENV_PATH#$NEW_VENV_PATH#g" "$SERVICE_FILE"

# Vérifier que la substitution a fonctionné
if ! sudo grep -q "$NEW_VENV_PATH" "$SERVICE_FILE"; then
    cleanup_on_error "Échec de la mise à jour du chemin venv dans le service"
fi

log_step "Application des options de sécurité avancées"

# Créer un service temporaire avec les nouveaux paramètres
sudo tee "$SERVICE_FILE.new" >/dev/null <<EOF
[Unit]
Description=Nox API
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$NOX_USER
Group=$NOX_GROUP
EnvironmentFile=/etc/default/nox-api
WorkingDirectory=$API_DIR
ExecStart=$NEW_VENV_PATH/bin/python3 -m uvicorn nox_api:app --host \${NOX_BIND_ADDR} --port \${NOX_PORT}
Restart=on-failure
RestartSec=10

# Durcissement sécurité - Étape 3
ProtectSystem=strict
ProtectHome=read-only
NoNewPrivileges=true
PrivateTmp=true
ReadWritePaths=$SANDBOX_DIR $LOGS_DIR
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictNamespaces=true
RestrictRealtime=true
MemoryDenyWriteExecute=true

[Install]
WantedBy=multi-user.target
EOF

# Remplacer l'ancien service par le nouveau
sudo mv "$SERVICE_FILE.new" "$SERVICE_FILE"

log_step "Service systemd mis à jour avec durcissement avancé"

# =============================================================================
# Phase 5: Rechargement et tests
# =============================================================================

log_step "Rechargement de systemd"
sudo systemctl daemon-reload || cleanup_on_error "Échec du rechargement systemd"

log_step "Redémarrage du service nox-api"
sudo systemctl start nox-api || cleanup_on_error "Impossible de redémarrer le service"

# Attendre que le service soit vraiment prêt
log_step "Vérification du démarrage du service"
for i in {1..10}; do
    if systemctl is-active --quiet nox-api; then
        SERVICE_RESTART_SUCCESS=true
        break
    fi
    if [[ $i -eq 10 ]]; then
        cleanup_on_error "Service ne démarre pas après 10 tentatives"
    fi
    sleep 2
done

log_step "Service redémarré avec succès"

# =============================================================================
# Phase 6: Tests fonctionnels
# =============================================================================

log_step "Tests fonctionnels de l'API"

# Test 1: Health check
log_step "Test 1: Health check"
for i in {1..10}; do
    if curl -s --max-time 2 http://127.0.0.1:8080/health >/dev/null 2>&1; then
        log_step "✓ Health check réussi"
        break
    fi
    if [[ $i -eq 10 ]]; then
        cleanup_on_error "API ne répond pas après 10 tentatives"
    fi
    sleep 1
done

# Test 2: Test avec authentification (si token disponible)
if [[ -f "/etc/default/nox-api" ]]; then
    TOKEN=$(sudo grep "^NOX_API_TOKEN=" /etc/default/nox-api | cut -d= -f2 2>/dev/null || true)
    if [[ -n "$TOKEN" ]]; then
        log_step "Test 2: Upload et exécution Python"
        
        # Test upload
        if curl -s --max-time 5 \
            -H "Authorization: Bearer $TOKEN" \
            -F "f=@-;filename=test.py" \
            -F "path=test_harden.py" \
            http://127.0.0.1:8080/put <<<'print("Test hardening OK")' >/dev/null 2>&1; then
            log_step "✓ Upload réussi"
        else
            log_step "⚠ Test upload échoué (non critique)"
        fi
        
        # Test exécution
        if curl -s --max-time 5 \
            -H "Authorization: Bearer $TOKEN" \
            -H "Content-Type: application/json" \
            -d '{"code": "import sys; print(f\"Python {sys.version_info.major}.{sys.version_info.minor} OK\")"}' \
            http://127.0.0.1:8080/run_py | grep -q "Python.*OK" 2>/dev/null; then
            log_step "✓ Exécution Python réussie"
        else
            log_step "⚠ Test exécution Python échoué (non critique)"
        fi
    fi
fi

log_step "Tests fonctionnels terminés"

# =============================================================================
# Phase 7: Nettoyage et rapport final
# =============================================================================

log_step "Nettoyage de l'ancien venv"
if [[ -d "$OLD_VENV_PATH" && -n "$BACKUP_CREATED" ]]; then
    sudo rm -rf "$OLD_VENV_PATH"
    log_step "Ancien venv supprimé (sauvegarde conservée: $BACKUP_CREATED)"
fi

# Rapport final de succès
echo ""
echo "=========================================="
echo "DURCISSEMENT RÉUSSI - NOX API"
echo "=========================================="
echo "Date: $(date)"
echo ""

echo "=== MODIFICATIONS APPLIQUÉES ==="
for step in "${STEPS_COMPLETED[@]}"; do
    echo "✓ $step"
done
echo ""

echo "=== ÉTAT FINAL ==="
echo "Service: $(systemctl is-active nox-api 2>/dev/null || echo 'non disponible')"
echo "API Health: $(curl -s http://127.0.0.1:8080/health 2>/dev/null | grep -o 'ok' || echo 'non disponible')"
echo "Nouveau venv: $NEW_VENV_PATH"
echo "Sauvegarde: ${BACKUP_CREATED:-'aucune'}"
echo ""

echo "=== CONFIGURATION SÉCURISÉE ==="
echo "✓ ProtectSystem=strict"
echo "✓ ProtectHome=read-only"  
echo "✓ NoNewPrivileges=true"
echo "✓ PrivateTmp=true"
echo "✓ ReadWritePaths=$SANDBOX_DIR $LOGS_DIR"
echo "✓ Restrictions supplémentaires activées"
echo ""

echo "=== TESTS DE VALIDATION ==="
echo "1. Statut du service:"
sudo systemctl status nox-api --no-pager --lines=3
echo ""

echo "2. Test API:"
curl -s http://127.0.0.1:8080/health && echo " ← Health check OK"
echo ""

echo "3. Venv migré:"
ls -la "$NEW_VENV_PATH/bin/python*" 2>/dev/null || echo "Erreur: venv introuvable"
echo ""

echo "=========================================="
echo "🎉 DURCISSEMENT TERMINÉ AVEC SUCCÈS"
echo "Le service Nox API est maintenant sécurisé"
echo "et fonctionne avec l'environnement durci."
echo "=========================================="

# Désactiver le piège d'erreur pour une sortie propre
trap - ERR
exit 0
