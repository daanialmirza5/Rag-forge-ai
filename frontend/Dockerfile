FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Values baked in at build time (Next.js inlines NEXT_PUBLIC_* into the
# client bundle) — override via --build-arg for a non-default deployment.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production

# node:22-slim already ships a non-root `node` user at uid/gid 1000 (every
# official Node image does, for exactly this purpose) — creating a new one
# at the same uid fails the build ("UID 1000 is not unique"), caught by
# actually running `docker build`. Reuse the existing user instead.
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder --chown=node:node /app/public ./public
USER node

EXPOSE 3000
ENV PORT=3000 HOSTNAME=0.0.0.0

CMD ["node", "server.js"]
