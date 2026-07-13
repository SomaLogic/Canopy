"""Unit tests for somadata.conversion.converter (Task 3: Conversion Path Router).

Covers:
- to_v2_adat() input validation (empty list, >2 inputs, bad types)
- Single v2_combined input warning
- Routing to the correct path handler for each approved combination
- Rejection of unlisted combinations (UnsupportedCombinationError)
- Special rejection of native_array + NGS-space inputs
- somadata.to_v2_adat() public surface accessible from top-level package
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import somadata.conversion.converter as converter_module
from somadata.conversion.converter import (
    _APPROVED_PAIR_CONVERSIONS,
    _APPROVED_SINGLE_CONVERSIONS,
    _load,
    to_v2_adat,
)
from somadata.conversion.detection import InputType
from somadata.conversion.errors import UnsupportedCombinationError
from tests.conversion.conftest import (
    make_bridged_array_adat,
    make_native_array_adat,
    make_ngs_adat,
    make_v2_combined_adat,
)

# ---------------------------------------------------------------------------
# _load() helper
# ---------------------------------------------------------------------------


class TestLoad:
    def test_returns_adat_unchanged(self):
        adat = make_native_array_adat()
        assert _load(adat) is adat

    def test_raises_type_error_on_bad_type(self):
        with pytest.raises(TypeError, match='file path.*or an Adat object'):
            _load(12345)  # type: ignore[arg-type]

    def test_raises_type_error_on_none(self):
        with pytest.raises(TypeError):
            _load(None)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Input validation: empty list and >2 inputs
# ---------------------------------------------------------------------------


class TestInputValidation:
    def test_empty_list_raises_value_error(self):
        with pytest.raises(ValueError, match='at least one ADAT'):
            to_v2_adat([])

    def test_three_inputs_raises_value_error(self):
        a = make_ngs_adat()
        with pytest.raises(ValueError, match='max 2 inputs.*Received: 3'):
            to_v2_adat([a, a, a])

    def test_four_inputs_raises_value_error(self):
        a = make_ngs_adat()
        with pytest.raises(ValueError, match='max 2 inputs.*Received: 4'):
            to_v2_adat([a, a, a, a])


# ---------------------------------------------------------------------------
# Single v2_combined input — warning, return as-is
# ---------------------------------------------------------------------------


class TestSingleV2CombinedInput:
    def test_returns_same_adat_object(self):
        adat = make_v2_combined_adat()
        result = to_v2_adat([adat])
        assert result is adat

    def test_emits_log_warning(self, caplog):
        import logging

        adat = make_v2_combined_adat()
        with caplog.at_level(logging.WARNING, logger='somadata.conversion.converter'):
            to_v2_adat([adat])
        assert 'already v2.0' in caplog.text

    def test_med_norm_ref_ignored_for_v2_combined_passthrough(self):
        adat = make_v2_combined_adat()
        result = to_v2_adat([adat], med_norm_ref='some-ref')
        assert result is adat


# ---------------------------------------------------------------------------
# Single-input routing
# ---------------------------------------------------------------------------


class TestSingleInputRouting:
    def test_bridged_array_routes_to_convert_bridged_array(self):
        adat = make_bridged_array_adat()
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(
            converter_module._APPROVED_SINGLE_CONVERSIONS,
            {InputType.BRIDGED_ARRAY: mock},
        ):
            to_v2_adat([adat])
        mock.assert_called_once_with(adat, med_norm_ref=None)

    def test_native_array_routes_to_convert_native_array(self):
        adat = make_native_array_adat()
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(
            converter_module._APPROVED_SINGLE_CONVERSIONS,
            {InputType.NATIVE_ARRAY: mock},
        ):
            to_v2_adat([adat])
        mock.assert_called_once_with(adat, med_norm_ref=None)

    def test_native_ngs_routes_to_convert_native_ngs(self):
        adat = make_ngs_adat()
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(
            converter_module._APPROVED_SINGLE_CONVERSIONS,
            {InputType.NATIVE_NGS: mock},
        ):
            to_v2_adat([adat])
        mock.assert_called_once_with(adat, med_norm_ref=None)


# ---------------------------------------------------------------------------
# Two-input routing
# ---------------------------------------------------------------------------


class TestTwoInputRouting:
    def test_bridged_array_plus_native_ngs_routes_to_merge(self):
        ba, ngs = make_bridged_array_adat(), make_ngs_adat()
        key = frozenset({InputType.BRIDGED_ARRAY, InputType.NATIVE_NGS})
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(converter_module._APPROVED_PAIR_CONVERSIONS, {key: mock}):
            to_v2_adat([ba, ngs])
        mock.assert_called_once_with(ba, ngs, med_norm_ref=None)

    def test_native_ngs_plus_bridged_array_routes_to_merge_order_independent(self):
        """Input order must not affect conversion selection."""
        ngs, ba = make_ngs_adat(), make_bridged_array_adat()
        key = frozenset({InputType.BRIDGED_ARRAY, InputType.NATIVE_NGS})
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(converter_module._APPROVED_PAIR_CONVERSIONS, {key: mock}):
            to_v2_adat([ngs, ba])
        mock.assert_called_once_with(ngs, ba, med_norm_ref=None)

    def test_bridged_array_plus_v2_combined_routes_to_merge(self):
        ba, v2 = make_bridged_array_adat(), make_v2_combined_adat()
        key = frozenset({InputType.BRIDGED_ARRAY, InputType.V2_COMBINED})
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(converter_module._APPROVED_PAIR_CONVERSIONS, {key: mock}):
            to_v2_adat([ba, v2])
        mock.assert_called_once_with(ba, v2, med_norm_ref=None)

    def test_v2_combined_plus_bridged_array_routes_to_merge_order_independent(self):
        v2, ba = make_v2_combined_adat(), make_bridged_array_adat()
        key = frozenset({InputType.BRIDGED_ARRAY, InputType.V2_COMBINED})
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(converter_module._APPROVED_PAIR_CONVERSIONS, {key: mock}):
            to_v2_adat([v2, ba])
        mock.assert_called_once_with(v2, ba, med_norm_ref=None)

    def test_native_ngs_plus_v2_combined_routes_to_merge(self):
        ngs, v2 = make_ngs_adat(), make_v2_combined_adat()
        key = frozenset({InputType.NATIVE_NGS, InputType.V2_COMBINED})
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(converter_module._APPROVED_PAIR_CONVERSIONS, {key: mock}):
            to_v2_adat([ngs, v2])
        mock.assert_called_once_with(ngs, v2, med_norm_ref=None)

    def test_v2_combined_plus_native_ngs_routes_to_merge_order_independent(self):
        v2, ngs = make_v2_combined_adat(), make_ngs_adat()
        key = frozenset({InputType.NATIVE_NGS, InputType.V2_COMBINED})
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(converter_module._APPROVED_PAIR_CONVERSIONS, {key: mock}):
            to_v2_adat([v2, ngs])
        mock.assert_called_once_with(v2, ngs, med_norm_ref=None)

    def test_native_array_plus_native_array_routes_to_merge(self):
        na1, na2 = make_native_array_adat(), make_native_array_adat()
        key = (InputType.NATIVE_ARRAY, InputType.NATIVE_ARRAY)
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(converter_module._APPROVED_PAIR_CONVERSIONS, {key: mock}):
            to_v2_adat([na1, na2])
        mock.assert_called_once_with(na1, na2, med_norm_ref=None)

    def test_v2_combined_plus_v2_combined_routes_to_merge(self):
        # Two v2_combined inputs — no single-input short-circuit; should merge.
        v2a, v2b = make_v2_combined_adat(), make_v2_combined_adat()
        key = (InputType.V2_COMBINED, InputType.V2_COMBINED)
        mock = MagicMock(return_value=MagicMock())
        with patch.dict(converter_module._APPROVED_PAIR_CONVERSIONS, {key: mock}):
            to_v2_adat([v2a, v2b])
        mock.assert_called_once_with(v2a, v2b, med_norm_ref=None)


# ---------------------------------------------------------------------------
# Rejected combinations (Section 5.1)
# ---------------------------------------------------------------------------


class TestUnsupportedCombinations:
    def test_native_array_plus_native_ngs_rejected(self):
        with pytest.raises(UnsupportedCombinationError, match='bridged first'):
            to_v2_adat([make_native_array_adat(), make_ngs_adat()])

    def test_native_ngs_plus_native_array_rejected_order_independent(self):
        with pytest.raises(UnsupportedCombinationError, match='bridged first'):
            to_v2_adat([make_ngs_adat(), make_native_array_adat()])

    def test_native_array_plus_v2_combined_rejected(self):
        """native_array + v2_combined is not an approved path."""
        with pytest.raises(UnsupportedCombinationError, match='bridged first'):
            to_v2_adat([make_native_array_adat(), make_v2_combined_adat()])

    def test_v2_combined_plus_native_array_rejected_order_independent(self):
        with pytest.raises(UnsupportedCombinationError, match='bridged first'):
            to_v2_adat([make_v2_combined_adat(), make_native_array_adat()])

    def test_bridged_array_plus_bridged_array_rejected(self):
        """bridged_array + bridged_array is not an approved path."""
        with pytest.raises(
            UnsupportedCombinationError, match='Unsupported input combination'
        ):
            to_v2_adat([make_bridged_array_adat(), make_bridged_array_adat()])

    def test_native_ngs_plus_native_ngs_rejected(self):
        """native_ngs + native_ngs is not an approved path."""
        with pytest.raises(
            UnsupportedCombinationError, match='Unsupported input combination'
        ):
            to_v2_adat([make_ngs_adat(), make_ngs_adat()])


# ---------------------------------------------------------------------------
# Approved paths table sanity check
# ---------------------------------------------------------------------------


class TestApprovedPathsTable:
    def test_pair_table_contains_five_conversions(self):
        assert len(_APPROVED_PAIR_CONVERSIONS) == 5

    def test_single_table_contains_three_conversions(self):
        assert len(_APPROVED_SINGLE_CONVERSIONS) == 3

    def test_all_handlers_are_callable(self):
        all_handlers = list(_APPROVED_PAIR_CONVERSIONS.values()) + list(
            _APPROVED_SINGLE_CONVERSIONS.values()
        )
        for handler in all_handlers:
            assert callable(handler), f'{handler!r} is not callable'

    def test_handler_names_are_descriptive(self):
        """No handler should still use a numeric path ID in its name."""
        import re

        all_handlers = list(_APPROVED_PAIR_CONVERSIONS.values()) + list(
            _APPROVED_SINGLE_CONVERSIONS.values()
        )
        for handler in all_handlers:
            assert not re.search(
                r'_path_\d+$', handler.__name__
            ), f'Handler {handler.__name__!r} still uses a numeric path ID suffix'


# ---------------------------------------------------------------------------
# Public surface: somadata.to_v2_adat
# ---------------------------------------------------------------------------


class TestPublicSurface:
    def test_accessible_from_somadata_package(self):
        import somadata

        assert hasattr(somadata, 'to_v2_adat')
        assert somadata.to_v2_adat is to_v2_adat

    def test_accessible_from_somadata_conversion(self):
        import somadata.conversion

        assert hasattr(somadata.conversion, 'to_v2_adat')
        assert somadata.conversion.to_v2_adat is to_v2_adat
