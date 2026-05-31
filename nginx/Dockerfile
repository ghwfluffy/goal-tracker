FROM node:22-bookworm-slim AS web-build

WORKDIR /workspace/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./

ARG VITE_APP_BASE_PATH=
ARG VITE_API_BASE_URL=/api/v1
ARG API_V1_PREFIX=/api/v1
ARG VITE_AUTH_MODE=local
ARG VITE_AUTH_BASE_URL=/auth

ENV VITE_APP_BASE_PATH=${VITE_APP_BASE_PATH}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV API_V1_PREFIX=${API_V1_PREFIX}
ENV VITE_AUTH_MODE=${VITE_AUTH_MODE}
ENV VITE_AUTH_BASE_URL=${VITE_AUTH_BASE_URL}

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx/10-normalize-app-base-path.envsh /docker-entrypoint.d/10-normalize-app-base-path.envsh
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=web-build /workspace/web/dist /usr/share/nginx/html
