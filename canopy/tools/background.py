from .math import mad
import numpy as np


def compute_estimated_limit_of_detection(adat):
    buffer_adat = adat.pick_on_meta(axis=0, name='SampleType', values=['Buffer'])
    lod_vals = buffer_adat.apply(np.median) + 4.9 * buffer_adat.apply(mad)
    return lod_vals


def subtract_background_from_adat(adat):
    backgrounds = []
    dilution_index = [i for i, x in enumerate(adat.columns.names) if x == 'Dilution'][0]
    buffer_adat = adat.pick_on_meta(axis=0, name='SampleType', values=['Buffer'])
    for column_index in buffer_adat:
        if column_index[dilution_index] == '0':  
            backgrounds.append(0)
        else:
            backgrounds.append(buffer_adat[column_index].median())
    background_subtracted_adat = adat - backgrounds
    return background_subtracted_adat


def subtract_bad_background_from_adats(adat, good_background_adats_plate_ids, bad_background_adats_plate_id):
    # Subset adat to individual plates
    good_background_adats = (
        adat.pick_on_meta(axis=0, name='SampleType', values=['Buffer'])
            .pick_on_meta(axis=0, name='PlateId', values=good_background_adats_plate_ids)
    )
    bad_background_adats = (
        adat.pick_on_meta(axis=0, name='SampleType', values=['Buffer'])
            .pick_on_meta(axis=0, name='PlateId', values=[bad_background_adats_plate_id])
    )

    # Find the background in the bad background adat that needs to be subtracted
    backgrounds_to_subtract = (bad_background_adats.median() - good_background_adats.groupby('PlateId').median().median()).values

    # Zero out the hyb controls since "background" doesn't apply to them
    for i, dilution in enumerate(adat.columns.get_level_values('Dilution')):
        if dilution == '0':
            backgrounds_to_subtract[i] = 0

    # Copy adat so we don't overwrite the original one
    mod_adat = adat.copy()
    mod_adat.iloc[adat.index.get_level_values('PlateId') == bad_background_adats_plate_id] = mod_adat.iloc[adat.index.get_level_values('PlateId') == bad_background_adats_plate_id] - backgrounds_to_subtract
    return mod_adat
