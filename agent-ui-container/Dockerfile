# Use mfe-shell image for mfe-shared library
ARG MFE_SHELL_IMAGE=docker pull ghcr.io/polecatworks/mfe-shell-mfe-shell:main
FROM ${MFE_SHELL_IMAGE} AS mfe-shell

FROM node:20-alpine as build

WORKDIR /app

# Copy and link mfe-shared library from mfe-shell image
COPY --from=mfe-shell /usr/share/mfe-shared /tmp/mfe-shared
WORKDIR /tmp/mfe-shared
RUN npm link

# Copy ui application
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Link mfe-shared into ui
RUN npm link mfe-shared

COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=build /app/dist/agent-ui/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
