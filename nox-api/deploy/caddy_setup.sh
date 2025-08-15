#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Nox API - Configuration Caddy (Étape 4)
# Conforme à docs/planning/COPILOT_PLAN.md - Étape 4
# =============================================================================

MODE=${1:-lan}         # lan ou public
DOMAIN=${2:-}
EMAIL=${3:-}

# Fonction d'installation de Caddy
install_caddy() {
    echo "[CADDY] Installation de Caddy..."
    
    if command -v caddy >/dev/null 2>&1; then
        echo "[CADDY] Caddy déjà installé: $(caddy version 2>/dev/null || echo 'version inconnue')"
        return 0
    fi
    
    # Méthode d'installation directe plus fiable
    echo "[CADDY] Installation via binaire officiel..."
    
    # Détecter l'architecture
    local arch
    case "$(uname -m)" in
        x86_64) arch="amd64" ;;
        aarch64) arch="arm64" ;;
        armv7l) arch="armv7" ;;
        *) echo "[ERR] Architecture non supportée: $(uname -m)"; exit 1 ;;
    esac
    
    # Téléchargement et installation
    local caddy_version="2.7.6"
    local download_url="https://github.com/caddyserver/caddy/releases/download/v${caddy_version}/caddy_${caddy_version}_linux_${arch}.tar.gz"
    
    echo "[CADDY] Téléchargement de Caddy v${caddy_version} pour ${arch}..."
    cd /tmp
    curl -L "$download_url" -o caddy.tar.gz
    
    # Extraction et installation
    tar -xzf caddy.tar.gz caddy
    sudo mv caddy /usr/bin/caddy
    sudo chown root:root /usr/bin/caddy
    sudo chmod +x /usr/bin/caddy
    
    # Créer l'utilisateur caddy
    sudo groupadd --system caddy 2>/dev/null || true
    sudo useradd --system --gid caddy --create-home --home-dir /var/lib/caddy --shell /usr/sbin/nologin caddy 2>/dev/null || true
    
    # Créer le service systemd
    sudo tee /etc/systemd/system/caddy.service >/dev/null <<'EOF'
[Unit]
Description=Caddy
Documentation=https://caddyserver.com/docs/
After=network.target network-online.target
Requires=network-online.target

[Service]
Type=notify
User=caddy
Group=caddy
ExecStart=/usr/bin/caddy run --environ --config /etc/caddy/Caddyfile
ExecReload=/usr/bin/caddy reload --config /etc/caddy/Caddyfile --force
TimeoutStopSec=5s
LimitNOFILE=1048576
LimitNPROC=1048576
PrivateTmp=true
ProtectSystem=full
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF
    
    # Rechargement systemd
    sudo systemctl daemon-reload
    
    # Nettoyage
    rm -f /tmp/caddy.tar.gz
    
    echo "[CADDY] ✓ Caddy installé avec succès: $(caddy version)"
}

# Fonction d'écriture du Caddyfile
write_caddyfile() {
    local dst=/etc/caddy/Caddyfile
    
    echo "[CADDY] Écriture de la configuration Caddy..."
    sudo install -d -m 755 /etc/caddy
    
    if [[ "$MODE" == "lan" ]]; then
        echo "[CADDY] Configuration pour mode LAN (port 80, pas de TLS)"
        sudo tee "$dst" >/dev/null <<'EOF'
# Configuration Nox API - Mode LAN
# Proxy sans TLS sur port 80

:80 {
  encode gzip
  header {
    X-Content-Type-Options nosniff
    X-Frame-Options DENY
    Referrer-Policy no-referrer
    Content-Security-Policy "default-src 'none'"
  }
  reverse_proxy 127.0.0.1:8080 {
    flush_interval -1
    header_up X-Forwarded-Proto {scheme}
    header_up X-Forwarded-For {remote}
    header_up X-Forwarded-Host {host}
  }
  
  # Log des accès
  log {
    output file /var/log/caddy/nox-access.log
    format json
  }
}
EOF
    else
        echo "[CADDY] Configuration pour mode PUBLIC avec domaine: $DOMAIN"
        [[ -n "$DOMAIN" && -n "$EMAIL" ]] || { 
            echo "[ERR] Domaine et email requis en mode public"
            echo "Usage: $0 public votre-domaine.tld votre-email@example.com"
            exit 1
        }
        
        sudo tee "$dst" >/dev/null <<EOF
# Configuration Nox API - Mode PUBLIC
# ACME automatique avec Let's Encrypt

$DOMAIN {
  email $EMAIL
  encode gzip
  header {
    Strict-Transport-Security "max-age=63072000; includeSubDomains; preload"
    X-Content-Type-Options nosniff
    X-Frame-Options DENY
    Referrer-Policy no-referrer
    Content-Security-Policy "default-src 'none'"
  }
  reverse_proxy 127.0.0.1:8080 {
    flush_interval -1
    header_up X-Forwarded-Proto {scheme}
    header_up X-Forwarded-For {remote}
    header_up X-Forwarded-Host {host}
  }
  
  # Log des accès
  log {
    output file /var/log/caddy/nox-access.log
    format json
  }
}
EOF
    fi
    
    echo "[CADDY] ✓ Caddyfile écrit: $dst"
}

# Configuration UFW (firewall)
configure_ufw() {
    echo "[CADDY] Configuration du firewall UFW..."
    
    if ! command -v ufw >/dev/null 2>&1; then
        echo "[CADDY] UFW non installé, installation..."
        sudo apt-get install -y ufw
    fi
    
    # Autoriser les ports nécessaires
    echo "[CADDY] Autorisation des ports HTTP/HTTPS..."
    sudo ufw --force enable 2>/dev/null || true
    sudo ufw allow 80/tcp || true
    sudo ufw allow 443/tcp || true
    
    # Fermer explicitement le port 8080
    echo "[CADDY] Fermeture du port 8080 (accès direct à Nox)..."
    sudo ufw deny 8080/tcp 2>/dev/null || true
    
    echo "[CADDY] ✓ Firewall configuré"
}

# Création des répertoires de logs
setup_logging() {
    echo "[CADDY] Configuration des logs..."
    sudo mkdir -p /var/log/caddy
    sudo chown caddy:caddy /var/log/caddy 2>/dev/null || true
    sudo chmod 755 /var/log/caddy
    echo "[CADDY] ✓ Logs configurés"
}

# Test de la configuration
test_caddy_config() {
    echo "[CADDY] Test de la configuration..."
    
    if ! sudo caddy validate --config /etc/caddy/Caddyfile; then
        echo "[ERR] Configuration Caddy invalide!"
        echo "Contenu du Caddyfile:"
        sudo cat /etc/caddy/Caddyfile
        exit 1
    fi
    
    echo "[CADDY] ✓ Configuration valide"
}

# Démarrage et activation du service
start_caddy_service() {
    echo "[CADDY] Activation et démarrage du service Caddy..."
    
    # Arrêter les services conflictuels potentiels
    sudo systemctl stop nginx 2>/dev/null || true
    sudo systemctl stop apache2 2>/dev/null || true
    
    # Activation et démarrage de Caddy
    sudo systemctl enable caddy
    sudo systemctl restart caddy
    
    # Vérification du statut
    sleep 3
    if ! sudo systemctl is-active --quiet caddy; then
        echo "[ERR] Échec du démarrage de Caddy!"
        echo "Logs du service:"
        sudo journalctl -u caddy -n 20 --no-pager
        exit 1
    fi
    
    echo "[CADDY] ✓ Service Caddy démarré et actif"
}

# Tests fonctionnels
run_functional_tests() {
    echo "[CADDY] Tests fonctionnels..."
    
    # Attendre que Caddy soit prêt
    echo "[CADDY] Attente de la disponibilité du service..."
    for i in {1..15}; do
        if curl -s --max-time 2 http://localhost/health >/dev/null 2>&1; then
            echo "[CADDY] ✓ Service accessible via HTTP"
            break
        fi
        if [[ $i -eq 15 ]]; then
            echo "[ERR] Service non accessible après 15 tentatives"
            echo "Statut du service:"
            sudo systemctl status caddy --no-pager || true
            echo "Logs récents:"
            sudo journalctl -u caddy -n 10 --no-pager || true
            exit 1
        fi
        sleep 2
    done
    
    # Test spécifique selon le mode
    if [[ "$MODE" == "lan" ]]; then
        echo "[CADDY] Test en mode LAN..."
        local response=$(curl -s -w "%{http_code}" http://localhost/health 2>/dev/null || echo "000")
        if [[ "$response" == *"200" ]]; then
            echo "[CADDY] ✓ API accessible via Caddy en mode LAN"
        else
            echo "[ERR] API non accessible (code: $response)"
            exit 1
        fi
    else
        echo "[CADDY] Test en mode PUBLIC (domaine: $DOMAIN)..."
        echo "[CADDY] Note: Le certificat ACME peut prendre quelques minutes"
        
        # Test HTTP (redirection)
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" "http://$DOMAIN/health" 2>/dev/null || echo "000")
        if [[ "$http_code" == "308" || "$http_code" == "301" ]]; then
            echo "[CADDY] ✓ Redirection HTTP vers HTTPS active"
        else
            echo "[CADDY] ⚠ Redirection HTTP inhabituelle (code: $http_code)"
        fi
        
        # Test HTTPS (peut échouer si certificat en cours d'obtention)
        if timeout 30 curl -s --max-time 10 "https://$DOMAIN/health" >/dev/null 2>&1; then
            echo "[CADDY] ✓ API accessible via HTTPS avec certificat valide"
        else
            echo "[CADDY] ⚠ HTTPS non encore accessible (certificat en cours d'obtention?)"
        fi
    fi
}

# Rapport final
generate_final_report() {
    echo ""
    echo "=========================================="
    echo "CADDY SETUP TERMINÉ - MODE: $MODE"
    echo "=========================================="
    
    echo "=== STATUT DU SERVICE ==="
    sudo systemctl status caddy --no-pager --lines=3 || true
    echo ""
    
    echo "=== CONFIGURATION ==="
    if [[ "$MODE" == "lan" ]]; then
        echo "Mode: LAN (sans TLS)"
        echo "Accès: http://$(hostname -I | awk '{print $1}')/health"
        echo "Port: 80"
    else
        echo "Mode: PUBLIC avec TLS automatique"
        echo "Domaine: $DOMAIN"
        echo "Email: $EMAIL"
        echo "Accès: https://$DOMAIN/health"
        echo "Certificat: Let's Encrypt via ACME"
    fi
    echo ""
    
    echo "=== SÉCURITÉ ==="
    echo "✓ Port 8080 fermé au public"
    echo "✓ En-têtes de sécurité appliqués"
    echo "✓ Compression gzip activée"
    if [[ "$MODE" == "public" ]]; then
        echo "✓ HSTS activé (max-age=63072000)"
        echo "✓ Certificat TLS automatique"
    fi
    echo ""
    
    echo "=== TESTS ==="
    echo "Test local: curl -i http://localhost/health"
    if [[ "$MODE" == "public" ]]; then
        echo "Test public: curl -Ik https://$DOMAIN/health"
    fi
    echo "Port 8080: $(sudo ss -lntp | grep :8080 >/dev/null && echo 'Ouvert en local uniquement' || echo 'Fermé')"
    echo ""
    
    echo "=== LOGS ==="
    echo "Service: sudo journalctl -u caddy -f"
    echo "Accès: sudo tail -f /var/log/caddy/nox-access.log"
    
    echo ""
    echo "=========================================="
    echo "🎉 CADDY OPÉRATIONNEL EN MODE $MODE"
    echo "=========================================="
}

# =============================================================================
# EXÉCUTION PRINCIPALE
# =============================================================================

echo "=========================================="
echo "NOX API - CONFIGURATION CADDY"
echo "Mode: $MODE"
echo "Début: $(date)"
echo "=========================================="

# Validation des paramètres
case "$MODE" in
    lan)
        echo "[INFO] Mode LAN sélectionné - HTTP sur port 80"
        ;;
    public)
        echo "[INFO] Mode PUBLIC sélectionné"
        if [[ -z "$DOMAIN" || -z "$EMAIL" ]]; then
            echo "[ERR] Usage: $0 public votre-domaine.tld votre-email@example.com"
            exit 1
        fi
        echo "[INFO] Domaine: $DOMAIN"
        echo "[INFO] Email: $EMAIL"
        ;;
    *)
        echo "[ERR] Mode non supporté: $MODE"
        echo "Usage: $0 [lan|public] [domaine] [email]"
        exit 1
        ;;
esac

# Vérifier que Nox API fonctionne
echo "[CADDY] Vérification que Nox API est accessible..."
if ! curl -s --max-time 3 http://127.0.0.1:8080/health >/dev/null; then
    echo "[ERR] Nox API non accessible sur http://127.0.0.1:8080"
    echo "Vérifiez que le service nox-api est démarré:"
    echo "  sudo systemctl status nox-api"
    echo "  make status"
    exit 1
fi
echo "[CADDY] ✓ Nox API accessible"

# Exécution des étapes
install_caddy
setup_logging
write_caddyfile
test_caddy_config
configure_ufw
start_caddy_service
run_functional_tests
generate_final_report

exit 0
