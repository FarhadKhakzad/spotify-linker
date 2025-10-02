from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from spotify_linker.api import webhook_router
from spotify_linker.clients import build_spotify_client
from spotify_linker.config.settings import AppSettings, get_settings
from spotify_linker.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown events."""

    logger.info("Spotify Linker service is starting up")
    settings = get_settings()
    validate_critical_settings(settings)

    spotify_client = None
    if settings.spotify_client_id and settings.spotify_client_secret:
        spotify_client = build_spotify_client(settings)
        app.state.spotify_client = spotify_client
        logger.info("Spotify client initialized successfully")
    else:
        app.state.spotify_client = None
        logger.info("Spotify client not initialized due to missing credentials")

    try:
        yield
    finally:
        app.state.spotify_client = None
        logger.info("Spotify Linker service is shutting down")


app = FastAPI(title="Spotify Linker Bot", version="0.1.0", lifespan=lifespan)
app.include_router(webhook_router)


@app.get("/health", summary="Health check")
async def health_check() -> JSONResponse:
    """Simple endpoint to verify the service is running."""

    return JSONResponse(content={"status": "ok"})


def validate_critical_settings(settings: AppSettings) -> None:
    """Ensure critical settings are present and non-empty."""

    missing: list[str] = []
    if not settings.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if not settings.spotify_client_id:
        missing.append("SPOTIFY_CLIENT_ID")
    if not settings.spotify_client_secret:
        missing.append("SPOTIFY_CLIENT_SECRET")

    if missing:
        logger.warning(
            "Missing recommended environment variables: %s", ", ".join(missing)
        )
    else:
        logger.info("All critical environment variables are present")
