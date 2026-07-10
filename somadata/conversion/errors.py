from __future__ import annotations

from somadata.errors import AdatBaseError


class ConversionError(AdatBaseError):
    """Base class for all ADAT v2.0 conversion errors."""


class UnsupportedCombinationError(ConversionError):
    """Raised when the combination of input types has no approved conversion path."""


class SampleMatrixMismatchError(ConversionError):
    """Raised when source ADATs have incompatible SampleMatrix values."""


class AssayVersionError(ConversionError):
    """Raised when an array ADAT has an AssayVersion below the minimum supported (v4)."""


class MedNormMismatchError(ConversionError):
    """Raised when MedNorm reference values are not compatible across source ADATs."""


class ProcessStepsMismatchError(ConversionError):
    """Raised when ProcessSteps are incompatible across source ADATs for a given merge path."""


class UnrecognizedFormatError(ConversionError):
    """Raised when an Adat cannot be classified as any known input type."""
