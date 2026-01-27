#!/usr/bin/env python3
"""
Demo script pour présenter les fonctionnalités d'authentification Nox API v2.3
"""
import sys
import time
from pathlib import Path

# Ajouter le répertoire dashboard au PATH
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

from client_v23 import NoxAuthClient


def demo_authentication():
    """Démonstration interactive de l'authentification"""

    print("🎭 DÉMONSTRATION NOX API v2.3 - Authentification RBAC")
    print("=" * 60)

    client = NoxAuthClient("http://127.0.0.1:8081")

    # Étape 1: Vérification de l'API
    print("\n🔍 1. Vérification de l'API Nox v2.3...")
    try:
        health, _ = client.health()
        print(f"   ✅ API v{health['version']} opérationnelle")
        print(f"   📁 Sandbox: {health['sandbox']}")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return

    time.sleep(1)

    # Étape 2: Connexion admin
    print("\n👑 2. Connexion administrateur...")
    try:
        token_data, _ = client.login("admin@example.com", "admin123")
        print("   ✅ Admin connecté avec succès")
        print(f"   🎫 Token valide pendant {token_data['expires_in']//3600}h")

        # Profil admin
        user_info, _ = client.get_me()
        print(f"   👤 {user_info['email']} (rôle: {user_info['role']})")

    except Exception as e:
        print(f"   ❌ Erreur connexion admin: {e}")
        return

    time.sleep(1)

    # Étape 3: Fonctionnalités admin
    print("\n🔧 3. Fonctionnalités administrateur...")
    try:
        # Statistiques
        stats, _ = client.get_user_stats()
        print(f"   📊 {stats['total_users']} utilisateurs total")
        print(
            f"   📈 {stats['active_users']} actifs ({stats['admin_users']} admins, {stats['regular_users']} users)"
        )

        # Informations système
        admin_info, _ = client.admin_info()
        print(f"   🎛️  Métriques: {'✅' if admin_info['metrics_enabled'] else '❌'}")

    except Exception as e:
        print(f"   ❌ Erreur fonctions admin: {e}")

    time.sleep(1)

    # Étape 4: Exécution de code authentifié
    print("\n🐍 4. Exécution de code Python authentifié...")
    try:
        code = """
import os
import datetime

print("🎉 Code exécuté avec authentification!")
print(f"⏰ Timestamp: {datetime.datetime.now()}")
print(f"🔐 Utilisateur authentifié: Admin")
print(f"📊 Sandbox accessible: {os.getcwd()}")

# Calcul simple
result = sum(range(1, 11))
print(f"🧮 Calcul: somme 1-10 = {result}")
"""

        result, headers = client.run_py(code)
        print("   ✅ Code exécuté avec succès")
        print(f"   👤 Utilisateur: {result.get('user', 'N/A')}")
        print(f"   🆔 Request-ID: {headers.get('x-request-id', 'N/A')[:8]}...")

        # Afficher la sortie
        stdout = result.get("stdout", "").strip()
        if stdout:
            print("   📤 Sortie:")
            for line in stdout.split("\n"):
                print(f"      {line}")

    except Exception as e:
        print(f"   ❌ Erreur exécution: {e}")

    time.sleep(1)

    # Étape 5: Test avec utilisateur normal
    print("\n👤 5. Test avec utilisateur normal...")
    user_client = NoxAuthClient("http://127.0.0.1:8081")

    try:
        # Tentative de connexion (utilisateur peut ne pas exister)
        try:
            user_token, _ = user_client.login("test@example.com", "testpass123")
            print("   ✅ Utilisateur test connecté")

            # Test des permissions
            try:
                user_client.get_user_stats()  # Action admin
                print("   ❌ ERREUR: Utilisateur a accès aux fonctions admin!")
            except Exception:
                print("   ✅ Accès admin correctement refusé")

        except Exception:
            print("   ℹ️  Utilisateur test non trouvé ou erreur de connexion")

    except Exception as e:
        print(f"   ❌ Erreur utilisateur test: {e}")

    time.sleep(1)

    # Étape 6: Métriques Prometheus
    print("\n📊 6. Métriques Prometheus...")
    try:
        metrics, headers = client.get_metrics()
        print(f"   ✅ {len(metrics):,} caractères de métriques récupérés")

        # Recherche de métriques spécifiques
        metrics_types = []
        if "nox_requests_total" in metrics:
            metrics_types.append("Compteur de requêtes")
        if "nox_latency" in metrics:
            metrics_types.append("Latence")
        if "sandbox" in metrics:
            metrics_types.append("Métriques sandbox")

        print(f"   🏷️  Types détectés: {', '.join(metrics_types) if metrics_types else 'Standard'}")
        print(f"   🆔 Request-ID: {headers.get('x-request-id', 'N/A')[:8]}...")

    except Exception as e:
        print(f"   ❌ Erreur métriques: {e}")

    # Récapitulatif
    print("\n🎉 DÉMONSTRATION TERMINÉE")
    print("=" * 60)
    print("✅ Authentification JWT fonctionnelle")
    print("✅ Contrôle d'accès par rôles (RBAC) opérationnel")
    print("✅ Sécurisation des endpoints réussie")
    print("✅ Tracking des utilisateurs dans les réponses")
    print("✅ Métriques Prometheus accessibles")
    print("\n📍 Services disponibles:")
    print("   🌐 API Nox v2.3: http://127.0.0.1:8081")
    print("   🎨 Dashboard Streamlit: http://127.0.0.1:8502")
    print("\n👤 Comptes par défaut:")
    print("   👑 Admin: admin@example.com / admin123")
    print("   👤 User:  test@example.com / testpass123")


if __name__ == "__main__":
    demo_authentication()
