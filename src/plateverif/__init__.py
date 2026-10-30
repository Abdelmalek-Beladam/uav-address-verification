"""plateverif: verification of house-number plates against the official address register."""

from ._version import __version__
from .config import Config, load_config
from .errors import ConfigError, InputError, PlateVerifError, VerificationError
from .report import write_outputs
from .statuses import STATUS_INFO, Status
from .verify import VerificationResult, run_verification

__all__ = [
    "__version__",
    "Config",
    "load_config",
    "run_verification",
    "VerificationResult",
    "write_outputs",
    "Status",
    "STATUS_INFO",
    "PlateVerifError",
    "InputError",
    "ConfigError",
    "VerificationError",
]
