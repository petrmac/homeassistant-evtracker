"""API client wrapper for EV Tracker integration.

This module re-exports the aioevtracker library classes for use in the integration.
"""

from __future__ import annotations

from aioevtracker import (
    DEFAULT_API_BASE_URL,
    EVTrackerApiError,
    EVTrackerAuthenticationError,
    EVTrackerClient,
    EVTrackerConnectionError,
    EVTrackerRateLimitError,
)

# Re-export for backwards compatibility and convenience
__all__ = [
    "DEFAULT_API_BASE_URL",
    "EVTrackerAPI",
    "EVTrackerApiError",
    "EVTrackerAuthenticationError",
    "EVTrackerConnectionError",
    "EVTrackerRateLimitError",
]

# Alias for backwards compatibility with existing code
EVTrackerAPI = EVTrackerClient
