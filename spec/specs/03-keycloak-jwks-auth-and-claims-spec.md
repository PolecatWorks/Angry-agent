# Spec 03: Keycloak JWKS Authentication, `angry-agent-api` Claims Gatekeeper & `angry-agent-sa` Service Auth

- **Status**: `draft`
- **Derived From**: [service-claims-and-keycloak-auth-prd.md](../prds/service-claims-and-keycloak-auth-prd.md)
- **Dependencies**: [01-ui-bidirectional-mfe-canvas-spec.md](./01-ui-bidirectional-mfe-canvas-spec.md), [02-be-shared-canvas-tools-and-endpoints-spec.md](./02-be-shared-canvas-tools-and-endpoints-spec.md)

---

## 1. Objective

Implement OIDC Bearer token verification via Keycloak JWKS and domain-specific claims enforcement across `Angry-agent`'s frontend (`agent-ui-container`) and backend (`agent-be-container` / `agentrs-be-container`), with **zero dev/fake auth bypasses** (complete elimination of `X-User-ID` or fallback mock headers):
1. **Frontend Integration (`agent-ui-container`)**: Consume `SharedContextService.getAccessToken()` from `@polecatworks/mfe-shared` and attach Bearer token to all `/api/*` HTTP and SSE requests.
2. **Backend JWKS Gatekeeper (`agent-be-container`)**: Validate OIDC tokens against Keycloak JWKS, verify audience `aud: ["angry-agent-api"]`, and extract canonical `user_id = sub`.
3. **Role Enforcement**: Enforce `agent:execute`, `agent:create`, and `agent:admin` from `resource_access["angry-agent-api"].roles`.
4. **Ecosystem Realm Groups Integration**: Compatible with roles granted via `DataAgentAdmins` and `DataAgentUsers` realm groups.
5. **Machine-to-Machine Outbound Auth (`angry-agent-sa`)**: Mint client credentials tokens to authenticate outbound calls to `Graphrag` (`aud: graphrag-api`) and `data-engine` (`aud: data-engine-api`).

---

## 2. Request Flow & Middleware Architecture

```mermaid
flowchart TD
    subgraph Browser ["MFE Shell Browser Session"]
        SharedCtx["SharedContextService (@polecatworks/mfe-shared)"]
        UI_Interceptor["Angular AuthInterceptor (agent-ui-container)"]
    end

    subgraph Backend ["agent-be-container / agentrs-be-container"]
        AuthMiddleware["FastAPI / Axum Auth Middleware"]
        JWKS["Keycloak JWKS Verifier"]
        ClaimsGate["AngryAgentClaims Gatekeeper"]
        AgentEngine["LangGraph / Rig Agent Loop"]
    end

    subgraph Downstream ["Ecosystem Downstream Services"]
        SA_Vault["angry-agent-sa Credentials"]
        Graphrag["GraphRAG MCP (/api/graphrag/v1/mcp)"]
        DataEngine["Data-Engine MCP (/api/data-engine/v1/mcp)"]
    end

    SharedCtx -->|getAccessToken()| UI_Interceptor
    UI_Interceptor -->|Bearer <JWT>| AuthMiddleware
    AuthMiddleware -->|Verify Signature & aud: angry-agent-api| JWKS
    AuthMiddleware -->|Authenticated UserContext| ClaimsGate
    ClaimsGate -->|"role: agent:execute"| AgentEngine
    AgentEngine -->|Mint SA Token| SA_Vault
    SA_Vault -->|Bearer SA Token| Graphrag & DataEngine
```

---

## 3. Configuration & Error Handling Contract

### 3.1 Backend Auth Configuration
Defined in backend configuration (env prefix `ANGRY_AGENT__AUTH__*`, zero hardcoded defaults, fail-fast startup validation):
- `issuer_url: String` — Keycloak realm URL (e.g. `http://keycloak-keycloakx-http.auth.svc.cluster.local/auth/realms/sw-dev`)
- `jwks_url: String` — Keycloak JWKS certs URL
- `expected_audience: String` (default: `"angry-agent-api"`)
- `jwks_cache_ttl_seconds: u64` (default: 300)
- `sa_client_id: String` (default: `"angry-agent-sa"`)
- `sa_client_secret_file: String` — Path to mounted secret key

### 3.2 Error Responses
- Missing `Authorization` header $\rightarrow$ `401 Unauthorized` (`{"error": "MissingBearerToken"}`)
- Invalid / Expired / Wrong audience token $\rightarrow$ `401 Unauthorized` (`{"error": "InvalidToken"}`)
- Missing required role $\rightarrow$ `403 Forbidden` (`{"error": "InsufficientRole", "required": "agent:execute"}`)

---

## 4. Claims Structure & Role Mapping

### 4.1 Token Claims Representation
```json
{
  "iss": "http://keycloak-keycloakx-http.auth.svc.cluster.local/auth/realms/sw-dev",
  "sub": "4a761e82-2d17-4861-8290-79883bfad211",
  "aud": ["angry-agent-api"],
  "preferred_username": "developer",
  "email": "dev@polecatworks.com",
  "resource_access": {
    "angry-agent-api": {
      "roles": ["agent:execute", "agent:create"]
    }
  },
  "angry_agent": {
    "max_concurrent_agents": 5,
    "allowed_models": ["claude-3-7-sonnet", "gpt-4o"]
  }
}
```

### 4.2 Endpoint Role Gates
- `agent:execute`:
  - `POST /api/chat`, `POST /api/threads`, `GET /api/threads/{id}`
  - `PATCH /api/threads/{id}/visualizations/{viz_id}`
- `agent:create`:
  - `POST /api/agents`, `PUT /api/agents/{id}`
- `agent:admin`:
  - `DELETE /api/threads/{id}`
  - Global prompt overrides and user session audits.

---

## 5. Test Strategy

### 5.1 Frontend Unit Tests (`agent-ui-container`)
- Verify Angular `AuthInterceptor` injects Bearer token from `SharedContextService`.
- Verify 401 handling triggers authentication renewal event rather than falling back to mock headers.

### 5.2 Backend Unit Tests (`agent-be-container`)
- Test JWKS cache initialization, token validation, and error propagation.
- Test endpoint role rejection when caller lacks `agent:execute` or `agent:admin`.

### 5.3 Integration Tests (`integration-tests/`)
- Verify elimination of `X-User-ID`: requests with only `X-User-ID` return `401 Unauthorized`.
- Verify requests with `DataAgentAdmins` tokens succeed across all chat, agent creation, and deletion operations.
- Verify outbound MCP calls to `Graphrag` and `data-engine` carry valid `angry-agent-sa` tokens.
