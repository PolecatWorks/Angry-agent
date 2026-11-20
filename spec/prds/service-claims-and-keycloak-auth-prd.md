# Backend-Specific Keycloak Claims, Service Accounts & Zero-Fake-Auth Architecture PRD

## Overview
This PRD defines the production authentication, authorization, and claims architecture for **Angry-Agent (`agent-ui-container`, `agent-be-container`, `agentrs-be-container`)** integrated into the PolecatWorks ecosystem.

It codifies:
1. **Zero Fake/Dev-Only Auth**: Total elimination of client-controlled identity headers (such as `X-User-ID`, fake mock bearer tokens, or fallback mock users).
2. **MFE Shell Driven OIDC Session & Silent Refresh**: Token lifecycle management hosted by `Mfe-shell` via PKCE OIDC and propagated to `agent-ui-container` through `@polecatworks/mfe-shared` (`SharedContextService`).
3. **Application-Specific Claims & Scopes**: Isolation of roles and domain claims per backend service via Keycloak client-level scopes and `resource_access.<client-id>` mappings.
4. **Machine-to-Machine (M2M) Service Accounts**: Explicit `client_credentials` authentication for backend-to-backend communication (e.g. `Angry-agent` calling `Graphrag` or `data-engine`).
5. **Dynamic JWKS Verification**: OIDC token validation via cluster Keycloak JWKS endpoints (`/.well-known/openid-configuration` / `jwks_uri`) replacing static PEM public keys.

---

## Authentication & Authorization Topology

```mermaid
flowchart TD
    subgraph Browser ["Browser Session (PolecatWorks AI Portal)"]
        Shell["Mfe-shell-container\n(angular-oauth2-oidc + PKCE)"]
        SharedCtx["@polecatworks/mfe-shared\n(SharedContextService)"]
        AgentUI["Angry-agent UI (agent-ui-container)\n(Angular HTTP Interceptor)"]
    end

    subgraph Identity ["Identity Provider (Keycloak / EPAM Keycloak Operator)"]
        KC_JWKS["JWKS Endpoint\n(/protocol/openid-connect/certs)"]
        Client_Shell["KeycloakClient: mfe-shell\n(Public, PKCE)"]
        Client_API["KeycloakClient: angry-agent-api\n(Bearer-Only / Resource Server)"]
        Client_SA["KeycloakClient: angry-agent-sa\n(Confidential / Service Account)"]
    end

    subgraph Backends ["Angry-Agent Backends"]
        AgentBE["agent-be-container (FastAPI)"]
        AgentRS["agentrs-be-container (Axum/Rust)"]
    end

    subgraph Downstream ["Ecosystem Services"]
        GraphRAG["Graphrag (:8080/api/v1/mcp)"]
        DataEngine["data-engine (:8080/api/v1/mcp)"]
    end

    Shell -->|1. Auth Code + PKCE| Client_Shell
    Client_Shell -->|2. Mint User Access Token| Shell
    Shell -->|3. setContext(accessToken, claims)| SharedCtx
    SharedCtx -.->|4. getAccessToken()| AgentUI
    AgentUI -->|5. HTTP Bearer Token| AgentBE
    AgentUI -->|5. HTTP Bearer Token| AgentRS
    AgentBE -->|6. Verify Signature & Claims| KC_JWKS
    AgentRS -->|6. Verify Signature & Claims| KC_JWKS

    AgentBE -->|7. M2M client_credentials| Client_SA
    Client_SA -->|8. SA Token (aud: downstream)| AgentBE
    AgentBE -->|9. MCP Request + SA Token| GraphRAG & DataEngine
```

---

## Specification Details

### 1. Unique Keycloak Client & Claims for Angry-Agent

#### A. Keycloak Client Definition (`KeycloakClient: angry-agent-api`)
- **Client ID**: `angry-agent-api`
- **Type**: Bearer-only / Resource Server
- **Audience**: `aud: ["angry-agent-api"]`
- **Client Roles**:
  - `agent:execute`: Execute agent workflows and run tasks.
  - `agent:create`: Author and register new agents.
  - `agent:admin`: Delete sessions, administer system prompts, view audit logs across all users.

#### B. Token Claims Structure
Tokens received by `agent-be` and `agentrs-be` must conform to the following schema:
```json
{
  "iss": "http://keycloak-keycloakx-http.auth.svc.cluster.local/auth/realms/sw-dev",
  "sub": "4a761e82-2d17-4861-8290-79883bfad211",
  "aud": ["angry-agent-api"],
  "preferred_username": "bgreene",
  "email": "ben@polecatworks.com",
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

#### C. Identity Claims Rules
- **Canonical User ID**: The backend **must** extract `user_id = token["sub"]`.
- **Zero Fallback**: If the `Authorization` header is missing or the token signature / audience validation fails, the service returns `401 Unauthorized`. It never falls back to `default-user` or `X-User-ID`.

---

### 2. Frontend Integration (`agent-ui-container`)

- **HTTP Interceptor**: An Angular interceptor reads `SharedContextService.getAccessToken()` from `@polecatworks/mfe-shared`.
- **Bearer Injection**: For every request matching `/api/*`, injects `Authorization: Bearer ${token}`.
- **Unauthenticated Handling**: If `token` is missing or expired and refresh fails, emit an authentication event back to `Mfe-shell` to trigger login redirect. Do not construct fake JWTs.

---

### 3. Backend Verification (`agent-be-container` & `agentrs-be-container`)

- **JWKS Caching**: Backends fetch JWKS from Keycloak OIDC certs endpoint and cache public keys with TTL and key-id (`kid`) rotation handling.
- **Audience & Issuer Check**: Must verify `iss` matches realm issuer and `aud` contains `angry-agent-api`.
- **Service Account Identity**: When `sub` belongs to a service account (e.g. `service-account-angry-agent-sa`), verify `client_id` / `azp` matches authorized ecosystem callers.

---

### 4. Machine-to-Machine Communication (`angry-agent-sa`)

- When `agent-be-container` connects to downstream MCP services (`Graphrag`, `data-engine`):
  - Uses Keycloak `client_credentials` grant with client ID `angry-agent-sa` and secret mounted via Kubernetes Secret `angry-agent-sa-credentials`.
  - Obtains tokens with audience `aud: ["graphrag-api"]` or `aud: ["data-engine-api"]`.
  - Attaches Bearer token to JSON-RPC / SSE MCP requests.
