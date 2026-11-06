"""Base utilities, UUID helpers, and timestamp generators for MongoDB Beanie models."""

import uuid
from datetime import datetime, timezone


def generate_uuid() -> str:
    """Generate a clean UUID string."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """Generate timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)
