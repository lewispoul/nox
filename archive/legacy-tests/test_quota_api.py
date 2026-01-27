#!/usr/bin/env python3
"""
Test script pour l'API avec quotas - Milestone 5.3
Test de l'enforcement middleware et des endpoints
"""
import json
import time
from urllib.parse import urljoin

import requests

API_BASE_URL = "http://127.0.0.1:8082"
API_TOKEN = "test123"


def make_request(endpoint, method="GET", data=None, headers=None):
    """Fait une requête API avec gestion d'erreur"""
    url = urljoin(API_BASE_URL, endpoint)
    default_headers = {"Authorization": f"Bearer {API_TOKEN}"}
    if headers:
        default_headers.update(headers)

    try:
        if method == "GET":
            response = requests.get(url, headers=default_headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=default_headers, timeout=10)
        else:
            print(f"❌ Méthode {method} non supportée")
            return None

        print(f"{method} {endpoint} -> {response.status_code}")

        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Erreur: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Exception lors de la requête vers {endpoint}: {e}")
        return None


def test_api_availability():
    """Test de disponibilité de l'API"""
    print("\n🔍 Test 1: Disponibilité de l'API")

    # Test health endpoint
    health_data = make_request("/health")
    if health_data:
        print(f"✅ API Health: {health_data}")
        return True
    else:
        print("❌ API non disponible")
        return False


def test_quota_endpoints():
    """Test des endpoints de quotas"""
    print("\n🔍 Test 2: Endpoints de quotas")

    # Test mes quotas
    print("\n--- Mes quotas ---")
    quotas_data = make_request("/quotas/my/quotas")
    if quotas_data:
        print(f"✅ Quotas utilisateur: {json.dumps(quotas_data, indent=2)}")

    # Test mon usage
    print("\n--- Mon usage ---")
    usage_data = make_request("/quotas/my/usage")
    if usage_data:
        print(f"✅ Usage utilisateur: {json.dumps(usage_data, indent=2)}")

    # Test mes violations
    print("\n--- Mes violations ---")
    violations_data = make_request("/quotas/my/violations")
    if violations_data:
        print(f"✅ Violations utilisateur: {json.dumps(violations_data, indent=2)}")


def test_metrics_endpoint():
    """Test de l'endpoint métriques"""
    print("\n🔍 Test 3: Endpoint métriques")

    # Test métriques Prometheus (sans auth)
    try:
        response = requests.get(f"{API_BASE_URL}/metrics", timeout=10)
        if response.status_code == 200:
            lines = response.text.split("\n")[:10]  # Premières lignes
            print("✅ Métriques Prometheus disponibles:")
            for line in lines:
                if line and not line.startswith("#"):
                    print(f"  {line}")
        else:
            print(f"❌ Métriques non disponibles: {response.status_code}")
    except Exception as e:
        print(f"❌ Erreur récupération métriques: {e}")


def test_quota_enforcement():
    """Test de l'enforcement des quotas avec des requêtes répétées"""
    print("\n🔍 Test 4: Enforcement des quotas")

    # Faire plusieurs requêtes pour tester les quotas
    print("🔄 Test de multiples requêtes pour déclencher les quotas...")

    for i in range(5):
        print(f"\nRequête {i+1}/5:")
        health_data = make_request("/health")
        if health_data and "quota_stats" in health_data:
            print(f"  Stats quotas: {health_data['quota_stats']}")
        time.sleep(1)


def test_code_execution():
    """Test d'exécution de code avec quotas"""
    print("\n🔍 Test 5: Exécution de code avec quotas")

    # Test run_py
    python_code = {"code": "print('Hello from Python with quotas!')\nprint(2 + 2)"}

    py_result = make_request("/run_py", method="POST", data=python_code)
    if py_result:
        print(f"✅ Exécution Python: {py_result}")

    # Test run_sh
    shell_code = {"cmd": "echo 'Hello from Shell with quotas!'"}

    sh_result = make_request("/run_sh", method="POST", data=shell_code)
    if sh_result:
        print(f"✅ Exécution Shell: {sh_result}")


def main():
    """Point d'entrée principal"""
    print("🚀 Test de l'API Nox avec Quotas - Milestone 5.3")
    print(f"API: {API_BASE_URL}")
    print(f"Token: {API_TOKEN}")

    # Tests séquentiels
    if not test_api_availability():
        print("❌ API non disponible - arrêt des tests")
        return 1

    test_quota_endpoints()
    test_metrics_endpoint()
    test_quota_enforcement()
    test_code_execution()

    print("\n🎉 Tests terminés!")
    return 0


if __name__ == "__main__":
    exit(main())
