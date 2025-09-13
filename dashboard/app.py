# dashboard/app.py
import os
import tempfile
import time

import streamlit as st
from client import NoxClient

st.set_page_config(page_title="Nox Dashboard", layout="wide")

st.sidebar.title("🔧 Configuration")
base_url = st.sidebar.text_input(
    "Nox API URL", os.getenv("NOX_API_URL", "http://127.0.0.1:8081")
)
token = st.sidebar.text_input(
    "Nox API Token", os.getenv("NOX_API_TOKEN", ""), type="password"
)

if not base_url:
    st.warning("⚠️ Renseigne l'URL de l'API pour activer le tableau de bord")
    st.stop()

# Créer le client (avec ou sans token)
client = NoxClient(base_url, token or "")

st.title("🚀 Nox Dashboard - Étape 2.2")
st.markdown("*Interface d'administration pour l'API Nox avec observabilité*")

# Test de connectivité
try:
    health_data, health_headers = client.health()
    st.sidebar.success("✅ API connectée")
    if "x-request-id" in health_headers:
        st.sidebar.code(f"Request-ID: {health_headers['x-request-id']}")
except Exception as e:
    st.sidebar.error(f"❌ Erreur API: {str(e)}")
    st.error("Impossible de se connecter à l'API Nox. Vérifiez l'URL et le token.")
    st.stop()

tabs = st.tabs(["📁 Fichiers", "🐍 Python", "💻 Shell", "📊 Système", "📈 Métriques"])

# === ONGLET FICHIERS ===
with tabs[0]:
    st.header("📁 Gestion des Fichiers")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📤 Upload de fichier")
        dest = st.text_input(
            "Chemin destination", "tests/upload.txt", key="upload_dest"
        )
        up = st.file_uploader("Choisir un fichier")
        if up and st.button("📤 Uploader", key="upload_btn"):
            with st.spinner("Upload en cours..."):
                try:
                    # Sauvegarder temporairement
                    with tempfile.NamedTemporaryFile(
                        delete=False, suffix=f"_{up.name}"
                    ) as tmp:
                        tmp.write(up.getbuffer())
                        tmp_path = tmp.name

                    data, hdr = client.put(dest, tmp_path)
                    os.unlink(tmp_path)  # Nettoyer

                    st.success(f"✅ {data}")
                    if "x-request-id" in hdr:
                        st.code(f"Request-ID: {hdr['x-request-id']}")
                except Exception as e:
                    st.error(f"❌ Erreur upload: {str(e)}")

    with col2:
        st.subheader("📂 Explorer les fichiers")
        list_path = st.text_input("Chemin à explorer", "", key="list_path")
        recursive = st.checkbox("Récursif", key="list_recursive")

        if st.button("📂 Lister", key="list_btn"):
            try:
                data, hdr = client.list_files(list_path, recursive)
                st.json(data)
                if "x-request-id" in hdr:
                    st.code(f"Request-ID: {hdr['x-request-id']}")
            except Exception as e:
                st.error(f"❌ Erreur listing: {str(e)}")

    # === ACTIONS FICHIERS ===
    st.subheader("🔍 Actions sur fichiers")
    file_action = st.selectbox("Action", ["Lire (cat)", "Supprimer"], key="file_action")
    file_path = st.text_input("Chemin du fichier", key="file_path")

    if st.button("🚀 Exécuter l'action", key="file_action_btn") and file_path:
        try:
            if file_action == "Lire (cat)":
                data, hdr = client.cat_file(file_path)
                st.text_area("Contenu:", data.get("content", ""), height=300)
                if "x-request-id" in hdr:
                    st.code(f"Request-ID: {hdr['x-request-id']}")
            elif file_action == "Supprimer":
                if st.checkbox(
                    f"⚠️ Confirmer suppression de {file_path}", key="delete_confirm"
                ):
                    data, hdr = client.delete_file(file_path)
                    st.success(f"✅ {data}")
                    if "x-request-id" in hdr:
                        st.code(f"Request-ID: {hdr['x-request-id']}")
        except Exception as e:
            st.error(f"❌ Erreur action: {str(e)}")

# === ONGLET PYTHON ===
with tabs[1]:
    st.header("🐍 Exécution Python")
    code = st.text_area(
        "Code Python",
        "print('Hello from Nox Dashboard!')",
        height=160,
        key="python_code",
    )
    filename = st.text_input(
        "Nom du fichier", "dashboard_run.py", key="python_filename"
    )

    if st.button("🚀 Run Python", key="python_run"):
        with st.spinner("Exécution en cours..."):
            try:
                data, hdr = client.run_py(code, filename)

                st.subheader("📤 Résultat:")
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.text_area("STDOUT:", data.get("stdout", ""), height=200)
                with col2:
                    st.text_area("STDERR:", data.get("stderr", ""), height=200)

                if data.get("returncode") == 0:
                    st.success(f"✅ Exécution réussie (code: {data.get('returncode')})")
                else:
                    st.error(f"❌ Échec (code: {data.get('returncode')})")

                if "x-request-id" in hdr:
                    st.code(f"Request-ID: {hdr['x-request-id']}")

            except Exception as e:
                st.error(f"❌ Erreur exécution: {str(e)}")

# === ONGLET SHELL ===
with tabs[2]:
    st.header("💻 Exécution Shell Autorisée")
    st.info(
        "💡 Commandes interdites: rm, reboot, shutdown, mkfs, dd, mount, umount, kill, pkill, sudo"
    )

    cmd = st.text_input("Commande", "echo 'Hello from Nox Shell'", key="shell_cmd")

    if st.button("🚀 Run Shell", key="shell_run"):
        with st.spinner("Exécution en cours..."):
            try:
                data, hdr = client.run_sh(cmd)

                st.subheader("📤 Résultat:")
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.text_area("STDOUT:", data.get("stdout", ""), height=200)
                with col2:
                    st.text_area("STDERR:", data.get("stderr", ""), height=200)

                if data.get("returncode") == 0:
                    st.success(f"✅ Exécution réussie (code: {data.get('returncode')})")
                else:
                    st.error(f"❌ Échec (code: {data.get('returncode')})")

                if "x-request-id" in hdr:
                    st.code(f"Request-ID: {hdr['x-request-id']}")

            except Exception as e:
                st.error(f"❌ Erreur exécution: {str(e)}")

# === ONGLET SYSTÈME ===
with tabs[3]:
    st.header("📊 Santé Système")

    if st.button("🔄 Actualiser", key="health_refresh"):
        try:
            data, hdr = client.health()

            col1, col2 = st.columns([1, 1])
            with col1:
                st.success(f"✅ Status: {data.get('status')}")
                st.info(f"📁 Sandbox: {data.get('sandbox')}")

            with col2:
                st.json(data)

            if "x-request-id" in hdr:
                st.code(f"Request-ID: {hdr['x-request-id']}")

        except Exception as e:
            st.error(f"❌ Erreur santé: {str(e)}")

# === ONGLET MÉTRIQUES ===
with tabs[4]:
    st.header("📈 Métriques Prometheus")

    if st.button("📊 Charger les métriques", key="metrics_load"):
        try:
            metrics_text, hdr = client.get_metrics()

            # Afficher quelques métriques clés
            if "nox_requests_total" in metrics_text:
                st.success("✅ Métriques Nox détectées")

                # Parser quelques métriques importantes
                lines = metrics_text.split("\n")
                nox_lines = [line for line in lines if line.startswith("nox_")]

                st.subheader("🎯 Métriques Nox:")
                for line in nox_lines[:10]:  # Afficher les 10 premières
                    if not line.startswith("#"):
                        st.code(line)

            st.subheader("📄 Métriques complètes:")
            st.text_area("Données Prometheus:", metrics_text, height=400)

            if "x-request-id" in hdr:
                st.code(f"Request-ID: {hdr['x-request-id']}")

        except Exception as e:
            st.error(f"❌ Erreur métriques: {str(e)}")

# === FOOTER ===
st.markdown("---")
st.markdown("🚀 **Nox Dashboard v2.2** - Observabilité et Administration")
st.markdown(f"🔗 API: `{base_url}` | ⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}")
