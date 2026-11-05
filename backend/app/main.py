
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.repositories import router as repository_router


app = FastAPI(
    title="RepoLens AI",
    description="AI-powered Repository Understanding and Debugging Assistant",
    version="1.0.0"
)


# Register API routers
app.include_router(repository_router)


@app.get("/")
def root():
    return {
        "message": "Welcome to RepoLens AI!",
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "application": "RepoLens AI"
    }


@app.get("/health/database")
def database_health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))

        return {
            "status": "connected",
            "database": "PostgreSQL",
            "message": "Database connection successful"
        }

    except Exception:
        return {
            "status": "error",
            "database": "PostgreSQL",
            "message": "Database connection failed"
        }
