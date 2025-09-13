"""
OAuth2 Client for Nox Dashboard
Handles OAuth2 authentication integration with Streamlit
"""

import os
from typing import Any, Dict

import requests
import streamlit as st


class OAuth2Client:
    """OAuth2 client for dashboard authentication"""

    def __init__(self):
        self.api_base_url = os.getenv("NOX_API_URL", "http://localhost:8000")
        self.dashboard_url = os.getenv("DASHBOARD_URL", "http://localhost:8501")

    def get_available_providers(self) -> Dict[str, Any]:
        """Get available OAuth2 providers from API"""
        try:
            response = requests.get(f"{self.api_base_url}/auth/oauth2/providers")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.error(f"Failed to get OAuth2 providers: {e}")
            return {"providers": [], "enabled": False}

    def get_login_url(self, provider: str) -> str:
        """Get OAuth2 login URL for provider"""
        return f"{self.api_base_url}/auth/oauth2/{provider}/login"

    def render_oauth2_login(self):
        """Render OAuth2 login buttons in Streamlit"""

        # Check if we have OAuth2 tokens from URL parameters
        query_params = st.query_params

        if "auth" in query_params:
            if query_params["auth"] == "success":
                self._handle_oauth2_success(query_params)
                return True
            elif query_params["auth"] == "error":
                self._handle_oauth2_error(query_params)
                return False

        # Get available providers
        providers_data = self.get_available_providers()

        if not providers_data["enabled"]:
            st.info("🔐 OAuth2 authentication is not configured")
            return False

        st.subheader("🚀 Sign in with OAuth2")
        st.markdown("Choose your preferred authentication provider:")

        # Create columns for provider buttons
        providers = providers_data["providers"]
        if not providers:
            st.warning("No OAuth2 providers are configured")
            return False

        cols = st.columns(len(providers))

        for i, provider in enumerate(providers):
            with cols[i]:
                if st.button(
                    f"{provider['icon']} Sign in with {provider['display_name']}",
                    key=f"oauth2_{provider['name']}",
                    use_container_width=True,
                ):
                    login_url = self.get_login_url(provider["name"])
                    st.markdown(
                        f'<meta http-equiv="refresh" content="0;url={login_url}">',
                        unsafe_allow_html=True,
                    )
                    st.info(f"Redirecting to {provider['display_name']}...")
                    st.stop()

        return False

    def _handle_oauth2_success(self, query_params: Dict[str, Any]):
        """Handle successful OAuth2 authentication"""

        # Extract tokens from query parameters
        access_token = query_params.get("access_token")
        refresh_token = query_params.get("refresh_token")
        user_email = query_params.get("user_email")
        user_role = query_params.get("user_role")

        if access_token and refresh_token:
            # Store tokens in session state
            st.session_state["access_token"] = access_token
            st.session_state["refresh_token"] = refresh_token
            st.session_state["user_email"] = user_email
            st.session_state["user_role"] = user_role
            st.session_state["authenticated"] = True
            st.session_state["auth_method"] = "oauth2"

            # Clear URL parameters
            st.query_params.clear()

            st.success(f"✅ Successfully signed in as {user_email}")
            st.rerun()
        else:
            st.error("❌ OAuth2 authentication failed: No tokens received")

    def _handle_oauth2_error(self, query_params: Dict[str, Any]):
        """Handle OAuth2 authentication error"""

        error = query_params.get("error", "Unknown error")
        st.error(f"❌ OAuth2 authentication failed: {error}")

        # Clear URL parameters
        st.query_params.clear()

    def is_authenticated(self) -> bool:
        """Check if user is authenticated via OAuth2"""

        return (
            st.session_state.get("authenticated", False)
            and st.session_state.get("access_token") is not None
            and st.session_state.get("auth_method") == "oauth2"
        )

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""

        access_token = st.session_state.get("access_token")
        if not access_token:
            return {}

        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    def get_user_info(self) -> Dict[str, Any]:
        """Get current user information"""

        return {
            "email": st.session_state.get("user_email", ""),
            "role": st.session_state.get("user_role", "user"),
            "auth_method": "oauth2",
        }

    def logout(self):
        """Logout user and clear session"""

        # Clear OAuth2 session data
        keys_to_clear = [
            "access_token",
            "refresh_token",
            "user_email",
            "user_role",
            "authenticated",
            "auth_method",
        ]

        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]

        st.success("✅ Successfully logged out")
        st.rerun()

    def refresh_token(self) -> bool:
        """Refresh access token using refresh token"""

        refresh_token = st.session_state.get("refresh_token")
        if not refresh_token:
            return False

        try:
            # This would require implementing token refresh endpoint
            # For now, just return False to force re-authentication
            return False

        except Exception as e:
            st.error(f"Failed to refresh token: {e}")
            return False

    def render_user_info(self):
        """Render authenticated user information"""

        if not self.is_authenticated():
            return

        user_info = self.get_user_info()

        with st.sidebar:
            st.markdown("---")
            st.subheader("👤 User Info")
            st.write(f"**Email:** {user_info['email']}")
            st.write(f"**Role:** {user_info['role'].title()}")
            st.write("**Auth:** OAuth2")

            if st.button("🚪 Logout", use_container_width=True):
                self.logout()


# Global OAuth2 client instance
oauth2_client = OAuth2Client()
