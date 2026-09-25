"""Application service exceptions."""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for actionable service-layer errors."""


class ProjectNotFoundError(ServiceError):
    """Raised when a project reference cannot be resolved."""


class BackendOperationError(ServiceError):
    """Raised when a runtime operation returns an unsuccessful result."""
