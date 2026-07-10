from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from somadata.conversion.detection import InputType, detect_input_type
from somadata.conversion.errors import UnsupportedCombinationError

if TYPE_CHECKING:
    from somadata.adat import Adat

logger = logging.getLogger(__name__)

# NGS-space input types that cannot be combined with native_array.
_NGS_SPACE_TYPES: frozenset[InputType] = frozenset(
    {InputType.NATIVE_NGS, InputType.V2_COMBINED}
)


def to_v2_adat(
    adats: list[str | Adat],
    med_norm_ref: str | None = None,
) -> Adat:
    """Convert one or two pre-v2.0 ADATs (or file paths) into a single v2.0 Adat.

    Parameters
    ----------
    adats : list of str or Adat
        One or two items. Each element is either a file-system path to an
        ``.adat`` file or an already-loaded :class:`~somadata.adat.Adat`
        object (mixed allowed).  Paths are read via the existing
        :func:`~somadata.io.adat.file.read_adat` function.
    med_norm_ref : str or None, optional
        MedNorm reference identifier used to resolve a mismatch between
        ``Ref.MedNormExt`` vectors when merging two sources. When
        ``None`` (default) both sources must carry identical reference
        vectors.

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
        raise ValueError(
            f'to_v2_adat() accepts max 2 inputs. Received: {len(adats)}.'
        )

    loaded = [_load(adat) for adat in adats]
    
    if len(loaded) == 1:
        input_type = detect_input_type(loaded[0])

        if input_type is InputType.V2_COMBINED:
            logger.warning('Input already v2.0. Returning as-is.')
            return loaded[0]

        handler = _APPROVED_SINGLE_CONVERSIONS.get(input_type)
        if handler is None:
            raise UnsupportedCombinationError(
                f'Unsupported input combination: {input_type.value}.'
            )
        return handler(loaded[0], med_norm_ref=med_norm_ref)

    # Two inputs
    type_a = detect_input_type(loaded[0])
    type_b = detect_input_type(loaded[1])

    # native_array cannot be combined with any NGS-space input; the array
    # must be bridged first.
    input_types = {type_a, type_b}
    if InputType.NATIVE_ARRAY in input_types and input_types & _NGS_SPACE_TYPES:
        ngs_type = next(t for t in input_types if t in _NGS_SPACE_TYPES)
        raise UnsupportedCombinationError(
            f'Native array data cannot be combined with NGS-space data. '
            f'Array must be bridged first. Input: {ngs_type.value}.'
        )

    # Same-type pairs use a canonical tuple key; mixed-type pairs use a frozenset.
    key = (type_a, type_b) if type_a is type_b else frozenset({type_a, type_b})

    handler = _APPROVED_PAIR_CONVERSIONS.get(key)
    if handler is None:
        raise UnsupportedCombinationError(
            f'Unsupported input combination: {type_a.value} + {type_b.value}.'
        )
    return handler(loaded[0], loaded[1], med_norm_ref=med_norm_ref)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load(adat: str | Adat) -> Adat:
    """Return an Adat, reading from disk if a path string was supplied."""
    from somadata.adat import Adat as AdatClass
    from somadata.io.adat.file import read_adat

    if isinstance(adat, str):
        return read_adat(adat)
    if isinstance(adat, AdatClass):
        return adat
    raise TypeError(
        f'Each element of adats must be a file path (str) or an Adat object; '
        f'got {type(adat).__name__!r}.'
    )


# ---------------------------------------------------------------------------
# Conversion handlers
#
# Each handler will be fully implemented in later tickets.
# Raising NotImplementedError signals that routing is wired up but the
# conversion logic itself is pending.
# ---------------------------------------------------------------------------


def _merge_bridged_array_and_ngs(
    adat_a: Adat, adat_b: Adat, *, med_norm_ref: str | None
) -> Adat:
    """Merge a bridged array ADAT and a native NGS ADAT into a Mixed v2.0 output."""
    raise NotImplementedError(
        'Merging bridged_array + native_ngs is not yet implemented.'
    )


def _merge_bridged_array_and_v2(
    adat_a: Adat, adat_b: Adat, *, med_norm_ref: str | None
) -> Adat:
    """Merge a bridged array ADAT and an existing v2.0 ADAT into a Mixed v2.0 output."""
    raise NotImplementedError(
        'Merging bridged_array + v2_combined is not yet implemented.'
    )


def _merge_ngs_and_v2(
    adat_a: Adat, adat_b: Adat, *, med_norm_ref: str | None
) -> Adat:
    """Merge a native NGS ADAT and an existing v2.0 ADAT into a Mixed or NGS v2.0 output."""
    raise NotImplementedError(
        'Merging native_ngs + v2_combined is not yet implemented.'
    )


def _merge_native_arrays(
    adat_a: Adat, adat_b: Adat, *, med_norm_ref: str | None
) -> Adat:
    """Merge two native array ADATs into an Array v2.0 output."""
    raise NotImplementedError(
        'Merging native_array + native_array is not yet implemented.'
    )


def _merge_v2_combined_adats(
    adat_a: Adat, adat_b: Adat, *, med_norm_ref: str | None
) -> Adat:
    """Merge two existing v2.0 ADATs into a single v2.0 output."""
    raise NotImplementedError(
        'Merging v2_combined + v2_combined is not yet implemented.'
    )


def _convert_bridged_array(adat: Adat, *, med_norm_ref: str | None) -> Adat:
    """Convert a single bridged array ADAT to Array v2.0 format."""
    raise NotImplementedError(
        'Converting bridged_array to v2.0 is not yet implemented.'
    )


def _convert_native_array(adat: Adat, *, med_norm_ref: str | None) -> Adat:
    """Convert a single native array ADAT to Array v2.0 format."""
    raise NotImplementedError(
        'Converting native_array to v2.0 is not yet implemented.'
    )


def _convert_native_ngs(adat: Adat, *, med_norm_ref: str | None) -> Adat:
    """Convert a single native NGS ADAT to NGS v2.0 format."""
    raise NotImplementedError(
        'Converting native_ngs to v2.0 is not yet implemented.'
    )


# ---------------------------------------------------------------------------
# Approved conversion lookup tables
#
# Defined after the handler functions so they can reference the callables
# directly. Two-input and single-input conversions are kept in separate
# tables so that same-type pairs (e.g. native_array + native_array) cannot
# collide with single-input entries — frozenset({X, X}) == frozenset({X}).
#
# Two-input keys: frozenset for mixed-type pairs; canonical 2-tuple for
#   same-type pairs.
# Single-input keys: InputType enum member.
# ---------------------------------------------------------------------------

_APPROVED_PAIR_CONVERSIONS: dict = {
    frozenset({InputType.BRIDGED_ARRAY, InputType.NATIVE_NGS}):
        _merge_bridged_array_and_ngs,
    frozenset({InputType.BRIDGED_ARRAY, InputType.V2_COMBINED}):
        _merge_bridged_array_and_v2,
    frozenset({InputType.NATIVE_NGS, InputType.V2_COMBINED}):
        _merge_ngs_and_v2,
    (InputType.NATIVE_ARRAY, InputType.NATIVE_ARRAY):
        _merge_native_arrays,
    (InputType.V2_COMBINED, InputType.V2_COMBINED):
        _merge_v2_combined_adats,
}

_APPROVED_SINGLE_CONVERSIONS: dict[InputType, object] = {
    InputType.BRIDGED_ARRAY: _convert_bridged_array,
    InputType.NATIVE_ARRAY:  _convert_native_array,
    InputType.NATIVE_NGS:    _convert_native_ngs,
}
