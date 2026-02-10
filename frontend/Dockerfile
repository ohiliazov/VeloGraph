# -------- Builder stage --------
FROM node:22 AS builder

WORKDIR /app

# Install deps (including dev) for build
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Prune devDependencies to reduce final image size
RUN npm ci --omit=dev && npm cache clean --force

# -------- Development stage --------
FROM node:22 AS dev
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source (can be overridden by volume mount for live reload)
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]

# -------- Production runtime stage --------
FROM node:22 AS prod
ENV NODE_ENV=production
WORKDIR /app

# Copy only what we need to run the production server
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["npm", "run", "start"]
