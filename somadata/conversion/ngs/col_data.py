"""NGS v1.x → v2.0 COL_DATA (SOMAmer annotation) field conversion.

Public API
----------
convert_ngs_col_data(adat) -> pd.MultiIndex
    Convert the column MultiIndex of a legacy NGS ADAT to v2.0 field names
    and values.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from somadata.adat import Adat

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static field renames (remove spaces, fix casing)
# ---------------------------------------------------------------------------
_COL_RENAMES: dict[str, str] = {
    'Target Full Name': 'TargetFullName',
    'UniProt ID': 'UniProt',
    'Entrez Gene ID': 'EntrezGeneId',
    'Entrez Gene Symbol': 'EntrezGeneSymbol',
    'BlockList': 'BlockListNGS',
}

# ---------------------------------------------------------------------------
# Fields to drop entirely from the output MultiIndex
# ---------------------------------------------------------------------------
_FIELDS_TO_REMOVE: frozenset[str] = frozenset(
    {
        'SeqIdVersion',
        'SomaId',
        'Units',
        'LoD.Plasma',
        'LoD.Serum',
    }
)

# ---------------------------------------------------------------------------
# Dynamic rename patterns
# ---------------------------------------------------------------------------
_QC_CHECK_RE = re.compile(r'^QCCheck_(.+?)_ScaleFactor$')
_QC_CHECK_PASSFLAG_RE = re.compile(r'^QCCheck_(.+?)_PassFlag$')
_DRC_LEVEL_RE = re.compile(r'^DRC_Level')


def _rename_col_field(name: str) -> str | None:
    """Return the v2.0 name for a legacy NGS COL_DATA field.

    Parameters
    ----------
    name : str
        The legacy level name.

    Returns
    -------
    str or None
        The v2.0 name, or ``None`` if the field should be removed.

    Examples
    --------
    >>> _rename_col_field('Target Full Name')
    'TargetFullName'
    >>> _rename_col_field('DRC_Level')
    'DRCLevelNGS'
    >>> _rename_col_field('DRC_Level.W4')
    'DRCLevelNGS'
    >>> _rename_col_field('QCCheck_PLT123_ScaleFactor')
    'QCRatio_PLT123'
    >>> _rename_col_field('SomaId')
    None
    """
    if name in _FIELDS_TO_REMOVE:
        return None

    # Static renames
    if name in _COL_RENAMES:
        return _COL_RENAMES[name]

    # DRC_Level* → DRCLevelNGS (handles DRC_Level, DRC_Level.W4, etc.)
    if _DRC_LEVEL_RE.match(name):
        return 'DRCLevelNGS'

    # QCCheck_<PlateId>_ScaleFactor → QCRatio_<PlateId>
    m = _QC_CHECK_RE.match(name)
    if m:
        return f'QCRatio_{m.group(1)}'

    # QCCheck_<PlateId>_PassFlag → remove (not in v2.0)
    if _QC_CHECK_PASSFLAG_RE.match(name):
        return None

    # Reference fields: ensure Ref.NGS.* prefix
    if name.startswith('Ref.'):
        return _ensure_ngs_ref_prefix(name)

    # Pass-through fields (SeqId, Target, Type, etc.)
    return name


def _ensure_ngs_ref_prefix(name: str) -> str:
    """Ensure reference fields have the ``Ref.NGS.*`` prefix.

    Parameters
    ----------
    name : str
        A field name starting with ``Ref.``.

    Returns
    -------
    str
        The field name with ``Ref.NGS.*`` prefix enforced.

    Examples
    --------
    >>> _ensure_ngs_ref_prefix('Ref.Bridging.params')
    'Ref.NGS.Bridging.params'
    >>> _ensure_ngs_ref_prefix('Ref.NGS.MedNormExt.Matrix')
    'Ref.NGS.MedNormExt.Matrix'
    >>> _ensure_ngs_ref_prefix('Ref.MedNorm.Id')
    'Ref.MedNorm.Id'
    """
    # If already has Ref.NGS prefix, pass through
    if name.startswith('Ref.NGS.'):
        return name

    # If Ref.MedNorm.*, pass through (shared between Array and NGS)
    if name.startswith('Ref.MedNorm.'):
        return name

    # Otherwise, insert NGS after Ref.
    # e.g., Ref.Bridging.* → Ref.NGS.Bridging.*
    if name.startswith('Ref.'):
        return name.replace('Ref.', 'Ref.NGS.', 1)

    return name


def convert_ngs_col_data(adat: Adat) -> pd.MultiIndex:
    """Convert the column MultiIndex of a legacy NGS ADAT to v2.0 field names.

    Parameters
    ----------
    adat : Adat
        The source NGS ADAT.  Only ``adat.columns`` is read.

    Returns
    -------
    pd.MultiIndex
        A new MultiIndex with v2.0-compliant level names and values.

    Examples
    --------
    >>> new_cols = convert_ngs_col_data(ngs_adat)
    >>> 'TargetFullName' in new_cols.names
    True
    >>> 'DRCLevelNGS' in new_cols.names
    True
    >>> 'SomaId' in new_cols.names
    False
    """
    src_index: pd.MultiIndex = adat.columns

    level_names: list[str] = list(src_index.names)
    level_arrays: list[list] = [
        list(src_index.get_level_values(i)) for i in range(src_index.nlevels)
    ]

    # ------------------------------------------------------------------
    # 1. Build rename map for all level names
    # ------------------------------------------------------------------
    rename_map: dict[str, str | None] = {}
    for name in level_names:
        rename_map[name] = _rename_col_field(name)

    # ------------------------------------------------------------------
    # 2. Build new arrays, filtering out removed fields
    # ------------------------------------------------------------------
    new_names: list[str] = []
    new_arrays: list[list] = []

    for old_name, values in zip(level_names, level_arrays):
        new_name = rename_map[old_name]
        if new_name is None:
            logger.debug(f'Removing NGS COL_DATA field: {old_name}')
            continue  # field removed
        new_names.append(new_name)
        new_arrays.append(values)

    # ------------------------------------------------------------------
    # 3. HybControl level
    #    If the source already has a HybControl field, it has been passed
    #    through in step 2 above (it is not in _FIELDS_TO_REMOVE and is not
    #    renamed).  Only synthesise it when it is absent — deriving from
    #    Type == 'Hybridization Control' as a fallback.
    # ------------------------------------------------------------------
    if 'HybControl' not in new_names:
        if 'Type' in level_names:
            type_idx = level_names.index('Type')
            type_values = level_arrays[type_idx]
            hyb_control_values = [
                'True' if t == 'Hybridization Control' else 'False' for t in type_values
            ]
        else:
            n_cols = len(level_arrays[0]) if level_arrays else 0
            hyb_control_values = ['False'] * n_cols
            logger.warning(
                'COL_DATA conversion: no "Type" or "HybControl" level found; '
                'HybControl defaulted to False.'
            )
        new_names.append('HybControl')
        new_arrays.append(hyb_control_values)

    # ------------------------------------------------------------------
    # 4. Reconstruct MultiIndex
    # ------------------------------------------------------------------
    return pd.MultiIndex.from_arrays(new_arrays, names=new_names)
