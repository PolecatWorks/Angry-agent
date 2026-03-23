#!/bin/bash
docker rm -f agent-postgres || true
docker run --name agent-postgres -e POSTGRES_PASSWORD=mysecretpassword -e POSTGRES_DB=agentdb -p 5432:5432 -d pgvector/pgvector:pg15
echo "Postgres started on port 5432"
