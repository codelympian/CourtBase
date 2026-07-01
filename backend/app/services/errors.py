"""Service-layer exceptions, mapped to HTTP status codes in the routes."""

from __future__ import annotations


class ServiceError(Exception):
    """Base class for expected, user-facing service errors."""


class NotFoundError(ServiceError):
    """Requested entity does not exist (or is soft-deleted / out of tenant scope)."""


class ConflictError(ServiceError):
    """Uniqueness or state conflict (e.g. duplicate natural key)."""


class ValidationError(ServiceError):
    """Business-rule validation failure."""


class ForbiddenError(ServiceError):
    """Caller lacks scope/permission for this specific resource."""
