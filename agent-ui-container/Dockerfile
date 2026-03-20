# Use mfe-shell image for mfe-shared library
ARG MFE_SHELL_IMAGE=ghcr.io/polecatworks/mfe-shell-mfe-shell:main
FROM ${MFE_SHELL_IMAGE} AS mfe-shell

FROM node:22-alpine AS build

WORKDIR /app

# Copy mfe-shared library from mfe-shell image to a path that matches package.json relative path
# package.json has: "mfe-shared": "file:../../Mfe-shell/mfe-shell-container/dist/mfe-shared"
# We need to recreate this structure relative to /app/agent-ui-container (where we will build)

# Create the directory structure needed by package.json
COPY --from=mfe-shell /usr/share/mfe-shared /Mfe-shell/mfe-shell-container/dist/mfe-shared


# Switch to app directory
COPY package.json ./
RUN npm install

# Copy application code
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine

# Add OCI labels
LABEL org.opencontainers.image.title="Agent UI"
LABEL org.opencontainers.image.description="AI Agent User Interface (Micro-Frontend)"
LABEL org.opencontainers.image.authors="Ben Greene <BenJGreene@gmail.com>"
LABEL org.opencontainers.image.source="https://github.com/polecatworks/Angry-agent"
LABEL org.opencontainers.image.created="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

COPY --from=build /app/dist/agent-ui/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
