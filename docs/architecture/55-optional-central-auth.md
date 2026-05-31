# Optional Central Auth

Goal Tracker defaults to local standalone authentication. Local login, registration, profile, password, avatar, invitation-code management, and local app sessions remain active when `AUTH_MODE=local`.

When `AUTH_MODE=oauth`, Goal Tracker delegates login and identity management to the configured central auth site:

- unauthenticated users start OAuth through `/api/v1/auth/oauth/login`
- the OAuth callback creates a Goal Tracker session cookie for this app only
- failed or expired OAuth callbacks redirect back to the app landing screen with
  an `oauth_error` query value so the frontend can show a toast instead of
  leaving users on an API error response
- relative `AUTH_BASE_URL` values are resolved against `PUBLIC_URL` for backend
  token and userinfo calls
- first OAuth login links an existing local user by username when that user is not already linked
- otherwise first OAuth login creates a local user linked by central issuer and subject
- profile, password, avatar, and invitation-code menu actions open `VITE_AUTH_BASE_URL`
- share links, backups, goals, metrics, dashboards, and notifications remain local app features

The local session cookie is still app-owned. Configure `SESSION_COOKIE_NAME` and `SESSION_COOKIE_PATH` so same-host deployments do not collide with other apps.
