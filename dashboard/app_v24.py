# dashboard/app_v24.py - Dashboard Streamlit avec OAuth2
import os
import tempfile

import pandas as pd
import plotly.express as px
import streamlit as st
from client_v23 import NoxAuthClient
from oauth2_client import oauth2_client

# Configuration de la page
st.set_page_config(
    page_title="Nox API v2.4 - Dashboard with OAuth2", page_icon="🚀", layout="wide"
)

# Configuration de base
API_BASE_URL = os.getenv("NOX_API_URL", "http://127.0.0.1:8000")


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
    if "auth_method" not in st.session_state:
        st.session_state.auth_method = "jwt"  # "jwt" or "oauth2"


def login_form():
    """Affiche le formulaire de connexion avec choix JWT ou OAuth2"""
    st.title("🚀 Nox API v2.4 - Authentication")

    # Tabs for different authentication methods
    tab1, tab2 = st.tabs(["🔑 JWT Login", "🌐 OAuth2 Login"])

    with tab1:
        st.subheader("JWT Authentication")

        with st.form("login_form"):
            email = st.text_input("Email", key="jwt_email")
            password = st.text_input("Password", type="password", key="jwt_password")
            submit_button = st.form_submit_button("Login with JWT")

            if submit_button and email and password:
                try:
                    # Attempt JWT login
                    client = NoxAuthClient(API_BASE_URL)
                    response = client.login(email, password)

                    if response and "access_token" in response:
                        st.session_state.access_token = response["access_token"]
                        st.session_state.logged_in = True
                        st.session_state.user_info = response.get("user", {})
                        st.session_state.auth_method = "jwt"
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")

                except Exception as e:
                    st.error(f"❌ Login failed: {str(e)}")

        # Registration option
        with st.expander("📝 Don't have an account?"):
            st.subheader("Create New Account")

            with st.form("register_form"):
                reg_email = st.text_input("Email", key="reg_email")
                reg_password = st.text_input(
                    "Password", type="password", key="reg_password"
                )
                reg_role = st.selectbox("Role", ["user", "admin"], key="reg_role")
                register_button = st.form_submit_button("Create Account")

                if register_button and reg_email and reg_password:
                    try:
                        client = NoxAuthClient(API_BASE_URL)
                        result = client.register(reg_email, reg_password, reg_role)

                        if result:
                            st.success(
                                "✅ Account created successfully! You can now login."
                            )
                        else:
                            st.error("❌ Registration failed")

                    except Exception as e:
                        st.error(f"❌ Registration failed: {str(e)}")

    with tab2:
        st.subheader("OAuth2 Authentication")

        # Check if OAuth2 authentication was successful
        if oauth2_client.is_authenticated():
            st.session_state.logged_in = True
            st.session_state.auth_method = "oauth2"
            st.session_state.user_info = oauth2_client.get_user_info()
            st.success("✅ OAuth2 authentication successful!")
            st.rerun()
        else:
            # Render OAuth2 login buttons
            oauth2_client.render_oauth2_login()


def show_dashboard():
    """Affiche le dashboard principal"""

    # Header
    st.title("🚀 Nox API v2.4 - Execution Dashboard")

    # User info in sidebar
    with st.sidebar:
        st.subheader("👤 User Info")

        if st.session_state.auth_method == "oauth2":
            user_info = oauth2_client.get_user_info()
            st.write(f"**Email:** {user_info['email']}")
            st.write(f"**Role:** {user_info['role']}")
            st.write("**Auth:** OAuth2")

            if st.button("🚪 Logout", use_container_width=True):
                oauth2_client.logout()
        else:
            # JWT authentication
            user_info = st.session_state.user_info
            st.write(f"**Email:** {user_info.get('email', 'N/A')}")
            st.write(f"**Role:** {user_info.get('role', 'N/A')}")
            st.write("**Auth:** JWT")

            if st.button("🚪 Logout", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.access_token = ""
                st.session_state.user_info = {}
                st.session_state.auth_method = "jwt"
                st.rerun()

    # Main dashboard content
    tab1, tab2, tab3, tab4 = st.tabs(["🐍 Python", "💾 Files", "📊 System", "⚙️ Admin"])

    with tab1:
        show_python_executor()

    with tab2:
        show_file_manager()

    with tab3:
        show_system_metrics()

    with tab4:
        if is_admin():
            show_admin_panel()
        else:
            st.warning("🔒 Admin access required")


def show_python_executor():
    """Interface d'exécution Python"""
    st.subheader("🐍 Python Code Executor")

    # Code input
    code = st.text_area(
        "Python Code",
        height=200,
        placeholder="print('Hello, Nox!')\n\n# Your Python code here...",
        key="python_code",
    )

    col1, col2 = st.columns([1, 3])

    with col1:
        if st.button("▶️ Run Code", use_container_width=True):
            if code.strip():
                run_python_code(code)
            else:
                st.warning("Please enter some Python code")

    with col2:
        if st.button("🧹 Clear", use_container_width=True):
            st.session_state.python_code = ""
            st.rerun()


def run_python_code(code: str):
    """Exécute le code Python via l'API"""
    try:
        # Get authentication headers
        if st.session_state.auth_method == "oauth2":
            _headers = oauth2_client.get_auth_headers()
        else:
            _headers = {
                "Authorization": f"Bearer {st.session_state.access_token}",
                "Content-Type": "application/json",
            }

        # Create client with proper authentication
        client = st.session_state.client
        if st.session_state.auth_method == "oauth2":
            client.token = (
                oauth2_client.get_auth_headers()
                .get("Authorization", "")
                .replace("Bearer ", "")
            )
        else:
            client.token = st.session_state.access_token

        with st.spinner("Executing Python code..."):
            result = client.run_python(code)

        if result:
            st.subheader("📤 Output")

            # Show stdout
            if result.get("stdout"):
                st.code(result["stdout"], language="text")

            # Show stderr if any
            if result.get("stderr"):
                st.error("**Stderr:**")
                st.code(result["stderr"], language="text")

            # Show execution info
            with st.expander("ℹ️ Execution Info"):
                st.json(
                    {
                        "exit_code": result.get("exit_code", "N/A"),
                        "execution_time": f"{result.get('execution_time', 0):.2f}s",
                        "sandbox_path": result.get("sandbox_path", "N/A"),
                    }
                )
        else:
            st.error("❌ Code execution failed")

    except Exception as e:
        st.error(f"❌ Execution error: {str(e)}")


def show_file_manager():
    """Interface de gestion des fichiers"""
    st.subheader("💾 File Manager")

    # File upload
    uploaded_file = st.file_uploader("Upload File", type=None)

    if uploaded_file:
        if st.button("📤 Upload"):
            upload_file(uploaded_file)

    # File list
    st.subheader("📂 Files")
    list_files()


def upload_file(uploaded_file):
    """Upload un fichier"""
    try:
        client = st.session_state.client

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_file_path = tmp_file.name

        result = client.upload_file(uploaded_file.name, tmp_file_path)

        os.unlink(tmp_file_path)  # Clean up

        if result:
            st.success(f"✅ File '{uploaded_file.name}' uploaded successfully")
        else:
            st.error("❌ File upload failed")

    except Exception as e:
        st.error(f"❌ Upload error: {str(e)}")


def list_files():
    """Liste les fichiers"""
    try:
        client = st.session_state.client
        files = client.list_files("/")

        if files and "files" in files:
            for file_info in files["files"]:
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(f"📄 {file_info['name']}")

                with col2:
                    st.write(f"{file_info.get('size', 'N/A')} bytes")

                with col3:
                    if st.button("🗑️", key=f"delete_{file_info['name']}"):
                        delete_file(file_info["name"])
        else:
            st.info("No files found")

    except Exception as e:
        st.error(f"❌ Failed to list files: {str(e)}")


def delete_file(filename: str):
    """Supprime un fichier"""
    try:
        client = st.session_state.client
        result = client.delete_file(filename)

        if result:
            st.success(f"✅ File '{filename}' deleted")
            st.rerun()
        else:
            st.error(f"❌ Failed to delete '{filename}'")

    except Exception as e:
        st.error(f"❌ Delete error: {str(e)}")


def show_system_metrics():
    """Affiche les métriques système"""
    st.subheader("📊 System Metrics")

    try:
        # Get metrics from API
        client = st.session_state.client
        metrics = client.get_metrics()

        if metrics:
            # Display metrics in columns
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("API Requests", metrics.get("requests_total", 0))

            with col2:
                st.metric("Active Users", metrics.get("active_users", 0))

            with col3:
                st.metric(
                    "Avg Response Time", f"{metrics.get('avg_response_time', 0):.2f}ms"
                )

            # Charts if available
            if "request_history" in metrics:
                st.subheader("📈 Request History")
                df = pd.DataFrame(metrics["request_history"])
                fig = px.line(
                    df, x="timestamp", y="requests", title="API Requests Over Time"
                )
                st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("No metrics available")

    except Exception as e:
        st.error(f"❌ Failed to load metrics: {str(e)}")


def show_admin_panel():
    """Panel d'administration"""
    st.subheader("⚙️ Administration Panel")

    # User management
    st.subheader("👥 User Management")

    try:
        client = st.session_state.client
        users = client.get_users() if hasattr(client, "get_users") else []

        if users:
            for user in users:
                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

                with col1:
                    st.write(f"📧 {user.get('email', 'N/A')}")

                with col2:
                    st.write(f"🏷️ {user.get('role', 'N/A')}")

                with col3:
                    status = (
                        "✅ Active" if user.get("is_active", False) else "❌ Inactive"
                    )
                    st.write(status)

                with col4:
                    auth_method = user.get("oauth_provider", "JWT")
                    st.write(f"🔐 {auth_method}")
        else:
            st.info("No users found or user management not available")

    except Exception as e:
        st.error(f"❌ Failed to load users: {str(e)}")


def is_admin() -> bool:
    """Vérifie si l'utilisateur est admin"""
    if st.session_state.auth_method == "oauth2":
        user_info = oauth2_client.get_user_info()
        return user_info.get("role") == "admin"
    else:
        user_info = st.session_state.user_info
        return user_info.get("role") == "admin"


def main():
    """Fonction principale"""
    init_session_state()

    # Check authentication
    if not st.session_state.logged_in and not oauth2_client.is_authenticated():
        login_form()
    else:
        # Update login state if OAuth2 is authenticated
        if oauth2_client.is_authenticated():
            st.session_state.logged_in = True
            st.session_state.auth_method = "oauth2"

        show_dashboard()


if __name__ == "__main__":
    main()
