"""NGS ADAT validation — pre-conversion checks."""

from __future__ import annotations

from typing import TYPE_CHECKING

from somadata.conversion._helpers import lookup_header
from somadata.conversion.errors import ConversionError

if TYPE_CHECKING:
    from somadata.adat import Adat

# These header fields are optional — present in single-run ADATs but absent when DPQ
# combines multiple runs (e.g. ICM merged outputs). If missing, the corresponding
# ROW_DATA columns are created with empty values rather than raising an error.
# Exported so that row_data and context modules can reference the same set.
OPTIONAL_HEADER_FIELDS: frozenset[str] = frozenset({
    'RunId',
    'YieldDemux',
    'YieldQ30Demux',
    'Q30WeightedMean',
})


def validate_source_ngs_adat(adat: Adat) -> None:
    """Validate that *adat* meets NGS v1.x → v2.0 conversion requirements.

    Parameters
    ----------
    adat : Adat
        The source NGS ADAT to validate.

    Raises
    ------
    ConversionError
        If any required header fields are missing or invalid.
        If the ADAT does not appear to be an NGS platform ADAT.

    Examples
    --------
    >>> validate_source_ngs_adat(ngs_adat)  # passes if valid
    >>> validate_source_ngs_adat(array_adat)
    Traceback (most recent call last):
        ...
    ConversionError: ADAT does not appear to be NGS format...
    """
    hdr = getattr(adat, 'header_metadata', {})

    # Required header fields for NGS conversion
    required_fields = {
        'ProcessSteps': 'Comma-separated processing steps string',
        'SOMAmerReferenceSource': 'SOMAmer reagent annotation reference identifier',
        'Version': 'DPQ software version',
        'InstrumentType': 'Sequencing instrument type',
        'Flowcell': 'Flowcell identifier',
    }

    # Fields in OPTIONAL_HEADER_FIELDS are skipped here; their absence is handled
    # gracefully by the row_data/context modules (empty strings instead of errors).

    missing = []
    for field, description in required_fields.items():
        value = lookup_header(hdr, field)
        if not value:
            missing.append(f'{field} ({description})')

    if missing:
        raise ConversionError(
            f'Missing required NGS header fields: {", ".join(missing)}'
        )

    # Check for NGS platform marker: SOMAmerReads should exist as a ROW_DATA field
    # (or, rarely, as a COL_DATA level name / flat column label).
    if hasattr(adat, 'index') and hasattr(adat.index, 'names'):
        if 'SOMAmerReads' in adat.index.names:
            return  # Valid NGS

    if hasattr(adat, 'columns'):
        if 'SOMAmerReads' in getattr(adat.columns, 'names', []):
            return  # Valid NGS
        if 'SOMAmerReads' in list(adat.columns):
            return  # Valid NGS
    raise ConversionError(
        'ADAT does not appear to be NGS format: missing SOMAmerReads column/field. '
        'NGS ADATs should have sequencing read count metadata.'
    )
