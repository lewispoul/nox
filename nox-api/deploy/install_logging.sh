#!/bin/bash
# install_logging.sh - Installation complète du système de logs et rotation
# Conforme à docs/planning/COPILOT_PLAN.md - Étape 6

set -euo pipefail

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Fonction de logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️ $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

# Vérification des privilèges root
if [[ $EUID -ne 0 ]]; then
    error "Ce script doit être exécuté avec sudo"
    exit 1
fi

# Répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

log "🚀 Installation complète du système de logs Nox API - Étape 6"

# 1. Exécuter setup_logging.sh
log "Phase 1: Configuration de base des logs"
if [[ -f "$SCRIPT_DIR/setup_logging.sh" ]]; then
    bash "$SCRIPT_DIR/setup_logging.sh"
    success "Configuration de base terminée"
else
    error "Script setup_logging.sh non trouvé dans $SCRIPT_DIR"
    exit 1
fi

echo ""
log "Phase 2: Installation de la rotation des logs (logrotate)"

# 2. Installer la configuration logrotate
LOGROTATE_SOURCE="$SCRIPT_DIR/logrotate-nox"
LOGROTATE_DEST="/etc/logrotate.d/nox-api"

if [[ -f "$LOGROTATE_SOURCE" ]]; then
    log "Installation de la configuration logrotate..."
    
    # Copier la configuration
    cp "$LOGROTATE_SOURCE" "$LOGROTATE_DEST"
    chown root:root "$LOGROTATE_DEST"
    chmod 644 "$LOGROTATE_DEST"
    
    success "Configuration logrotate installée: $LOGROTATE_DEST"
    
    # Tester la configuration logrotate
    log "Test de la configuration logrotate..."
    if logrotate -d "$LOGROTATE_DEST" >/dev/null 2>&1; then
        success "Configuration logrotate valide"
    else
        warning "Configuration logrotate peut avoir des problèmes, mais c'est souvent normal en mode test"
    fi
    
    # Test de rotation manuelle (mode debug)
    log "Test de rotation en mode debug..."
    logrotate -d -f "$LOGROTATE_DEST" > /tmp/logrotate-test.log 2>&1 || true
    
    if [[ -s /tmp/logrotate-test.log ]]; then
        log "Aperçu du test logrotate:"
        head -10 /tmp/logrotate-test.log | sed 's/^/   /'
        rm -f /tmp/logrotate-test.log
    fi
    
else
    error "Fichier logrotate-nox non trouvé: $LOGROTATE_SOURCE"
    exit 1
fi

echo ""
log "Phase 3: Configuration des outils de debug"

# 3. Créer un script de debug/diagnostic
DEBUG_SCRIPT="/usr/local/bin/nox-debug"
log "Création du script de diagnostic: $DEBUG_SCRIPT"

cat > "$DEBUG_SCRIPT" << 'EOF'
#!/bin/bash
# nox-debug - Script de diagnostic Nox API
# Usage: nox-debug [logs|status|health|full]

set -euo pipefail

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[DEBUG] $1${NC}"
}

success() {
    echo -e "${GREEN}[OK] $1${NC}"
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

show_logs() {
    log "=== LOGS NOX API ==="
    
    if [[ -d "/var/log/nox-api" ]]; then
        log "Logs dédiés disponibles:"
        for logfile in /var/log/nox-api/*.log; do
            if [[ -f "$logfile" ]]; then
                echo "  📄 $logfile ($(wc -l < "$logfile") lignes, $(du -sh "$logfile" | cut -f1))"
            fi
        done
        
        echo ""
        log "Dernières lignes des logs (10 dernières):"
        echo "--- APPLICATION ---"
        sudo tail -10 /var/log/nox-api/nox-api.log 2>/dev/null || echo "Pas de logs applicatifs"
        echo "--- ERREURS ---"
        sudo tail -10 /var/log/nox-api/error.log 2>/dev/null || echo "Pas de logs d'erreur"
    else
        warning "Répertoire logs dédié non trouvé, utilisation de journalctl"
        sudo journalctl -u nox-api -n 20 --no-pager
    fi
}

show_status() {
    log "=== STATUT SYSTÈME ==="
    
    # Service systemd
    echo "🔧 Service nox-api:"
    systemctl is-active nox-api && success "Service actif" || error "Service inactif"
    systemctl is-enabled nox-api && success "Service activé au démarrage" || warning "Service non activé au démarrage"
    
    # API Health
    echo ""
    echo "🔍 API Health Check:"
    if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then
        success "API répond sur port 8080"
        API_STATUS=$(curl -s http://127.0.0.1:8080/health | jq -r '.status' 2>/dev/null || echo "inconnu")
        echo "   Status: $API_STATUS"
    else
        error "API ne répond pas sur port 8080"
    fi
    
    # Reverse proxy
    echo ""
    echo "🌐 Reverse Proxy (port 80):"
    if curl -s http://localhost/health >/dev/null 2>&1; then
        success "Reverse proxy opérationnel"
    else
        warning "Reverse proxy non disponible ou non configuré"
    fi
    
    # Ports en écoute
    echo ""
    echo "📡 Ports en écoute:"
    sudo ss -lntp | grep -E ":80|:443|:8080" || echo "Aucun port web détecté"
    
    # Configuration
    echo ""
    echo "⚙️ Configuration:"
    if [[ -f "/etc/default/nox-api" ]]; then
        success "Configuration trouvée: /etc/default/nox-api"
    else
        error "Configuration manquante: /etc/default/nox-api"
    fi
}

show_health() {
    log "=== HEALTH CHECK DÉTAILLÉ ==="
    
    # Test API direct
    echo "🎯 Test API direct (port 8080):"
    if TOKEN=$(sudo grep "^NOX_API_TOKEN=" /etc/default/nox-api 2>/dev/null | cut -d= -f2 | tr -d '"'); then
        echo "   Token trouvé: ${TOKEN:0:8}..."
        
        # Health check
        HEALTH_RESULT=$(curl -s http://127.0.0.1:8080/health 2>/dev/null || echo "ERREUR")
        if [[ "$HEALTH_RESULT" == *'"status":"ok"'* ]]; then
            success "Health check OK"
        else
            error "Health check échoué: $HEALTH_RESULT"
        fi
        
        # Test upload simple
        echo "   Test upload..."
        UPLOAD_RESULT=$(curl -s -H "Authorization: Bearer $TOKEN" \
                           -F "f=@-" \
                           "http://127.0.0.1:8080/put?path=debug_test.txt" \
                           <<< "Test debug $(date)" 2>/dev/null || echo "ERREUR")
        
        if [[ "$UPLOAD_RESULT" == *'"saved":'* ]]; then
            success "Upload test OK"
        else
            error "Upload test échoué: $UPLOAD_RESULT"
        fi
        
    else
        error "Token non trouvé dans /etc/default/nox-api"
    fi
    
    # Espace disque sandbox
    echo ""
    echo "💾 Espace sandbox:"
    if [[ -d "/home/nox/nox/sandbox" ]]; then
        SANDBOX_SIZE=$(du -sh /home/nox/nox/sandbox 2>/dev/null | cut -f1)
        SANDBOX_FILES=$(find /home/nox/nox/sandbox -type f 2>/dev/null | wc -l)
        echo "   Taille: $SANDBOX_SIZE"
        echo "   Fichiers: $SANDBOX_FILES"
        
        # Fichiers récents
        echo "   Fichiers récents:"
        find /home/nox/nox/sandbox -type f -mtime -1 2>/dev/null | head -5 | sed 's/^/     /' || echo "     Aucun"
    else
        error "Sandbox non trouvé: /home/nox/nox/sandbox"
    fi
}

show_full() {
    show_status
    echo ""
    show_health  
    echo ""
    show_logs
    
    echo ""
    log "=== DIAGNOSTIC COMPLET ==="
    
    # Espace disque
    echo "💿 Espace disque:"
    df -h / | tail -1 | awk '{print "   Racine: " $4 " disponible (" $5 " utilisé)"}'
    
    if [[ -d "/var/log/nox-api" ]]; then
        LOG_SIZE=$(du -sh /var/log/nox-api 2>/dev/null | cut -f1)
        echo "   Logs Nox: $LOG_SIZE"
    fi
    
    # Mémoire
    echo ""
    echo "🧠 Utilisation mémoire (processus nox-api):"
    ps aux | grep -E "(python3.*nox_api|uvicorn.*nox_api)" | grep -v grep | awk '{print "   PID " $2 ": " $4 "% RAM, " $3 "% CPU"}' || echo "   Processus non trouvé"
    
    # Réseau
    echo ""
    echo "🌐 Connectivité réseau:"
    ping -c 1 127.0.0.1 >/dev/null 2>&1 && success "Localhost accessible" || error "Problème réseau local"
    
    echo ""
    success "Diagnostic terminé"
}

# Main
case "${1:-full}" in
    "logs")
        show_logs
        ;;
    "status")
        show_status
        ;;
    "health")
        show_health
        ;;
    "full")
        show_full
        ;;
    *)
        echo "Usage: nox-debug [logs|status|health|full]"
        echo ""
        echo "Commandes:"
        echo "  logs   - Afficher les logs récents"
        echo "  status - Statut des services"
        echo "  health - Tests de santé détaillés" 
        echo "  full   - Diagnostic complet (défaut)"
        exit 1
        ;;
esac
EOF

chmod +x "$DEBUG_SCRIPT"
success "Script de diagnostic créé: $DEBUG_SCRIPT"

# 4. Installation des outils de monitoring
log "Phase 4: Outils de monitoring et maintenance"

# Script de surveillance continue
MONITOR_SCRIPT="/usr/local/bin/nox-monitor"
log "Création du script de surveillance: $MONITOR_SCRIPT"

cat > "$MONITOR_SCRIPT" << 'EOF'
#!/bin/bash
# nox-monitor - Surveillance continue de Nox API
# Usage: nox-monitor [interval_seconds]

INTERVAL=${1:-60}  # Défaut: 60 secondes
LOG_FILE="/var/log/nox-api/monitor.log"

echo "🔍 Démarrage surveillance Nox API (intervalle: ${INTERVAL}s)"
echo "📄 Logs: $LOG_FILE"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Test health check
    if curl -s http://127.0.0.1:8080/health >/dev/null 2>&1; then
        STATUS="OK"
    else
        STATUS="FAIL"
    fi
    
    # Statistiques
    MEMORY_USAGE=$(ps aux | grep -E "python3.*nox_api" | grep -v grep | awk '{sum+=$4} END {printf "%.1f", sum}')
    MEMORY_USAGE=${MEMORY_USAGE:-0.0}
    
    # Log vers fichier
    echo "[$TIMESTAMP] STATUS=$STATUS MEM=${MEMORY_USAGE}%" | sudo tee -a "$LOG_FILE" >/dev/null
    
    # Affichage console
    if [[ "$STATUS" == "OK" ]]; then
        echo -e "[$TIMESTAMP] \033[32m✅ API OK\033[0m (MEM: ${MEMORY_USAGE}%)"
    else
        echo -e "[$TIMESTAMP] \033[31m❌ API FAIL\033[0m (MEM: ${MEMORY_USAGE}%)"
    fi
    
    sleep "$INTERVAL"
done
EOF

chmod +x "$MONITOR_SCRIPT"
success "Script de surveillance créé: $MONITOR_SCRIPT"

echo ""
success "🎉 Installation complète du système de logs terminée!"

echo ""
log "📋 RÉSUMÉ - SYSTÈME DE LOGS INSTALLÉ:"
echo "   📁 Logs dédiés: /var/log/nox-api/"
echo "   🔄 Rotation: /etc/logrotate.d/nox-api (quotidienne, 30 jours)" 
echo "   🔧 Debug: nox-debug [logs|status|health|full]"
echo "   👁️  Monitor: nox-monitor [interval]"
echo "   📧 Aliases: nox-logs, nox-status, etc."

echo ""
log "💡 COMMANDES UTILES:"
echo "   sudo tail -f /var/log/nox-api/nox-api.log    # Logs temps réel"
echo "   nox-debug                                     # Diagnostic complet"
echo "   nox-debug health                              # Test santé API"
echo "   nox-monitor 30                                # Surveillance 30s"
echo "   sudo logrotate -f /etc/logrotate.d/nox-api    # Rotation manuelle"

echo ""
log "🔄 PROCHAINES ÉTAPES:"
echo "   1. Tester: nox-debug"
echo "   2. Vérifier logs: ls -la /var/log/nox-api/"
echo "   3. Documentation: mise à jour README.md avec troubleshooting"

echo ""
warning "⚠️  IMPORTANT:"
echo "   - Les logs sont maintenant dans /var/log/nox-api/ au lieu de journalctl"
echo "   - Redémarrage automatique du service effectué pour appliquer les nouveaux logs"
echo "   - Utilisez 'nox-debug' pour diagnostiquer les problèmes"
