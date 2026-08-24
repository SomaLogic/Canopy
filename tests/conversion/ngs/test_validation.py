"""Unit tests for somadata.conversion.ngs.validation.

Tests validate_source_ngs_adat() pre-conversion checks.
"""

from __future__ import annotations

import pandas as pd
import pytest

from somadata.conversion.errors import ConversionError
from somadata.conversion.ngs.validation import validate_source_ngs_adat
from tests.conversion.ngs.conftest import make_ngs_adat


class TestValidateSourceNGSAdat:
    """Test NGS ADAT validation."""

    def test_passes_for_valid_ngs_adat(self, minimal_ngs_adat):
        validate_source_ngs_adat(minimal_ngs_adat)  # Should not raise

    def test_raises_when_version_missing(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        del adat.header_metadata['!Version']
        with pytest.raises(ConversionError, match='Missing required.*Version'):
            validate_source_ngs_adat(adat)

    def test_run_id_is_optional(self, minimal_ngs_adat):
        """RunId is optional — absent in multi-run DPQ outputs; should not raise."""
        adat = minimal_ngs_adat
        del adat.header_metadata['!RunId']
        validate_source_ngs_adat(adat)  # Should not raise

    def test_yield_fields_are_optional(self, minimal_ngs_adat):
        """YieldDemux / YieldQ30Demux / Q30WeightedMean are optional per-run metrics."""
        adat = minimal_ngs_adat
        for key in ('!YieldDemux', '!YieldQ30Demux', '!Q30WeightedMean'):
            adat.header_metadata.pop(key, None)
        validate_source_ngs_adat(adat)  # Should not raise

    def test_raises_when_instrument_type_missing(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        del adat.header_metadata['!InstrumentType']
        with pytest.raises(ConversionError, match='Missing required.*InstrumentType'):
            validate_source_ngs_adat(adat)

    def test_raises_when_flowcell_missing(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        del adat.header_metadata['!Flowcell']
        with pytest.raises(ConversionError, match='Missing required.*Flowcell'):
            validate_source_ngs_adat(adat)

    def test_raises_when_somamer_reads_missing(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        # Remove SOMAmerReads from row metadata
        adat.index = adat.index.droplevel('SOMAmerReads')
        with pytest.raises(
            ConversionError, match='does not appear to be NGS format.*SOMAmerReads'
        ):
            validate_source_ngs_adat(adat)

    def test_accepts_somamer_reads_in_columns(self, minimal_ngs_adat):
        adat = minimal_ngs_adat
        # Remove SOMAmerReads from row metadata and add it as a COL_DATA level name.
        adat.index = adat.index.droplevel('SOMAmerReads')

        col_names = list(adat.columns.names) + ['SOMAmerReads']
        col_values = [
            list(adat.columns.get_level_values(i)) for i in range(adat.columns.nlevels)
        ]
        col_values.append([''] * len(adat.columns))
        adat.columns = pd.MultiIndex.from_arrays(col_values, names=col_names)

        validate_source_ngs_adat(adat)  # Should not raise
