"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.database import Base, engine
from app.routers import ads, analytics, auth, campaigns, events, recommendations, visitor_sessions


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
    app = FastAPI(title="Website & Advertisement Optimizer API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
allow_origins=[
    "https://simple-test-website-orcin.vercel.app",
    "https://project-189r3.vercel.app"
],
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
