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
    'CrossPlatformPlateScale, CrossPlatformCalibrate, MedNormExt'
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
            '!ProteinEffectiveDate': '2020-08-07',
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


def make_full_legacy_array_adat() -> Adat:
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


# ---------------------------------------------------------------------------
# Full legacy NGS factory for merge testing
# ---------------------------------------------------------------------------

# NGS ProcessSteps required for MedNorm merge validation
NGS_BRIDGED_STEPS = (
    'Raw, HybNorm, MedNormInt, PlatformSpecificPlateScale, '
    'PlatformSpecificCalibrate, CrossPlatformPlateScale, CrossPlatformCalibrate, MedNormExt'
)


def make_full_legacy_ngs_adat(
    shared_seqids: list[str] | None = None,
    ngs_only_seqids: list[str] | None = None,
    mednorm_ext_values: list[str] | None = None,
) -> Adat:
    """NGS Adat with ALL legacy header/col/row fields for merge testing.

    Includes:
    - Header: full NGS required fields (Version, RunId, InstrumentType, etc.)
              and ProcessSteps matching the required NGS merge sequence.
    - COL_DATA: SOMAmer annotation fields including Ref.MedNormExt.Plasma level
      for MedNorm validation.
    - ROW_DATA: SOMAmerReads, HybNorm scale factors, etc.

    Parameters
    ----------
    shared_seqids : list[str] or None
        SeqIds that overlap with the array source.  Defaults to ``['10000-28', '10001-7']``.
    ngs_only_seqids : list[str] or None
        SeqIds that are NGS-exclusive.  Defaults to ``['20000-01']``.
    mednorm_ext_values : list[str] or None
        ``Ref.MedNormExt.Plasma`` values for the shared SeqIds (one per SeqId).
        Defaults to ``['REF-1', 'REF-2']`` to match the array defaults.
    """
    shared_seqids = shared_seqids or ['10000-28', '10001-7']
    ngs_only_seqids = ngs_only_seqids or ['20000-01']
    all_seqids = shared_seqids + ngs_only_seqids
    n_cols = len(all_seqids)

    if mednorm_ext_values is None:
        mednorm_ext_values = [1200.0, 950.0]
    # Pad to full length (NGS-only SeqIds get a generic value)
    mednorm_ext_all = list(mednorm_ext_values) + [800.0] * len(ngs_only_seqids)

    header = {
        '!AdatId': 'SL-NGS-99999',
        '!AssayVersion': 'v1',
        '!SOMAmerReferenceSource': 'SomaSuite-NGS-4.0',
        '!Version': '4.0.1',
        '!RunId': 'RUN12345',
        '!InstrumentType': 'NovaSeq6000',
        '!Flowcell': 'H7LNMDRXY',
        '!YieldDemux': '5000000000',
        '!YieldQ30Demux': '4500000000',
        '!Q30WeightedMean': '0.91',
        '!ProcessSteps': NGS_BRIDGED_STEPS,
        # Plate-keyed NGS fields
        'PlatformSpecificPlateScale_ScaleFactor_NGSPLT1': '1.01',
        'CrossPlatformPlateScale_ScaleFactor_NGSPLT1': '0.99',
        'PlatformSpecificCalibrateTailPercent_NGSPLT1': '4.9',
        'CrossPlatformCalibrateTailPercent_NGSPLT1': '5.1',
        'PlatformSpecificCalibrateTailPercent_PassFlag_NGSPLT1': 'PASS',
        'CrossPlatformCalibrateTailPercent_PassFlag_NGSPLT1': 'PASS',
        'QCCheckTailPercent_NGSPLT1': '3.5',
        'PlateSOMAmerNormReads_NGSPLT1_PassFlag': 'PASS',
    }

    row_names = [
        'SampleId',
        'SampleType',
        'PlateId',
        'SOMAmerReads',
        'HybNorm_1_ScaleFactor',
        'MedNormInt_0_4_ScaleFactor',
        'MedNormExt_0_4_ScaleFactor',
    ]

    row_values = [
        ['NS1', 'NS2'],  # SampleId
        ['Sample', 'Sample'],  # SampleType
        ['NGSPLT1', 'NGSPLT1'],  # PlateId
        ['14250000', '13800000'],  # SOMAmerReads
        ['1.05', '0.98'],  # HybNorm_1_ScaleFactor
        ['1.02', '0.97'],  # MedNormInt_0_4_ScaleFactor
        ['1.01', '0.99'],  # MedNormExt_0_4_ScaleFactor
    ]

    col_level_names = [
        'SeqId',
        'Target',
        'Type',
        'Entrez Gene ID',
        'Ref.MedNormExt.Plasma',
        'Ref.MedNorm.Id',
        'DRC_Level',
        'BlockList',
    ]

    col_values = [
        all_seqids,  # SeqId
        ['ProteinA', 'ProteinB', 'ProteinC'][:n_cols],  # Target
        ['Protein'] * n_cols,  # Type
        ['12345', '67890', '54321'][:n_cols],  # Entrez Gene ID
        mednorm_ext_all,  # Ref.MedNormExt.Plasma
        ['MEDNORM-REF-001'] * n_cols,  # Ref.MedNorm.Id
        ['Below LOD', 'Above LOD', 'Below LOD'][:n_cols],  # DRC_Level
        ['0', '0', '0'][:n_cols],  # BlockList
    ]

    index = pd.MultiIndex.from_arrays(row_values, names=row_names)
    columns = pd.MultiIndex.from_arrays(col_values, names=col_level_names)
    data = [[1000.0] * n_cols, [1200.0] * n_cols]

    return Adat(
        data=data,
        index=index,
        columns=columns,
        header_metadata=header,
    )


def make_bridged_array_with_mednorm(
    shared_seqids: list[str] | None = None,
    array_only_seqids: list[str] | None = None,
    mednorm_ext_values: list[str] | None = None,
) -> Adat:
    """Array Adat with Ref.MedNormExt.* COL_DATA columns for merge testing.

    Uses the bridged ProcessSteps so it passes MedNorm merge validation.

    Parameters
    ----------
    shared_seqids : list[str] or None
        SeqIds that overlap with the NGS source.  Defaults to ``['10000-28', '10001-7']``.
    array_only_seqids : list[str] or None
        SeqIds that are array-exclusive.  Defaults to ``['30000-01']``.
    mednorm_ext_values : list[str] or None
        ``Ref.MedNormExt.Plasma`` values for the shared SeqIds (one per SeqId).
        Defaults to ``['REF-1', 'REF-2']`` to match the NGS defaults.
    """
    shared_seqids = shared_seqids or ['10000-28', '10001-7']
    array_only_seqids = array_only_seqids or ['30000-01']
    all_seqids = shared_seqids + array_only_seqids
    n_cols = len(all_seqids)

    if mednorm_ext_values is None:
        mednorm_ext_values = [1200.0, 950.0]
    mednorm_ext_all = list(mednorm_ext_values) + [700.0] * len(array_only_seqids)

    header = {
        '!AdatId': 'SL-99888',
        '!AssayVersion': 'V4',
        '!Title': 'Test Study',
        '!StudyOrganism': 'Human',
        '!StudyMatrix': 'EDTA Plasma',
        '!UseRestriction': 'Research Use Only',
        '!GeneratedBy': 'SomaSuite 4.0.0',
        '!ProteinEffectiveDate': '2020-08-07',
        '!CreatedDate': '2021-01-15',
        '!ProcessSteps': BRIDGED_STEPS,
        '!ReportConfig': 'DefaultReport',
        'PlateScale_Scalar_PLT1': '1.02',
        'CalPlateTailPercent_PLT1': '5.2',
        'CalPlateTailTest_PLT1': 'PASS',
        'PlateScale_PassFlag_PLT1': 'PASS',
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
    ]

    row_values = [
        ['AS1', 'AS2'],  # SampleId
        ['Sample', 'Sample'],  # SampleType
        ['PLT1', 'PLT1'],  # PlateId
        ['A1', 'A2'],  # PlatePosition
        ['258740110837', '258740110837'],  # SlideId
        ['3', '3'],  # Subarray
        ['1.05', '0.98'],  # HybControlNormScale
        ['PASS', 'PASS'],  # RowCheck
    ]

    col_level_names = [
        'SeqId',
        'Target',
        'Type',
        'EntrezGeneID',
        'Cal_PLT1',
        'PlateScale_Reference',
        'CalReference',
        'SeqIdVersion',
        'SomaId',
        'ColCheck',
        'Ref.MedNormExt.Plasma',
        'medNormRef_ReferenceRFU',
    ]

    col_values = [
        all_seqids,  # SeqId
        ['ProteinA', 'ProteinB', 'ProteinD'][:n_cols],  # Target
        ['Protein'] * n_cols,  # Type
        ['12345', '67890', '11111'][:n_cols],  # EntrezGeneID
        ['1.01', '1.03', '1.00'][:n_cols],  # Cal_PLT1
        ['SL-REF-1'] * n_cols,  # PlateScale_Reference
        ['SL-CAL-1'] * n_cols,  # CalReference
        ['4'] * n_cols,  # SeqIdVersion
        ['SL-1', 'SL-2', 'SL-3'][:n_cols],  # SomaId
        ['PASS'] * n_cols,  # ColCheck
        mednorm_ext_all,  # Ref.MedNormExt.Plasma
        ['MEDNORM-REF-001'] * n_cols,  # medNormRef_ReferenceRFU → renames to Ref.MedNorm.Id
    ]

    index = pd.MultiIndex.from_arrays(row_values, names=row_names)
    columns = pd.MultiIndex.from_arrays(col_values, names=col_level_names)
    data = [[1000.0] * n_cols, [1200.0] * n_cols]

    return Adat(
        data=data,
        index=index,
        columns=columns,
        header_metadata=header,
    )
