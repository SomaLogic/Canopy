"""Tests for the v2.0 ADAT writer path."""

from __future__ import annotations

import io
import json
import logging

import pandas as pd
import pytest

from somadata.adat import Adat
from somadata.io.adat.file import write_adat
from somadata.io.adat.v2_fields import FieldType
from somadata.io.adat.v2_fields import (
    serialize_header_value_v2 as _serialize_header_value_v2,
)
from somadata.io.adat.v2_fields import v2_col_field_type as _v2_col_field_type
from somadata.io.adat.v2_fields import v2_row_field_type as _v2_row_field_type

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_v2_adat(
    header: dict | None = None,
    row_names: list[str] | None = None,
    row_values: list[list] | None = None,
    col_names: list[str] | None = None,
    col_levels: dict[str, list] | None = None,
    rfu: list[list[float]] | None = None,
) -> Adat:
    """Build a minimal v2.0 Adat for writer tests."""
    default_header = {
        'FileVersion': '2.0',
        'AdatId': 'GID-test-0001',
        'AssayType': 'Array',
        'AssayVersion': 'v5.0',
        'UseRestriction': 'Research Use Only',
        'SourceFile': '',
        'SOMAmerReferenceSource': '2025-04-10',
        'FileCreatedDate': '2026-01-31',
        'Title': '',
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
        col_names = col_names or ['10000-01', '10001-02']
        col_index = pd.MultiIndex.from_arrays([col_names], names=['SeqId'])

    index = pd.MultiIndex.from_arrays(row_values, names=row_names)
    n_samples = len(row_values[0])
    n_analytes = len(col_index)
    data = rfu or [[1000.0] * n_analytes for _ in range(n_samples)]
    return Adat(
        data=data, index=index, columns=col_index, header_metadata=default_header
    )


def _write_to_string(adat: Adat, **kwargs) -> str:
    buf = io.StringIO()
    write_adat(adat, buf, **kwargs)
    return buf.getvalue()


def _parse_sections(content: str) -> dict[str, list[str]]:
    """Split written output into named sections."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if stripped in ('^HEADER', '^COL_DATA', '^ROW_DATA', '^TABLE_BEGIN'):
            current = stripped
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


# ---------------------------------------------------------------------------
# Type registry helpers
# ---------------------------------------------------------------------------


class TestV2ColFieldType:
    def test_static_string_fields(self):
        for name in (
            'SeqId',
            'Target',
            'TargetFullName',
            'Type',
            'Organism',
            'HybControl',
        ):
            assert _v2_col_field_type(name) is FieldType.STRING

    def test_static_integer_field(self):
        # EntrezGeneId was changed to String (supports pipe-delimited multi-gene IDs)
        assert _v2_col_field_type('EntrezGeneId') is FieldType.STRING

    def test_dynamic_platform_specific_calibrate(self):
        assert (
            _v2_col_field_type('PlatformSpecificCalibrate_PLT001_ScaleFactor')
            is FieldType.DECIMAL
        )

    def test_dynamic_cross_platform_calibrate(self):
        assert (
            _v2_col_field_type('CrossPlatformCalibrate_PLT001_ScaleFactor')
            is FieldType.DECIMAL
        )

    def test_dynamic_qc_ratio(self):
        assert _v2_col_field_type('QCRatio_PLT001') is FieldType.DECIMAL

    def test_dynamic_ref_array(self):
        assert _v2_col_field_type('Ref.Array.PlateScale_CAL123') is FieldType.DECIMAL

    def test_dynamic_ref_ngs(self):
        assert _v2_col_field_type('Ref.NGS.MedNormExt.Plasma') is FieldType.DECIMAL

    def test_unknown_field_defaults_to_string(self):
        assert _v2_col_field_type('UnknownField') is FieldType.STRING


class TestV2RowFieldType:
    def test_string_fields(self):
        for name in ('SampleId', 'SampleType', 'PlateId', 'WellPosition'):
            assert _v2_row_field_type(name) is FieldType.STRING

    def test_integer_fields(self):
        for name in ('Subarray', 'SOMAmerReads', 'YieldDemux', 'YieldQ30Demux'):
            assert _v2_row_field_type(name) is FieldType.INTEGER

    def test_decimal_fields(self):
        for name in (
            'HybNormScaleFactor',
            'SOMAmerNormReads',
            'RefCorr',
            'Q30WeightedMean',
        ):
            assert _v2_row_field_type(name) is FieldType.DECIMAL

    def test_date_field(self):
        assert _v2_row_field_type('PlateRunDate') is FieldType.DATE

    def test_dynamic_norm_scale(self):
        assert _v2_row_field_type('NormScale_20') is FieldType.DECIMAL
        assert _v2_row_field_type('NormScale_0.005') is FieldType.DECIMAL

    def test_dynamic_med_norm_int(self):
        assert _v2_row_field_type('MedNormInt_0.2_ScaleFactor') is FieldType.DECIMAL

    def test_dynamic_med_norm_ext(self):
        assert _v2_row_field_type('MedNormExt_0.2_ScaleFactor') is FieldType.DECIMAL

    def test_dynamic_anml(self):
        assert _v2_row_field_type('ANMLFractionUsed_20') is FieldType.DECIMAL

    def test_unknown_field_defaults_to_string(self):
        assert _v2_row_field_type('CustomAnnotation') == 'String'


class TestSerializeHeaderValueV2:
    def test_json_field_dict_is_minified(self):
        value = {'PLT001': {'PlatformSpecific': 0.72}}
        result = _serialize_header_value_v2('PlateScaleScalar', value)
        assert result == '{"PLT001":{"PlatformSpecific":0.72}}'

    def test_json_field_empty_string(self):
        assert _serialize_header_value_v2('ReportConfig', '') == ''

    def test_string_field_passthrough(self):
        assert _serialize_header_value_v2('AssayType', 'Array') == 'Array'

    def test_date_field_passthrough(self):
        assert (
            _serialize_header_value_v2('FileCreatedDate', '2026-01-31') == '2026-01-31'
        )

    def test_none_value_becomes_empty_string(self):
        assert _serialize_header_value_v2('Title', None) == ''

    def test_process_steps_json_list(self):
        value = {'1': ['Raw RFU', 'Hyb Normalization']}
        result = _serialize_header_value_v2('ProcessSteps', value)
        parsed = json.loads(result)
        assert parsed == value


# ---------------------------------------------------------------------------
# write_adat v2.0 dispatch and output format
# ---------------------------------------------------------------------------


class TestWriteAdatV2Dispatch:
    def test_v2_adat_uses_v2_writer(self):
        """FileVersion == '2.0' triggers v2 path (no !Checksum, no ! on Name/Type)."""
        adat = _make_v2_adat()
        out = _write_to_string(adat)
        assert '!Checksum' not in out
        assert '\t!Name\t' not in out
        assert '\t!Type\t' not in out

    def test_nonv2_adat_uses_nonv2_writer(self):
        """An Adat without FileVersion == '2.0' still gets !Checksum and !Name."""
        index = pd.MultiIndex.from_arrays([['S1']], names=['SampleId'])
        cols = pd.MultiIndex.from_arrays([['10000-01']], names=['SeqId'])
        adat = Adat(data=[[1000.0]], index=index, columns=cols, header_metadata={})
        out = _write_to_string(adat)
        assert '!Checksum' in out
        assert '!Name' in out

    def test_v2_adat_no_checksum_line(self):
        adat = _make_v2_adat()
        out = _write_to_string(adat)
        assert '!Checksum' not in out

    def test_convert_to_v3_seq_ids_ignored_for_v2(self):
        """convert_to_v3_seq_ids kwarg must not crash the v2 writer."""
        adat = _make_v2_adat()
        out = _write_to_string(adat, convert_to_v3_seq_ids=True)
        assert '!Checksum' not in out


class TestWriteAdatV2SectionOrder:
    def test_sections_present(self):
        adat = _make_v2_adat()
        out = _write_to_string(adat)
        for section in ('^HEADER', '^COL_DATA', '^ROW_DATA', '^TABLE_BEGIN'):
            assert section in out

    def test_sections_in_correct_order(self):
        adat = _make_v2_adat()
        out = _write_to_string(adat)
        positions = {
            s: out.index(s)
            for s in ('^HEADER', '^COL_DATA', '^ROW_DATA', '^TABLE_BEGIN')
        }
        assert positions['^HEADER'] < positions['^COL_DATA']
        assert positions['^COL_DATA'] < positions['^ROW_DATA']
        assert positions['^ROW_DATA'] < positions['^TABLE_BEGIN']


class TestWriteAdatV2Header:
    def test_header_fields_written(self):
        adat = _make_v2_adat()
        sections = _parse_sections(_write_to_string(adat))
        header_text = '\n'.join(sections['^HEADER'])
        assert 'FileVersion\t2.0' in header_text
        assert 'AssayType\tArray' in header_text

    def test_json_header_value_is_minified(self):
        header = {'ProcessSteps': {'1': ['Raw RFU', 'Hyb Normalization']}}
        adat = _make_v2_adat(header=header)
        sections = _parse_sections(_write_to_string(adat))
        header_text = '\n'.join(sections['^HEADER'])
        assert 'ProcessSteps\t{"1":["Raw RFU","Hyb Normalization"]}' in header_text

    def test_json_header_value_no_formatting_whitespace(self):
        header = {'PlateScaleScalar': {'PLT001': {'PlatformSpecific': 0.72}}}
        adat = _make_v2_adat(header=header)
        sections = _parse_sections(_write_to_string(adat))
        header_text = '\n'.join(sections['^HEADER'])
        assert ' ' not in header_text.split('PlateScaleScalar\t')[1].split('\n')[0]

    def test_empty_header_value_written_as_key_only(self):
        adat = _make_v2_adat(header={'Title': ''})
        out = _write_to_string(adat)
        lines = out.splitlines()
        title_lines = [l for l in lines if l.startswith('Title')]
        assert any(
            '\t' not in l or l.endswith('\t') or l == 'Title' for l in title_lines
        )


class TestWriteAdatV2ColData:
    def test_name_row_has_no_bang_prefix(self):
        adat = _make_v2_adat()
        sections = _parse_sections(_write_to_string(adat))
        col_data = sections['^COL_DATA']
        name_row = col_data[0]
        assert name_row.startswith('Name\t')
        assert not name_row.startswith('!Name')

    def test_type_row_has_no_bang_prefix(self):
        adat = _make_v2_adat()
        sections = _parse_sections(_write_to_string(adat))
        col_data = sections['^COL_DATA']
        type_row = col_data[1]
        assert type_row.startswith('Type\t')
        assert not type_row.startswith('!Type')

    def test_seqid_type_is_string(self):
        adat = _make_v2_adat()
        sections = _parse_sections(_write_to_string(adat))
        name_parts = sections['^COL_DATA'][0].split('\t')
        type_parts = sections['^COL_DATA'][1].split('\t')
        # name_parts[0] == 'Name', name_parts[1..] are field names
        # type_parts[0] == 'Type', type_parts[1..] are types at matching indices
        assert name_parts[0] == 'Name'
        assert type_parts[0] == 'Type'
        idx = name_parts.index('SeqId')
        assert type_parts[idx] == 'String'

    def test_decimal_col_field_type(self):
        """PlatformSpecificCalibrate_* fields should appear with Decimal type."""
        col_levels = {
            'SeqId': ['10000-01', '10001-02'],
            'PlatformSpecificCalibrate_PLT001_ScaleFactor': ['1.04', '0.97'],
        }
        adat = _make_v2_adat(col_levels=col_levels)
        sections = _parse_sections(_write_to_string(adat))
        name_parts = sections['^COL_DATA'][0].split('\t')
        type_parts = sections['^COL_DATA'][1].split('\t')
        idx = name_parts.index('PlatformSpecificCalibrate_PLT001_ScaleFactor')
        assert type_parts[idx] == 'Decimal'

    def test_integer_col_field_type(self):
        # EntrezGeneId is now String (supports pipe-delimited multi-gene IDs)
        col_levels = {
            'SeqId': ['10000-01'],
            'EntrezGeneId': ['8514'],
        }
        adat = _make_v2_adat(col_levels=col_levels)
        sections = _parse_sections(_write_to_string(adat))
        name_parts = sections['^COL_DATA'][0].split('\t')
        type_parts = sections['^COL_DATA'][1].split('\t')
        idx = name_parts.index('EntrezGeneId')
        assert type_parts[idx] == 'String'


class TestWriteAdatV2RowData:
    def test_name_row_has_no_bang_prefix(self):
        adat = _make_v2_adat()
        sections = _parse_sections(_write_to_string(adat))
        row_data = sections['^ROW_DATA']
        name_row = row_data[0]
        assert name_row.startswith('Name\t')
        assert not name_row.startswith('!Name')

    def test_type_row_has_no_bang_prefix(self):
        adat = _make_v2_adat()
        sections = _parse_sections(_write_to_string(adat))
        row_data = sections['^ROW_DATA']
        type_row = row_data[1]
        assert type_row.startswith('Type\t')
        assert not type_row.startswith('!Type')

    def test_sampleid_type_is_string(self):
        adat = _make_v2_adat()
        sections = _parse_sections(_write_to_string(adat))
        name_parts = sections['^ROW_DATA'][0].split('\t')
        type_parts = sections['^ROW_DATA'][1].split('\t')
        idx = name_parts.index('SampleId')
        assert type_parts[idx] == 'String'

    def test_subarray_type_is_integer(self):
        adat = _make_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'Subarray'],
            row_values=[['S1'], ['Sample'], ['PLT001'], ['3']],
        )
        sections = _parse_sections(_write_to_string(adat))
        name_parts = sections['^ROW_DATA'][0].split('\t')
        type_parts = sections['^ROW_DATA'][1].split('\t')
        idx = name_parts.index('Subarray')
        assert type_parts[idx] == 'Integer'

    def test_hybnormscalefactor_type_is_decimal(self):
        adat = _make_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'HybNormScaleFactor'],
            row_values=[['S1'], ['Sample'], ['PLT001'], ['1.024']],
        )
        sections = _parse_sections(_write_to_string(adat))
        name_parts = sections['^ROW_DATA'][0].split('\t')
        type_parts = sections['^ROW_DATA'][1].split('\t')
        idx = name_parts.index('HybNormScaleFactor')
        assert type_parts[idx] == 'Decimal'

    def test_platerundate_type_is_date(self):
        adat = _make_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'PlateRunDate'],
            row_values=[['S1'], ['Sample'], ['PLT001'], ['2026-02-04']],
        )
        sections = _parse_sections(_write_to_string(adat))
        name_parts = sections['^ROW_DATA'][0].split('\t')
        type_parts = sections['^ROW_DATA'][1].split('\t')
        idx = name_parts.index('PlateRunDate')
        assert type_parts[idx] == 'Date'

    def test_dynamic_normscale_type_is_decimal(self):
        adat = _make_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'NormScale_20'],
            row_values=[['S1'], ['Sample'], ['PLT001'], ['0.989']],
        )
        sections = _parse_sections(_write_to_string(adat))
        name_parts = sections['^ROW_DATA'][0].split('\t')
        type_parts = sections['^ROW_DATA'][1].split('\t')
        idx = name_parts.index('NormScale_20')
        assert type_parts[idx] == 'Decimal'


class TestWriteAdatV2TableData:
    def test_rfu_values_present_in_output(self):
        adat = _make_v2_adat(rfu=[[1234.5, 5678.9], [9876.5, 4321.0]])
        out = _write_to_string(adat)
        assert '1234.5' in out
        assert '5678.9' in out

    def test_rfu_rounded_to_one_decimal(self):
        adat = _make_v2_adat(rfu=[[1234.567, 5678.901]])
        out = _write_to_string(adat, round_rfu=True)
        assert '1234.6' in out
        assert '5678.9' in out

    def test_rfu_not_rounded_when_disabled(self):
        adat = _make_v2_adat(
            col_names=['10000-01'],
            row_names=['SampleId', 'SampleType', 'PlateId'],
            row_values=[['S1'], ['Sample'], ['PLT001']],
            rfu=[[1234.567]],
        )
        out = _write_to_string(adat, round_rfu=False)
        assert '1234.567' in out

    def test_row_metadata_written_in_table(self):
        adat = _make_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId'],
            row_values=[
                ['SAMPLE-001', 'SAMPLE-002'],
                ['Sample', 'Sample'],
                ['PLT999', 'PLT999'],
            ],
        )
        out = _write_to_string(adat)
        assert 'SAMPLE-001' in out
        assert 'PLT999' in out

    def test_col_metadata_written_in_table(self):
        col_levels = {
            'SeqId': ['10000-01', '10001-02'],
            'Target': ['ProteinA', 'ProteinB'],
        }
        adat = _make_v2_adat(col_levels=col_levels)
        out = _write_to_string(adat)
        assert 'ProteinA' in out
        assert 'ProteinB' in out


class TestWriteAdatV2RoundTrip:
    def test_v2_output_is_parseable(self):
        """Write a v2.0 Adat and confirm parse_file can read it back without error."""
        from somadata.io.adat.file import parse_file

        adat = _make_v2_adat()
        buf = io.StringIO(_write_to_string(adat))
        rfu_matrix, row_metadata, column_metadata, header_metadata = parse_file(buf)
        assert header_metadata.get('FileVersion') == '2.0'
        assert len(rfu_matrix) == 2

    def test_v2_header_preserved_on_roundtrip(self):
        from somadata.io.adat.file import parse_file

        adat = _make_v2_adat(header={'AssayType': 'NGS'})
        buf = io.StringIO(_write_to_string(adat))
        _, _, _, header_metadata = parse_file(buf)
        assert header_metadata.get('AssayType') == 'NGS'

    def test_v2_json_header_roundtrip(self):
        from somadata.io.adat.file import parse_file

        ps = {'1': ['Raw RFU', 'Hyb Normalization']}
        adat = _make_v2_adat(header={'ProcessSteps': ps})
        buf = io.StringIO(_write_to_string(adat))
        _, _, _, header_metadata = parse_file(buf)
        assert header_metadata.get('ProcessSteps') == ps


class TestWriteAdatV2HeaderValidation:
    def test_compliant_header_emits_no_warnings(self, caplog):
        adat = _make_v2_adat()
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.v2_fields'):
            _write_to_string(adat)
        assert not caplog.records

    def test_compliant_header_returns_true(self):
        from somadata.io.adat.v2_fields import validate_v2_header_fields

        adat = _make_v2_adat()
        assert validate_v2_header_fields(adat.header_metadata) is True

    def test_extra_field_returns_false(self):
        from somadata.io.adat.v2_fields import validate_v2_header_fields

        adat = _make_v2_adat(header={'LegacyField': 'x'})
        assert validate_v2_header_fields(adat.header_metadata) is False

    def test_missing_field_returns_false(self):
        from somadata.io.adat.v2_fields import validate_v2_header_fields

        adat = _make_v2_adat()
        adat = adat.copy()
        adat.header_metadata = {
            k: v for k, v in adat.header_metadata.items() if k != 'UseRestriction'
        }
        assert validate_v2_header_fields(adat.header_metadata) is False

    def test_extra_and_missing_returns_false(self):
        from somadata.io.adat.v2_fields import validate_v2_header_fields

        adat = _make_v2_adat(header={'ExtraField': 'x'})
        adat = adat.copy()
        adat.header_metadata = {
            k: v for k, v in adat.header_metadata.items() if k != 'UseRestriction'
        }
        assert validate_v2_header_fields(adat.header_metadata) is False

    def test_extra_field_emits_warning(self, caplog):
        from somadata.io.adat.v2_fields import validate_v2_header_fields

        adat = _make_v2_adat(header={'LegacyField': 'some_value', 'AnotherExtra': 'x'})
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.v2_fields'):
            validate_v2_header_fields(adat.header_metadata)
        messages = [r.message for r in caplog.records]
        assert any('LegacyField' in m or 'AnotherExtra' in m for m in messages)

    def test_missing_field_emits_warning(self, caplog):
        from somadata.io.adat.v2_fields import validate_v2_header_fields

        adat = _make_v2_adat()
        adat = adat.copy()
        adat.header_metadata = {
            k: v for k, v in adat.header_metadata.items() if k != 'UseRestriction'
        }
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.v2_fields'):
            validate_v2_header_fields(adat.header_metadata)
        assert any('UseRestriction' in r.message for r in caplog.records)

    def test_both_extra_and_missing_each_emit_separate_warning(self, caplog):
        from somadata.io.adat.v2_fields import validate_v2_header_fields

        adat = _make_v2_adat(header={'ExtraField': 'x'})
        adat = adat.copy()
        adat.header_metadata = {
            k: v for k, v in adat.header_metadata.items() if k != 'UseRestriction'
        }
        with caplog.at_level(logging.WARNING, logger='somadata.io.adat.v2_fields'):
            validate_v2_header_fields(adat.header_metadata)
        messages = [r.message for r in caplog.records]
        assert any('ExtraField' in m for m in messages)
        assert any('UseRestriction' in m for m in messages)


class TestWriteAdatV2HeaderValidationException:
    def test_extra_field_raises(self):
        from somadata.io.adat.errors import AdatWriteError

        adat = _make_v2_adat(header={'LegacyField': 'x'})
        with pytest.raises(AdatWriteError):
            _write_to_string(adat)

    def test_missing_field_raises(self):
        from somadata.io.adat.errors import AdatWriteError

        adat = _make_v2_adat()
        adat = adat.copy()
        adat.header_metadata = {
            k: v for k, v in adat.header_metadata.items() if k != 'UseRestriction'
        }
        with pytest.raises(AdatWriteError):
            _write_to_string(adat)

    def test_extra_and_missing_raises(self):
        from somadata.io.adat.errors import AdatWriteError

        adat = _make_v2_adat(header={'ExtraField': 'x'})
        adat = adat.copy()
        adat.header_metadata = {
            k: v for k, v in adat.header_metadata.items() if k != 'UseRestriction'
        }
        with pytest.raises(AdatWriteError):
            _write_to_string(adat)

    def test_compliant_header_does_not_raise(self):
        from somadata.io.adat.errors import AdatWriteError

        adat = _make_v2_adat()
        try:
            _write_to_string(adat)
        except AdatWriteError:
            pytest.fail('AdatWriteError raised on a compliant v2.0 header')


class TestV2DateMissingValueSpec:
    """Verify that Date fields accept empty string as the missing-value sentinel (spec §2.6.2)."""

    def test_plate_run_date_empty_string_does_not_raise(self):
        """PlateRunDate = '' (missing) should pass v2.0 write without errors."""
        adat = _make_v2_adat(
            row_names=['SampleId', 'SampleType', 'PlateId', 'PlateRunDate'],
            row_values=[
                ['S1', 'S2'],
                ['Sample', 'Sample'],
                ['PLT001', 'PLT001'],
                ['', ''],  # empty string = missing Date value per spec
            ],
        )
        # Should not raise
        content = _write_to_string(adat)
        assert 'PlateRunDate' in content

    def test_plate_run_date_empty_string_passes_validation(self):
        """_validate_v2_field_values must not flag empty string as invalid for Date fields."""
        import warnings

        from somadata.io.adat.file import _validate_v2_field_values

        # Simulate a row-metadata dict with PlateRunDate = ''
        row_metadata = {'PlateRunDate': ['', '']}
        # Should run without emitting any warnings
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            _validate_v2_field_values(row_metadata, {})
        date_warnings = [w for w in caught if 'PlateRunDate' in str(w.message)]
        assert date_warnings == [], f'Unexpected warnings for empty PlateRunDate: {date_warnings}'
