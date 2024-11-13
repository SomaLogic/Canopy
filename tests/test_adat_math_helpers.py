import os
from unittest import TestCase

import pytest
from numpy import isclose

import somadata
from somadata import Adat
from somadata.data.lift import LiftData


class TestAdatLift(TestCase):
    filename = './tests/data/control_data.adat'

    @classmethod
    def setUpClass(cls):
        cls.ld = LiftData('v4.0', 'v5.0', 'plasma')
        cls.adat = somadata.read_adat(cls.filename)
        cls.lift_adat = cls.adat.lift('v5.0')

    def test_scaling_math(self):
        back_scalers = self.lift_adat.divide(self.adat).mean(axis=0)
        # there's rounding error but we're lifting columns. The Ratio of lifted values is the scale factors again.
        assert all(
            isclose(back_scalers.values, self.ld.scale_factors.values, atol=0.05)
        )

    def test_processing_steps(self):
        assert self.lift_adat.header_metadata['!ProcessSteps'].endswith(
            'Lifting Bridge (v4.0 -> v5.0)'
        )

    def test_signal_space(self):
        assert self.lift_adat.header_metadata['SignalSpace'] == 'v5.0'

    def test_e_lod_by_reagent(self):
        e_lod_df = self.adat.e_lod_by_reagent()
        assert not e_lod_df.empty
        assert all(e_lod_df > 0)

    def test_cv_decomp(self):
        cv_decomp_df = self.adat.cv_decomp()
        assert not cv_decomp_df.empty
        assert 'Total' in cv_decomp_df.columns
        assert 'Intra' in cv_decomp_df.columns
        assert 'Inter' in cv_decomp_df.columns
