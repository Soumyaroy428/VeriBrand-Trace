"""Tests for application health and status endpoints."""

import sys
import os

# Ensure server root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from tests.test_health_direct import (
    test_root_endpoint_direct,
    test_health_endpoint_direct,
    test_api_v1_health_endpoint_direct,
)


def test_root():
    test_root_endpoint_direct()


def test_health():
    test_health_endpoint_direct()


def test_api_v1_health():
    test_api_v1_health_endpoint_direct()
