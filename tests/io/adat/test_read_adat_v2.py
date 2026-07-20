"""Tests for the v2.0 ADAT reader (Tasks 4.1 and 4.2).

Task 4.1 — v2.0-aware reader dispatch:
  - read_adat correctly parses v2.0 files (no ``!`` prefix on Name/Type rows)
  - JSON header values parsed as dicts/lists, not raw strings
  - Round-trip: write_adat(v2.0) → read_adat → structure preserved

Task 4.2 — v2.0 field type validation on read:
  - Integer fields: non-integer values log a warning
  - Decimal fields: non-numeric values log a warning
  - Date fields: non-ISO-8601 values log a warning
  - JSON fields: invalid JSON logs a warning (COL_DATA context)
  - String fields: values >1024 chars log a warning
  - Missing values (empty string, "NA", "N/A") are silently accepted for all types
  - Clean v2.0 files produce no type-violation log warnings
"""

from __future__ import annotations

import io
import logging

import pandas as pd
import pytest

from somadata.adat import Adat
from somadata.io.adat.file import read_adat, write_adat

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_v2_adat(
    header: dict | None = None,
    row_names: list[str] | None = None,
    row_values: list[list] | None = None,
    col_levels: dict[str, list] | None = None,
) -> Adat:
    """Build a minimal, spec-compliant v2.0 Adat for reader/roundtrip tests."""
    default_header = {
        'FileVersion': '2.0',
        'AdatId': 'GID-test-reader-001',
        'AssayType': 'Array',
        'AssayVersion': 'v5.0',
        'UseRestriction': 'Research Use Only',
        'SourceFile': '',
        'SOMAmerReferenceSource': '2025-04-10',
        'FileCreatedDate': '2026-01-31',
        'Title': 'Reader Test',
        'StudyOrganism': 'Human',
        'StudyMatrix': 'Plasma',
        'ProcessSteps': {'1': ['Raw RFU', 'Hyb Normalization']},
        'ReportConfig': '',
        'PlateScaleScalar': '',
        'CalibrateTailPercent': '',
        'CalibrateTailPercentStatus': '',
        'QCCheckTailPercent': '',
        'QCCheckTailPercentStatus': '',
        'PlateScaleStatus': '',
        'PlateSOMAmerNormReadsStatus': '',
    }
    if header:
        default_header.update(header)

    row_names = row_names or ['SampleId', 'SampleType', 'PlateId']
    row_values = row_values or [
        ['S1', 'S2'],
        ['Sample', 'Sample'],
        ['PLT001', 'PLT001'],
    ]

    if col_levels is not None:
        arrays = [col_levels[n] for n in col_levels]
        col_index = pd.MultiIndex.from_arrays(arrays, names=list(col_levels.keys()))
    else:
        col_index = pd.MultiIndex.from_arrays(
            [['10000-01', '10001-02']], names=['SeqId']
        )

    index = pd.MultiIndex.from_arrays(row_values, names=row_names)
    n_samples = len(row_values[0])
    n_analytes = len(col_index)
    data = [[1000.0] * n_analytes for _ in range(n_samples)]
    return Adat(
        data=data, index=index, columns=col_index, header_metadata=default_header
    )


def _roundtrip(adat: Adat) -> Adat:
    """Write then read back an Adat."""
    buf = io.StringIO()
    write_adat(adat, buf)
    buf.seek(0)
    return read_adat(buf)


# ---------------------------------------------------------------------------
# Task 4.1: v2.0-aware reader dispatch
# ---------------------------------------------------------------------------


class TestV2ReaderDispatch:
    def test_fileversion_parsed_as_string(self):
        """FileVersion header value must survive roundtrip as a plain string."""
        adat = _make_minimal_v2_adat()
        rt = _roundtrip(adat)
        assert rt.header_metadata.get('FileVersion') == '2.0'

    def test_header_preserved_on_roundtrip(self):
        adat = _make_minimal_v2_adat(header={'AssayType': 'NGS'})
        rt = _roundtrip(adat)
        assert rt.header_metadata.get('AssayType') == 'NGS'

    def test_json_header_dict_preserved(self):
        """JSON-typed header fields round-trip as dicts (not raw strings)."""
        ps = {'1': ['Raw RFU', 'Hyb Normalization']}
        adat = _make_minimal_v2_adat(header={'ProcessSteps': ps})
        rt = _roundtrip(adat)
        assert rt.header_metadata.get('ProcessSteps') == ps

    def test_json_header_dict_with_nested_values(self):
        scalar = {'PLT001': {'PlatformSpecific': 1.04}}
        adat = _make_minimal_v2_adat(header={'PlateScaleScalar': scalar})
        rt = _roundtrip(adat)
        assert rt.header_metadata.get('PlateScaleScalar') == scalar

    def test_rfu_shape_preserved(self):
        adat = _make_minimal_v2_adat()
        rt = _roundtrip(adat)
        assert rt.shape == adat.shape

    def test_rfu_values_preserved(self):
        adat = _make_minimal_v2_adat()
        rt = _roundtrip(adat)
        assert list(rt.values[0]) == list(adat.values[0])

    def test_column_names_preserved(self):
        adat = _make_minimal_v2_adat()
        rt = _roundtrip(adat)
        assert list(rt.columns.names) == list(adat.columns.names)

    def test_row_names_preserved(self):
        adat = _make_minimal_v2_adat()
        rt = _roundtrip(adat)
        assert list(rt.index.names) == list(adat.index.names)

    def test_seqid_values_preserved(self):
        adat = _make_minimal_v2_adat()
        rt = _roundtrip(adat)
        assert list(rt.columns.get_level_values('SeqId')) == list(
            adat.columns.get_level_values('SeqId')
        )

    def test_row_metadata_values_preserved(self):
        adat = _make_minimal_v2_adat()
        rt = _roundtrip(adat)
        assert list(rt.index.get_level_values('SampleId')) == list(
            adat.index.get_level_values('SampleId')
        )

    def test_multi_level_col_metadata_preserved(self):
        """Multiple COL_DATA levels survive write→read."""
        adat = _make_minimal_v2_adat(
            col_levels={
                'SeqId': ['10000-01', '10001-02'],
                'Target': ['ProteinA', 'ProteinB'],
                'EntrezGeneId': ['8514', '3479'],
            }
        )
        rt = _roundtrip(adat)
        assert list(rt.columns.names) == ['SeqId', 'Target', 'EntrezGeneId']
        assert list(rt.columns.get_level_values('Target')) == ['ProteinA', 'ProteinB']

    def test_no_bang_prefix_in_col_data_on_write(self):
        """v2.0 writer must not emit ``!Name`` / ``!Type`` in ^COL_DATA."""
        buf = io.StringIO()
        write_adat(_make_minimal_v2_adat(), buf)
        content = buf.getvalue()
        assert '!Name' not in content
        assert '!Type' not in content

    def test_no_checksum_line_on_write(self):
        buf = io.StringIO()
        write_adat(_make_minimal_v2_adat(), buf)
        assert '!Checksum' not in buf.getvalue()

    def test_read_v2_from_file_path(self, tmp_path):
        """read_adat accepts a file path string and handles v2.0 content."""
        adat = _make_minimal_v2_adat()
        path = tmp_path / 'test_v2.adat'
        with open(path, 'w') as f:
            write_adat(adat, f)
        rt = read_adat(str(path))
        assert rt.header_metadata.get('FileVersion') == '2.0'
        assert rt.shape == adat.shape

    def test_missing_rfu_values_handled(self):
        """Non-numeric RFU values (e.g., 'NA') raise ValueError on read."""
        adat = _make_minimal_v2_adat()
        buf = io.StringIO()
        write_adat(adat, buf)
        content = buf.getvalue()
        # Replace one RFU value with a non-numeric sentinel (simulates missing data)
        content = content.replace('1000.0\t1000.0', 'NA\t1000.0', 1)
        with pytest.raises(ValueError):
            # Attempting to parse a non-numeric RFU value raises ValueError
            read_adat(io.StringIO(content))

    def test_all_header_fields_round_trip(self):
        """Every field in the closed v2.0 header set survives a round-trip."""
        adat = _make_minimal_v2_adat(
            header={
                'Title': 'Full Round-trip Test',
                'StudyMatrix': 'CSF',
                'StudyOrganism': 'Mouse',
                'SOMAmerReferenceSource': '2025-01-01',
                'AssayVersion': 'v4.1',
                'UseRestriction': 'RUO',
            }
        )
        rt = _roundtrip(adat)
        for key in adat.header_metadata:
            assert (
                key in rt.header_metadata
            ), f'Missing header key after roundtrip: {key}'


# ---------------------------------------------------------------------------
# Task 4.2: v2.0 field type validation on read
# ---------------------------------------------------------------------------


class TestV2TypeValidationInteger:
    def test_non_integer_float_warns(self, caplog):
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'Subarray'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['3.5', '3'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        messages = [r.message for r in caplog.records]
        assert any('Subarray' in m and 'Integer' in m for m in messages)

    def test_non_numeric_integer_warns(self, caplog):
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'Subarray'],
            row_values=[
                ['S1'],
                ['Sample'],
                ['PLT001'],
                ['not_an_int'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        messages = [r.message for r in caplog.records]
        assert any('Subarray' in m and 'Integer' in m for m in messages)

    def test_valid_integer_no_warn(self, caplog):
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'Subarray'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['3', '4'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations

    def test_missing_value_no_warn_for_integer(self, caplog):
        """Empty string and 'NA' in an Integer field must not trigger a warning."""
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'Subarray'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['', 'NA'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations


class TestV2TypeValidationDecimal:
    def test_non_numeric_decimal_warns(self, caplog):
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'HybNormScaleFactor'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['not_a_number', '1.05'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        messages = [r.message for r in caplog.records]
        assert any('HybNormScaleFactor' in m and 'Decimal' in m for m in messages)

    def test_valid_decimal_no_warn(self, caplog):
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'HybNormScaleFactor'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['1.05', '0.98'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations

    def test_missing_decimal_no_warn(self, caplog):
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'HybNormScaleFactor'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['', 'NA'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations

    def test_dynamic_decimal_prefix_warns(self, caplog):
        """Dynamic Decimal fields like NormScale_* also trigger validation."""
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'NormScale_20'],
            row_values=[
                ['S1'],
                ['Sample'],
                ['PLT001'],
                ['BAD'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        messages = [r.message for r in caplog.records]
        assert any('NormScale_20' in m and 'Decimal' in m for m in messages)


class TestV2TypeValidationDate:
    def test_non_iso8601_date_warns(self, caplog):
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'PlateRunDate'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['01/31/2026', '2026-01-31'],  # first is not ISO 8601
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        messages = [r.message for r in caplog.records]
        assert any('PlateRunDate' in m and 'Date' in m for m in messages)

    def test_valid_date_no_warn(self, caplog):
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'PlateRunDate'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['2026-01-31', '2025-12-01'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations

    def test_iso8601_datetime_no_warn(self, caplog):
        """Full ISO 8601 datetime (with T and Z) is also valid."""
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'PlateRunDate'],
            row_values=[
                ['S1'],
                ['Sample'],
                ['PLT001'],
                ['2026-07-15T20:54:06Z'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations

    def test_missing_date_no_warn(self, caplog):
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'PlateRunDate'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['', 'NA'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations


class TestV2TypeValidationString:
    def test_long_string_warns(self, caplog):
        """A string value over 1024 characters in a String field must log a warning."""
        long_value = 'x' * 1025
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId'],
            row_values=[
                [long_value],
                ['Sample'],
                ['PLT001'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        messages = [r.message for r in caplog.records]
        assert any('SampleId' in m and 'String' in m for m in messages)

    def test_exactly_1024_chars_no_warn(self, caplog):
        ok_value = 'y' * 1024
        adat = _make_minimal_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId'],
            row_values=[
                [ok_value],
                ['Sample'],
                ['PLT001'],
            ],
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations


class TestV2TypeValidationColData:
    def test_integer_col_field_non_integer_warns(self, caplog):
        """EntrezGeneId is INTEGER; a float value must log a warning."""
        adat = _make_minimal_v2_adat(
            col_levels={
                'SeqId': ['10000-01'],
                'EntrezGeneId': ['12.5'],  # not a whole number
            }
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        messages = [r.message for r in caplog.records]
        assert any('EntrezGeneId' in m and 'Integer' in m for m in messages)

    def test_decimal_col_field_non_numeric_warns(self, caplog):
        """A Ref.Array.* field is DECIMAL; a non-numeric value must log a warning."""
        adat = _make_minimal_v2_adat(
            col_levels={
                'SeqId': ['10000-01'],
                'Ref.Array.PlateScale_CAL001': ['NOT_A_FLOAT'],
            }
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        messages = [r.message for r in caplog.records]
        assert any(
            'Ref.Array.PlateScale_CAL001' in m and 'Decimal' in m for m in messages
        )

    def test_missing_na_col_field_no_warn(self, caplog):
        """'N/A' in a Decimal COL_DATA field (e.g., Ref.*) must not log a warning."""
        adat = _make_minimal_v2_adat(
            col_levels={
                'SeqId': ['10000-01', '10001-02'],
                'Ref.Array.PlateScale_CAL001': ['N/A', '986.5'],
            }
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations

    def test_valid_integer_col_field_no_warn(self, caplog):
        adat = _make_minimal_v2_adat(
            col_levels={
                'SeqId': ['10000-01'],
                'EntrezGeneId': ['8514'],
            }
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations


class TestV2TypeValidationNonV2:
    def test_no_validation_on_pre_v2_adat(self, caplog):
        """Type validation must not run for pre-v2.0 ADATs."""
        index = pd.MultiIndex.from_arrays(
            [['S1'], ['not_an_int']],
            names=['SampleId', 'Subarray'],
        )
        cols = pd.MultiIndex.from_arrays([['10000-01']], names=['SeqId'])
        adat = Adat(
            data=[[1000.0]],
            index=index,
            columns=cols,
            header_metadata={'FileVersion': '1.2'},
        )
        buf = io.StringIO()
        from somadata.io.adat.file import _write_adat

        _write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations


class TestV2TypeValidationCleanFile:
    def test_compliant_v2_adat_no_type_violations(self, caplog):
        """A well-formed v2.0 Adat with typed fields produces zero type log warnings."""
        adat = _make_minimal_v2_adat(
            row_names=[
                'SampleId',
                'SampleType',
                'PlateId',
                'Subarray',
                'HybNormScaleFactor',
                'PlateRunDate',
            ],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Calibrator'],
                ['PLT001', 'PLT001'],
                ['3', '3'],
                ['1.05', '0.98'],
                ['2026-01-31', '2026-01-31'],
            ],
            col_levels={
                'SeqId': ['10000-01', '10001-02'],
                'EntrezGeneId': ['8514', '3479'],
                'Ref.Array.PlateScale_CAL001': ['986.5', '262.5'],
            },
        )
        buf = io.StringIO()
        write_adat(adat, buf)
        buf.seek(0)
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.file'):
            read_adat(buf)
        type_violations = [
            r for r in caplog.records if 'v2.0 type violation' in r.message
        ]
        assert not type_violations, f'Unexpected type violations: {type_violations}'
