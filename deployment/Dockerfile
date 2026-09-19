# Multi-stage Dockerfile for Amazon Bedrock AgentCore Runtime & Local Execution
FROM python:3.11-slim as base

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

# Set environment defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV ENV=aws

EXPOSE 8080 8000

# Production Bedrock AgentCore entrypoint
CMD ["python", "agent_orchestrator/bedrock_agentcore_app.py"]
