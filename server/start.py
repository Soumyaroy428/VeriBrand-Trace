"""Production startup runner for VeriBrand Trace API.

Safely parses port and host from environment variables without relying
on shell variable expansion in container environments.
"""

import os
import sys

# Ensure server root directory is on the python path
server_dir = os.path.dirname(os.path.abspath(__file__))
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[STARTUP] Starting VeriBrand Trace API on {host}:{port}...")
    uvicorn.run("app.main:app", host=host, port=port, log_level="info")
