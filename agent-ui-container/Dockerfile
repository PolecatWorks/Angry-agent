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
COPY --from=build /app/dist/agent-ui/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
