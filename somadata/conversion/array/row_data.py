"""Array v1.x → v2.0 ROW_DATA (sample annotation) field conversion.

Public API
----------
convert_array_row_data(adat, ctx) -> pd.MultiIndex
    Convert the row MultiIndex of a legacy array ADAT to v2.0 field names
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
    from somadata.conversion.array import ArrayConversionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static field renames (legacy → v2.0)
# ---------------------------------------------------------------------------
_ROW_RENAMES: dict[str, str] = {
    'PlatePosition': 'WellPosition',
    'HybControlNormScale': 'HybNormScaleFactor',
    'RowCheck': 'RowCheckStatus',
    'StudyId': 'Project',
    'SubjectID': 'SubjectId',
    'Barcode2d': 'MatrixTubeBarcode',
}

# ---------------------------------------------------------------------------
# Fields to remove from the output MultiIndex
# ---------------------------------------------------------------------------
_FIELDS_TO_REMOVE: frozenset[str] = frozenset(
    {
        'ExtIdentifier',
        'SsfExtId',
        'ScannerID',
        'Barcode',
        'SampleName',
        'SampleDescription',
        'TimePoint',
        'SampleGroup',
        'SiteId',
        'CLI',
        'PercentDilution',
        'SampleNotes',
        'AliquotingNotes',
        'AssayNotes',
    }
)

# ---------------------------------------------------------------------------
# NGS-only fields that must be present (blank) in array-only output
# ---------------------------------------------------------------------------
_NGS_ONLY_FIELDS: list[str] = [
    'SequencingRunId',
    'InputType',
    'KitType',
    'SOMAmerBeadPlate',
    'NGSPlateMasterMixLot',
    'SOMAmerReads',
    'SOMAmerReadsStatus',
    'SOMAmerNormReads',
    'SOMAmerNormReadsStatus',
    'RefCorr',
    'EmpericalHybTemp',
    'EmpiricalHybTempStatus',
    'MedNormExtStatus',
    'CrossPlateMedNormIntScaleFactor',
    'InstrumentType',
    'Flowcell',
    'YieldDemux',
    'YieldQ30Demux',
    'Q30WeightedMean',
]

# SampleTypes that should have ControlId populated from SampleId.
_CONTROL_SAMPLE_TYPES: frozenset[str] = frozenset({'QC', 'Buffer', 'Calibrator'})

# SampleTypes eligible for MedNormIntStatus derivation.
_MED_NORM_INT_ELIGIBLE: frozenset[str] = frozenset({'Calibrator', 'Buffer'})

_NORM_SCALE_RE = re.compile(r'^NormScale_')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


def _derive_med_norm_int_status(
    sample_type: str,
    norm_scale_values: dict[str, str],
) -> str:
    """Derive MedNormIntStatus for a single sample row.

    Only applies to ``Calibrator`` and ``Buffer`` SampleTypes; blank for all
    others.

    Parameters
    ----------
    sample_type : str
        The sample's ``SampleType`` value.
    norm_scale_values : dict[str, str]
        Mapping of ``NormScale_<DilutionGroup>`` level name → raw value for
        this sample.

    Returns
    -------
    str
        ``'PASS'``, ``'FLAG'``, or ``''``.
    """
    if sample_type not in _MED_NORM_INT_ELIGIBLE:
        return ''
    if not norm_scale_values:
        return ''
    floats = [_try_float(v) for v in norm_scale_values.values()]
    if any(f is None for f in floats):
        return ''
    return (
        'PASS'
        if all(0.4 <= f <= 2.5 for f in floats)  # type: ignore[operator]
        else 'FLAG'
    )


# ---------------------------------------------------------------------------
# Main conversion function
# ---------------------------------------------------------------------------


def convert_array_row_data(
    adat: Adat,
    ctx: ArrayConversionContext,
) -> pd.MultiIndex:
    """Convert the row MultiIndex of a legacy array ADAT to v2.0 field names.

    Parameters
    ----------
    adat : Adat
        The source array ADAT.  Only ``adat.index`` is read.
    ctx : ArrayConversionContext
        Shared conversion state carrying header-derived values
        (``generated_by``, ``created_date``, ``process_steps_id``, etc.).

    Returns
    -------
    pd.MultiIndex
        A new MultiIndex with v2.0-compliant level names and values, including
        derived fields and blank NGS-only placeholders.
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
        new_name = _ROW_RENAMES.get(old_name, old_name)
        out_levels[new_name] = list(values)

    # ------------------------------------------------------------------
    # 2. Identify NormScale_* levels (needed for MedNormIntStatus)
    # ------------------------------------------------------------------
    norm_scale_level_names: list[str] = [
        n for n in out_levels if _NORM_SCALE_RE.match(n)
    ]

    # ------------------------------------------------------------------
    # 3. PlateRunDate fallback from ctx.created_date
    # ------------------------------------------------------------------
    if 'PlateRunDate' in out_levels and ctx.created_date:
        out_levels['PlateRunDate'] = [
            v if v else ctx.created_date for v in out_levels['PlateRunDate']
        ]

    # ------------------------------------------------------------------
    # 4. ControlId population for QC/Buffer/Calibrator rows
    # ------------------------------------------------------------------
    sample_type_vals = out_levels.get('SampleType', [''] * n_rows)
    sample_id_vals = out_levels.get('SampleId', [''] * n_rows)

    if 'ControlId' not in out_levels:
        out_levels['ControlId'] = ['' for _ in range(n_rows)]

    out_levels['ControlId'] = [
        sid if stype in _CONTROL_SAMPLE_TYPES else out_levels['ControlId'][i]
        for i, (stype, sid) in enumerate(zip(sample_type_vals, sample_id_vals))
    ]

    # ------------------------------------------------------------------
    # 5. HybNormStatus — derived from (renamed) HybNormScaleFactor
    # ------------------------------------------------------------------
    hyb_norm_scale_vals = out_levels.get('HybNormScaleFactor', [''] * n_rows)
    out_levels['HybNormStatus'] = [
        _derive_hyb_norm_status(v) for v in hyb_norm_scale_vals
    ]

    # ------------------------------------------------------------------
    # 6. MedNormIntStatus — derived per-row from NormScale_* levels
    # ------------------------------------------------------------------
    out_levels['MedNormIntStatus'] = []
    for i in range(n_rows):
        stype = sample_type_vals[i] if i < len(sample_type_vals) else ''
        norm_vals = {ns: out_levels[ns][i] for ns in norm_scale_level_names}
        out_levels['MedNormIntStatus'].append(
            _derive_med_norm_int_status(stype, norm_vals)
        )

    # ------------------------------------------------------------------
    # 7. New generated fields (one value per row)
    # ------------------------------------------------------------------
    out_levels['SampleReadout'] = ['Array'] * n_rows
    out_levels['UniqueSampleKey'] = [generate_guid() for _ in range(n_rows)]
    out_levels['SourceFileId'] = [ctx.source_file_id] * n_rows
    out_levels['ProcessStepsId'] = [ctx.process_steps_id] * n_rows
    out_levels['ReportConfigId'] = [ctx.report_config_id] * n_rows
    out_levels['SoftwareVersion'] = [ctx.generated_by] * n_rows

    # ------------------------------------------------------------------
    # 8. NGS-only blank fields
    #    Only add if not already present (MatrixTubeBarcode may have come
    #    from the renamed Barcode2d).
    # ------------------------------------------------------------------
    for ngs_field in _NGS_ONLY_FIELDS:
        if ngs_field not in out_levels:
            out_levels[ngs_field] = [''] * n_rows

    # ------------------------------------------------------------------
    # 9. Reconstruct MultiIndex
    # ------------------------------------------------------------------
    names = list(out_levels.keys())
    arrays = list(out_levels.values())
    return pd.MultiIndex.from_arrays(arrays, names=names)
