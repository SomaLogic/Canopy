"""Unit tests for somadata.conversion.ngs.context.

Tests NGSConversionContext extraction from source NGS ADATs.
"""

from __future__ import annotations

import pytest

from somadata.conversion.ngs import NGSConversionContext
from tests.conversion.ngs.conftest import make_ngs_adat


class TestNGSConversionContext:
    """Test NGSConversionContext.from_adat() extraction."""

    def test_extracts_dpq_version(self):
        adat = make_ngs_adat()
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.dpq_version == '4.0.1'

    def test_extracts_sequencing_run_id(self):
        adat = make_ngs_adat()
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.sequencing_run_id == 'RUN12345'

    def test_extracts_instrument_type(self):
        adat = make_ngs_adat()
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.instrument_type == 'NovaSeq6000'

    def test_extracts_flowcell(self):
        adat = make_ngs_adat()
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.flowcell == 'HFFKNDSXF'

    def test_extracts_yield_demux(self):
        adat = make_ngs_adat()
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.yield_demux == 12500000

    def test_extracts_yield_q30_demux(self):
        adat = make_ngs_adat()
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.yield_q30_demux == 11800000

    def test_extracts_q30_weighted_mean(self):
        adat = make_ngs_adat()
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.q30_weighted_mean == 92.5

    def test_extracts_plate_ids(self):
        adat = make_ngs_adat(n_plates=2, n_samples=4)
        ctx = NGSConversionContext.from_adat(adat)
        assert 'PLT100' in ctx.plate_ids
        assert 'PLT101' in ctx.plate_ids

    def test_extracts_process_steps(self):
        adat = make_ngs_adat()
        ctx = NGSConversionContext.from_adat(adat)
        assert 'Raw Counts' in ctx.process_steps
        assert 'Hyb Normalization' in ctx.process_steps

    def test_extracts_source_adat_id_when_present(self):
        adat = make_ngs_adat()
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.source_adat_id == 'GID-old-ngs-id'

    def test_source_adat_id_none_when_missing(self, minimal_ngs_adat):
        # Remove AdatId from header
        adat = minimal_ngs_adat
        if '!AdatId' in adat.header_metadata:
            del adat.header_metadata['!AdatId']
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.source_adat_id is None

    def test_safe_int_conversion_handles_blank(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        adat.header_metadata['!YieldDemux'] = ''
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.yield_demux is None

    def test_safe_float_conversion_handles_blank(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        adat.header_metadata['!Q30WeightedMean'] = ''
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.q30_weighted_mean is None

    def test_defaults_to_empty_when_header_missing(self):
        adat = make_ngs_adat()
        adat.header_metadata = {}
        ctx = NGSConversionContext.from_adat(adat)
        assert ctx.dpq_version == ''
        assert ctx.sequencing_run_id == ''
        assert ctx.instrument_type == ''
