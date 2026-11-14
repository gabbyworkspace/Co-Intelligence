class CointError(Exception):
    """Base error."""


class TransientError(CointError):
    """Retry after 1, 5, 15 minutes (network, 5xx, rate limit, timeout)."""


class PermanentError(CointError):
    """Do not retry automatically; mark BLOCKED."""


class AuthError(PermanentError):
    """Authentication failed (bad/expired credentials)."""


class PermissionDenied(PermanentError):
    """Authenticated but not permitted."""


class InvalidInput(PermanentError):
    """Inputs or outputs are malformed / incomplete."""


class UnsupportedAdapter(PermanentError):
    """No callable adapter is configured for this role."""


class StaleAssignment(CointError):
    """Result belongs to an obsolete cycle/assignment; reject it."""


class CommandRejected(CointError):
    """A founder/agent command was rejected; message is user-facing."""
