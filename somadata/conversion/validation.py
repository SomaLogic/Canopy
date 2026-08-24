"""MedNorm and ProcessSteps validation utilities for ADAT v2.0 conversion."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from somadata.adat import Adat

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# MedNorm Validation Utilities
# ---------------------------------------------------------------------------


class MedNormValidator:
    """Utilities for validating MedNorm compatibility between ADATs."""

    @staticmethod
    def get_mednorm_ext_vectors(adat: Adat) -> dict[str, dict[str, str]]:
        """Extract Ref.MedNormExt.* column values keyed by (field, SeqId).

        Parameters
        ----------
        adat : Adat
            Source ADAT.

        Returns
        -------
        dict
            ``{field_name: {seq_id: value}}`` for all ``Ref.MedNormExt.*`` levels.
        """
        columns = getattr(adat, 'columns', None)
        if columns is None or not hasattr(columns, 'names'):
            return {}

        result: dict[str, dict[str, str]] = {}
        seq_id_level = None
        if 'SeqId' in columns.names:
            seq_id_level = columns.get_level_values('SeqId')

        for name in columns.names:
            if name.startswith('Ref.MedNormExt.'):
                values = columns.get_level_values(name)
                if seq_id_level is not None:
                    result[name] = {
                        str(sid): str(val) for sid, val in zip(seq_id_level, values)
                    }
                else:
                    result[name] = {}

        return result

    @staticmethod
    def get_mednorm_id_set(adat: Adat) -> set[str]:
        """Return the set of Ref.MedNorm.Id values present in COL_DATA.

        Parameters
        ----------
        adat : Adat
            Source ADAT.

        Returns
        -------
        set[str]
            Set of Ref.MedNorm.Id values.
        """
        columns = getattr(adat, 'columns', None)
        if columns is None or 'Ref.MedNorm.Id' not in columns.names:
            return set()
        return set(str(v) for v in columns.get_level_values('Ref.MedNorm.Id') if v)

    @staticmethod
    def has_mednorm_ext(header: dict) -> bool:
        """Check if ProcessSteps contains MedNormExt (pre-conversion format).

        Parameters
        ----------
        header : dict
            Pre-conversion header metadata (ProcessSteps is a string).

        Returns
        -------
        bool
            True if ProcessSteps contains 'MedNormExt'.
        """
        raw = lookup_header(header, 'ProcessSteps')
        if not raw:
            return False
        steps = parse_process_steps(raw)
        return 'MedNormExt' in steps

    @staticmethod
    def has_mednorm_ext_v2(header: dict) -> bool:
        """Check if ProcessSteps contains MedNormExt (v2.0 format).

        Parameters
        ----------
        header : dict
            v2.0 header metadata (ProcessSteps is a dict).

        Returns
        -------
        bool
            True if any ProcessSteps entry contains 'MedNormExt'.
        """
        ps = header.get('ProcessSteps')
        if not ps or not isinstance(ps, dict):
            return False
        for steps_str in ps.values():
            if 'MedNormExt' in steps_str:
                return True
        return False

    @staticmethod
    def validate_with_v2(
        raw_adat: Adat,
        v2_adat: Adat,
        med_norm_ref: str | None,
    ) -> Literal['array', 'ngs'] | None:
        """Validate MedNorm compatibility between a pre-conversion and v2.0 ADAT.

        Parameters
        ----------
        raw_adat : Adat
            Pre-conversion ADAT (array or NGS).
        v2_adat : Adat
            v2.0 ADAT.
        med_norm_ref : str or None
            MedNorm reference override identifier.

        Returns
        -------
        Literal['array', 'ngs'] or None
            Which source's Ref.MedNormExt values to use, or None if identical.

        Raises
        ------
        MedNormMismatchError
            If Ref.MedNormExt vectors are incompatible.
        """
        from somadata.conversion.detection import InputType, detect_input_type
        from somadata.conversion.errors import MedNormMismatchError

        raw_vecs = MedNormValidator.get_mednorm_ext_vectors(raw_adat)
        v2_vecs = MedNormValidator.get_mednorm_ext_vectors(v2_adat)

        shared_fields = set(raw_vecs) & set(v2_vecs)
        if not shared_fields:
            return None

        raw_cols = getattr(raw_adat, 'columns', None)
        v2_cols = getattr(v2_adat, 'columns', None)
        if raw_cols is None or v2_cols is None:
            return None

        if 'SeqId' in raw_cols.names and 'SeqId' in v2_cols.names:
            raw_seqids = set(raw_cols.get_level_values('SeqId'))
            v2_seqids = set(v2_cols.get_level_values('SeqId'))
            shared_seqids = raw_seqids & v2_seqids
        else:
            return None

        if not shared_seqids:
            return None

        mismatches: list[str] = []
        for field in sorted(shared_fields):
            for seq_id in sorted(shared_seqids):
                raw_val_str = raw_vecs[field].get(seq_id, '')
                v2_val_str = v2_vecs[field].get(seq_id, '')

                # Skip if either value is missing/NA sentinel
                def _is_missing(v: str) -> bool:
                    return not v or v.upper() in ('NA', 'NAN', 'NONE', '')

                if _is_missing(raw_val_str) or _is_missing(v2_val_str):
                    continue

                try:
                    raw_float = float(raw_val_str)
                    v2_float = float(v2_val_str)
                    if abs(raw_float - v2_float) > 0.1:
                        mismatches.append(
                            f'{field}[{seq_id}]: raw={raw_val_str!r} vs v2={v2_val_str!r} '
                            f'(diff={abs(raw_float - v2_float):.2e})'
                        )
                except (ValueError, TypeError):
                    if raw_val_str != v2_val_str:
                        mismatches.append(
                            f'{field}[{seq_id}]: raw={raw_val_str!r} vs v2={v2_val_str!r}'
                        )

        if not mismatches:
            return None

        if med_norm_ref is not None:
            raw_ids = MedNormValidator.get_mednorm_id_set(raw_adat)
            v2_ids = MedNormValidator.get_mednorm_id_set(v2_adat)

            raw_type = detect_input_type(raw_adat)

            if med_norm_ref in raw_ids:
                source_name = (
                    'array'
                    if raw_type in (InputType.BRIDGED_ARRAY, InputType.NATIVE_ARRAY)
                    else 'ngs'
                )
                logger.info(
                    'Ref.MedNormExt mismatch resolved by med_norm_ref=%r (%s source)',
                    med_norm_ref,
                    source_name,
                )
                return source_name
            if med_norm_ref in v2_ids:
                source_name = (
                    'ngs'
                    if raw_type in (InputType.BRIDGED_ARRAY, InputType.NATIVE_ARRAY)
                    else 'array'
                )
                logger.info(
                    'Ref.MedNormExt mismatch resolved by med_norm_ref=%r (v2 source as %s)',
                    med_norm_ref,
                    source_name,
                )
                return source_name

            raise MedNormMismatchError(
                f'med_norm_ref={med_norm_ref!r} does not match any Ref.MedNorm.Id '
                f'value in either source. '
                f'Raw IDs: {sorted(raw_ids)!r}. v2.0 IDs: {sorted(v2_ids)!r}.'
            )

        detail = '\n  '.join(mismatches[:10])
        if len(mismatches) > 10:
            detail += f'\n  ... and {len(mismatches) - 10} more'
        raise MedNormMismatchError(
            f'Ref.MedNormExt reference vectors are not equivalent for shared SeqIds '
            f'(spec §3.4 requires |a − b| ≤ 0.1 RFU for common non-missing SeqIds). '
            f'Mismatches ({len(mismatches)} total):\n  {detail}\n'
            f'Provide med_norm_ref to override.'
        )

    @staticmethod
    def validate_v2_pair(
        adat_a: Adat,
        adat_b: Adat,
        med_norm_ref: str | None,
    ) -> Literal['array', 'ngs'] | None:
        """Validate MedNorm compatibility between two v2.0 ADATs.

        Parameters
        ----------
        adat_a : Adat
            First v2.0 ADAT.
        adat_b : Adat
            Second v2.0 ADAT.
        med_norm_ref : str or None
            MedNorm reference override identifier.

        Returns
        -------
        Literal['array', 'ngs'] or None
            Which source's Ref.MedNormExt values to use, or None if identical.

        Raises
        ------
        MedNormMismatchError
            If Ref.MedNormExt vectors are incompatible.
        """
        from somadata.conversion.errors import MedNormMismatchError

        vecs_a = MedNormValidator.get_mednorm_ext_vectors(adat_a)
        vecs_b = MedNormValidator.get_mednorm_ext_vectors(adat_b)

        shared_fields = set(vecs_a) & set(vecs_b)
        if not shared_fields:
            return None

        cols_a = getattr(adat_a, 'columns', None)
        cols_b = getattr(adat_b, 'columns', None)
        if cols_a is None or cols_b is None:
            return None

        if 'SeqId' in cols_a.names and 'SeqId' in cols_b.names:
            seqids_a = set(cols_a.get_level_values('SeqId'))
            seqids_b = set(cols_b.get_level_values('SeqId'))
            shared_seqids = seqids_a & seqids_b
        else:
            return None

        if not shared_seqids:
            return None

        mismatches: list[str] = []
        for field in sorted(shared_fields):
            for seq_id in sorted(shared_seqids):
                val_a_str = vecs_a[field].get(seq_id, '')
                val_b_str = vecs_b[field].get(seq_id, '')

                # Skip if either value is missing/NA sentinel
                def _is_missing_v(v: str) -> bool:
                    return not v or v.upper() in ('NA', 'NAN', 'NONE', '')

                if _is_missing_v(val_a_str) or _is_missing_v(val_b_str):
                    continue

                # NGS-only pairs require exact match — use tight float tolerance
                # to absorb float-representation noise while treating any
                # meaningful difference as a true mismatch.
                try:
                    float_a = float(val_a_str)
                    float_b = float(val_b_str)
                    if not math.isclose(float_a, float_b, rel_tol=1e-9, abs_tol=1e-12):
                        mismatches.append(
                            f'{field}[{seq_id}]: source_a={val_a_str!r} vs source_b={val_b_str!r} '
                            f'(diff={abs(float_a - float_b):.2e})'
                        )
                except (ValueError, TypeError):
                    if val_a_str != val_b_str:
                        mismatches.append(
                            f'{field}[{seq_id}]: source_a={val_a_str!r} vs source_b={val_b_str!r}'
                        )

        if not mismatches:
            return None

        if med_norm_ref is not None:
            ids_a = MedNormValidator.get_mednorm_id_set(adat_a)
            ids_b = MedNormValidator.get_mednorm_id_set(adat_b)

            if med_norm_ref in ids_a:
                logger.info(
                    'Ref.MedNormExt mismatch resolved by med_norm_ref=%r (first source)',
                    med_norm_ref,
                )
                return 'array'
            if med_norm_ref in ids_b:
                logger.info(
                    'Ref.MedNormExt mismatch resolved by med_norm_ref=%r (second source)',
                    med_norm_ref,
                )
                return 'ngs'

            raise MedNormMismatchError(
                f'med_norm_ref={med_norm_ref!r} does not match any Ref.MedNorm.Id '
                f'value in either source. '
                f'Source A IDs: {sorted(ids_a)!r}. Source B IDs: {sorted(ids_b)!r}.'
            )

        detail = '\n  '.join(mismatches[:10])
        if len(mismatches) > 10:
            detail += f'\n  ... and {len(mismatches) - 10} more'
        raise MedNormMismatchError(
            f'Ref.MedNormExt reference vectors are not equivalent for shared SeqIds '
            f'(NGS-only merges require near-exact Ref.MedNormExt match across sources; '
            f'float representation noise is tolerated but meaningful differences are not). '
            f'Mismatches ({len(mismatches)} total):\n  {detail}\n'
            f'Provide med_norm_ref to override.'
        )


# ---------------------------------------------------------------------------
# ProcessSteps Validation
# ---------------------------------------------------------------------------


def validate_v2_ngs_process_steps(adat_a: Adat, adat_b: Adat) -> None:
    """Validate that two v2.0 NGS-only ADATs have identical ProcessSteps.

    For NGS-only pairs, both sources must have the same ProcessSteps entries.

    Parameters
    ----------
    adat_a : Adat
        First v2.0 NGS ADAT.
    adat_b : Adat
        Second v2.0 NGS ADAT.

    Raises
    ------
    ProcessStepsMismatchError
        If ProcessSteps are not identical.
    """
    from somadata.conversion.errors import ProcessStepsMismatchError

    ps_a = adat_a.header_metadata.get('ProcessSteps', {})
    ps_b = adat_b.header_metadata.get('ProcessSteps', {})

    if not isinstance(ps_a, dict) or not isinstance(ps_b, dict):
        return

    steps_a = sorted(ps_a.values())
    steps_b = sorted(ps_b.values())

    if steps_a != steps_b:
        raise ProcessStepsMismatchError(
            f'NGS-only v2.0 pair requires identical ProcessSteps. '
            f'Source A has {len(ps_a)} ProcessSteps entries; '
            f'Source B has {len(ps_b)} ProcessSteps entries. '
            f'ProcessSteps values do not match.'
        )
