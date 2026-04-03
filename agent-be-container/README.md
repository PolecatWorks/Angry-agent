# Agent Backend

## 🚀 Core Technology
- **Framework**: [Aiohttp](https://docs.aiohttp.org/) (Asynchronous HTTP Server)
- **AI Engine**: [LangGraph](https://langchain-ai.github.io/langgraph/) (Stateful Multi-Agent Orchestration)
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
