# Optional Central Auth

Goal Tracker defaults to local standalone authentication. Local login, registration, profile, password, avatar, invitation-code management, and local app sessions remain active when `AUTH_MODE=local`.

When `AUTH_MODE=oauth`, Goal Tracker delegates login and identity management to the configured central auth site:

- unauthenticated users automatically start OAuth through `/api/v1/auth/oauth/login`
- the OAuth callback creates a Goal Tracker session cookie for this app only
- failed or expired OAuth callbacks redirect back to the app landing screen with
  an `oauth_error` query value so the frontend can show a toast instead of
  leaving users on an API error response or immediately starting another redirect
- `AUTH_BASE_URL` is the public browser/issuer base, while
  `OAUTH_SERVER_BASE_URL` can point backend token and userinfo calls at an
  internal auth API URL
- first OAuth login links an existing local user by username when that user is not already linked
- otherwise first OAuth login creates a local user linked by central issuer and subject
- profile, password, avatar, and invitation-code menu actions open `VITE_AUTH_BASE_URL`
- share links, backups, goals, metrics, dashboards, and notifications remain local app features
- the shared federated banner is loaded from `vendor/federated-banner` in OAuth
  mode and uses root-provided app base paths for cross-app switching

The local session cookie is still app-owned. Configure `SESSION_COOKIE_NAME` and `SESSION_COOKIE_PATH` so same-host deployments do not collide with other apps.

## Agent-Scoped Bearer Tokens

The omnisite AI assistant can call selected Goal Tracker APIs through
short-lived signed bearer tokens. Set `AGENT_INTEGRATION_TOKEN_SECRET` to the
same ignored secret value used by the agent service. Tokens must have:

- issuer `agent-service`;
- audience `goals`;
- subject matching this user's central OAuth subject;
- scope matching the exact allowed agent action, such as `goals.list_goals`;
- a valid HMAC-SHA256 signature and future expiration.

Agent tokens do not create sessions and are not accepted for local auth,
profile, backup, invitation-code, or share-link APIs. They only map to users
that already have a central OAuth-linked local account.
