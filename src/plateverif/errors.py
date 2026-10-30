"""Exceptions raised by plateverif."""


class PlateVerifError(Exception):
    """Base class for all plateverif errors."""


class InputError(PlateVerifError):
    """An input file is missing, malformed or inconsistent."""


class ConfigError(PlateVerifError):
    """The configuration contains an unknown key or an invalid value."""


class VerificationError(PlateVerifError):
    """The verification cannot run on the given data."""
