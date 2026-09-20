# Stage 1: Build the React / Vite Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /app/ui_react
COPY ui_react/package.json ./
RUN npm install
COPY ui_react/ ./
RUN npm run build

# Stage 2: Production Python Backend & Web Server
FROM python:3.11-slim AS production
WORKDIR /app

# Install build dependencies for Tree-sitter and C extensions
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Copy compiled frontend from Stage 1 into ui_react/dist
COPY --from=frontend-builder /app/ui_react/dist ./ui_react/dist

# Set environment defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV ENV=aws
ENV PORT=8000

EXPOSE 8000 8080

# Production entrypoint: Serves both REST APIs and compiled React dashboard
CMD ["python", "-m", "ui.api_server"]
