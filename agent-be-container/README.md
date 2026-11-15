# Agent Backend

## 🚀 Core Technology
- **Framework**: [Aiohttp](https://docs.aiohttp.org/) (Asynchronous HTTP Server)
- **AI Engine**: [LangGraph](https://langchain-ai.github.io/langgraph/) (Stateful Multi-Agent Orchestration)
- **State Management**: Unified persistence using LangGraph PostgreSQL checkpointers for both chat history and workspace visualizations.
- **Response Pipeline**: Includes a deterministic `post_process_node` for reliable MFE/Mermaid metadata extraction and a tool-call repair mechanism in the generation path.
- **Database**: [PostgreSQL](https://www.postgresql.org/) (State Persistence and Checkpointing)

For detailed functional and architectural specifications, see the [PRD](./spec/prd.md).

## 🐳 Docker Build

The Docker build runs tests (including `deepeval` evaluations) during the build process. These tests require a `GOOGLE_API_KEY`.

To build the image locally, ensure you have the `GOOGLE_API_KEY` exported in your environment and use the root Makefile:

```bash
export GOOGLE_API_KEY=your_key_here
make agent-be-docker
```

Or pass it directly:
```bash
GOOGLE_API_KEY=your_key make agent-be-docker
```

## 🛠 CI/CD

The GitHub Actions workflow (or other CI system) must provide the `GOOGLE_API_KEY` secret during the build.

Example GitHub Action step:
```yaml
- name: Build and test
  uses: docker/build-push-action@v5
  with:
    context: agent-be-container
    secrets: |
      "GOOGLE_API_KEY=${{ secrets.GOOGLE_API_KEY }}"
```

## Authentication configuration

Incoming API access tokens are validated using the `auth` section of the Pydantic `ServiceConfig`. Keep these values in the service YAML configuration and/or the configured Pydantic secrets directory; the request middleware does not read process environment variables directly.

Example YAML:

```yaml
auth:
  jwt_public_key: |
    -----BEGIN PUBLIC KEY-----
    REPLACE_WITH_KEYCLOAK_REALM_PUBLIC_KEY
    -----END PUBLIC KEY-----
  jwt_issuer: https://keycloak.example.com/realms/your-realm
  jwt_audience: angry-agent-api
```

The public key is a Pydantic `SecretStr`. The issuer and audience must match the claims in the access token. The backend requires RS256 tokens containing `exp`, `iss`, `aud`, and `sub`; missing or invalid credentials are rejected. Configure the matching values in the YAML or secrets directory before deploying.
