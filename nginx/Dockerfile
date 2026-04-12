FROM node:22-bookworm-slim AS web-build

WORKDIR /workspace/web

COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./

ARG VITE_APP_BASE_PATH=
ARG VITE_API_BASE_URL=/api/v1

ENV VITE_APP_BASE_PATH=${VITE_APP_BASE_PATH}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx/default.conf /etc/nginx/conf.d/default.conf
COPY --from=web-build /workspace/web/dist /usr/share/nginx/html
