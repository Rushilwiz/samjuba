# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS builder
WORKDIR /app
RUN corepack enable && corepack prepare pnpm@11.3.0 --activate

# Public env vars are baked into the client bundle at build time
# (SvelteKit `$env/static/public`), so they must exist during `pnpm build`.
ARG PUBLIC_SUPABASE_URL
ARG PUBLIC_SUPABASE_ANON_KEY
ARG PUBLIC_SUPABASE_BUCKET=samjuba-uploads
ARG PUBLIC_UPLOADS_TABLE=uploads
ENV PUBLIC_SUPABASE_URL=$PUBLIC_SUPABASE_URL \
    PUBLIC_SUPABASE_ANON_KEY=$PUBLIC_SUPABASE_ANON_KEY \
    PUBLIC_SUPABASE_BUCKET=$PUBLIC_SUPABASE_BUCKET \
    PUBLIC_UPLOADS_TABLE=$PUBLIC_UPLOADS_TABLE

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml .npmrc ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

COPY --from=builder /app/build ./build
COPY --from=builder /app/package.json ./package.json

EXPOSE 3000
USER node
CMD ["node", "build/index.js"]
