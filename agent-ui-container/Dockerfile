FROM node:22-alpine AS build

WORKDIR /app

# Accept GitHub token for private/scoped package installation
ARG NODE_POLECATWORKS

# Add .npmrc for GitHub Packages inside the container before install
RUN echo "@polecatworks:registry=https://npm.pkg.github.com" > .npmrc && \
    echo "//npm.pkg.github.com/:_authToken=${NODE_POLECATWORKS}" >> .npmrc

# Switch to app directory
COPY package.json package-lock.json ./
RUN npm ci

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
