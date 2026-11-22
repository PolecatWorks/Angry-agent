# Angry-Agent Keycloak Service Claims & Auth Addendum PRD

> [!IMPORTANT]
> **Canonical Auth Pattern**: Global Keycloak OIDC (`shell-ui` + `ecosystem-audiences`), `@polecatworks/mfe-shared` token distribution, zero-fake-auth rules, dynamic JWKS verification, and M2M `client_credentials` mechanics are defined canonically in [**Mfe-shell: Ecosystem Keycloak OIDC, Claims Distribution & Service Auth Pattern PRD**](https://github.com/PolecatWorks/Mfe-shell/blob/main/spec/prds/keycloak-oidc-and-claims-distribution-prd.md).
>
> This document specifies only the **Angry-Agent (`agent-ui-container`, `agent-be-container`)** service-local contract.

---

## 1. Keycloak Client & Roles (`angry-agent-api`)

- **Client ID (`aud`)**: `angry-agent-api`
- **Type**: Bearer-only / Resource Server (declared in `fluxcd-dev/keycloak-crs.yaml`)
- **Client Roles** (`resource_access["angry-agent-api"].roles`):
  - `agent:execute`: Execute agent workflows and run conversational turns.
  - `agent:create`: Author and register new agents.
  - `agent:admin`: Delete sessions, administer system prompts, and view audit logs across all users.

---

## 2. Service-Specific Token Claims (`angry_agent`)

```json
{
  "sub": "4a761e82-2d17-4861-8290-79883bfad211",
  "aud": ["angry-agent-api"],
  "resource_access": {
    "angry-agent-api": {
      "roles": ["agent:create", "agent:execute"]
    }
  },
  "angry_agent": {
    "max_concurrent_agents": 5,
    "allowed_models": ["claude-3-7-sonnet", "gpt-4o", "gemini-2.5-flash"]
  }
}
```

---

## 3. Service-Local Integration Notes

- **Frontend (`agent-ui-container`)**: Consumes `SharedContextService.getAccessToken()` via Angular HTTP interceptor for all `/api/*` requests per the canonical child MFE pattern; no local login or `localStorage` fallback.
- **Backend (`agent-be-container`, Rust/Axum)**: Enforces the canonical JWKS middleware (`aud` contains `angry-agent-api`, `user_id = claims.sub`, zero `X-User-ID` or `default_user` fallback).
- **Outbound M2M (`angry-agent-sa`)**: Uses Kubernetes Secret `angry-agent-sa-credentials` to obtain `client_credentials` tokens targeting `graphrag-api`, `data-engine-api`, and `agent-as-data-api` when invoking downstream MCP servers.
