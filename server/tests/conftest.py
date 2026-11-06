"""Shared Pytest configuration and in-memory MongoDB fixtures for server tests."""

import sys
import os
import pytest_asyncio
import mongomock
from mongomock_motor import AsyncMongoMockClient

# Ensure server root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Patch mongomock Database.list_collection_names to only accept supported kwargs
_orig_list_colls = mongomock.database.Database.list_collection_names
def _patched_list_colls(self, *args, **kwargs):
    valid_kwargs = {}
    if "filter" in kwargs:
        valid_kwargs["filter"] = kwargs["filter"]
    return _orig_list_colls(self, *args, **valid_kwargs)
mongomock.database.Database.list_collection_names = _patched_list_colls

from app.core.database import init_db, close_db


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Initializes in-memory mock MongoDB before each test."""
    mock_client = AsyncMongoMockClient()
    await init_db(client=mock_client, db_name="test_unified_db")
    yield
    await close_db()
