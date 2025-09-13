# dashboard/client_v23.py - Client avec support authentification
from typing import Any, Dict, Tuple

import requests


class NoxAuthClient:
    """Client Nox avec support complet de l'authentification JWT"""

    def __init__(self, base_url: str, token: str = "", timeout: float = 15.0):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout
        self.current_token = token

        # Configurer le token si fourni
        if token:
            self.set_token(token)

    def set_token(self, token: str):
        """Configure le token JWT pour les requêtes"""
        self.current_token = token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def clear_token(self):
        """Supprime le token JWT"""
        self.current_token = ""
        if "Authorization" in self.session.headers:
            del self.session.headers["Authorization"]

    # === AUTHENTIFICATION ===

    def register(
        self, email: str, password: str, role: str = "user"
    ) -> Tuple[Dict[str, Any], Dict]:
        """Inscription d'un nouvel utilisateur"""
        data = {"email": email, "password": password, "role": role}
        r = self.session.post(
            f"{self.base_url}/auth/register", json=data, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json(), r.headers

    def login(self, email: str, password: str) -> Tuple[Dict[str, Any], Dict]:
        """Connexion utilisateur"""
        data = {"email": email, "password": password}
        r = self.session.post(
            f"{self.base_url}/auth/login", json=data, timeout=self.timeout
        )
        r.raise_for_status()

        response_data = r.json()
        # Configurer automatiquement le token après connexion
        if "access_token" in response_data:
            self.set_token(response_data["access_token"])

        return response_data, r.headers

    def get_me(self) -> Tuple[Dict[str, Any], Dict]:
        """Informations sur l'utilisateur connecté"""
        r = self.session.get(f"{self.base_url}/auth/me", timeout=self.timeout)
        r.raise_for_status()
        return r.json(), r.headers

    def init_admin(self) -> Tuple[Dict[str, Any], Dict]:
        """Initialise l'utilisateur admin par défaut"""
        r = self.session.post(f"{self.base_url}/auth/init-admin", timeout=self.timeout)
        r.raise_for_status()
        return r.json(), r.headers

    # === ENDPOINTS UTILISATEUR ===

    def list_users(
        self, limit: int = 50, offset: int = 0
    ) -> Tuple[Dict[str, Any], Dict]:
        """Liste tous les utilisateurs (admin uniquement)"""
        params = {"limit": limit, "offset": offset}
        r = self.session.get(
            f"{self.base_url}/auth/users", params=params, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json(), r.headers

    def get_user_stats(self) -> Tuple[Dict[str, Any], Dict]:
        """Statistiques des utilisateurs (admin uniquement)"""
        r = self.session.get(f"{self.base_url}/auth/stats", timeout=self.timeout)
        r.raise_for_status()
        return r.json(), r.headers

    # === ENDPOINTS EXISTANTS (avec authentification) ===

    def health(self) -> Tuple[Dict[str, Any], Dict]:
        """Santé du système"""
        r = self.session.get(f"{self.base_url}/health", timeout=self.timeout)
        r.raise_for_status()
        return r.json(), r.headers

    def put(self, dest_path: str, local_path: str) -> Tuple[Dict[str, Any], Dict]:
        """Upload de fichier"""
        with open(local_path, "rb") as f:
            files = {"f": f}
            r = self.session.post(
                f"{self.base_url}/put",
                params={"path": dest_path},
                files=files,
                timeout=self.timeout,
            )
        r.raise_for_status()
        return r.json(), r.headers

    def run_py(
        self, code: str, filename: str = "run.py"
    ) -> Tuple[Dict[str, Any], Dict]:
        """Exécution de code Python"""
        data = {"code": code, "filename": filename}
        r = self.session.post(
            f"{self.base_url}/run_py", json=data, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json(), r.headers

    def run_sh(self, cmd: str) -> Tuple[Dict[str, Any], Dict]:
        """Exécution de commandes shell"""
        data = {"cmd": cmd}
        r = self.session.post(
            f"{self.base_url}/run_sh", json=data, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json(), r.headers

    def list_files(
        self, path: str = "", recursive: bool = False
    ) -> Tuple[Dict[str, Any], Dict]:
        """Listing des fichiers"""
        params = {"path": path, "recursive": recursive}
        r = self.session.get(
            f"{self.base_url}/list", params=params, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json(), r.headers

    def cat_file(self, path: str) -> Tuple[Dict[str, Any], Dict]:
        """Lecture d'un fichier"""
        params = {"path": path}
        r = self.session.get(
            f"{self.base_url}/cat", params=params, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json(), r.headers

    def delete_file(self, path: str) -> Tuple[Dict[str, Any], Dict]:
        """Suppression de fichier (admin uniquement)"""
        params = {"path": path}
        r = self.session.delete(
            f"{self.base_url}/delete", params=params, timeout=self.timeout
        )
        r.raise_for_status()
        return r.json(), r.headers

    def get_metrics(self) -> Tuple[str, Dict]:
        """Récupération des métriques Prometheus"""
        r = self.session.get(f"{self.base_url}/metrics", timeout=self.timeout)
        r.raise_for_status()
        return r.text, r.headers

    def admin_info(self) -> Tuple[Dict[str, Any], Dict]:
        """Informations admin"""
        r = self.session.get(f"{self.base_url}/admin/info", timeout=self.timeout)
        r.raise_for_status()
        return r.json(), r.headers


# Classe de compatibilité avec l'ancien client
class NoxClient(NoxAuthClient):
    """Alias pour la compatibilité avec l'ancien code"""

    pass
