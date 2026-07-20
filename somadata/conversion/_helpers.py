"""Shared utility functions for ADAT v2.0 conversion.

These helpers are used by both the ``array/`` and ``ngs/`` conversion
sub-packages.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import TYPE_CHECKING, Any

import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from somadata.adat import Adat


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
    md5 = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5.update(chunk)
    return md5.hexdigest()


def _compute_adat_md5sum(adat: Adat) -> str:
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
    md5 = hashlib.md5()

    hdr = getattr(adat, 'header_metadata', {})
    for key in sorted(hdr.keys()):
        val = str(hdr[key])
        md5.update(key.encode('utf-8'))
        md5.update(val.encode('utf-8'))

    if hasattr(adat, 'columns'):
        for name in adat.columns.names:
            md5.update(str(name).encode('utf-8'))
        for i in range(min(10, adat.columns.nlevels)):
            vals = adat.columns.get_level_values(i)
            for val in list(vals)[:10]:
                md5.update(str(val).encode('utf-8'))

    if hasattr(adat, 'index'):
        for name in adat.index.names:
            md5.update(str(name).encode('utf-8'))
        for i in range(min(10, adat.index.nlevels)):
            vals = adat.index.get_level_values(i)
            for val in list(vals)[:10]:
                md5.update(str(val).encode('utf-8'))

    if hasattr(adat, 'values'):
        values = adat.values
        if values.size > 10000:
            md5.update(values[:5, :5].tobytes())
            md5.update(values[-5:, -5:].tobytes())
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
# Merge utilities (used by merge.py for Mixed conversions)
# ---------------------------------------------------------------------------


def merge_pipe_delimited(val_a: str, val_b: str) -> str:
    """Merge two strings by combining unique, non-empty pipe-delimited values.

    Values already pipe-delimited inside each argument are split and
    deduplicated before rejoining.  Insertion order is preserved (``val_a``
    tokens first).

    Parameters
    ----------
    val_a : str
        First string value (may itself be pipe-delimited).
    val_b : str
        Second string value (may itself be pipe-delimited).

    Returns
    -------
    str
        A single pipe-delimited string of unique non-empty tokens, or ``''``
        if both inputs are blank.

    Examples
    --------
    >>> merge_pipe_delimited('Human', 'Human')
    'Human'
    >>> merge_pipe_delimited('Human', 'Mouse')
    'Human|Mouse'
    >>> merge_pipe_delimited('A|B', 'B|C')
    'A|B|C'
    >>> merge_pipe_delimited('', 'EDTA Plasma')
    'EDTA Plasma'
    """
    seen: set[str] = set()
    tokens: list[str] = []
    for raw in (val_a, val_b):
        if not raw:
            continue
        for part in raw.split('|'):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                tokens.append(part)
    return '|'.join(tokens)


def merge_plate_json(
    dict_a: dict,
    dict_b: dict,
    field_name: str = '',
) -> dict:
    """Combine two plate-keyed JSON dicts, raising on duplicate PlateId.

    Parameters
    ----------
    dict_a : dict
        First plate-keyed dict (e.g. ``{"PLT1": {"PlatformSpecific": "1.02"}}``).
    dict_b : dict
        Second plate-keyed dict.
    field_name : str, optional
        Field name used in the error message when a duplicate is found.

    Returns
    -------
    dict
        Merged dict containing all PlateId keys from both inputs.

    Raises
    ------
    ValueError
        If the same PlateId key appears in both ``dict_a`` and ``dict_b``.

    Examples
    --------
    >>> merge_plate_json({'PLT1': '1.02'}, {'PLT2': '0.98'})
    {'PLT1': '1.02', 'PLT2': '0.98'}
    >>> merge_plate_json({'PLT1': '1.02'}, {'PLT1': '0.98'})
    Traceback (most recent call last):
        ...
    ValueError: Duplicate PlateId 'PLT1' in field ...
    """
    duplicates = set(dict_a) & set(dict_b)
    if duplicates:
        dup_list = ', '.join(repr(k) for k in sorted(duplicates))
        field_info = f' for field {field_name!r}' if field_name else ''
        raise ValueError(
            f'Duplicate PlateId {dup_list} found when merging plate-keyed JSON'
            f'{field_info}. Each PlateId must appear in only one source ADAT.'
        )
    return {**dict_a, **dict_b}


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


# ---------------------------------------------------------------------------
# Row data conversion helpers (shared by array/row_data and ngs/row_data)
# ---------------------------------------------------------------------------


def try_float(value: str) -> float | None:
    """Return *value* as float, or ``None`` on failure.

    Parameters
    ----------
    value : str
        String value to convert to float.

    Returns
    -------
    float or None
        Float value if conversion succeeds, None otherwise.

    Examples
    --------
    >>> try_float('1.23')
    1.23
    >>> try_float('invalid') is None
    True
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def derive_hyb_norm_status(scale_factor: str) -> str:
    """Return ``'PASS'`` if 0.4 <= float(scale_factor) <= 2.5, else ``'FLAG'``.

    Returns ``''`` for missing / non-numeric values.

    Parameters
    ----------
    scale_factor : str
        HybNormScaleFactor value to check.

    Returns
    -------
    str
        'PASS', 'FLAG', or '' (empty for non-numeric).

    Examples
    --------
    >>> derive_hyb_norm_status('1.0')
    'PASS'
    >>> derive_hyb_norm_status('3.0')
    'FLAG'
    >>> derive_hyb_norm_status('')
    ''
    """
    f = try_float(scale_factor)
    if f is None:
        return ''
    return 'PASS' if 0.4 <= f <= 2.5 else 'FLAG'


def derive_hyb_norm_status_vectorized(scale_factors: list[str]) -> list[str]:
    """Vectorized version of HybNormStatus derivation.

    Returns 'PASS' if 0.4 <= float(value) <= 2.5, else 'FLAG', or '' for non-numeric.

    Parameters
    ----------
    scale_factors : list[str]
        HybNormScaleFactor values for all rows.

    Returns
    -------
    list[str]
        Status values ('PASS', 'FLAG', or '') for each row.

    Examples
    --------
    >>> derive_hyb_norm_status_vectorized(['1.0', '3.0', 'invalid'])
    ['PASS', 'FLAG', '']
    """
    arr = np.array(scale_factors, dtype=object)
    result = np.full(len(arr), '', dtype=object)

    try:
        numeric = pd.to_numeric(arr, errors='coerce')
        valid_mask = ~np.isnan(numeric)

        pass_mask = valid_mask & (numeric >= 0.4) & (numeric <= 2.5)
        flag_mask = valid_mask & ~pass_mask

        result[pass_mask] = 'PASS'
        result[flag_mask] = 'FLAG'
    except Exception:
        return [derive_hyb_norm_status(v) for v in scale_factors]

    return result.tolist()
