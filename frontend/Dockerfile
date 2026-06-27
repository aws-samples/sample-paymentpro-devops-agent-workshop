FROM node:20-slim AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

FROM nginxinc/nginx-unprivileged:alpine AS production

COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "-q", "--spider", "http://localhost:8080/"]

# nginxinc/nginx-unprivileged runs as user 101 (nginx) by default; declared
# explicitly here for the Probe checkov rule.
USER 101
