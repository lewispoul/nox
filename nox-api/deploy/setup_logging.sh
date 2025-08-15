#!/bin/bash
# setup_logging.sh - Configuration du système de logs pour Nox API
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

log "🔧 Configuration du système de logs pour Nox API"

# 1. Créer le répertoire de logs
LOG_DIR="/var/log/nox-api"
log "Création du répertoire de logs: $LOG_DIR"

if [[ ! -d "$LOG_DIR" ]]; then
    mkdir -p "$LOG_DIR"
    chown nox:nox "$LOG_DIR"
    chmod 755 "$LOG_DIR"
    success "Répertoire de logs créé: $LOG_DIR"
else
    warning "Répertoire de logs existe déjà: $LOG_DIR"
fi

# 2. Créer les fichiers de logs
ACCESS_LOG="$LOG_DIR/access.log"
ERROR_LOG="$LOG_DIR/error.log"
APP_LOG="$LOG_DIR/nox-api.log"

for logfile in "$ACCESS_LOG" "$ERROR_LOG" "$APP_LOG"; do
    if [[ ! -f "$logfile" ]]; then
        touch "$logfile"
        chown nox:nox "$logfile"
        chmod 644 "$logfile"
        success "Fichier de log créé: $logfile"
    else
        warning "Fichier de log existe déjà: $logfile"
    fi
done

# 3. Configurer le service systemd pour utiliser les logs dédiés
SERVICE_FILE="/etc/systemd/system/nox-api.service"
log "Mise à jour de la configuration systemd pour les logs"

if [[ -f "$SERVICE_FILE" ]]; then
    # Créer une sauvegarde
    cp "$SERVICE_FILE" "$SERVICE_FILE.backup-$(date +%Y%m%d-%H%M%S)"
    
    # Vérifier si StandardOutput est déjà configuré
    if grep -q "StandardOutput=append:" "$SERVICE_FILE"; then
        warning "Configuration des logs déjà présente dans le service"
    else
        # Ajouter la configuration des logs dans la section [Service]
        sed -i '/\[Service\]/a\
# Logs dédiés - Étape 6\
StandardOutput=append:/var/log/nox-api/nox-api.log\
StandardError=append:/var/log/nox-api/error.log' "$SERVICE_FILE"
        
        success "Configuration des logs ajoutée au service systemd"
        
        # Recharger systemd
        systemctl daemon-reload
        success "Configuration systemd rechargée"
        
        # Redémarrer le service pour appliquer les nouveaux logs
        log "Redémarrage du service nox-api..."
        systemctl restart nox-api
        sleep 2
        
        if systemctl is-active nox-api >/dev/null; then
            success "Service nox-api redémarré avec succès"
        else
            error "Échec du redémarrage du service nox-api"
            log "Affichage des logs d'erreur:"
            journalctl -u nox-api -n 10 --no-pager
            exit 1
        fi
    fi
else
    error "Fichier de service systemd non trouvé: $SERVICE_FILE"
    exit 1
fi

# 4. Test des logs
log "Test de l'écriture des logs..."
sleep 3

# Vérifier que les logs sont écrits
if [[ -s "$APP_LOG" ]]; then
    success "Logs applicatifs fonctionnels"
    log "Dernières lignes du log:"
    tail -3 "$APP_LOG"
else
    warning "Pas encore de logs applicatifs (service peut être en cours de démarrage)"
fi

# 5. Configuration des permissions d'accès aux logs
log "Configuration des permissions d'accès aux logs"

# Créer un groupe pour l'accès aux logs
if ! getent group nox-logs >/dev/null; then
    groupadd nox-logs
    success "Groupe nox-logs créé"
else
    warning "Groupe nox-logs existe déjà"
fi

# Ajouter l'utilisateur nox et l'administrateur au groupe
usermod -a -G nox-logs nox
if [[ -n "${SUDO_USER:-}" ]]; then
    usermod -a -G nox-logs "$SUDO_USER"
    success "Utilisateur $SUDO_USER ajouté au groupe nox-logs"
fi

# Ajuster les permissions
chgrp nox-logs "$LOG_DIR"
chmod 750 "$LOG_DIR"
chgrp nox-logs "$LOG_DIR"/*.log
chmod 640 "$LOG_DIR"/*.log

success "Permissions des logs configurées"

# 6. Créer des alias utiles pour les logs
log "Création d'aliases pour la consultation des logs"

ALIAS_FILE="/etc/bash.bashrc.d/nox-logs-aliases.sh"
mkdir -p "$(dirname "$ALIAS_FILE")"

cat > "$ALIAS_FILE" << 'EOF'
# Aliases Nox API - Logs et debugging
# Générés automatiquement par setup_logging.sh

# Consultation des logs
alias nox-logs='sudo tail -f /var/log/nox-api/nox-api.log'
alias nox-logs-errors='sudo tail -f /var/log/nox-api/error.log'
alias nox-logs-access='sudo tail -f /var/log/nox-api/access.log'
alias nox-logs-all='sudo tail -f /var/log/nox-api/*.log'

# Statistiques des logs
alias nox-stats='sudo wc -l /var/log/nox-api/*.log'
alias nox-errors-today='sudo grep "$(date +%Y-%m-%d)" /var/log/nox-api/error.log | wc -l'

# Service et debug
alias nox-status='systemctl status nox-api'
alias nox-journal='sudo journalctl -u nox-api -f'
alias nox-restart='sudo systemctl restart nox-api && sleep 2 && systemctl status nox-api'
EOF

success "Aliases de logs créés dans $ALIAS_FILE"

echo ""
success "🎉 Configuration des logs terminée avec succès!"
echo ""
log "📋 Résumé de la configuration:"
echo "   📁 Répertoire logs: $LOG_DIR"
echo "   📄 Logs applicatifs: $APP_LOG"
echo "   📄 Logs d'erreurs: $ERROR_LOG" 
echo "   📄 Logs d'accès: $APP_LOG (via stdout)"
echo "   👥 Groupe d'accès: nox-logs"
echo "   🔧 Aliases disponibles: nox-logs, nox-logs-errors, nox-status, etc."
echo ""
log "💡 Commandes utiles:"
echo "   sudo tail -f /var/log/nox-api/nox-api.log  # Suivre les logs en temps réel"
echo "   sudo journalctl -u nox-api -f              # Logs systemd (anciens)"
echo "   systemctl status nox-api                   # Statut du service"
echo ""
log "🔄 Prochaine étape: Configuration de la rotation des logs (logrotate)"
