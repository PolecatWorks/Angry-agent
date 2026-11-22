# Build stage
FROM rust:1.98-slim as builder

WORKDIR /usr/src/agentrs-be

RUN apt-get update && apt-get install -y pkg-config libssl-dev && rm -rf /var/lib/apt/lists/*

COPY Cargo.toml Cargo.lock ./
COPY src ./src
COPY migrations ./migrations
COPY tests ./tests

RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Add OCI labels
LABEL org.opencontainers.image.title="Agent Backend (Rust)"
LABEL org.opencontainers.image.description="AI Agent Backend in Rust with Tokio, Axum, sqlx, and rig-core"
LABEL org.opencontainers.image.authors="Ben Greene <BenJGreene@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/polecatworks/Angry-agent"

RUN apt-get update && apt-get install -y ca-certificates libssl3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/src/agentrs-be/target/release/agentrs-be /app/agentrs-be
RUN ln -s /app/agentrs-be /usr/local/bin/agent-be && ln -s /app/agentrs-be /usr/local/bin/agentrs-be

ENV PORT=8080
ENV HAMS_PORT=8079
EXPOSE 8080 8079

ENTRYPOINT ["/app/agentrs-be"]
CMD ["start", "--config", "/opt/app/configs/config.yaml", "--secrets", "/opt/app/secrets"]
