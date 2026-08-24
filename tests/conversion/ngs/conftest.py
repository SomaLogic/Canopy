"""Shared fixtures for NGS conversion tests."""

from __future__ import annotations

import pandas as pd
import pytest

from somadata.adat import Adat

# ---------------------------------------------------------------------------
# NGS ProcessSteps constants
# ---------------------------------------------------------------------------

NGS_NATIVE_STEPS = 'Raw Counts, Hyb Normalization, MedNormInt, PlateScale, PlatformSpecificCalibration, CrossPlatformCalibration'

# ---------------------------------------------------------------------------
# NGS Adat factory helpers
# ---------------------------------------------------------------------------


def make_ngs_adat(
    assay_version: str = '6k',
    process_steps: str = NGS_NATIVE_STEPS,
    n_samples: int = 2,
    n_plates: int = 1,
) -> Adat:
    """Build a minimal NGS Adat with required header and row metadata for conversion testing.

    Parameters
    ----------
    assay_version : str
        NGS platform version (e.g., '6k', '9k TMS', 'Calypso').
    process_steps : str
        Comma-separated ProcessSteps string.
    n_samples : int
        Number of sample rows.
    n_plates : int
        Number of unique PlateIds.

    Returns
    -------
    Adat
        Minimal NGS Adat suitable for conversion testing.
    """
    plate_ids = [f'PLT{100 + i}' for i in range(n_plates)]
    
    # Header metadata (required for NGS conversion)
    header = {
        '!AssayVersion': assay_version,
        '!ProcessSteps': process_steps,
        '!SOMAmerReferenceSource': '2025-04-10',
        '!Version': '4.0.1',  # DPQ version
        '!RunId': 'RUN12345',
        '!InstrumentType': 'NovaSeq6000',
        '!Flowcell': 'HFFKNDSXF',
        '!YieldDemux': '12500000',
        '!YieldQ30Demux': '11800000',
        '!Q30WeightedMean': '92.5',
        '!AdatId': 'GID-old-ngs-id',
        '!StudyMatrix': 'Plasma',
    }
    
    # Row metadata (NGS-specific fields)
    row_names = [
        'SampleId',
        'SampleType',
        'PlateId',
        'WellPosition',
        'SOMAmerReads',
        'SOMAmerNormReads',
        'MatrixType',
        'ProbePlate',
        'HybNorm_1_ScaleFactor',
        'MedNormInt_0-2_ScaleFactor',
    ]
    
    row_values = [
        [f'S{i}' for i in range(n_samples)],
        ['Sample'] * n_samples,
        [plate_ids[i % n_plates] for i in range(n_samples)],
        [f'A{i+1:02d}' for i in range(n_samples)],
        [str(14250000 - i * 100000) for i in range(n_samples)],
        [str(13900000 - i * 100000) for i in range(n_samples)],
        ['Plasma'] * n_samples,
        ['Lot2B'] * n_samples,
        [str(1.024 - i * 0.01) for i in range(n_samples)],
        [str(1.012 - i * 0.01) for i in range(n_samples)],
    ]
    
    # Column metadata (NGS SOMAmer annotations)
    col_names = [
        'SeqId',
        'Target',
        'Target Full Name',
        'Type',
        'Organism',
        'UniProt ID',
        'Entrez Gene ID',
        'Entrez Gene Symbol',
        'DRC_Level',
        'BlockList',
        'Dilution',
    ]
    
    col_values = [
        ['10000-01', '10001-02'],
        ['KCAB2', 'IL6'],
        ['Voltage-gated potassium channel', 'Interleukin-6'],
        ['Protein', 'Protein'],
        ['Human', 'Human'],
        ['Q13303', 'P05231'],
        ['8514', '3569'],
        ['KCNAB2', 'IL6'],
        ['1.0', '1.0'],
        ['False', 'False'],
        ['0.2', '0.2'],
    ]
    
    index = pd.MultiIndex.from_arrays(row_values, names=row_names)
    columns = pd.MultiIndex.from_arrays(col_values, names=col_names)
    data = [[1000.0] * len(col_values[0])] * n_samples
    
    return Adat(data=data, index=index, columns=columns, header_metadata=header)


@pytest.fixture
def minimal_ngs_adat() -> Adat:
    """Pytest fixture: minimal NGS Adat for testing."""
    return make_ngs_adat()


@pytest.fixture
def multi_plate_ngs_adat() -> Adat:
    """Pytest fixture: NGS Adat with multiple plates."""
    return make_ngs_adat(n_samples=4, n_plates=2)
