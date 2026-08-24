from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from somadata.adat import Adat as AdatClass
from somadata.conversion.utils import compute_file_md5sum
from somadata.conversion.detection import InputType, detect_input_type, diagnose_bridging
from somadata.conversion.errors import (
    UnsupportedCombinationError,
)
from somadata.conversion.pair_conversions import (
    _merge_bridged_array_and_ngs,
    _merge_bridged_array_and_v2,
    _merge_native_arrays,
    _merge_ngs_and_v2,
    _merge_v2_combined_adats,
)
from somadata.conversion.array import ArrayConversionContext
from somadata.conversion.array.col_data import convert_array_col_data
from somadata.conversion.array.header import convert_array_header
from somadata.conversion.array.row_data import convert_array_row_data
from somadata.conversion.array.validation import validate_source_array_adat
from somadata.conversion.ngs import NGSConversionContext
from somadata.conversion.ngs.col_data import convert_ngs_col_data
from somadata.conversion.ngs.header import convert_ngs_header
from somadata.conversion.ngs.row_data import convert_ngs_row_data
from somadata.conversion.ngs.validation import validate_source_ngs_adat
from somadata.conversion.errors import ConversionError
from somadata.conversion.utils import align_row_indexes
from somadata.io.adat.v2_fields import validate_v2_header_fields

import pandas as pd

if TYPE_CHECKING:
    from somadata.adat import Adat

logger = logging.getLogger(__name__)

# NGS-space input types that cannot be combined with native_array.
_NGS_SPACE_TYPES: frozenset[InputType] = frozenset(
    {InputType.NATIVE_NGS, InputType.V2_COMBINED}
)


def to_v2_adat(
    adats: list[str | Adat],
) -> Adat:
    """Convert one or two pre-v2.0 ADATs (or file paths) into a single v2.0 Adat.

    Parameters
    ----------
    adats : list of str or Adat
        One or two items. Each element is either a file-system path to an
        ``.adat`` file or an already-loaded :class:`~somadata.adat.Adat`
        object (mixed allowed).  Paths are read via the existing
        :func:`~somadata.io.adat.file.read_adat` function.

    Returns
    -------
    Adat
        A single v2.0 combined-format Adat.

    Raises
    ------
    ValueError
        If *adats* is empty or contains more than 2 items.
    UnsupportedCombinationError
        If the detected input-type combination does not have an approved
        conversion.

    Examples
    --------
    >>> result = to_v2_adat(['bridged_array.adat', 'ngs_sample.adat'])
    >>> somadata.write_adat(result, 'output_v2.adat')
    """
    if not adats:
        raise ValueError('adats must contain at least one ADAT.')
    if len(adats) > 2:
        raise ValueError(f'to_v2_adat() accepts max 2 inputs. Received: {len(adats)}.')

    loaded = [_load(adat) for adat in adats]

    if len(loaded) == 1:
        adat, md5sum = loaded[0]
        input_type = detect_input_type(adat)

        if input_type is InputType.V2_COMBINED:
            logger.warning('Input already v2.0. Returning as-is.')
            return adat

        handler = _APPROVED_SINGLE_CONVERSIONS.get(input_type)
        if handler is None:
            raise UnsupportedCombinationError(
                f'Unsupported input combination: {input_type.value}.'
            )
        return handler(adat, md5sum=md5sum)

    # Two inputs
    adat_a, md5_a = loaded[0]
    adat_b, md5_b = loaded[1]
    type_a = detect_input_type(adat_a)
    type_b = detect_input_type(adat_b)

    input_types = {type_a, type_b}
    if InputType.NATIVE_ARRAY in input_types and input_types & _NGS_SPACE_TYPES:
        ngs_type = next(t for t in input_types if t in _NGS_SPACE_TYPES)
        array_adat = adat_a if type_a is InputType.NATIVE_ARRAY else adat_b
        diag = diagnose_bridging(array_adat)
        msg = (
            f'Native array data cannot be combined with NGS-space data '
            f'({ngs_type.value}). '
            f'The array input was not detected as bridged.'
        )
        if diag:
            msg += f'\n{diag}'
        raise UnsupportedCombinationError(msg)

    key = (type_a, type_b) if type_a is type_b else frozenset({type_a, type_b})

    handler = _APPROVED_PAIR_CONVERSIONS.get(key)
    if handler is None:
        raise UnsupportedCombinationError(
            f'Unsupported input combination: {type_a.value} + {type_b.value}.'
        )
    return handler(adat_a, adat_b, md5sum_a=md5_a, md5sum_b=md5_b)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(adat: str | Adat) -> tuple[Adat, str | None]:
    """Return an Adat and optional md5sum, reading from disk if a path string was supplied.

    Returns
    -------
    tuple[Adat, str | None]
        The loaded Adat and the md5sum of the source file (if loaded from file).
        Returns None for the md5sum when an in-memory Adat object is passed.
    """
    # Import here to avoid circular dependency
    from somadata.io.adat.file import read_adat

    if isinstance(adat, str):
        md5sum = compute_file_md5sum(adat)
        loaded_adat = read_adat(adat)
        return loaded_adat, md5sum
    if isinstance(adat, AdatClass):
        return adat, None
    raise TypeError(
        f'Each element of adats must be a file path (str) or an Adat object; '
        f'got {type(adat).__name__!r}.'
    )


# ---------------------------------------------------------------------------
# Single-input conversion handlers
# ---------------------------------------------------------------------------


def _convert_bridged_array(adat: Adat, *, md5sum: str | None) -> Adat:
    """Convert a single bridged array ADAT to Array v2.0 format."""
    return _run_array_conversion(adat, md5sum=md5sum)


def _convert_native_array(adat: Adat, *, md5sum: str | None) -> Adat:
    """Convert a single native array ADAT to Array v2.0 format."""
    return _run_array_conversion(adat, md5sum=md5sum)


def _run_array_conversion(
    adat: Adat, *, md5sum: str | None = None, assay_type: str = 'Array'
) -> Adat:
    """Shared array conversion pipeline used by both native and bridged paths.

    Parameters
    ----------
    adat : Adat
        The source array ADAT to convert.
    md5sum : str or None, optional
        MD5 checksum of the source ADAT file, if available.
    assay_type : str, optional
        ``'Array'`` for single-array conversions (default).

    Returns
    -------
    Adat
        A new Adat in v2.0 format with ``AssayType = assay_type``.
    """
    validate_source_array_adat(adat)
    ctx = ArrayConversionContext.from_adat(adat, source_file_md5sum=md5sum)
    new_header = convert_array_header(adat, ctx, assay_type=assay_type)
    new_columns = convert_array_col_data(adat, calibrator_id=ctx.calibrator_id)
    new_index = convert_array_row_data(adat, ctx)
    return _assemble_v2_adat(adat, new_header, new_columns, new_index)


def _assemble_v2_adat(
    source: Adat,
    header: dict,
    columns: pd.MultiIndex,
    index: pd.MultiIndex,
) -> Adat:
    """Construct a v2.0 Adat from converted components.

    Parameters
    ----------
    source : Adat
        The original ADAT; only its RFU matrix values are used.
    header : dict
        The converted v2.0 header_metadata dict.
    columns : pd.MultiIndex
        The converted v2.0 column MultiIndex.
    index : pd.MultiIndex
        The converted v2.0 row MultiIndex.

    Returns
    -------
    Adat
        A new Adat with the converted structure.
    """
    result = AdatClass(
        data=source.values,
        index=index,
        columns=columns,
        header_metadata=header,
    )
    if not validate_v2_header_fields(header):
        raise ConversionError(
            'Converted header metadata is not compliant with the v2.0 closed field set. '
            'See logged warnings above for details.'
        )
    return result


def _convert_native_ngs(adat: Adat, *, md5sum: str | None) -> Adat:
    """Convert a single native NGS ADAT to NGS v2.0 format."""
    return _run_ngs_conversion(adat, md5sum=md5sum)


def _run_ngs_conversion(
    adat: Adat, *, md5sum: str | None = None, assay_type: str = 'NGS'
) -> Adat:
    """Shared NGS conversion pipeline used by single-NGS and merge paths.

    Parameters
    ----------
    adat : Adat
        The source NGS ADAT to convert.
    md5sum : str or None, optional
        MD5 checksum of the source ADAT file, if available.
    assay_type : str, optional
        ``'NGS'`` for single-NGS conversions (default).

    Returns
    -------
    Adat
        A new Adat in v2.0 format with ``AssayType = assay_type``.
    """
    validate_source_ngs_adat(adat)
    ctx = NGSConversionContext.from_adat(adat, source_file_md5sum=md5sum)
    new_header = convert_ngs_header(adat, ctx, assay_type=assay_type)
    new_columns = convert_ngs_col_data(adat, matrix=ctx.matrix)
    new_index = convert_ngs_row_data(adat, ctx)
    return _assemble_v2_adat(adat, new_header, new_columns, new_index)


# ---------------------------------------------------------------------------
# Approved conversion lookup tables
# ---------------------------------------------------------------------------

_APPROVED_PAIR_CONVERSIONS: dict = {
    frozenset(
        {InputType.BRIDGED_ARRAY, InputType.NATIVE_NGS}
    ): _merge_bridged_array_and_ngs,
    frozenset(
        {InputType.BRIDGED_ARRAY, InputType.V2_COMBINED}
    ): _merge_bridged_array_and_v2,
    frozenset({InputType.NATIVE_NGS, InputType.V2_COMBINED}): _merge_ngs_and_v2,
    (InputType.NATIVE_ARRAY, InputType.NATIVE_ARRAY): _merge_native_arrays,
    (InputType.BRIDGED_ARRAY, InputType.BRIDGED_ARRAY): _merge_native_arrays,
    (InputType.V2_COMBINED, InputType.V2_COMBINED): _merge_v2_combined_adats,
}

_APPROVED_SINGLE_CONVERSIONS: dict[InputType, object] = {
    InputType.BRIDGED_ARRAY: _convert_bridged_array,
    InputType.NATIVE_ARRAY: _convert_native_array,
    InputType.NATIVE_NGS: _convert_native_ngs,
}
