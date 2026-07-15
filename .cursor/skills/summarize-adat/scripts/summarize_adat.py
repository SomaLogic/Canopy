"""Print a concise structural summary of an ADAT file using somadata."""

from __future__ import annotations

import sys
import warnings

warnings.filterwarnings('ignore')

import somadata


def summarize(path: str) -> None:
    adat = somadata.read_adat(path)
    hm = adat.header_metadata

    print(f'=== ADAT SUMMARY: {path} ===\n')

    # --- Header ---
    print('HEADER')
    key_fields = [
        '!Version',
        '!Title',
        '!AssayType',
        '!AssayVersion',
        '!StudyMatrix',
        '!StudyOrganism',
        '!ProcessSteps',
        '!CreatedDate',
        '!RunId',
    ]
    for k in key_fields:
        if k in hm:
            print(f'  {k}: {hm[k]}')
    other = {k: v for k, v in hm.items() if k not in key_fields}
    if other:
        print(f'  ... +{len(other)} additional header fields')

    # --- Shape ---
    n_samples, n_analytes = adat.shape
    print(f'\nSHAPE')
    print(f'  Samples (rows):  {n_samples}')
    print(f'  Analytes (cols): {n_analytes}')

    # --- Row metadata ---
    print(f'\nROW METADATA ({len(adat.index.names)} fields)')
    for name in adat.index.names:
        vals = adat.index.get_level_values(name)
        unique = vals.unique()
        if len(unique) <= 8:
            print(f'  {name}: {sorted(str(v) for v in unique)}')
        else:
            sample = sorted(str(v) for v in unique)[:3]
            print(f'  {name}: [{", ".join(sample)}, ...] ({len(unique)} unique)')

    # --- Sample type breakdown ---
    if 'SampleType' in adat.index.names:
        counts = adat.index.get_level_values('SampleType').value_counts()
        print(f'\nSAMPLE TYPE COUNTS')
        for st, n in counts.items():
            print(f'  {st}: {n}')

    # --- Column metadata ---
    print(f'\nCOLUMN METADATA ({len(adat.columns.names)} fields)')
    print(f'  Fields: {adat.columns.names}')

    # Units breakdown if present
    if 'Units' in adat.columns.names:
        units = adat.columns.get_level_values('Units').unique().tolist()
        print(f'  Units: {units}')

    # HybControl split if present
    if 'HybControl' in adat.columns.names:
        is_hyb = adat.columns.get_level_values('HybControl')
        n_hyb = sum(str(v).lower() in ('true', '1') for v in is_hyb)
        print(f'  HybControl analytes: {n_hyb}, Protein analytes: {n_analytes - n_hyb}')

    # Dilution groups if present
    if 'Dilution' in adat.columns.names:
        dils = adat.columns.get_level_values('Dilution').unique().tolist()
        print(f'  Dilution groups: {dils}')

    print()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python summarize_adat.py <path_to.adat>')
        sys.exit(1)
    summarize(sys.argv[1])
