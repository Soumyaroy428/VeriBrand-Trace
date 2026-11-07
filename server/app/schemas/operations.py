"""Pydantic schemas for System Telemetry, Disaster Recovery, and Release Readiness."""

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EngineStatus(BaseModel):
    name: str
    status: str  # OPERATIONAL, DEGRADED, OFFLINE
    latency_ms: float
    description: str


class SystemTelemetryResponse(BaseModel):
    """Real-time operations, telemetry, and release readiness telemetry."""
    workspace_id: str
    overall_status: str
    uptime_seconds: float
    engines: Dict[str, str]
    performance_benchmarks: Dict[str, Any]
    governance_metrics: Dict[str, int]
    release_gates: Dict[str, bool]
    team_signoff: Dict[str, str]
    timestamp: str


class WorkspaceBackupResponse(BaseModel):
    """Cryptographically sealed disaster recovery workspace archive."""
    workspace_id: str
    workspace_name: str
    backup_timestamp: str
    backup_seal_sha256: str
    entities_backed_up: Dict[str, int]
    payload: Dict[str, Any]
