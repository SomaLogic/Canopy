"""NGS v1.x → v2.0 ROW_DATA (sample annotation) field conversion.

Public API
----------
convert_ngs_row_data(adat, ctx) -> pd.MultiIndex
    Convert the row MultiIndex of a legacy NGS ADAT to v2.0 field names
    and values.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import pandas as pd

from somadata.conversion._helpers import generate_guid

if TYPE_CHECKING:
    from somadata.adat import Adat
    from somadata.conversion.ngs import NGSConversionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static field renames (legacy → v2.0)
# ---------------------------------------------------------------------------
_ROW_RENAMES: dict[str, str] = {
    'SampleID': 'SampleId',
    'SequencingRunID': 'SequencingRunId',
    'ControlID': 'ControlId',
    'ControlD': 'ControlId',
    'BatchID': 'BatchId',
    'MatrixType': 'KitType',
    'ProbePlate': 'NGSPlateMasterMixLot',
    'HybNorm_1_ScaleFactor': 'HybNormScaleFactor',
    'CrossPlateMedNormInt_ScaleFactor': 'CrossPlateMedNormIntScaleFactor',
    'HybNorm_PassFlag': 'HybNormStatus',
    'MedNormInt_PassFlag': 'MedNormIntStatus',
    'MedNormExt_PassFlag': 'MedNormExtStatus',
    'RowCheck_PassFlag': 'RowCheckStatus',
    'SOMAmerReads_PassFlag': 'SOMAmerReadsStatus',
    'SOMAmerNormReads_PassFlag': 'SOMAmerNormReadsStatus',
    'EmpiricalHybTemp': 'EmpericalHybTemp',
    'EmpiricalHybTemp_PassFlag': 'EmpiricalHybTempStatus',
}

# ---------------------------------------------------------------------------
# Fields to remove from the output MultiIndex
# ---------------------------------------------------------------------------
_FIELDS_TO_REMOVE: frozenset[str] = frozenset(
    {
        'ExtIdentifier',
        'SsfExtId',
        'SampleName',
        'SampleDescription',
        'TimePoint',
        'SampleGroup',
        'SiteId',
        'SampleNotes',
        'AliquotingNotes',
        'AssayNotes',
    }
)

# ---------------------------------------------------------------------------
# Array-only fields that must be present (blank) in NGS-only output
# ---------------------------------------------------------------------------
_ARRAY_ONLY_FIELDS: list[str] = [
    'PlateRunDate',
    'ReportConfigId',
    'SlideId',
    'Subarray',
    'SampleMatrix',
]

# ---------------------------------------------------------------------------
# MedNormInt dilution suffix normalization: replace '-' with '_'
# ---------------------------------------------------------------------------
_MED_NORM_INT_RE = re.compile(r'^(MedNormInt_)(.+?)(_ScaleFactor)$')


def _normalize_dilution_suffix(name: str) -> str:
    """Replace hyphens with underscores in MedNormInt dilution suffixes.

    Parameters
    ----------
    name : str
        A field name, possibly containing a dilution suffix.

    Returns
    -------
    str
        The field name with hyphens replaced by underscores in dilution values.

    Examples
    --------
    >>> _normalize_dilution_suffix('MedNormInt_0-2_ScaleFactor')
    'MedNormInt_0_2_ScaleFactor'
    >>> _normalize_dilution_suffix('MedNormInt_0.005_ScaleFactor')
    'MedNormInt_0_005_ScaleFactor'
    >>> _normalize_dilution_suffix('SampleId')
    'SampleId'
    """
    m = _MED_NORM_INT_RE.match(name)
    if m:
        prefix, dilution, suffix = m.groups()
        # Replace hyphens with underscores, and dots with underscores
        dilution_normalized = dilution.replace('-', '_').replace('.', '_')
        return f'{prefix}{dilution_normalized}{suffix}'
    return name


def _try_float(value: str) -> float | None:
    """Return *value* as float, or ``None`` on failure."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _derive_hyb_norm_status(scale_factor: str) -> str:
    """Return ``'PASS'`` if 0.4 <= float(scale_factor) <= 2.5, else ``'FLAG'``.

    Returns ``''`` for missing / non-numeric values.
    """
    f = _try_float(scale_factor)
    if f is None:
        return ''
    return 'PASS' if 0.4 <= f <= 2.5 else 'FLAG'


def _derive_med_norm_status(scale_factors: list[str]) -> str:
    """Return ``'PASS'`` if all scale factors are in [0.4, 2.5], else ``'FLAG'``.

    Returns ``''`` if all values are blank or non-numeric.
    """
    floats = [_try_float(v) for v in scale_factors if v]
    if not floats:
        return ''
    if any(f is None for f in floats):
        return ''
    return 'PASS' if all(0.4 <= f <= 2.5 for f in floats) else 'FLAG'  # type: ignore[operator]


def convert_ngs_row_data(
    adat: Adat,
    ctx: NGSConversionContext,
) -> pd.MultiIndex:
    """Convert the row MultiIndex of a legacy NGS ADAT to v2.0 field names.

    Parameters
    ----------
    adat : Adat
        The source NGS ADAT.  Only ``adat.index`` is read.
    ctx : NGSConversionContext
        Shared conversion state carrying header-derived values
        (``dpq_version``, ``sequencing_run_id``, ``process_steps_id``, etc.).

    Returns
    -------
    pd.MultiIndex
        A new MultiIndex with v2.0-compliant level names and values, including
        derived fields and blank Array-only placeholders.

    Examples
    --------
    >>> ctx = NGSConversionContext.from_adat(ngs_adat)
    >>> new_index = convert_ngs_row_data(ngs_adat, ctx)
    >>> 'SampleReadout' in new_index.names
    True
    >>> 'UniqueSampleKey' in new_index.names
    True
    """
    src_index: pd.MultiIndex = adat.index
    n_rows = len(src_index)

    level_names: list[str] = list(src_index.names)
    level_arrays: dict[str, list] = {
        name: list(src_index.get_level_values(name)) for name in level_names
    }

    # ------------------------------------------------------------------
    # 1. Apply renames and build working dict of output levels
    # ------------------------------------------------------------------
    out_levels: dict[str, list] = {}

    for old_name, values in level_arrays.items():
        if old_name in _FIELDS_TO_REMOVE:
            continue
        # Apply static renames
        new_name = _ROW_RENAMES.get(old_name, old_name)
        # Apply dilution suffix normalization
        new_name = _normalize_dilution_suffix(new_name)
        out_levels[new_name] = list(values)

    # ------------------------------------------------------------------
    # 2. New generated fields (one value per row)
    # ------------------------------------------------------------------
    out_levels['SampleReadout'] = ['NGS'] * n_rows
    out_levels['UniqueSampleKey'] = [generate_guid() for _ in range(n_rows)]
    out_levels['SourceFileId'] = [ctx.source_file_id] * n_rows
    out_levels['ProcessStepsId'] = [ctx.process_steps_id] * n_rows

    # ------------------------------------------------------------------
    # 3. Header → Sample table moves
    # ------------------------------------------------------------------
    out_levels['SoftwareVersion'] = [ctx.dpq_version] * n_rows

    # SequencingRunId: prefer existing row value, fallback to ctx
    if 'SequencingRunId' not in out_levels:
        out_levels['SequencingRunId'] = [ctx.sequencing_run_id] * n_rows
    else:
        # Fill blanks with ctx value
        out_levels['SequencingRunId'] = [
            v if v else ctx.sequencing_run_id for v in out_levels['SequencingRunId']
        ]

    # InstrumentType, Flowcell, Yield*, Q30*: replicate from header
    out_levels['InstrumentType'] = [ctx.instrument_type] * n_rows
    out_levels['Flowcell'] = [ctx.flowcell] * n_rows
    out_levels['YieldDemux'] = [str(ctx.yield_demux)] * n_rows
    out_levels['YieldQ30Demux'] = [str(ctx.yield_q30_demux)] * n_rows
    out_levels['Q30WeightedMean'] = [str(ctx.q30_weighted_mean)] * n_rows

    # ------------------------------------------------------------------
    # 4. Derive Status fields from PassFlag if not already present
    # ------------------------------------------------------------------
    # HybNormStatus: derive from HybNormScaleFactor if PassFlag not present
    if 'HybNormStatus' not in out_levels and 'HybNormScaleFactor' in out_levels:
        out_levels['HybNormStatus'] = [
            _derive_hyb_norm_status(v) for v in out_levels['HybNormScaleFactor']
        ]

    # MedNormIntStatus: derive from MedNormInt_*_ScaleFactor if not present
    if 'MedNormIntStatus' not in out_levels:
        med_norm_int_fields = [
            name
            for name in out_levels
            if name.startswith('MedNormInt_') and name.endswith('_ScaleFactor')
        ]
        if med_norm_int_fields:
            out_levels['MedNormIntStatus'] = []
            for i in range(n_rows):
                scale_factors = [out_levels[field][i] for field in med_norm_int_fields]
                out_levels['MedNormIntStatus'].append(
                    _derive_med_norm_status(scale_factors)
                )
        else:
            out_levels['MedNormIntStatus'] = [''] * n_rows

    # MedNormExtStatus: derive from MedNormExt_*_ScaleFactor if not present
    if 'MedNormExtStatus' not in out_levels:
        med_norm_ext_fields = [
            name
            for name in out_levels
            if name.startswith('MedNormExt_') and name.endswith('_ScaleFactor')
        ]
        if med_norm_ext_fields:
            out_levels['MedNormExtStatus'] = []
            for i in range(n_rows):
                scale_factors = [out_levels[field][i] for field in med_norm_ext_fields]
                out_levels['MedNormExtStatus'].append(
                    _derive_med_norm_status(scale_factors)
                )
        else:
            out_levels['MedNormExtStatus'] = [''] * n_rows

    # RowCheckStatus: use existing or derive as FLAG if any norm step failed
    if 'RowCheckStatus' not in out_levels:
        out_levels['RowCheckStatus'] = []
        for i in range(n_rows):
            hyb_status = out_levels.get('HybNormStatus', [''])[i]
            int_status = out_levels.get('MedNormIntStatus', [''])[i]
            ext_status = out_levels.get('MedNormExtStatus', [''])[i]
            if any(status == 'FLAG' for status in [hyb_status, int_status, ext_status]):
                out_levels['RowCheckStatus'].append('FLAG')
            else:
                out_levels['RowCheckStatus'].append('PASS')

    # ------------------------------------------------------------------
    # 5. Array-only blank fields
    # ------------------------------------------------------------------
    for array_field in _ARRAY_ONLY_FIELDS:
        if array_field not in out_levels:
            out_levels[array_field] = [''] * n_rows

    # ------------------------------------------------------------------
    # 6. Ensure EmpericalHybTemp exists (blank stub for rows where absent)
    # ------------------------------------------------------------------
    if 'EmpericalHybTemp' not in out_levels:
        out_levels['EmpericalHybTemp'] = [''] * n_rows

    # ------------------------------------------------------------------
    # 7. Reconstruct MultiIndex
    # ------------------------------------------------------------------
    names = list(out_levels.keys())
    arrays = list(out_levels.values())
    return pd.MultiIndex.from_arrays(arrays, names=names)
