"""API routers for the Spotify Linker bot."""

from .webhook import router as webhook_router

__all__ = ["webhook_router"]
