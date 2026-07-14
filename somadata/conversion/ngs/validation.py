"""NGS ADAT validation — pre-conversion checks."""

from __future__ import annotations

from somadata.conversion._helpers import lookup_header
from somadata.conversion.errors import ConversionError


def validate_source_ngs_adat(adat: object) -> None:
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
        'Version': 'DPQ software version',
        'RunId': 'Sequencing run identifier',
        'InstrumentType': 'Sequencing instrument type',
        'Flowcell': 'Flowcell identifier',
        'YieldDemux': 'Demultiplexed yield',
        'YieldQ30Demux': 'Q30 demultiplexed yield',
        'Q30WeightedMean': 'Weighted mean Q30 score',
    }
    
    missing = []
    for field, description in required_fields.items():
        value = lookup_header(hdr, field)
        if not value:
            missing.append(f'{field} ({description})')
    
    if missing:
        raise ConversionError(
            f'Missing required NGS header fields: {", ".join(missing)}'
        )
    
    # Check for NGS platform marker: SOMAmerReads column should exist
    if hasattr(adat, 'columns'):
        col_names = []
        if hasattr(adat.columns, 'names'):
            # MultiIndex columns
            if 'SOMAmerReads' in adat.columns.names:
                return  # Valid NGS
            # Check level values
            for level in range(adat.columns.nlevels):
                col_names.extend(adat.columns.get_level_values(level))
        else:
            col_names = list(adat.columns)
        
        # Look for SOMAmerReads in any column level
        if any('SOMAmerReads' in str(name) for name in col_names):
            return  # Valid NGS
    
    # Check row metadata for SOMAmerReads
    if hasattr(adat, 'index'):
        if hasattr(adat.index, 'names') and 'SOMAmerReads' in adat.index.names:
            return  # Valid NGS
    
    raise ConversionError(
        'ADAT does not appear to be NGS format: missing SOMAmerReads column/field. '
        'NGS ADATs should have sequencing read count metadata.'
    )
