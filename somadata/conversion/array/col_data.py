"""Array v1.x → v2.0 COL_DATA (SOMAmer annotation) field conversion.

Public API
----------
convert_array_col_data(adat) -> pd.MultiIndex
    Convert the column MultiIndex of a legacy array ADAT to v2.0 field names
    and values.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import TYPE_CHECKING

import pandas as pd

from somadata.conversion.errors import ConversionError

if TYPE_CHECKING:
    from somadata.adat import Adat

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static field renames
# ---------------------------------------------------------------------------
_COL_RENAMES: dict[str, str] = {
    'EntrezGeneID': 'EntrezGeneId',
}

# ---------------------------------------------------------------------------
# Fields to drop entirely from the output MultiIndex
# ---------------------------------------------------------------------------
_FIELDS_TO_REMOVE: frozenset[str] = frozenset(
    {'SeqIdVersion', 'SomaId', 'ColCheck', 'Units', 'eLOD'}
)

# ---------------------------------------------------------------------------
# Dynamic rename patterns
# ---------------------------------------------------------------------------
_CAL_PLATE_RE = re.compile(r'^Cal_(.+)$')
_CAL_QC_RATIO_RE = re.compile(r'^CalQcRatio_(.+)_([^_]+)$')
_PLATE_SCALE_REF_RE = re.compile(r'^PlateScale_Reference$')
_CAL_REFERENCE_RE = re.compile(r'^CalReference$')
_QC_REFERENCE_RE = re.compile(r'^QcReference_(.+)$')
_MED_NORM_RFU_RE = re.compile(r'^medNorm(?:Ref|SMP)_ReferenceRFU$')
_QC_CHECK_SCALE_RE = re.compile(r'^QCCheck_(.+?)_ScaleFactor$')
_QC_CHECK_PASSFLAG_RE = re.compile(r'^QCCheck_(.+?)_PassFlag$')


def _rename_col_field(
    name: str,
    calibrator_id: str = '',
) -> str | None:
    """Return the v2.0 name for a legacy COL_DATA field.

    Parameters
    ----------
    name : str
        The legacy level name.
    calibrator_id : str
        The calibrator identifier used when renaming ``PlateScale_Reference``
        and ``CalReference``.  May be empty if not known.

    Returns
    -------
    str or None
        The v2.0 name, or ``None`` if the field should be removed.
    """
    if name in _FIELDS_TO_REMOVE:
        return None

    # Static renames
    if name in _COL_RENAMES:
        return _COL_RENAMES[name]

    # Cal_<PlateId> → PlatformSpecificCalibrate_<PlateId>_ScaleFactor
    m = _CAL_PLATE_RE.match(name)
    if m:
        return f'PlatformSpecificCalibrate_{m.group(1)}_ScaleFactor'

    # PlateScale_Reference → Ref.Array.PlateScale_<CalibratorId>
    if _PLATE_SCALE_REF_RE.match(name):
        suffix = f'_{calibrator_id}' if calibrator_id else ''
        return f'Ref.Array.PlateScale{suffix}'

    # CalReference → Ref.Array.Calibrate_<CalibratorId>
    if _CAL_REFERENCE_RE.match(name):
        suffix = f'_{calibrator_id}' if calibrator_id else ''
        return f'Ref.Array.Calibrate{suffix}'

    # QcReference_<QCSampleId> → Ref.Array.QCRatio_<QCSampleId>
    m = _QC_REFERENCE_RE.match(name)
    if m:
        return f'Ref.Array.QCRatio_{m.group(1)}'

    # QCCheck_<PlateId>_ScaleFactor → QCRatio_<PlateId>
    # (bridged array ADATs may carry NGS-style QCCheck columns)
    m = _QC_CHECK_SCALE_RE.match(name)
    if m:
        return f'QCRatio_{m.group(1)}'

    # QCCheck_<PlateId>_PassFlag → remove
    if _QC_CHECK_PASSFLAG_RE.match(name):
        return None

    # medNormRef_ReferenceRFU or medNormSMP_ReferenceRFU → Ref.MedNorm.Id
    if _MED_NORM_RFU_RE.match(name):
        return 'Ref.MedNorm.Id'

    # Other Ref.* fields from the array source that need Ref.NGS.* prefix:
    # per spec §3.2.2, ONLY Ref.QCCheck.* and Ref.MedNormExt.* are renamed
    # to Ref.NGS.*.  All other Ref.* fields (Ref.MedBg.*, Ref.StdDevBg.*,
    # Ref.Bridging.*, etc.) pass through unchanged (§3.4 undefined fields
    # pass through; §3.2.2 Ref.Bridging.* is explicitly kept as-is).
    if name.startswith('Ref.'):
        if name.startswith('Ref.NGS.') or name.startswith('Ref.MedNorm.'):
            return name
        if name.startswith('Ref.QCCheck.') or name.startswith('Ref.MedNormExt.'):
            return name.replace('Ref.', 'Ref.NGS.', 1)
        # All other Ref.* fields (Ref.Bridging.*, Ref.MedBg.*, etc.) pass through.
        return name

    return name  # pass through unchanged


def _resolve_cal_qc_ratio_renames(
    level_names: list[str],
) -> dict[str, str]:
    """Build rename map for all ``CalQcRatio_*`` fields.

    Validates that each PlateId has at most one QCSampleId.  Raises
    :class:`~somadata.conversion.errors.ConversionError` if a plate has
    multiple QC IDs (ambiguous rename).

    Parameters
    ----------
    level_names : list[str]
        All column-level names from the source MultiIndex.

    Returns
    -------
    dict[str, str]
        Mapping from legacy name → v2.0 name for every ``CalQcRatio_*`` field.

    Raises
    ------
    ConversionError
        If any PlateId maps to more than one QCSampleId.
    """
    plate_to_qc_ids: dict[str, set[str]] = defaultdict(set)
    matches: list[tuple[str, str, str]] = []

    for name in level_names:
        m = _CAL_QC_RATIO_RE.match(name)
        if m:
            plate_id, qc_id = m.group(1), m.group(2)
            plate_to_qc_ids[plate_id].add(qc_id)
            matches.append((name, plate_id, qc_id))

    conflicts = {
        plate: qc_ids for plate, qc_ids in plate_to_qc_ids.items() if len(qc_ids) > 1
    }
    if conflicts:
        details = '; '.join(
            f'{plate}: {sorted(qc_ids)}' for plate, qc_ids in sorted(conflicts.items())
        )
        raise ConversionError(
            f'Multiple QCSampleIds found for the same PlateId in CalQcRatio '
            f'fields — cannot unambiguously rename to QCRatio_<PlateId>. '
            f'Conflicts: {details}. '
            f'Specify the intended QC sample ID explicitly.'
        )

    return {name: f'QCRatio_{plate_id}' for name, plate_id, _ in matches}


def convert_array_col_data(
    adat: Adat,
    calibrator_id: str = '',
) -> pd.MultiIndex:
    """Convert the column MultiIndex of a legacy array ADAT to v2.0 field names.

    Parameters
    ----------
    adat : Adat
        The source array ADAT.  Only ``adat.columns`` is read.
    calibrator_id : str, optional
        Calibrator identifier appended to ``Ref.Array.PlateScale_*`` and
        ``Ref.Array.Calibrate_*`` level names.  Defaults to ``''``.

    Returns
    -------
    pd.MultiIndex
        A new MultiIndex with v2.0-compliant level names and values, including
        the derived ``HybControl`` level.

    Raises
    ------
    ConversionError
        If any plate has multiple QCSampleIds across ``CalQcRatio_*`` fields.
    """
    src_index: pd.MultiIndex = adat.columns

    level_names: list[str] = list(src_index.names)
    level_arrays: list[list] = [
        list(src_index.get_level_values(i)) for i in range(src_index.nlevels)
    ]

    # ------------------------------------------------------------------
    # 1. Resolve CalQcRatio → QCRatio renames (validated separately)
    # ------------------------------------------------------------------
    cal_qc_renames = _resolve_cal_qc_ratio_renames(level_names)

    # ------------------------------------------------------------------
    # 2. Build rename map for all level names
    # ------------------------------------------------------------------
    rename_map: dict[str, str | None] = {}
    for name in level_names:
        if name in cal_qc_renames:
            rename_map[name] = cal_qc_renames[name]
        else:
            rename_map[name] = _rename_col_field(name, calibrator_id=calibrator_id)

    # ------------------------------------------------------------------
    # 3. Build new arrays, filtering out removed fields and deduplicating.
    #    When two legacy fields map to the same v2.0 name (e.g. a stray
    #    QCCheck_*_ScaleFactor alongside a CalQcRatio_*-derived QCRatio_*),
    #    the first occurrence wins.
    # ------------------------------------------------------------------
    new_names: list[str] = []
    new_arrays: list[list] = []
    seen_output_names: set[str] = set()

    for old_name, values in zip(level_names, level_arrays):
        new_name = rename_map[old_name]
        if new_name is None:
            continue  # field removed
        if new_name in seen_output_names:
            logger.warning(
                'Array COL_DATA: duplicate output field %r (from legacy field %r); '
                'skipping duplicate.',
                new_name,
                old_name,
            )
            continue
        seen_output_names.add(new_name)

        # Per spec §3.2.2: array Dilution values are percentages (e.g. 20, 0.5,
        # 0.005) and must be divided by 100 to produce the NGS-convention
        # fractions used in v2.0 (e.g. 0.2, 0.005, 0.00005).
        if new_name == 'Dilution':
            converted: list = []
            for v in values:
                try:
                    converted.append(str(float(v) / 100))
                except (TypeError, ValueError):
                    converted.append(v)
            values = converted

        new_names.append(new_name)
        new_arrays.append(values)

    # ------------------------------------------------------------------
    # 3b. Normalise missing-value sentinels for String-typed fields.
    #     Array COL_DATA may contain "nan" (pandas NaN→str), "N/A", or
    #     "NA" in string fields.  v2.0 spec mandates empty strings for
    #     missing String values.
    # ------------------------------------------------------------------
    from somadata.io.adat.v2_fields import FieldType as _FieldType
    from somadata.io.adat.v2_fields import v2_col_field_type as _v2_col_type
    _NA_SENTINELS = frozenset({'n/a', 'na', 'nan'})
    for i, (name, values) in enumerate(zip(new_names, new_arrays)):
        if _v2_col_type(name) is _FieldType.STRING:
            new_arrays[i] = [
                '' if (isinstance(v, str) and v.strip().lower() in _NA_SENTINELS)
                else v
                for v in values
            ]

    # ------------------------------------------------------------------
    # 4. Derive HybControl level
    #    Value = 'True' where Type == 'Hybridization Control', else 'False'.
    # ------------------------------------------------------------------
    if 'Type' in level_names:
        type_idx = level_names.index('Type')
        type_values = level_arrays[type_idx]
        hyb_control_values = [
            'True' if t == 'Hybridization Control' else 'False' for t in type_values
        ]
    else:
        # If Type level absent, default all to 'False'.
        n_cols = len(level_arrays[0]) if level_arrays else 0
        hyb_control_values = ['False'] * n_cols
        logger.warning(
            'COL_DATA conversion: no "Type" level found; HybControl defaulted to False.'
        )

    new_names.append('HybControl')
    new_arrays.append(hyb_control_values)

    # ------------------------------------------------------------------
    # 5. Reconstruct MultiIndex
    # ------------------------------------------------------------------
    return pd.MultiIndex.from_arrays(new_arrays, names=new_names)
