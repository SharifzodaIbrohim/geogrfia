"""Root import fallback — delegates to db.force_olympiad_routes."""
from db.force_olympiad_routes import install  # noqa: F401

__all__ = ["install"]
