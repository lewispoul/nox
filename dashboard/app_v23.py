# dashboard/app_v23.py - Dashboard Streamlit avec authentification
import os
import tempfile

import pandas as pd
import streamlit as st
from client_v23 import NoxAuthClient

# Configuration de la page
st.set_page_config(page_title="Nox API v2.3 - Dashboard Admin", page_icon="🚀", layout="wide")

# Configuration de base
API_BASE_URL = "http://127.0.0.1:8081"


def init_session_state():
    """Initialise les variables de session"""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "access_token" not in st.session_state:
        st.session_state.access_token = ""
    if "user_info" not in st.session_state:
        st.session_state.user_info = {}
    if "client" not in st.session_state:
        st.session_state.client = NoxAuthClient(API_BASE_URL)


def login_form():
    """Formulaire de connexion"""
    st.title("🔐 Connexion Nox API v2.3")

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="admin@nox.local")
        password = st.text_input("Mot de passe", type="password", placeholder="admin123")
        col1, col2 = st.columns(2)

        with col1:
            login_btn = st.form_submit_button("Se connecter", type="primary")
        with col2:
            init_admin_btn = st.form_submit_button("Initialiser Admin")

    if init_admin_btn:
        try:
            admin_info, _ = st.session_state.client.init_admin()
            st.success(f"✅ Admin créé: {admin_info.get('email')}")
            st.info("Utilisez les identifiants par défaut pour vous connecter:")
            st.code("Email: admin@nox.local\\nMot de passe: admin123")
        except Exception as e:
            st.error(f"❌ Erreur: {str(e)}")

    if login_btn:
        if not email or not password:
            st.error("Veuillez remplir tous les champs")
            return

        try:
            token_data, headers = st.session_state.client.login(email, password)

            # Sauvegarder les informations de session
            st.session_state.access_token = token_data["access_token"]
            st.session_state.logged_in = True

            # Récupérer les infos utilisateur
            user_info, _ = st.session_state.client.get_me()
            st.session_state.user_info = user_info

            st.success(f"✅ Connexion réussie! Bonjour {user_info.get('email')}")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Erreur de connexion: {str(e)}")


def logout():
    """Déconnexion"""
    st.session_state.logged_in = False
    st.session_state.access_token = ""
    st.session_state.user_info = {}
    st.session_state.client.clear_token()
    st.rerun()


def main_dashboard():
    """Dashboard principal pour les utilisateurs connectés"""

    # Header avec informations utilisateur
    col1, col2, col3 = st.columns([3, 1, 1])

    with col1:
        st.title("🚀 Nox API v2.3 - Dashboard")
        st.caption(
            f"Connecté en tant que: **{st.session_state.user_info.get('email')}** ({st.session_state.user_info.get('role')})"
        )

    with col2:
        if st.button("👤 Mon Profil"):
            show_profile_modal()

    with col3:
        if st.button("🚪 Déconnexion", type="primary"):
            logout()

    st.divider()

    # Onglets du dashboard
    tabs = ["🏠 Accueil", "📁 Fichiers", "🐍 Python", "⚡ Shell", "📊 Métriques"]

    # Ajouter l'onglet Admin si l'utilisateur est admin
    if st.session_state.user_info.get("role") == "admin":
        tabs.append("👑 Administration")

    tab_objects = st.tabs(tabs)

    # Onglet Accueil
    with tab_objects[0]:
        show_home_tab()

    # Onglet Fichiers
    with tab_objects[1]:
        show_files_tab()

    # Onglet Python
    with tab_objects[2]:
        show_python_tab()

    # Onglet Shell
    with tab_objects[3]:
        show_shell_tab()

    # Onglet Métriques
    with tab_objects[4]:
        show_metrics_tab()

    # Onglet Administration (si admin)
    if st.session_state.user_info.get("role") == "admin":
        with tab_objects[5]:
            show_admin_tab()


def show_profile_modal():
    """Affiche le profil utilisateur dans une modal"""
    user = st.session_state.user_info

    with st.expander("👤 Profil Utilisateur", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Email", user.get("email", "N/A"))
            st.metric("Rôle", user.get("role", "N/A"))
            st.metric("Statut", "Actif" if user.get("is_active") else "Inactif")

        with col2:
            st.metric("Quota Fichiers", f"{user.get('quota_files', 0)}")
            st.metric("Quota CPU (sec)", f"{user.get('quota_cpu_seconds', 0)}")
            st.metric("Quota Mémoire (MB)", f"{user.get('quota_memory_mb', 0)}")


def show_home_tab():
    """Onglet d'accueil avec statut du système"""
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏠 Bienvenue")
        st.info(
            """
        **Nox API v2.3** avec authentification RBAC
        
        Fonctionnalités disponibles selon votre rôle:
        - **User**: Exécution de code, gestion de fichiers, consultation des métriques
        - **Admin**: Toutes les fonctionnalités + administration des utilisateurs
        """
        )

        # Test de connectivité
        if st.button("🔍 Tester la connectivité"):
            try:
                health, headers = st.session_state.client.health()
                st.success("✅ API accessible")
                st.json(health)
            except Exception as e:
                st.error(f"❌ Erreur: {str(e)}")

    with col2:
        st.subheader("📊 Informations Système")

        try:
            health, _ = st.session_state.client.health()
            st.metric("Version API", health.get("version", "N/A"))
            st.metric("Sandbox", health.get("sandbox", "N/A"))

            # Informations admin si disponibles
            if st.session_state.user_info.get("role") == "admin":
                try:
                    admin_info, _ = st.session_state.client.admin_info()
                    st.success("🔧 Accès administrateur confirmé")
                    st.json(admin_info)
                except:
                    pass

        except Exception as e:
            st.error(f"Erreur lors de la récupération des informations: {str(e)}")


def show_files_tab():
    """Onglet de gestion des fichiers"""
    st.subheader("📁 Gestion des Fichiers")

    col1, col2 = st.columns(2)

    with col1:
        # Upload de fichier
        st.write("**📤 Upload de Fichier**")
        uploaded_file = st.file_uploader(
            "Choisir un fichier", type=["py", "txt", "json", "yaml", "md"]
        )
        dest_path = st.text_input("Chemin de destination", value="uploaded_file.txt")

        if st.button("Uploader") and uploaded_file:
            try:
                # Sauvegarder temporairement le fichier
                with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_path = tmp_file.name

                result, headers = st.session_state.client.put(dest_path, tmp_path)
                st.success(f"✅ {result.get('message')}")

                # Nettoyer le fichier temporaire
                os.unlink(tmp_path)

            except Exception as e:
                st.error(f"❌ Erreur upload: {str(e)}")

    with col2:
        # Listing des fichiers
        st.write("**📋 Liste des Fichiers**")
        list_path = st.text_input("Chemin à lister", value="")
        recursive = st.checkbox("Récursif")

        if st.button("Lister"):
            try:
                files_data, _ = st.session_state.client.list_files(list_path, recursive)

                if files_data.get("type") == "directory":
                    files = files_data.get("files", [])
                    if files:
                        df = pd.DataFrame(files)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Aucun fichier trouvé")
                else:
                    st.json(files_data)

            except Exception as e:
                st.error(f"❌ Erreur listing: {str(e)}")


def show_python_tab():
    """Onglet d'exécution Python"""
    st.subheader("🐍 Exécution Python")

    # Éditeur de code
    code = st.text_area(
        "Code Python à exécuter:",
        value='print("Hello from Nox API v2.3!")\\nprint("User authenticated:", True)',
        height=200,
    )

    filename = st.text_input("Nom du fichier", value="script.py")

    if st.button("▶️ Exécuter Python", type="primary"):
        try:
            result, headers = st.session_state.client.run_py(code, filename)

            col1, col2 = st.columns(2)
            with col1:
                st.write("**📤 Sortie Standard (stdout):**")
                st.code(result.get("stdout", ""), language="text")

            with col2:
                st.write("**🚨 Erreurs (stderr):**")
                if result.get("stderr"):
                    st.code(result.get("stderr"), language="text")
                else:
                    st.success("Aucune erreur")

            st.info(
                f"Code de retour: {result.get('returncode')} | Utilisateur: {result.get('user')}"
            )

        except Exception as e:
            st.error(f"❌ Erreur exécution: {str(e)}")


def show_shell_tab():
    """Onglet d'exécution Shell"""
    st.subheader("⚡ Exécution Shell")

    cmd = st.text_input("Commande à exécuter:", value="ls -la")

    if st.button("▶️ Exécuter Shell", type="primary"):
        try:
            result, headers = st.session_state.client.run_sh(cmd)

            col1, col2 = st.columns(2)
            with col1:
                st.write("**📤 Sortie Standard (stdout):**")
                st.code(result.get("stdout", ""), language="bash")

            with col2:
                st.write("**🚨 Erreurs (stderr):**")
                if result.get("stderr"):
                    st.code(result.get("stderr"), language="bash")
                else:
                    st.success("Aucune erreur")

            st.info(
                f"Code de retour: {result.get('returncode')} | Utilisateur: {result.get('user')}"
            )

        except Exception as e:
            st.error(f"❌ Erreur exécution: {str(e)}")


def show_metrics_tab():
    """Onglet des métriques Prometheus"""
    st.subheader("📊 Métriques Prometheus")

    if st.button("🔄 Actualiser les Métriques"):
        try:
            metrics_text, headers = st.session_state.client.get_metrics()

            # Affichage des métriques brutes
            with st.expander("📋 Métriques Brutes", expanded=False):
                st.text(metrics_text)

            # Parsing simple des métriques pour affichage
            st.write("**📈 Métriques Principales:**")

            lines = metrics_text.split("\\n")
            metrics_found = []

            for line in lines:
                if line and not line.startswith("#"):
                    parts = line.split(" ")
                    if len(parts) >= 2:
                        metric_name = parts[0]
                        metric_value = parts[1]

                        if any(
                            keyword in metric_name
                            for keyword in ["nox_requests", "nox_latency", "sandbox"]
                        ):
                            metrics_found.append({"Métrique": metric_name, "Valeur": metric_value})

            if metrics_found:
                df = pd.DataFrame(metrics_found)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Aucune métrique Nox trouvée")

            st.success(f"✅ {len(metrics_text)} caractères de métriques récupérés")

        except Exception as e:
            st.error(f"❌ Erreur métriques: {str(e)}")


def show_admin_tab():
    """Onglet d'administration (admin uniquement)"""
    st.subheader("👑 Administration")

    tab1, tab2, tab3 = st.tabs(["👥 Utilisateurs", "📊 Statistiques", "🗑️ Actions Admin"])

    with tab1:
        st.write("**👥 Gestion des Utilisateurs**")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📋 Lister tous les utilisateurs"):
                try:
                    users, _ = st.session_state.client.list_users(limit=100)
                    if users:
                        df = pd.DataFrame(users)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("Aucun utilisateur trouvé")
                except Exception as e:
                    st.error(f"❌ Erreur: {str(e)}")

        with col2:
            st.write("**➕ Inscription d'un nouvel utilisateur**")
            with st.form("register_form"):
                new_email = st.text_input("Email")
                new_password = st.text_input("Mot de passe", type="password")
                new_role = st.selectbox("Rôle", ["user", "admin"])

                if st.form_submit_button("Créer Utilisateur"):
                    try:
                        # Créer un client temporaire sans token pour l'inscription
                        temp_client = NoxAuthClient(API_BASE_URL)
                        result, _ = temp_client.register(new_email, new_password, new_role)
                        st.success(f"✅ Utilisateur créé: {new_email}")
                    except Exception as e:
                        st.error(f"❌ Erreur création: {str(e)}")

    with tab2:
        st.write("**📊 Statistiques des Utilisateurs**")

        if st.button("📈 Actualiser les statistiques"):
            try:
                stats, _ = st.session_state.client.get_user_stats()

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Utilisateurs", stats.get("total_users", 0))
                with col2:
                    st.metric("Utilisateurs Actifs", stats.get("active_users", 0))
                with col3:
                    st.metric("Administrateurs", stats.get("admin_users", 0))
                with col4:
                    st.metric("Utilisateurs Réguliers", stats.get("regular_users", 0))

            except Exception as e:
                st.error(f"❌ Erreur statistiques: {str(e)}")

    with tab3:
        st.write("**🗑️ Actions Administrateur**")

        # Test de suppression de fichier (admin uniquement)
        st.write("**Suppression de Fichier (Admin uniquement)**")
        delete_path = st.text_input("Chemin du fichier à supprimer")

        if st.button("🗑️ Supprimer", type="secondary"):
            if not delete_path:
                st.error("Veuillez spécifier un chemin")
            else:
                try:
                    result, _ = st.session_state.client.delete_file(delete_path)
                    st.success(f"✅ {result.get('message')}")
                except Exception as e:
                    st.error(f"❌ Erreur suppression: {str(e)}")


def main():
    """Point d'entrée principal de l'application"""
    init_session_state()

    # Vérifier l'état de connexion
    if not st.session_state.logged_in:
        login_form()
    else:
        main_dashboard()


if __name__ == "__main__":
    main()
