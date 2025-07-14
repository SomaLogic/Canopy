from io import StringIO
from unittest import TestCase

import pandas as pd

from somadata import Adat, Annotations
from somadata.errors import AnnotationsLiftingError

# Test data constants
ANNOTATION_CSV_DATA = 'SeqId,SomaId,Plasma Scalar v4.0 5K to v4.1 7K\n54321-21,SL054321,0.8\n12345-12,SL012345,1.1\n'
ANNOTATION_CSV_DATA_NEW_SOMA_IDS = 'SeqId,SomaId,Plasma Scalar v4.0 5K to v4.1 7K\n54321-21,SLNEW1,0.8\n12345-12,SLNEW2,1.1\n'
ANNOTATION_CSV_DATA_NO_SEQID = (
    'SomaId,Plasma Scalar v4.0 5K to v4.1 7K\nSL054321,0.8\nSL012345,1.1\n'
)
ANNOTATION_CSV_DATA_NO_SEQID_NEW_IDS = (
    'SomaId,Plasma Scalar v4.0 5K to v4.1 7K\nSLNEW1,0.8\nSLNEW2,1.1\n'
)

EXPECTED_LIFTED_VALUES = [[1.1, 1.6], [4.4, 4]]
EXPECTED_NEW_SOMA_IDS = ['SLNEW2', 'SLNEW1']


def create_annotations_from_csv(csv_data: str, index_col=False) -> Annotations:
    """Create an Annotations object from CSV string data.

    Args:
        csv_data: CSV string data
        index_col: Column to use as index, or False for default index

    Returns:
        Annotations object
    """
    s = StringIO(csv_data)
    df = pd.read_csv(s, index_col=index_col)
    if index_col is False:
        return Annotations(data=df.values, index=df.index, columns=df.columns)
    else:
        return Annotations(df)


def build_annotation_example():
    """Build standard annotation example with SeqId as column."""
    return create_annotations_from_csv(ANNOTATION_CSV_DATA, index_col=False)


def build_good_example_adat():
    rfu_data = [[1, 2], [4, 5]]
    col_metadata = {
        'SeqId': ['12345-12', '54321-21'],
        'SomaId': ['SL012345', 'SL054321'],
        'SeqIdVersion': ['1', '2'],
        'ColCheck': ['PASS', 'FLAG'],
    }
    row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
    header_metadata = {
        'AdatId': '1a2b3c',
        '!ProcessSteps': 'Raw RFU, Hyb Normalization, medNormInt (SampleId), plateScale, Calibration, anmlQC, qcCheck, anmlSMP',
        'StudyMatrix': 'EDTA Plasma',
        '!AssayVersion': 'v4.0',
    }
    return Adat.from_features(rfu_data, row_metadata, col_metadata, header_metadata)


def build_example_adat_with_extra_somamers():
    rfu_data = [[1, 2, 3], [4, 5, 6]]
    col_metadata = {
        'SeqId': ['12345-12', '54321-21', '23456-78'],
        'SomaId': ['SL012345', 'SL054321', 'SL023456'],
        'SeqIdVersion': ['1', '2', '3'],
        'ColCheck': ['PASS', 'FLAG', 'FLAG'],
    }
    row_metadata = {'PlateId': ['A12', 'A12'], 'Barcode': ['SL1234', 'SL1235']}
    header_metadata = {
        'AdatId': '1a2b3c',
        '!ProcessSteps': 'Raw RFU, Hyb Normalization, medNormInt (SampleId), plateScale, Calibration, anmlQC, qcCheck, anmlSMP',
        'StudyMatrix': 'EDTA Plasma',
        '!AssayVersion': 'v4.0',
    }
    return Adat.from_features(rfu_data, row_metadata, col_metadata, header_metadata)


class AdatLiftingTestCase(TestCase):
    def setUp(self):
        self.an = build_annotation_example()
        self.adat = build_good_example_adat()

    def _assert_lifting_values_correct(
        self, lifted_adat, expected_values=EXPECTED_LIFTED_VALUES
    ):
        """Helper method to assert lifting calculations are correct."""
        for correct_row, lifted_row in zip(expected_values, lifted_adat.values):
            for correct_value, lifted_value in zip(correct_row, lifted_row):
                self.assertAlmostEqual(correct_value, lifted_value)

    def _assert_soma_ids_match(self, adat, expected_ids=EXPECTED_NEW_SOMA_IDS):
        """Helper method to assert SomaId values match expected."""
        self.assertEqual(list(adat.columns.get_level_values('SomaId')), expected_ids)

    def _assert_error_contains_message(self, context_manager, expected_message):
        """Helper method to assert error contains expected message."""
        self.assertIn(expected_message, str(context_manager.exception))

    def test_lifting_correct(self):
        lifted_adat = self.an.lift_adat(self.adat)
        self._assert_lifting_values_correct(lifted_adat)

        self.assertEqual(lifted_adat.header_metadata['SignalSpace'], 'v4.1')
        self.assertTrue(
            lifted_adat.header_metadata['!ProcessSteps'].endswith(
                ', Lifting Bridge (v4.0 -> v4.1)'
            )
        )

    def test_orig_adat_unmodified(self):
        self.an.lift_adat(self.adat)

        orig_values = [[1, 2], [4, 5]]
        for orig_row, adat_row in zip(orig_values, self.adat.values):
            for orig_value, adat_value in zip(orig_row, adat_row):
                self.assertAlmostEqual(orig_value, adat_value)

        self.assertNotIn('SignalSpace', self.adat.header_metadata)
        self.assertFalse(
            self.adat.header_metadata['!ProcessSteps'].endswith(
                ', Lifting Bridge (v4.0 to v4.1)'
            )
        )

    def test_lifting_matrix_error(self):
        self.adat.header_metadata['StudyMatrix'] = 'NotSupportedMatrix'
        with self.assertRaises(AnnotationsLiftingError) as cm:
            self.an.lift_adat(self.adat)
        e_msg = str(cm.exception)
        self.assertEqual(
            e_msg,
            'Unsupported matrix: "NotSupportedMatrix". Supported matrices: Plasma.',
        )

    def test_lifting_assay_version_error(self):
        self.adat.header_metadata['!AssayVersion'] = 'NotSupportedVersion'
        with self.assertRaises(AnnotationsLiftingError) as cm:
            self.an.lift_adat(self.adat)
        e_msg = str(cm.exception)
        self.assertEqual(
            e_msg,
            'Unsupported lifting from: "NotSupportedVersion". Supported lifting: from "v4.0" to "v4.1".',
        )

    def test_lifting_signal_space_error(self):
        self.adat.header_metadata['SignalSpace'] = 'NotSupportedVersion'
        with self.assertRaises(AnnotationsLiftingError) as cm:
            self.an.lift_adat(self.adat)
        e_msg = str(cm.exception)
        self.assertEqual(
            e_msg,
            'Unsupported lifting from: "NotSupportedVersion". Supported lifting: from "v4.0" to "v4.1".',
        )

    def test_lifting_to_space_error(self):
        with self.assertRaises(AnnotationsLiftingError) as cm:
            self.an.lift_adat(self.adat, lift_to_version='NotSupportedVersion')
        e_msg = str(cm.exception)
        self.assertEqual(
            e_msg,
            'Unsupported lifting from "v4.0" to "NotSupportedVersion". Supported lifting: from "v4.0" to "v4.1".',
        )

    def test_analyte_mismatch(self):
        self.adat = build_example_adat_with_extra_somamers()
        with self.assertRaises(AnnotationsLiftingError) as cm:
            self.an.lift_adat(self.adat)
        e_msg = str(cm.exception)
        self.assertEqual(
            e_msg,
            'Unable to perform lifting due to analyte mismatch between adat & annotations. Has either file been modified?',
        )

    def test_update_adat_column_meta(self):
        an = create_annotations_from_csv(
            ANNOTATION_CSV_DATA_NEW_SOMA_IDS, index_col='SeqId'
        )
        new_adat = an.update_adat_column_meta(self.adat)
        self._assert_soma_ids_match(new_adat)

    def test_update_adat_column_meta_seqid_as_column(self):
        """Test update_adat_column_meta when SeqId is a regular column (not index)"""
        an = create_annotations_from_csv(
            ANNOTATION_CSV_DATA_NEW_SOMA_IDS, index_col=False
        )
        new_adat = an.update_adat_column_meta(self.adat)
        self._assert_soma_ids_match(new_adat)

    def test_update_adat_column_meta_missing_seqid(self):
        """Test update_adat_column_meta when SeqId is missing entirely"""
        an = create_annotations_from_csv(
            ANNOTATION_CSV_DATA_NO_SEQID_NEW_IDS, index_col=False
        )
        with self.assertRaises(ValueError) as cm:
            an.update_adat_column_meta(self.adat)
        self._assert_error_contains_message(
            cm, "SeqId not found in either index or columns"
        )

    def test_lift_adat_seqid_as_index(self):
        """Test lift_adat when SeqId is in the index"""
        an = create_annotations_from_csv(ANNOTATION_CSV_DATA, index_col='SeqId')
        lifted_adat = an.lift_adat(self.adat)
        self._assert_lifting_values_correct(lifted_adat)

    def test_lift_adat_seqid_as_column(self):
        """Test lift_adat when SeqId is a regular column (not index)"""
        an = create_annotations_from_csv(ANNOTATION_CSV_DATA, index_col=False)
        lifted_adat = an.lift_adat(self.adat)
        self._assert_lifting_values_correct(lifted_adat)

    def test_lift_adat_missing_seqid(self):
        """Test lift_adat when SeqId is missing entirely"""
        an = create_annotations_from_csv(ANNOTATION_CSV_DATA_NO_SEQID, index_col=False)
        with self.assertRaises(ValueError) as cm:
            an.lift_adat(self.adat)
        self._assert_error_contains_message(
            cm, "SeqId not found in either index or columns"
        )
