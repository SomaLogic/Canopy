"""Pre-conversion validation for array v1.x source ADATs.

Public API
----------
validate_source_array_adat(adat) -> None
    Raise :class:`~somadata.conversion.errors.ConversionError` if the source
    ADAT is missing fields that are unconditionally required in the v2.0 spec
    and have no reasonable default or fallback value.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from somadata.conversion._helpers import lookup_header
from somadata.conversion.errors import ConversionError

if TYPE_CHECKING:
    from somadata.adat import Adat


# ---------------------------------------------------------------------------
# Required source fields
#
# These are the legacy header fields that map to v2.0 fields whose
# "Value Required" column is "True" or "Array-only", and for which there is
# no reasonable generated default.
#
# Fields NOT listed here either:
#   (a) have a generated default (AdatId → new GUID, FileCreatedDate → now), or
#   (b) are genuinely optional in the spec (Title, ReportConfig, plate fields), or
#   (c) are already validated upstream (AssayVersion checked by the detection layer).
# ---------------------------------------------------------------------------

_REQUIRED_SOURCE_FIELDS: tuple[tuple[str, str], ...] = (
    # (legacy field name, v2.0 field it maps to)
    ('ProcessSteps', 'ProcessSteps'),
    ('ProteinEffectiveDate', 'SOMAmerReferenceSource'),
)


def validate_source_array_adat(adat: Adat) -> None:
    """Validate that *adat* has all fields required for array v1.x → v2.0 conversion.

    Only checks fields that are:
    - ``Value Required = True`` or ``Array-only`` in the v2.0 spec, **and**
    - have no generated default or upstream guard.

    Parameters
    ----------
    adat : Adat
        The source array ADAT to validate.

    Raises
    ------
    ConversionError
        If one or more required source fields are missing or blank.
    """
    hdr = getattr(adat, 'header_metadata', {})

    missing = [
        f'{legacy!r} (→ v2.0 field: {v2!r})'
        for legacy, v2 in _REQUIRED_SOURCE_FIELDS
        if not lookup_header(hdr, legacy)
    ]

    if missing:
        raise ConversionError(
            f'Source ADAT is missing required field(s) for v2.0 conversion: '
            f'{", ".join(missing)}.'
        )
