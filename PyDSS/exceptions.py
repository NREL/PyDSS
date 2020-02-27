"""Exceptions used in PyDSS"""


class InvalidParameter(Exception):
    """Raised when bad user input is detected."""


class OpenDssConvergenceError(Exception):
    """Raised when OpenDSS fails to converge on a solution."""
