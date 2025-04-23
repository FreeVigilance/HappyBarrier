# --- Stage 1: Build React app ---
FROM node:22.14.0-alpine AS build
WORKDIR /frontend_app

# Copy package.json and package-lock.json for installing dependencies
COPY package*.json  .
RUN npm install --frozen-lockfile

# Copy the rest of the application and build
COPY . .
RUN npm run build

# --- Stage 2: Development (Vite) ---
FROM node:22.14.0 AS development
WORKDIR /frontend_app

# Copy package.json and install dependencies
COPY package*.json .
RUN npm install --frozen-lockfile

# Copy the source code
COPY . .

# Expose port for Vite
EXPOSE 5173

# Run Vite development server
CMD ["npm", "run", "dev"]

# --- Stage 3: Production ---
FROM node:22.14.0-alpine AS production
WORKDIR /frontend_app

# Install curl for healthcheck
RUN apk add --no-cache curl

# Copy built app and dependencies for production preview
COPY --from=build /frontend_app/dist ./dist
COPY --from=build /frontend_app/node_modules ./node_modules
COPY --from=build /frontend_app/package.json ./
COPY --from=build ./frontend_app/vite.config.js ./

# Expose port used by Vite preview
EXPOSE 4173

# Run vite preview server
CMD ["npx", "vite", "preview", "--host"]