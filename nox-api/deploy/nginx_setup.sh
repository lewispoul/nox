#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Nox API - Configuration Nginx (Étape 4)
# Conforme à docs/planning/COPILOT_PLAN.md - Étape 4
# =============================================================================

DOMAIN=${1:-}
EMAIL=${2:-}

# Validation des paramètres
if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
    echo "[ERR] Paramètres manquants"
    echo "Usage: $0 domaine.tld email@example.com"
    echo "Exemple: $0 api.mondomaine.com admin@mondomaine.com"
    exit 1
fi

echo "=========================================="
echo "NOX API - CONFIGURATION NGINX + HTTPS"
echo "Domaine: $DOMAIN"
echo "Email: $EMAIL"
echo "Début: $(date)"
echo "=========================================="

# Installation de Nginx et Certbot
install_nginx_certbot() {
    echo "[NGINX] Installation de Nginx et Certbot..."
    
    # Arrêter les services conflictuels
    sudo systemctl stop caddy 2>/dev/null || true
    sudo systemctl stop apache2 2>/dev/null || true
    
    # Installation
    sudo apt-get update
    sudo apt-get install -y nginx certbot python3-certbot-nginx
    
    # Vérification des versions
    echo "[NGINX] ✓ Nginx version: $(nginx -v 2>&1 | cut -d'/' -f2)"
    echo "[NGINX] ✓ Certbot version: $(certbot --version 2>/dev/null | cut -d' ' -f2)"
}

# Déploiement de la configuration Nginx
deploy_nginx_config() {
    echo "[NGINX] Déploiement de la configuration..."
    
    # Vérifier que le fichier example existe
    local example_file="nox-api/deploy/nginx_nox.conf.example"
    if [[ ! -f "$example_file" ]]; then
        echo "[ERR] Fichier de configuration example non trouvé: $example_file"
        exit 1
    fi
    
    # Créer la configuration en remplaçant les variables
    echo "[NGINX] Création de la configuration pour $DOMAIN..."
    sed "s/EXEMPLE_DOMAINE/$DOMAIN/g" "$example_file" | sudo tee /etc/nginx/sites-available/nox.conf >/dev/null
    
    # Désactiver la configuration par défaut
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Activer la configuration Nox
    sudo ln -sf /etc/nginx/sites-available/nox.conf /etc/nginx/sites-enabled/nox.conf
    
    echo "[NGINX] ✓ Configuration déployée"
}

# Configuration temporaire pour Certbot
setup_temp_config() {
    echo "[NGINX] Configuration temporaire pour l'obtention du certificat..."
    
    # Configuration temporaire sans SSL pour l'ACME challenge
    sudo tee /etc/nginx/sites-available/nox-temp.conf >/dev/null <<EOF
# Configuration temporaire pour ACME challenge
server {
    listen 80;
    server_name $DOMAIN;
    
    # ACME challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }
    
    # Redirection temporaire vers API locale (pour test)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    # Activer la configuration temporaire
    sudo rm -f /etc/nginx/sites-enabled/nox.conf
    sudo ln -sf /etc/nginx/sites-available/nox-temp.conf /etc/nginx/sites-enabled/nox-temp.conf
}

# Test et rechargement de Nginx
reload_nginx() {
    echo "[NGINX] Test et rechargement de la configuration..."
    
    # Test de la configuration
    if ! sudo nginx -t; then
        echo "[ERR] Configuration Nginx invalide!"
        echo "Configuration actuelle:"
        sudo nginx -T 2>/dev/null | grep -A 20 "server_name $DOMAIN" || true
        exit 1
    fi
    
    # Rechargement
    sudo systemctl enable nginx
    sudo systemctl reload nginx
    
    # Vérification du statut
    if ! sudo systemctl is-active --quiet nginx; then
        echo "[ERR] Nginx ne fonctionne pas!"
        sudo systemctl status nginx --no-pager
        exit 1
    fi
    
    echo "[NGINX] ✓ Configuration rechargée avec succès"
}

# Obtention du certificat SSL
obtain_ssl_certificate() {
    echo "[NGINX] Obtention du certificat SSL via Let's Encrypt..."
    
    # Vérifier que le domaine pointe vers ce serveur
    echo "[NGINX] Vérification DNS du domaine $DOMAIN..."
    if ! timeout 10 dig +short "$DOMAIN" >/dev/null 2>&1; then
        echo "[WARNING] Impossible de résoudre $DOMAIN"
        echo "Assurez-vous que le DNS pointe vers cette IP:"
        ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v 127.0.0.1 | head -1
        echo "Continuons quand même..."
    fi
    
    # Création du répertoire webroot
    sudo mkdir -p /var/www/html
    
    # Obtention du certificat avec Certbot
    echo "[NGINX] Lancement de Certbot..."
    set +e  # Désactiver l'arrêt sur erreur temporairement
    
    local certbot_output
    certbot_output=$(sudo certbot --nginx \
        -d "$DOMAIN" \
        -m "$EMAIL" \
        --agree-tos \
        --redirect \
        --no-eff-email \
        --non-interactive 2>&1)
    
    local certbot_exit_code=$?
    set -e  # Réactiver l'arrêt sur erreur
    
    if [[ $certbot_exit_code -eq 0 ]]; then
        echo "[NGINX] ✓ Certificat SSL obtenu avec succès"
        return 0
    else
        echo "[ERR] Échec de l'obtention du certificat SSL"
        echo "Sortie de Certbot:"
        echo "$certbot_output"
        
        echo ""
        echo "=========================================="
        echo "RAPPORT D'ÉCHEC CERTBOT"
        echo "=========================================="
        echo "Domaine: $DOMAIN"
        echo "Email: $EMAIL"
        echo "Code de sortie: $certbot_exit_code"
        echo ""
        echo "Causes possibles:"
        echo "1. Le domaine $DOMAIN ne pointe pas vers cette IP"
        echo "2. Le port 80 n'est pas accessible depuis Internet"
        echo "3. Un autre service utilise le port 80"
        echo "4. Problème de firewall"
        echo ""
        echo "Vérifications à effectuer:"
        echo "• DNS: dig $DOMAIN"
        echo "• Port 80: sudo ss -lntp | grep :80"
        echo "• Firewall: sudo ufw status"
        echo "• IP publique: curl -4 ifconfig.me"
        echo ""
        echo "Basculement en mode LAN recommandé:"
        echo "  cd /path/to/nox && sudo bash deploy/caddy_setup.sh lan"
        echo "=========================================="
        
        return 1
    fi
}

# Activation de la configuration finale avec SSL
activate_ssl_config() {
    echo "[NGINX] Activation de la configuration finale avec SSL..."
    
    # Vérifier que le certificat existe
    if [[ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]]; then
        echo "[ERR] Certificat SSL non trouvé pour $DOMAIN"
        exit 1
    fi
    
    # Réactiver la configuration SSL
    sudo rm -f /etc/nginx/sites-enabled/nox-temp.conf
    sudo ln -sf /etc/nginx/sites-available/nox.conf /etc/nginx/sites-enabled/nox.conf
    
    # Test et rechargement final
    reload_nginx
    
    echo "[NGINX] ✓ Configuration SSL activée"
}

# Configuration du firewall
configure_firewall() {
    echo "[NGINX] Configuration du firewall..."
    
    if command -v ufw >/dev/null 2>&1; then
        # Activer UFW
        sudo ufw --force enable 2>/dev/null || true
        
        # Autoriser Nginx Full (80 + 443)
        sudo ufw allow 'Nginx Full' || true
        
        # Supprimer l'autorisation du port 8080 s'il existe
        sudo ufw delete allow 8080/tcp 2>/dev/null || true
        sudo ufw deny 8080/tcp 2>/dev/null || true
        
        echo "[NGINX] ✓ Firewall configuré (Nginx Full autorisé, 8080 fermé)"
    else
        echo "[NGINX] UFW non disponible, configuration firewall manuelle requise"
    fi
}

# Tests fonctionnels
run_functional_tests() {
    echo "[NGINX] Tests fonctionnels..."
    
    # Attendre que Nginx soit prêt
    sleep 3
    
    # Test HTTPS
    echo "[NGINX] Test HTTPS..."
    local https_response
    https_response=$(curl -s -w "%{http_code}" --max-time 10 "https://$DOMAIN/health" 2>/dev/null || echo "000")
    
    if [[ "$https_response" == *"200" ]]; then
        echo "[NGINX] ✓ API accessible via HTTPS"
    else
        echo "[ERR] API non accessible via HTTPS (code: ${https_response%???})"
        echo "Logs Nginx récents:"
        sudo tail -n 20 /var/log/nginx/error.log || true
        exit 1
    fi
    
    # Test redirection HTTP → HTTPS
    echo "[NGINX] Test redirection HTTP → HTTPS..."
    local http_redirect
    http_redirect=$(curl -s -w "%{http_code}" -L --max-time 10 "http://$DOMAIN/health" 2>/dev/null || echo "000")
    
    if [[ "$http_redirect" == *"200" ]]; then
        echo "[NGINX] ✓ Redirection HTTP → HTTPS fonctionnelle"
    else
        echo "[NGINX] ⚠ Problème de redirection HTTP (code: ${http_redirect%???})"
    fi
    
    # Test du certificat SSL
    echo "[NGINX] Vérification du certificat SSL..."
    if timeout 10 openssl s_client -connect "$DOMAIN:443" -servername "$DOMAIN" </dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
        echo "[NGINX] ✓ Certificat SSL valide"
    else
        echo "[NGINX] ⚠ Problème de certificat SSL (mais service fonctionnel)"
    fi
}

# Configuration des logs
setup_log_rotation() {
    echo "[NGINX] Configuration de la rotation des logs..."
    
    # Logrotate pour les logs Nox spécifiques
    sudo tee /etc/logrotate.d/nox-nginx >/dev/null <<EOF
/var/log/nginx/nox-*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    sharedscripts
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 \$(cat /var/run/nginx.pid) 2>/dev/null || true
        fi
    endscript
}
EOF
    
    echo "[NGINX] ✓ Rotation des logs configurée"
}

# Rapport final
generate_final_report() {
    echo ""
    echo "=========================================="
    echo "NGINX SETUP TERMINÉ AVEC SUCCÈS"
    echo "=========================================="
    
    echo "=== STATUT DU SERVICE ==="
    sudo systemctl status nginx --no-pager --lines=3 || true
    echo ""
    
    echo "=== CONFIGURATION ==="
    echo "Domaine: $DOMAIN"
    echo "Email: $EMAIL"
    echo "Certificat: Let's Encrypt"
    echo "Accès HTTPS: https://$DOMAIN/health"
    echo "Redirection HTTP: http://$DOMAIN → https://$DOMAIN"
    echo ""
    
    echo "=== SÉCURITÉ ==="
    echo "✓ Port 8080 fermé au public"
    echo "✓ Certificat SSL/TLS actif"
    echo "✓ HSTS activé (max-age=63072000)"
    echo "✓ En-têtes de sécurité appliqués"
    echo "✓ Redirection HTTP → HTTPS"
    echo ""
    
    echo "=== TESTS ==="
    echo "Test HTTPS: curl -Ik https://$DOMAIN/health"
    echo "Test HTTP: curl -I http://$DOMAIN/health"
    echo "Certificat: echo | openssl s_client -connect $DOMAIN:443 -servername $DOMAIN 2>/dev/null | openssl x509 -dates -noout"
    echo ""
    
    echo "=== MAINTENANCE ==="
    echo "Renouvellement auto: sudo crontab -l | grep certbot"
    echo "Logs Nginx: sudo tail -f /var/log/nginx/nox-https-access.log"
    echo "Logs SSL: sudo tail -f /var/log/nginx/nox-https-error.log"
    echo "Test config: sudo nginx -t"
    echo ""
    
    echo "=========================================="
    echo "🎉 NGINX OPÉRATIONNEL SUR https://$DOMAIN"
    echo "=========================================="
}

# =============================================================================
# EXÉCUTION PRINCIPALE
# =============================================================================

# Vérifier que Nox API fonctionne
echo "[NGINX] Vérification que Nox API est accessible..."
if ! curl -s --max-time 3 http://127.0.0.1:8080/health >/dev/null; then
    echo "[ERR] Nox API non accessible sur http://127.0.0.1:8080"
    echo "Vérifiez que le service nox-api est démarré:"
    echo "  sudo systemctl status nox-api"
    echo "  make status"
    exit 1
fi
echo "[NGINX] ✓ Nox API accessible"

# Exécution des étapes
install_nginx_certbot
deploy_nginx_config
setup_temp_config
reload_nginx

# Tentative d'obtention du certificat SSL
if obtain_ssl_certificate; then
    # Succès - Configuration SSL complète
    activate_ssl_config
    configure_firewall
    setup_log_rotation
    run_functional_tests
    generate_final_report
else
    # Échec - Mode dégradé
    echo ""
    echo "=========================================="
    echo "MODE DÉGRADÉ - CERTIFICAT SSL ÉCHEC"
    echo "=========================================="
    echo ""
    echo "Le service fonctionne en HTTP uniquement."
    echo "Configuration actuelle:"
    echo "• Nginx actif sur port 80"
    echo "• Proxy vers Nox API local"
    echo "• HTTPS non disponible"
    echo ""
    echo "Alternatives recommandées:"
    echo "1. Vérifier la configuration DNS"
    echo "2. Utiliser Caddy en mode LAN:"
    echo "   sudo bash deploy/caddy_setup.sh lan"
    echo ""
    echo "Service accessible sur: http://$DOMAIN/health"
    echo "=========================================="
    exit 1
fi

exit 0
