"""Shared utility functions for ADAT v2.0 conversion.

These helpers are used by both the ``array/`` and (future) ``ngs/``
conversion sub-packages.
"""

from __future__ import annotations

import re
import uuid
from typing import Any


def generate_guid() -> str:
    """Return a new GUID in ``GID-<uuid4>`` format."""
    return f'GID-{uuid.uuid4()}'


def _compute_file_md5sum(file_path: str) -> str:
    """Compute MD5 checksum of a file.

    Parameters
    ----------
    file_path : str
        Path to the file.

    Returns
    -------
    str
        Hexadecimal MD5 digest (32 characters).
    """
    import hashlib

    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        # Read in chunks for memory efficiency
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def _compute_adat_md5sum(adat: object) -> str:
    """Compute MD5 checksum of an Adat's structure and data.

    Computes a deterministic hash of the Adat's header metadata, column
    structure, row structure, and RFU values. Used as a fallback identifier
    when the source ADAT lacks an AdatId and was not loaded from a file.

    Parameters
    ----------
    adat : Adat
        The source ADAT object.

    Returns
    -------
    str
        Hexadecimal MD5 digest string (32 characters).

    Examples
    --------
    >>> md5 = _compute_adat_md5sum(adat)
    >>> len(md5)
    32
    """
    import hashlib

    md5 = hashlib.md5()

    # Hash header metadata (sorted for determinism)
    hdr = getattr(adat, 'header_metadata', {})
    for key in sorted(hdr.keys()):
        val = str(hdr[key])
        md5.update(key.encode('utf-8'))
        md5.update(val.encode('utf-8'))

    # Hash column structure
    if hasattr(adat, 'columns'):
        for name in adat.columns.names:
            md5.update(str(name).encode('utf-8'))
        # Sample a few column values for efficiency
        for i in range(min(10, adat.columns.nlevels)):
            vals = adat.columns.get_level_values(i)
            for val in list(vals)[:10]:  # First 10 values per level
                md5.update(str(val).encode('utf-8'))

    # Hash row structure
    if hasattr(adat, 'index'):
        for name in adat.index.names:
            md5.update(str(name).encode('utf-8'))
        # Sample a few row values for efficiency
        for i in range(min(10, adat.index.nlevels)):
            vals = adat.index.get_level_values(i)
            for val in list(vals)[:10]:  # First 10 values per level
                md5.update(str(val).encode('utf-8'))

    # Hash RFU matrix (sample for efficiency on large ADATs)
    if hasattr(adat, 'values'):
        values = adat.values
        # Sample corners and center for large matrices
        if values.size > 10000:
            # Top-left corner (5x5)
            md5.update(values[:5, :5].tobytes())
            # Bottom-right corner (5x5)
            md5.update(values[-5:, -5:].tobytes())
            # Center (5x5)
            mid_r, mid_c = values.shape[0] // 2, values.shape[1] // 2
            md5.update(values[mid_r : mid_r + 5, mid_c : mid_c + 5].tobytes())
        else:
            md5.update(values.tobytes())

    return md5.hexdigest()


def strip_bang_prefix(key: str) -> str:
    """Strip a leading ``!`` from a header key.

    Parameters
    ----------
    key : str
        A header key, possibly prefixed with ``!``.

    Returns
    -------
    str
        The key with any leading ``!`` removed.

    Examples
    --------
    >>> strip_bang_prefix('!Title')
    'Title'
    >>> strip_bang_prefix('Title')
    'Title'
    """
    return key.lstrip('!')


def lookup_header(header: dict, *keys: str) -> str:
    """Try multiple key variants (with and without ``!`` prefix) in *header*.

    Parameters
    ----------
    header : dict
        The ADAT header_metadata dictionary.
    *keys : str
        One or more canonical (no-bang) key names to try.

    Returns
    -------
    str
        The first non-empty value found, or ``''`` if none match.

    Examples
    --------
    >>> lookup_header({'!Title': 'Study 1'}, 'Title')
    'Study 1'
    """
    for key in keys:
        for candidate in (key, f'!{key}'):
            val = header.get(candidate, '')
            val_str = '' if val is None else str(val).strip()
            if val_str:
                return val_str
    return ''


def parse_process_steps(raw: str) -> list[str]:
    """Split a comma-separated ProcessSteps string into a clean list.

    Parameters
    ----------
    raw : str
        Legacy ProcessSteps value, e.g.
        ``'Raw RFU, Hyb Normalization, plateScale, Calibration'``.

    Returns
    -------
    list[str]
        Ordered list of stripped step names.

    Examples
    --------
    >>> parse_process_steps('Raw RFU, Hyb Normalization, plateScale')
    ['Raw RFU', 'Hyb Normalization', 'plateScale']
    """
    if not raw or not raw.strip():
        return []
    return [step.strip() for step in raw.split(',') if step.strip()]


def consolidate_plate_fields(
    header: dict,
    prefix: str,
    stage: str | None = 'PlatformSpecific',
) -> dict[str, Any]:
    """Extract plate-keyed header values into a JSON-ready dict.

    Scans *header* for keys matching ``<prefix><PlateId>`` (after stripping
    any leading ``!``) and returns a nested dict.

    Parameters
    ----------
    header : dict
        The ADAT header_metadata dictionary.
    prefix : str
        The key prefix to match (e.g. ``'PlateScale_Scalar_'``).
    stage : str or None, optional
        If provided, the value is wrapped under this sub-key:
        ``{"<PlateId>": {"<stage>": <value>}}``.
        If ``None``, the value is stored flat:
        ``{"<PlateId>": <value>}``.

    Returns
    -------
    dict
        A dict mapping PlateId to the (possibly nested) value, or an empty
        dict if no matching keys are found.

    Examples
    --------
    >>> consolidate_plate_fields(
    ...     {'PlateScale_Scalar_PLT1': '1.23', '!PlateScale_Scalar_PLT2': '0.99'},
    ...     prefix='PlateScale_Scalar_',
    ... )
    {'PLT1': {'PlatformSpecific': '1.23'}, 'PLT2': {'PlatformSpecific': '0.99'}}
    """
    result: dict[str, Any] = {}
    for raw_key, value in header.items():
        clean_key = strip_bang_prefix(raw_key)
        if clean_key.startswith(prefix):
            plate_id = clean_key[len(prefix) :]
            if plate_id:
                result[plate_id] = {stage: value} if stage is not None else value
    return result


# ---------------------------------------------------------------------------
# Pattern helpers used by col_data conversion
# ---------------------------------------------------------------------------

_CAL_PLATE_RE = re.compile(r'^Cal_(.+)$')
_CAL_QC_RATIO_RE = re.compile(r'^CalQcRatio_(.+?)_(.+)$')
_QC_REFERENCE_RE = re.compile(r'^QcReference_(.+)$')


def match_cal_plate(name: str) -> str | None:
    """Return the PlateId if *name* matches ``Cal_<PlateId>``, else ``None``."""
    m = _CAL_PLATE_RE.match(name)
    return m.group(1) if m else None


def match_cal_qc_ratio(name: str) -> tuple[str, str] | None:
    """Return ``(plate_id, qc_sample_id)`` if *name* matches ``CalQcRatio_*``, else ``None``."""
    m = _CAL_QC_RATIO_RE.match(name)
    return (m.group(1), m.group(2)) if m else None


def match_qc_reference(name: str) -> str | None:
    """Return the QCSampleId if *name* matches ``QcReference_<QCSampleId>``, else ``None``."""
    m = _QC_REFERENCE_RE.match(name)
    return m.group(1) if m else None
