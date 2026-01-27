#!/usr/bin/env python3
"""
Test du client d'authentification pour le dashboard Nox API v2.3
"""
import sys
from pathlib import Path

# Ajouter le répertoire dashboard au PATH
sys.path.insert(0, str(Path(__file__).parent.parent / "dashboard"))

from client_v23 import NoxAuthClient


def test_authentication():
    """Test complet de l'authentification"""

    print("🚀 Test du client d'authentification Nox API v2.3")
    print("=" * 50)

    client = NoxAuthClient("http://127.0.0.1:8081")

    # Test 1: Vérification de l'API
    print("\n1️⃣  Test de connectivité...")
    try:
        health, headers = client.health()
        print(f"✅ API v{health.get('version')} accessible")
        print(f"   Request-ID: {headers.get('x-request-id', 'N/A')}")
    except Exception as e:
        print(f"❌ Erreur connectivité: {e}")
        return

    # Test 2: Initialisation admin
    print("\n2️⃣  Initialisation admin...")
    try:
        admin_info, _ = client.init_admin()
        print(f"✅ Admin créé: {admin_info.get('email')}")
    except Exception as e:
        print(f"ℹ️  Admin existe déjà ou erreur: {e}")

    # Test 3: Connexion admin
    print("\n3️⃣  Connexion admin...")
    try:
        token_data, headers = client.login("admin@example.com", "admin123")
        print("✅ Connexion admin réussie")
        print(f"   Token: {token_data['access_token'][:50]}...")
        print(f"   Expire dans: {token_data['expires_in']} secondes")

        # Le token est automatiquement configuré dans le client

    except Exception as e:
        print(f"❌ Erreur connexion admin: {e}")
        return

    # Test 4: Profil utilisateur
    print("\n4️⃣  Profil utilisateur...")
    try:
        user_info, _ = client.get_me()
        print(f"✅ Utilisateur connecté: {user_info['email']}")
        print(f"   Rôle: {user_info['role']}")
        print(
            f"   Quotas: {user_info['quota_files']} fichiers, {user_info['quota_cpu_seconds']}s CPU, {user_info['quota_memory_mb']}MB RAM"
        )
    except Exception as e:
        print(f"❌ Erreur profil: {e}")

    # Test 5: Fonctionnalités authentifiées
    print("\n5️⃣  Test des fonctionnalités authentifiées...")

    # Exécution Python
    try:
        result, headers = client.run_py(
            'print("Authentification fonctionnelle!")\nprint("Admin access confirmed")'
        )
        print(f"✅ Exécution Python: {result['stdout'].strip()}")
        print(f"   Utilisateur: {result.get('user', 'N/A')}")
    except Exception as e:
        print(f"❌ Erreur exécution Python: {e}")

    # Listing des fichiers
    try:
        files_data, _ = client.list_files()
        files_count = len(files_data.get("files", []))
        print(f"✅ Listing fichiers: {files_count} éléments")
        print(f"   Utilisateur: {files_data.get('user', 'N/A')}")
    except Exception as e:
        print(f"❌ Erreur listing: {e}")

    # Test 6: Fonctionnalités admin
    print("\n6️⃣  Test des fonctionnalités admin...")

    # Statistiques utilisateurs
    try:
        stats, _ = client.get_user_stats()
        print(f"✅ Statistiques: {stats['total_users']} utilisateurs total")
        print(f"   Actifs: {stats['active_users']}, Admins: {stats['admin_users']}")
    except Exception as e:
        print(f"❌ Erreur statistiques: {e}")

    # Liste des utilisateurs
    try:
        users, _ = client.list_users(limit=10)
        print(f"✅ Liste utilisateurs: {len(users)} utilisateurs récupérés")
        for user in users[:3]:  # Afficher les 3 premiers
            print(f"   - {user['email']} ({user['role']})")
    except Exception as e:
        print(f"❌ Erreur liste utilisateurs: {e}")

    # Informations admin
    try:
        admin_info, _ = client.admin_info()
        print("✅ Accès admin confirmé")
        print(f"   Admin: {admin_info.get('admin_user')}")
        print(f"   Métriques: {'activées' if admin_info.get('metrics_enabled') else 'désactivées'}")
    except Exception as e:
        print(f"❌ Erreur info admin: {e}")

    # Test 7: Test d'un utilisateur régulier
    print("\n7️⃣  Test utilisateur régulier...")

    # Créer un utilisateur test
    user_client = NoxAuthClient("http://127.0.0.1:8081")

    try:
        # Inscription
        user_token, _ = user_client.register("testuser@example.com", "password123", "user")
        print("✅ Utilisateur test créé et connecté")

        # Test des permissions
        try:
            user_info, _ = user_client.get_me()
            print(f"   Utilisateur: {user_info['email']} (rôle: {user_info['role']})")

            # Test exécution (autorisée)
            result, _ = user_client.run_py('print("User execution test")')
            print(f"   ✅ Exécution autorisée: {result['stdout'].strip()}")

            # Test accès admin (interdit)
            try:
                user_client.get_user_stats()
                print("   ❌ ERREUR: Accès admin autorisé pour un user!")
            except Exception:
                print("   ✅ Accès admin correctement refusé")

        except Exception as e:
            print(f"   ❌ Erreur utilisateur test: {e}")

    except Exception as e:
        print(f"ℹ️  Utilisateur test existe déjà ou erreur: {e}")

    # Test 8: Métriques
    print("\n8️⃣  Test des métriques...")
    try:
        metrics, headers = client.get_metrics()
        print(f"✅ Métriques récupérées: {len(metrics)} caractères")
        print(f"   Contient nox_requests_total: {'nox_requests_total' in metrics}")
        print(f"   Request-ID: {headers.get('x-request-id', 'N/A')}")
    except Exception as e:
        print(f"❌ Erreur métriques: {e}")

    print("\n✅ Tests du client d'authentification terminés!")


if __name__ == "__main__":
    test_authentication()
