# Use Node 20 as requested
FROM node:20-alpine

# Create app directory
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source
COPY . .

# Expose Next.js dev port
EXPOSE 3000

# Default command: run dev server
CMD ["npm", "run", "dev"]
