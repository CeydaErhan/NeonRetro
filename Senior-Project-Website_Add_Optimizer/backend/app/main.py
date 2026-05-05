"""FastAPI application entrypoint."""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from dotenv import load_dotenv

from app.database import Base, engine
from app.routers import ads, analytics, auth, campaigns, events, recommendations, visitor_sessions

load_dotenv()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Initialize database schema at startup and release resources at shutdown."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS user_agent TEXT"))
        conn.execute(text("ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS referrer TEXT"))
        conn.execute(text("ALTER TABLE visitor_sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW()"))
        conn.execute(text("ALTER TABLE visitor_sessions ALTER COLUMN visitor_id DROP NOT NULL"))
        conn.commit()
    yield


def create_app() -> FastAPI:
    """Create the FastAPI app with middleware and routers."""
    cors_allow_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
    allow_origins = [origin.strip() for origin in cors_allow_origins.split(",") if origin.strip()]
    if not allow_origins:
        allow_origins = [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]

    app = FastAPI(title="Website & Advertisement Optimizer API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(events.router)
    app.include_router(campaigns.router)
    app.include_router(ads.router)
    app.include_router(analytics.router)
    app.include_router(recommendations.router)
    app.include_router(visitor_sessions.router)

    @app.get("/")
    async def healthcheck() -> dict[str, str]:
        """Simple health endpoint to verify the API is running."""
        return {"status": "ok"}

    return app


app = create_app()
