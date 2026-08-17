"""NGS v1.x → v2.0 header field conversion.

Public API
----------
convert_ngs_header(adat, ctx, assay_type='NGS') -> dict
    Convert a legacy NGS header_metadata dict to a v2.0-compliant dict.
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from typing import TYPE_CHECKING

from somadata.conversion._helpers import (
    _coerce_numeric,
    _compute_adat_md5sum,
    generate_guid,
    lookup_header,
    parse_process_steps,
    strip_bang_prefix,
)
from somadata.io.adat.v2_fields import V2_HEADER_FIELD_TYPES

if TYPE_CHECKING:
    from somadata.adat import Adat
    from somadata.conversion.ngs import NGSConversionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fields that copy straight across (canonical name, no bang).
# ---------------------------------------------------------------------------
_PASS_THROUGH_FIELDS = (
    'Title',
    'SOMAmerReferenceSource',
    'StudyOrganism',
    'StudyMatrix',
    'UseRestriction',
)

# ---------------------------------------------------------------------------
# AssayVersion mapping for NGS platforms
# ---------------------------------------------------------------------------
_NGS_ASSAY_VERSION_MAP = {
    '6k': 'SomaSeq v1',
    '9k TMS': 'SomaSeq v2',
    '9k xTMS': 'SomaSeq v3',
    'Calypso': 'SomaSeq v4',
    # Alternative forms seen in production ADATs
    'Illumina Protein Prep 9k': 'SomaSeq v2',
    'IPP 9k': 'SomaSeq v2',
}


def convert_ngs_header(
    adat: Adat,
    ctx: NGSConversionContext,
    *,
    assay_type: str = 'NGS',
) -> dict:
    """Convert NGS v1.x ``header_metadata`` to a v2.0-compliant header dict.

    Parameters
    ----------
    adat : Adat
        The source NGS ADAT.  Only ``adat.header_metadata`` is read.
    ctx : NGSConversionContext
        Shared conversion state extracted from the source ADAT.
    assay_type : str, optional
        ``'NGS'`` for single-NGS conversions (default); callers that are
        merging two sources pass ``'Mixed'``.

    Returns
    -------
    dict
        A new dict whose keys are exactly those of
        :data:`~somadata.io.adat.v2_fields.V2_HEADER_FIELD_TYPES`.

    Examples
    --------
    >>> ctx = NGSConversionContext.from_adat(ngs_adat)
    >>> new_hdr = convert_ngs_header(ngs_adat, ctx)
    >>> new_hdr['FileVersion']
    '2.0'
    >>> new_hdr['AssayType']
    'NGS'
    """
    hdr = getattr(adat, 'header_metadata', {})

    # Initialise every v2.0 field to '' (guarantees closed key set).
    out: dict = {key: '' for key in V2_HEADER_FIELD_TYPES}

    # ------------------------------------------------------------------
    # 1. Static / generated fields
    # ------------------------------------------------------------------
    out['FileVersion'] = '2.0'
    out['AssayType'] = assay_type
    out['FileCreatedDate'] = datetime.datetime.now(datetime.timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%SZ'
    )
    out['AdatId'] = generate_guid()

    # ------------------------------------------------------------------
    # 2. Pass-through fields — optional in spec; keep conditional
    # ------------------------------------------------------------------
    for field in _PASS_THROUGH_FIELDS:
        val = lookup_header(hdr, field)
        if val:
            out[field] = val

    # UseRestriction is required (Value Required = True in spec §2.3).
    # Fall back to the canonical default when the source ADAT lacks it.
    if not out.get('UseRestriction'):
        out['UseRestriction'] = 'Research Use Only'

    # ------------------------------------------------------------------
    # 3. SourceFile JSON  {"1": {"AdatId": "<old>"}} or {"1": {"md5sum": "<hash>"}}
    #    Priority: AdatId > file checksum > in-memory checksum (prefixed "mem.")
    # ------------------------------------------------------------------
    old_adat_id = ctx.source_adat_id or lookup_header(hdr, 'AdatId')
    if old_adat_id:
        out['SourceFile'] = {ctx.source_file_id: {'AdatId': old_adat_id}}
    elif ctx.source_file_md5sum:
        out['SourceFile'] = {ctx.source_file_id: {'md5sum': ctx.source_file_md5sum}}
    else:
        mem_md5 = f'mem.{_compute_adat_md5sum(adat)}'
        out['SourceFile'] = {ctx.source_file_id: {'md5sum': mem_md5}}

    # ------------------------------------------------------------------
    # 4. ProcessSteps  →  {"1": ["step1", "step2", ...]}
    #    Required (True); convert from comma-separated to JSON.
    # ------------------------------------------------------------------
    out['ProcessSteps'] = {ctx.process_steps_id: parse_process_steps(ctx.process_steps)}

    # ------------------------------------------------------------------
    # 5. ReportConfig  →  blank for NGS (uses separate YAML file)
    # ------------------------------------------------------------------
    out['ReportConfig'] = ''

    # ------------------------------------------------------------------
    # 7. NGS-specific JSON consolidations
    # ------------------------------------------------------------------

    # PlateScaleScalar: {"PlateId": {"PlatformSpecific": val, "CrossPlatform": val}}
    plate_scale = _consolidate_dual_platform_fields(
        hdr,
        'PlatformSpecificPlateScale_ScaleFactor',
        'CrossPlatformPlateScale_ScaleFactor',
        ctx.plate_ids,
    )
    if plate_scale:
        out['PlateScaleScalar'] = plate_scale

    # CalibrateTailPercent: dual-platform JSON
    cal_tail_pct = _consolidate_dual_platform_fields(
        hdr,
        'PlatformSpecificCalibrateTailPercent',
        'CrossPlatformCalibrateTailPercent',
        ctx.plate_ids,
    )
    if cal_tail_pct:
        out['CalibrateTailPercent'] = cal_tail_pct

    # CalibrateTailPercentStatus: dual-platform JSON
    cal_tail_status = _consolidate_dual_platform_fields(
        hdr,
        'PlatformSpecificCalibrateTailPercent_PassFlag',
        'CrossPlatformCalibrateTailPercent_PassFlag',
        ctx.plate_ids,
    )
    if cal_tail_status:
        out['CalibrateTailPercentStatus'] = cal_tail_status

    # QCCheckTailPercent: plate-keyed JSON.
    # The bare 'QCCheckTailPercent' key holds a whole-dict value in NGS ADATs.
    # Per-plate suffix style ('QCCheckTailPercent_<PlateId>') is also handled.
    qc_tail_pct = _extract_whole_dict_or_per_plate(
        hdr,
        bare_key='QCCheckTailPercent',
        per_plate_pattern=r'^QCCheckTailPercent[_\-](?!.*PassFlag)(.+)$',
    )
    if qc_tail_pct:
        out['QCCheckTailPercent'] = qc_tail_pct

    # QCCheckTailPercentStatus: plate-keyed JSON.
    qc_tail_status = _extract_whole_dict_or_per_plate(
        hdr,
        bare_key='QCCheckTailPercent_PassFlag',
        per_plate_pattern=r'^QCCheckTailPercent[_\-](.+)_PassFlag$',
    )
    if qc_tail_status:
        out['QCCheckTailPercentStatus'] = qc_tail_status

    # PlateSOMAmerNormReadsStatus: plate-keyed JSON
    plate_reads_status = _extract_whole_dict_or_per_plate(
        hdr,
        bare_key='PlateSOMAmerNormReads_PassFlag',
        per_plate_pattern=r'^PlateSOMAmerNormReads[_\-](.+)_PassFlag$',
    )
    if plate_reads_status:
        out['PlateSOMAmerNormReadsStatus'] = plate_reads_status

    # ------------------------------------------------------------------
    # 8. Array-only fields — blank for NGS-only output
    # ------------------------------------------------------------------
    # PlateScaleStatus, etc. handled by the generic v2.0 dict init above.

    return out


def _parse_python_dict_value(raw: str) -> dict:
    """Safely parse a Python-repr dict string into a dict.

    The NGS ADAT header stores some JSON-like values as Python ``repr``
    strings (single-quoted keys/values).  This handles both valid JSON and
    Python-repr format by falling back to ``ast.literal_eval``.

    Parameters
    ----------
    raw : str
        The raw header value string.

    Returns
    -------
    dict
        The parsed dict, or an empty dict on parse failure.
    """
    import ast
    import json

    if not raw or not raw.strip().startswith('{'):
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        pass
    try:
        result = ast.literal_eval(raw)
        if isinstance(result, dict):
            return result
    except (ValueError, SyntaxError):
        pass
    return {}


def _extract_whole_dict_or_per_plate(
    header: dict,
    bare_key: str,
    per_plate_pattern: str,
) -> dict:
    """Extract plate-keyed values from either a whole-dict header value or per-plate keys.

    Some NGS ADAT headers store a single key whose value is a Python-repr dict
    (e.g. ``QCCheckTailPercent → "{'TS00000001': 1.855}"``).  Others use
    per-plate suffixed keys.  This helper tries the bare-key approach first,
    then falls back to the per-plate regex pattern.

    Parameters
    ----------
    header : dict
        The ADAT header_metadata dictionary.
    bare_key : str
        The canonical key name (no ``!`` prefix) that may hold a whole-dict value.
    per_plate_pattern : str
        Regex pattern with a capture group for PlateId, used as a fallback.

    Returns
    -------
    dict
        Flat dict: ``{"PlateId": value}`` where numeric strings are stored as
        their numeric type (float/int) for correct JSON serialisation.
    """
    # Try bare key first
    for candidate in (bare_key, f'!{bare_key}'):
        raw_val = header.get(candidate, '')
        if raw_val:
            # If the raw value is already a dict (parsed from JSON by the reader),
            # return it directly with numeric coercion applied to values.
            if isinstance(raw_val, dict):
                return {str(k): _coerce_numeric(v) for k, v in raw_val.items()}
            parsed = _parse_python_dict_value(str(raw_val))
            if parsed:
                return {str(k): _coerce_numeric(v) for k, v in parsed.items()}
            # Non-dict bare value — no PlateId key available; fall back to per-plate scan
            break

    # Fall back to per-plate suffix pattern
    return _extract_plate_keyed_json(header, per_plate_pattern)


def _consolidate_dual_platform_fields(
    header: dict,
    platform_prefix: str,
    cross_prefix: str,
    plate_ids: list[str],
) -> dict:
    """Consolidate PlatformSpecific + CrossPlatform fields into nested JSON.

    Parameters
    ----------
    header : dict
        The ADAT header_metadata dictionary.
    platform_prefix : str
        Prefix for platform-specific fields (without PlateId suffix).
    cross_prefix : str
        Prefix for cross-platform fields (without PlateId suffix).
    plate_ids : list[str]
        List of PlateId values to search for.

    Returns
    -------
    dict
        Nested dict: ``{"PlateId": {"PlatformSpecific": val1, "CrossPlatform": val2}}``,
        or empty dict if no matching fields found.

    Examples
    --------
    >>> hdr = {
    ...     'PlatformSpecificPlateScale_ScaleFactor_PLT1': '1.02',
    ...     'CrossPlatformPlateScale_ScaleFactor_PLT1': '0.98',
    ... }
    >>> _consolidate_dual_platform_fields(
    ...     hdr,
    ...     'PlatformSpecificPlateScale_ScaleFactor',
    ...     'CrossPlatformPlateScale_ScaleFactor',
    ...     ['PLT1'],
    ... )
    {'PLT1': {'PlatformSpecific': 1.02, 'CrossPlatform': 0.98}}
    """
    result = {}

    # Try multiple suffix patterns: _PlateId and -PlateId
    for plate_id in plate_ids:
        platform_val = None
        cross_val = None

        # Try underscore suffix
        platform_key = f'{platform_prefix}_{plate_id}'
        cross_key = f'{cross_prefix}_{plate_id}'
        platform_val = lookup_header(header, platform_key)
        cross_val = lookup_header(header, cross_key)

        # Try hyphen suffix if underscore not found
        if not platform_val:
            platform_key = f'{platform_prefix}-{plate_id}'
            platform_val = lookup_header(header, platform_key)
        if not cross_val:
            cross_key = f'{cross_prefix}-{plate_id}'
            cross_val = lookup_header(header, cross_key)

        # Build nested dict if either value found
        if platform_val or cross_val:
            result[plate_id] = {}
            if platform_val:
                result[plate_id]['PlatformSpecific'] = _coerce_numeric(platform_val)
            if cross_val:
                result[plate_id]['CrossPlatform'] = _coerce_numeric(cross_val)

    if result:
        return result

    # Fallback: the NGS ADAT may store these as whole-dict values keyed by the
    # bare prefix (without per-plate suffix).  Parse PlatformSpecific and
    # CrossPlatform dicts and merge them per plate.
    platform_raw = lookup_header(header, platform_prefix)
    cross_raw = lookup_header(header, cross_prefix)
    platform_dict = _parse_python_dict_value(platform_raw)
    cross_dict = _parse_python_dict_value(cross_raw)
    all_plate_ids = set(platform_dict) | set(cross_dict)
    for pid in sorted(all_plate_ids):
        result[str(pid)] = {}
        if pid in platform_dict:
            result[str(pid)]['PlatformSpecific'] = _coerce_numeric(platform_dict[pid])
        if pid in cross_dict:
            result[str(pid)]['CrossPlatform'] = _coerce_numeric(cross_dict[pid])

    return result


def _extract_plate_keyed_json(header: dict, pattern: str) -> dict:
    """Extract plate-keyed fields matching a regex pattern into a JSON dict.

    Parameters
    ----------
    header : dict
        The ADAT header_metadata dictionary.
    pattern : str
        Regex pattern with a capture group for PlateId.

    Returns
    -------
    dict
        Flat dict: ``{"PlateId": value}`` where numeric strings are stored as
        their numeric type (float/int) for correct JSON serialisation.

    Examples
    --------
    >>> hdr = {'QCCheckTailPercent_PLT1': '0.95', '!QCCheckTailPercent-PLT2': '0.92'}
    >>> _extract_plate_keyed_json(hdr, r'^QCCheckTailPercent[_\\-](.+)$')
    {'PLT1': 0.95, 'PLT2': 0.92}
    """
    result = {}
    regex = re.compile(pattern)

    for raw_key, value in header.items():
        clean_key = strip_bang_prefix(raw_key)
        match = regex.match(clean_key)
        if not match:
            continue

        plate_id = match.group(1)
        # Remove trailing '_PassFlag' from PlateId if present
        plate_id = plate_id.replace('_PassFlag', '').replace('-PassFlag', '')
        if not plate_id or not value:
            continue

        # The matched *value* may itself be a Python-repr/JSON dict string
        # (NGS ADATs store whole-dict values on bare keys like
        # 'QCCheckTailPercent' → "{'TS00000001': 1.855}").
        if isinstance(value, dict):
            for inner_plate, inner_val in value.items():
                result[str(inner_plate)] = _coerce_numeric(inner_val)
        else:
            parsed = _parse_python_dict_value(str(value))
            if parsed:
                # Expand the inner dict into per-plate entries
                for inner_plate, inner_val in parsed.items():
                    result[str(inner_plate)] = _coerce_numeric(inner_val)
            else:
                result[plate_id] = _coerce_numeric(value)

    return result
