"""Shared fixtures and Adat factory helpers for tests/conversion/."""

from __future__ import annotations

import pandas as pd
import pytest

from somadata.adat import Adat

# ---------------------------------------------------------------------------
# ProcessSteps constants
# ---------------------------------------------------------------------------

BRIDGED_STEPS = (
    'Raw RFU, Hyb Normalization, medNormInt, plateScale, Calibration, '
    'CrossPlatformPlateScaling, CrossPlatformCalibrate, MedNormExt'
)

NATIVE_STEPS = 'Raw RFU, Hyb Normalization, medNormInt, plateScale, Calibration'

# ---------------------------------------------------------------------------
# Minimal Adat factory helpers
# ---------------------------------------------------------------------------


def make_adat(
    header: dict | None = None,
    row_names: list[str] | None = None,
    row_values: list[list] | None = None,
    col_names: list[str] | None = None,
) -> Adat:
    """Build a minimal Adat for testing without needing real file fixtures."""
    header = header or {}
    row_names = row_names or ['SampleId', 'SampleType']
    row_values = row_values or [['S1', 'S2'], ['Sample', 'Sample']]
    col_names = col_names or ['10000-01', '10001-02']

    index = pd.MultiIndex.from_arrays(row_values, names=row_names)
    columns = pd.MultiIndex.from_arrays([col_names], names=['SeqId'])
    data = [[1.0] * len(col_names)] * len(row_values[0])
    return Adat(data=data, index=index, columns=columns, header_metadata=header)


def make_array_adat(
    assay_version: str = 'V4',
    process_steps: str = NATIVE_STEPS,
    n_samples: int = 2,
) -> Adat:
    """Minimal array Adat with SlideId and Subarray row metadata."""
    return make_adat(
        header={
            '!AssayVersion': assay_version,
            '!ProcessSteps': process_steps,
        },
        row_names=['SampleId', 'SampleType', 'SlideId', 'Subarray'],
        row_values=[
            [f'S{i}' for i in range(n_samples)],
            ['Sample'] * n_samples,
            ['258740110837'] * n_samples,
            ['3'] * n_samples,
        ],
    )


def make_bridged_array_adat() -> Adat:
    """Minimal bridged array Adat (ProcessSteps end with the bridged terminal triple)."""
    return make_array_adat(process_steps=BRIDGED_STEPS)


def make_native_array_adat() -> Adat:
    """Minimal native array Adat (no bridged terminal steps)."""
    return make_array_adat(process_steps=NATIVE_STEPS)


def make_ngs_adat() -> Adat:
    """Minimal NGS Adat with SOMAmerReads row metadata."""
    return make_adat(
        header={'!AssayVersion': 'v1'},
        row_names=['SampleId', 'SampleType', 'SOMAmerReads'],
        row_values=[['S1', 'S2'], ['Sample', 'Sample'], ['14250000', '13800000']],
    )


def make_v2_combined_adat() -> Adat:
    """Minimal Adat already in v2.0 combined format."""
    return make_adat(header={'FileVersion': '2.0'})


def make_full_legacy_array_adat(n_samples: int = 3) -> Adat:
    """Array Adat with ALL legacy header/col/row fields for conversion testing.

    Includes:
    - Header: plate-keyed fields, GeneratedBy, ProteinEffectiveDate,
      CreatedDate, AdatId, ProcessSteps, ReportConfig
    - COL_DATA: Cal_PLT1, CalQcRatio_PLT1_QC1, PlateScale_Reference,
      CalReference, QcReference_QC1, EntrezGeneID, medNormRef_ReferenceRFU,
      ColCheck, SeqIdVersion, SomaId, Units, eLOD, Type (with Hyb Control rows)
    - ROW_DATA: PlatePosition, HybControlNormScale, RowCheck, StudyId,
      SubjectID, Barcode2d, NormScale_0.5, PlateRunDate, ControlId,
      SampleName, ExtIdentifier
    """
    header = {
        '!AdatId': 'SL-99999',
        '!AssayVersion': 'V4',
        '!Title': 'Test Study',
        '!StudyOrganism': 'Human',
        '!StudyMatrix': 'EDTA Plasma',
        '!UseRestriction': 'Research Use Only',
        '!GeneratedBy': 'SomaSuite 4.0.0',
        '!ProteinEffectiveDate': '2020-08-07',
        '!CreatedDate': '2021-01-15',
        '!ProcessSteps': 'Raw RFU, Hyb Normalization, medNormInt, plateScale, Calibration',
        '!ReportConfig': 'DefaultReport',
        # Plate-keyed fields
        'PlateScale_Scalar_PLT1': '1.02',
        'PlateScale_Scalar_PLT2': '0.98',
        'CalPlateTailPercent_PLT1': '5.2',
        'CalPlateTailPercent_PLT2': '4.8',
        'CalPlateTailTest_PLT1': 'PASS',
        'CalPlateTailTest_PLT2': 'WARNING',
        'PlateScale_PassFlag_PLT1': 'PASS',
        'PlateScale_PassFlag_PLT2': 'FLAG',
        'PlateTailPercent_PLT1': '3.1',
        'PlateTailTest_PLT1': 'PASS',
    }

    row_names = [
        'SampleId',
        'SampleType',
        'PlateId',
        'PlatePosition',
        'SlideId',
        'Subarray',
        'HybControlNormScale',
        'RowCheck',
        'StudyId',
        'SubjectID',
        'Barcode2d',
        'NormScale_0.5',
        'PlateRunDate',
        'ControlId',
        'SampleName',
        'ExtIdentifier',
    ]

    row_values = [
        ['S1', 'S2', 'S3'],  # SampleId
        ['Sample', 'Calibrator', 'QC'],  # SampleType
        ['PLT1', 'PLT1', 'PLT1'],  # PlateId
        ['A1', 'A2', 'A3'],  # PlatePosition
        ['258740110837', '258740110837', '258740110837'],  # SlideId
        ['3', '3', '3'],  # Subarray
        ['1.05', '0.35', '2.60'],  # HybControlNormScale
        ['PASS', 'PASS', 'FLAG'],  # RowCheck
        ['ST-001', 'ST-001', 'ST-001'],  # StudyId
        ['SUBJ-1', 'SUBJ-2', 'SUBJ-3'],  # SubjectID
        ['TUBE-A', 'TUBE-B', 'TUBE-C'],  # Barcode2d
        ['1.1', '1.0', '0.9'],  # NormScale_0.5
        ['', '2021-01-10', '2021-01-10'],  # PlateRunDate (S1 blank)
        ['', '', ''],  # ControlId (to be filled)
        ['Alice', 'Bob', 'Charlie'],  # SampleName
        ['EXT-1', 'EXT-2', 'EXT-3'],  # ExtIdentifier
    ]

    col_names_seq = ['10000-28', '10001-7', '10002-66']

    col_names = [
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
        col_names_seq,
    ]
    col_level_names = [
        'SeqId',
        'Target',
        'Type',
        'EntrezGeneID',
        'Cal_PLT1',
        'CalQcRatio_PLT1_QC1',
        'PlateScale_Reference',
        'CalReference',
        'QcReference_QC1',
        'medNormRef_ReferenceRFU',
        'SeqIdVersion',
        'SomaId',
        'ColCheck',
    ]

    col_values = [
        col_names_seq,  # SeqId
        ['ProteinA', 'ProteinB', 'HybCtrl'],  # Target
        ['Protein', 'Protein', 'Hybridization Control'],  # Type
        ['12345', '67890', ''],  # EntrezGeneID
        ['1.01', '1.03', '0.99'],  # Cal_PLT1
        ['0.97', '1.02', '1.00'],  # CalQcRatio_PLT1_QC1
        ['SL-REF-1', 'SL-REF-1', 'SL-REF-1'],  # PlateScale_Reference
        ['SL-CAL-1', 'SL-CAL-1', 'SL-CAL-1'],  # CalReference
        ['SL-QC-1', 'SL-QC-1', 'SL-QC-1'],  # QcReference_QC1
        ['SL-MEDNORM-1', 'SL-MEDNORM-1', 'SL-MEDNORM-1'],  # medNormRef_ReferenceRFU
        ['4', '4', '4'],  # SeqIdVersion
        ['SL-1', 'SL-2', 'SL-3'],  # SomaId
        ['PASS', 'PASS', 'PASS'],  # ColCheck
    ]

    index = pd.MultiIndex.from_arrays(row_values, names=row_names)
    columns = pd.MultiIndex.from_arrays(col_values, names=col_level_names)
    data = [[1000.0, 1500.0, 200.0]] * len(row_values[0])

    return Adat(
        data=data,
        index=index,
        columns=columns,
        header_metadata=header,
    )
