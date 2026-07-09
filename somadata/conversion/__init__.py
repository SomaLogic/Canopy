from __future__ import annotations

from somadata.conversion.converter import to_v2_adat
from somadata.conversion.detection import InputType, detect_input_type
from somadata.conversion.errors import (
    AssayVersionError,
    ConversionError,
    MedNormMismatchError,
    ProcessStepsMismatchError,
    SampleMatrixMismatchError,
    UnrecognizedFormatError,
    UnsupportedCombinationError,
)
