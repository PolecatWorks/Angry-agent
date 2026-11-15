# Build stage
FROM rust:1.98-slim as builder

WORKDIR /usr/src/agentrs-be

RUN apt-get update && apt-get install -y pkg-config libssl-dev && rm -rf /var/lib/apt/lists/*

COPY Cargo.toml ./
COPY src ./src
COPY tests ./tests

RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y ca-certificates libssl3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/src/agentrs-be/target/release/agentrs-be /app/agentrs-be

ENV PORT=8081
ENV HAMS_PORT=8078
EXPOSE 8081 8078

CMD ["/app/agentrs-be"]
