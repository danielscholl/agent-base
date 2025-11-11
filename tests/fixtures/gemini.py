"""
Shared fixtures for Gemini provider tests.

This module provides pytest fixtures for testing the Gemini provider
implementation, including mock clients and test configurations.
"""

import pytest

from agent.config import DEFAULT_GEMINI_MODEL


@pytest.fixture
def gemini_api_key() -> str:
    """Return a test API key for Gemini."""
    return "test-gemini-api-key-12345"


@pytest.fixture
def gemini_model() -> str:
    """Return a test model name for Gemini."""
    return DEFAULT_GEMINI_MODEL


@pytest.fixture
def gemini_project_id() -> str:
    """Return a test GCP project ID."""
    return "test-project-id"


@pytest.fixture
def gemini_location() -> str:
    """Return a test GCP location."""
    return "us-central1"
