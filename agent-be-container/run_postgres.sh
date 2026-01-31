#!/bin/bash
docker rm -f agent-postgres || true
docker run --name agent-postgres -e POSTGRES_PASSWORD=mysecretpassword -e POSTGRES_DB=agentdb -p 5432:5432 -d postgres:15-alpine
echo "Postgres started on port 5432"
