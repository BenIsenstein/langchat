FROM node:20 AS builder

WORKDIR /app

ARG VITE_BACKEND_URL
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM caddy:2.8.0-alpine

COPY --from=builder /app/dist /usr/share/caddy

COPY ./Caddyfile /etc/caddy/Caddyfile

EXPOSE 80
