"""Verification script for FastAPI backend health endpoints."""

import asyncio
import sys
import json

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from httpx import AsyncClient, ASGITransport
from app.main import app


async def run_checks():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Check root
        root_res = await client.get("/")
        print(f"ROOT_CHECK: {root_res.status_code}")
        assert root_res.status_code == 200, f"Expected 200, got {root_res.status_code}"
        print(json.dumps(root_res.json(), indent=2))

        # Check /health
        health_res = await client.get("/health")
        print(f"HEALTH_CHECK: {health_res.status_code}")
        assert health_res.status_code == 200, f"Expected 200, got {health_res.status_code}"
        print(json.dumps(health_res.json(), indent=2))

        # Check /api/v1/health
        api_health_res = await client.get("/api/v1/health")
        print(f"API_V1_HEALTH_CHECK: {api_health_res.status_code}")
        assert api_health_res.status_code == 200, f"Expected 200, got {api_health_res.status_code}"
        print(json.dumps(api_health_res.json(), indent=2))

    print("\nALL BACKEND HEALTH CHECKS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(run_checks())

