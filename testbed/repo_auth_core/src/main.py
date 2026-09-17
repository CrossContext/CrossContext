"""
Backend Auth Core Service - Main Application Entrypoint
FastAPI Microservice for Authentication and Token Lifecycle.
"""
from fastapi import FastAPI
from api.auth import router as auth_router

app = FastAPI(
    title="AuthCore Service",
    description="Central Authentication Microservice for the platform",
    version="1.2.0"
)

app.include_router(auth_router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "auth_core"}
