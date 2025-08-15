# OAuth2 Integration Guide - Nox API v2.4

This guide explains how to set up and use OAuth2 authentication with Google and GitHub providers in Nox API v2.4.

## 🔧 OAuth2 Configuration

### 1. Google OAuth2 Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google+ API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Set application type to "Web application"
6. Add authorized redirect URIs:
   - `http://localhost:8000/auth/oauth2/google/callback`
   - `https://your-domain.com/auth/oauth2/google/callback` (for production)
7. Copy the Client ID and Client Secret

### 2. GitHub OAuth2 Setup

1. Go to [GitHub Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in the application details:
   - **Application name**: Nox API
   - **Homepage URL**: `http://localhost:8501` (or your dashboard URL)
   - **Authorization callback URL**: `http://localhost:8000/auth/oauth2/github/callback`
4. Copy the Client ID and generate a Client Secret

### 3. Environment Configuration

Update your `.env` file with OAuth2 credentials:

```bash
# OAuth2 Configuration
OAUTH_GOOGLE_CLIENT_ID=your_google_client_id_here
OAUTH_GOOGLE_CLIENT_SECRET=your_google_client_secret_here
OAUTH_GITHUB_CLIENT_ID=your_github_client_id_here
OAUTH_GITHUB_CLIENT_SECRET=your_github_client_secret_here

# OAuth2 URLs (adjust for your domain)
OAUTH_REDIRECT_BASE_URL=http://localhost:8000
OAUTH_FRONTEND_SUCCESS_URL=http://localhost:8501?auth=success
OAUTH_FRONTEND_ERROR_URL=http://localhost:8501?auth=error
```

## 🚀 Using OAuth2 Authentication

### API Endpoints

#### Get Available Providers
```bash
GET /auth/oauth2/providers
```

Response:
```json
{
  "providers": [
    {
      "name": "google",
      "display_name": "Google", 
      "icon": "🌐",
      "login_url": "/auth/oauth2/google/login"
    },
    {
      "name": "github",
      "display_name": "GitHub",
      "icon": "🐙", 
      "login_url": "/auth/oauth2/github/login"
    }
  ],
  "enabled": true
}
```

#### Initiate OAuth2 Login
```bash
GET /auth/oauth2/{provider}/login
```
- Redirects to OAuth2 provider (Google/GitHub)
- User authorizes the application
- Provider redirects back to callback URL

#### OAuth2 Callback (Automatic)
```bash
GET /auth/oauth2/{provider}/callback
```
- Exchanges authorization code for access token
- Creates or updates user in database
- Generates JWT tokens for Nox API
- Redirects to dashboard with authentication tokens

#### Authentication Status
```bash
GET /auth/oauth2/status
```

Response:
```json
{
  "enabled": true,
  "providers": {
    "google": true,
    "github": true
  },
  "available_providers": 2,
  "redirect_base_url": "http://localhost:8000",
  "configuration_valid": true
}
```

### Dashboard Integration

The Streamlit dashboard (`app_v24.py`) includes OAuth2 integration:

1. **Login Page**: Shows both JWT and OAuth2 authentication tabs
2. **OAuth2 Tab**: Displays available provider buttons
3. **Auto-Login**: Handles OAuth2 callback parameters automatically
4. **Session Management**: Stores OAuth2 tokens in Streamlit session state

#### Usage Flow:
1. User clicks "Sign in with Google/GitHub" 
2. Redirected to OAuth2 provider
3. After authorization, redirected back to dashboard
4. Dashboard extracts tokens from URL parameters
5. User is authenticated and can access protected features

## 🔒 Security Features

### Token Management
- **JWT Access Tokens**: 15-minute expiration
- **JWT Refresh Tokens**: 7-day expiration  
- **Secure Cookies**: HttpOnly, Secure, SameSite=Lax
- **Token Rotation**: Refresh tokens invalidated after use

### User Data Protection
- **Minimal Scope**: Only request necessary permissions
- **Email Privacy**: Handles private GitHub emails
- **Profile Sync**: Updates user information on each login
- **Account Linking**: Links OAuth2 accounts to existing email accounts

### Database Security
- **OAuth Provider Tracking**: Stores provider and external ID
- **Password Placeholder**: OAuth2 users get placeholder passwords
- **Role Assignment**: Default 'user' role, admin promotion manual
- **Audit Trail**: Execution logs include authentication method

## 🎯 User Experience

### First-Time OAuth2 Users
1. Click OAuth2 login button
2. Authorize application with provider
3. Account created automatically in Nox database
4. Assigned 'user' role by default
5. Redirected to dashboard with full access

### Returning OAuth2 Users  
1. Click OAuth2 login button
2. Authorize application (may be automatic)
3. Profile information updated
4. Existing quotas and data preserved
5. Seamless dashboard access

### Account Linking
If a user has an existing Nox account with the same email:
- OAuth2 provider is linked to existing account
- Previous data, role, and quotas retained
- Can use either JWT or OAuth2 authentication

## 🐛 Troubleshooting

### Common Issues

#### "OAuth2 authentication is not configured"
- Check that `OAUTH_GOOGLE_CLIENT_ID` and/or `OAUTH_GITHUB_CLIENT_ID` are set
- Verify OAuth2 credentials are correct
- Restart the API server after configuration changes

#### "GitHub email not available"
- User's GitHub email is private
- Ask user to make email public in GitHub settings
- Or implement GitHub email API access in `oauth2_service.py`

#### "OAuth2 client not found"
- OAuth2 provider credentials are missing or invalid
- Check `.env` file configuration
- Verify provider name matches (google/github)

#### Redirect URI Mismatch
- OAuth2 provider callback URL doesn't match configuration
- Update provider settings to include correct callback URL
- Ensure `OAUTH_REDIRECT_BASE_URL` matches your API URL

### Debug Mode

Enable debug logging:
```bash
export OAUTH_DEBUG=1
```

Check OAuth2 status endpoint:
```bash
curl http://localhost:8000/auth/oauth2/status
```

## 🔮 Future Enhancements

### Planned Features
- **Microsoft OAuth2**: Azure AD integration
- **Token Refresh**: Automatic token renewal
- **Single Sign-Out**: Centralized logout across providers  
- **Profile Management**: User profile editing interface
- **Admin OAuth2**: Admin role assignment via provider claims

### API Extensions
- **Token Introspection**: Validate tokens without database lookup
- **Provider Profiles**: Extended user information from providers
- **Custom Scopes**: Configurable permission requests
- **Multi-Provider**: Users can link multiple OAuth2 accounts

---

**OAuth2 Integration v2.4**  
Part of Nox API Step 2.4+ Task Pack  
Last updated: August 2025
