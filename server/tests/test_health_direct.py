"""Direct ASGI unit test for FastAPI health check endpoints."""

import sys
import os
import asyncio
import json

# Ensure server root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app


async def call_asgi(path: str, method: str = "GET") -> tuple[int, dict]:
    status_code = None
    headers = []
    body = bytearray()

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": headers,
        "server": ("127.0.0.1", 8000),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code, body
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            body.extend(message.get("body", b""))

    await app(scope, receive, send)
    return status_code, json.loads(body.decode("utf-8"))


def test_root_endpoint_direct():
    status, data = asyncio.run(call_asgi("/"))
    assert status == 200
    assert data["service"] == "VeriBrand Trace API"
    assert "version" in data
    assert data["health"] == "/api/v1/health"


def test_health_endpoint_direct():
    status, data = asyncio.run(call_asgi("/health"))
    assert status == 200
    assert data["status"] == "healthy"
    assert data["checks"]["api"] == "operational"


def test_api_v1_health_endpoint_direct():
    status, data = asyncio.run(call_asgi("/api/v1/health"))
    assert status == 200
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["environment"] == "development"
    assert data["checks"]["deterministic_engine"] == "ready"


if __name__ == "__main__":
    print("Executing direct health check tests...")
    test_root_endpoint_direct()
    print("  ✓ Root endpoint passed (200 OK)")
    test_health_endpoint_direct()
    print("  ✓ /health endpoint passed (200 OK)")
    test_api_v1_health_endpoint_direct()
    print("  ✓ /api/v1/health endpoint passed (200 OK)")
    print("\nALL BACKEND HEALTH CHECKS PASSED SUCCESSFULLY!")
