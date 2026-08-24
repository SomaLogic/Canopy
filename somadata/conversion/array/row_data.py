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

from somadata.conversion._helpers import (
    derive_hyb_norm_status,
    derive_hyb_norm_status_vectorized,
    generate_guid,
    lookup_header,
    try_float,
)
from somadata.conversion.ngs.row_data import _normalize_dilution_suffix

if TYPE_CHECKING:
    from somadata.adat import Adat
    from somadata.conversion.array import ArrayConversionContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static field renames (legacy → v2.0)
# ---------------------------------------------------------------------------
_ROW_RENAMES: dict[str, str] = {
    'SampleID': 'SampleId',
    'PlatePosition': 'WellPosition',
    'HybControlNormScale': 'HybNormScaleFactor',
    'RowCheck': 'RowCheckStatus',
    'RowCheck_PassFlag': 'RowCheckStatus',
    'MedNormExt_PassFlag': 'MedNormExtStatus',
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
    'HybQC',
    'HybQCStatus',
    'MedNormExtStatus',
    'CrossPlateMedNormIntScaleFactor',
    'InstrumentType',
    'Flowcell',
    'RunYieldDemux',
    'RunYieldQ30Demux',
    'RunQ30WeightedMean',
]

# SampleTypes that should have ControlId populated from SampleId.
_CONTROL_SAMPLE_TYPES: frozenset[str] = frozenset({'QC', 'Buffer', 'Calibrator'})

# SampleTypes eligible for MedNormIntStatus derivation.
_MED_NORM_INT_ELIGIBLE: frozenset[str] = frozenset({'Calibrator', 'Buffer'})

_NORM_SCALE_RE = re.compile(r'^NormScale_')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _derive_med_norm_int_status(
    sample_types: list[str],
    norm_scale_level_names: list[str],
    out_levels: dict[str, list],
) -> list[str]:
    """Vectorized MedNormIntStatus derivation for all rows.

    Only applies to Calibrator and Buffer sample types. All NormScale_* values
    for a row must be numeric and in range [0.4, 2.5] for PASS.

    Parameters
    ----------
    sample_types : list[str]
        SampleType value for each row.
    norm_scale_level_names : list[str]
        Names of all NormScale_* fields present.
    out_levels : dict[str, list]
        The output levels dict containing NormScale_* arrays.

    Returns
    -------
    list[str]
        Status values for each row.
    """
    n_rows = len(sample_types)
    result = [''] * n_rows

    if not norm_scale_level_names:
        return result

    # Build matrix of all NormScale values (rows × norm_scale_fields)
    norm_matrix = []
    for field_name in norm_scale_level_names:
        norm_matrix.append(out_levels[field_name])

    # Process only eligible sample types
    for i in range(n_rows):
        stype = sample_types[i]
        if stype not in _MED_NORM_INT_ELIGIBLE:
            continue

        # Collect all NormScale values for this row
        values = [norm_matrix[j][i] for j in range(len(norm_scale_level_names))]
        if not values:
            continue

        # Try converting all to float
        try:
            floats = [float(v) if v else None for v in values]
        except (ValueError, TypeError):
            continue

        # Check if all are valid and in range
        if all(f is not None for f in floats):
            if all(0.4 <= f <= 2.5 for f in floats):  # type: ignore[operator]
                result[i] = 'PASS'
            else:
                result[i] = 'FLAG'

    return result


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
    # Extract level values once without creating intermediate lists
    level_arrays: dict[str, pd.Index] = {
        name: src_index.get_level_values(name) for name in level_names
    }

    # ------------------------------------------------------------------
    # 1. Apply renames and build working dict of output levels
    # ------------------------------------------------------------------
    out_levels: dict[str, list] = {}
    rma_values: pd.Index | None = None

    for old_name, values in level_arrays.items():
        if old_name in _FIELDS_TO_REMOVE:
            continue
        if old_name == 'RMA':
            # Spec §3.2.3: move RMA value into Project; do not emit as own field
            rma_values = values
            continue
        new_name = _ROW_RENAMES.get(old_name, old_name)
        # Apply dilution suffix normalization (converts e.g. MedNormExt_5e-05_ScaleFactor
        # → MedNormExt_0.00005_ScaleFactor; hyphens replaced, periods preserved)
        new_name = _normalize_dilution_suffix(new_name)
        # Convert to list only once per field
        out_levels[new_name] = list(values)

    # ------------------------------------------------------------------
    # 2. Project field population logic
    #    Priority: StudyId > RMA > Title (header) > blank
    #    For array study samples (SampleType == "Sample"), populate Project:
    #    - Use StudyId values if StudyId field exists (already renamed to Project)
    #    - Otherwise, use RMA values if RMA field was present
    #    - Otherwise, use Title from header for all sample rows
    #    - Otherwise, leave blank
    # ------------------------------------------------------------------
    sample_type_vals = out_levels.get('SampleType', [''] * n_rows)

    # Ensure Project field exists
    if 'Project' not in out_levels:
        out_levels['Project'] = [''] * n_rows

    # Get Title from header once (used for fallback)
    title_from_header = lookup_header(getattr(adat, 'header_metadata', {}), 'Title')

    # Apply fallback logic for study samples
    for i in range(n_rows):
        stype = sample_type_vals[i] if i < len(sample_type_vals) else ''
        # Only apply to study samples
        if stype == 'Sample':
            current_value = out_levels['Project'][i]
            # If Project (from StudyId) is already populated, keep it
            if current_value:
                continue
            # Try RMA fallback
            if rma_values is not None and i < len(rma_values) and rma_values[i]:
                out_levels['Project'][i] = rma_values[i]
                continue
            # Try Title fallback from header
            if title_from_header:
                out_levels['Project'][i] = title_from_header

    # ------------------------------------------------------------------
    # 3. Identify NormScale_* levels (needed for MedNormIntStatus)
    # ------------------------------------------------------------------
    norm_scale_level_names: list[str] = [
        n for n in out_levels if _NORM_SCALE_RE.match(n)
    ]

    # ------------------------------------------------------------------
    # 4. PlateRunDate fallback from ctx.created_date
    # ------------------------------------------------------------------
    if 'PlateRunDate' in out_levels and ctx.created_date:
        out_levels['PlateRunDate'] = [
            v if v else ctx.created_date for v in out_levels['PlateRunDate']
        ]

    # ------------------------------------------------------------------
    # 5. ControlId population for QC/Buffer/Calibrator rows
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
    # 6. HybNormStatus — derived from (renamed) HybNormScaleFactor (VECTORIZED)
    # ------------------------------------------------------------------
    hyb_norm_scale_vals = out_levels.get('HybNormScaleFactor', [''] * n_rows)
    out_levels['HybNormStatus'] = derive_hyb_norm_status_vectorized(hyb_norm_scale_vals)

    # ------------------------------------------------------------------
    # 7. MedNormIntStatus — derived per-row from NormScale_* levels (VECTORIZED)
    # ------------------------------------------------------------------
    out_levels['MedNormIntStatus'] = _derive_med_norm_int_status(
        sample_type_vals, norm_scale_level_names, out_levels
    )

    # ------------------------------------------------------------------
    # 8. New generated fields (one value per row)
    # ------------------------------------------------------------------
    out_levels['SampleReadout'] = ['Array'] * n_rows

    # AssayVersion: spec §3.2.1 — move from header to sample table.
    # Format: "SomaScan <AssayVersion>" (e.g. "SomaScan v5.0").
    raw_assay_version = lookup_header(getattr(adat, 'header_metadata', {}), 'AssayVersion')
    if raw_assay_version:
        assay_version_val = f'SomaScan {raw_assay_version}'
    else:
        assay_version_val = ''
    out_levels['AssayVersion'] = [assay_version_val] * n_rows

    # MasterMixVersion: spec §3.2.1 — move MasterMixLot from header to sample table.
    raw_master_mix = lookup_header(getattr(adat, 'header_metadata', {}), 'MasterMixLot')
    out_levels['MasterMixVersion'] = [raw_master_mix or ''] * n_rows

    # Only generate for missing/blank keys
    if 'UniqueSampleKey' in out_levels:
        # Some keys may already exist; only generate for missing/blank
        existing_keys = out_levels['UniqueSampleKey']
        out_levels['UniqueSampleKey'] = [
            (key if key and str(key).strip() else generate_guid())
            for key in existing_keys
        ]
    else:
        # No existing keys; generate all
        out_levels['UniqueSampleKey'] = [generate_guid() for _ in range(n_rows)]

    out_levels['SourceFileId'] = [ctx.source_file_id] * n_rows
    out_levels['ProcessStepsId'] = [ctx.process_steps_id] * n_rows
    out_levels['ReportConfigId'] = [ctx.report_config_id] * n_rows
    out_levels['SoftwareVersion'] = [ctx.generated_by] * n_rows

    # ------------------------------------------------------------------
    # 9. NGS-only blank fields
    #    MatrixTubeBarcode may have already been populated from Barcode2d
    #    via the _ROW_RENAMES mapping, so only add it if not present.
    # ------------------------------------------------------------------
    for ngs_field in _NGS_ONLY_FIELDS:
        if ngs_field not in out_levels:
            out_levels[ngs_field] = [''] * n_rows

    # ------------------------------------------------------------------
    # 10. Reconstruct MultiIndex
    # ------------------------------------------------------------------
    names = list(out_levels.keys())
    arrays = list(out_levels.values())
    return pd.MultiIndex.from_arrays(arrays, names=names)
