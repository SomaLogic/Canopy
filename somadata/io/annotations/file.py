from __future__ import annotations

import hashlib
import logging

import pandas as pd

from somadata import Annotations

from . import errors

CONFIG = {
    'skiprows': 8,
    'header': [0],
    'index_col': 0,
}


def read_annotations(filepath: str) -> Annotations:
    """Returns an Annotations object from the filepath/name.

    Parameters
    ----------
    filepath: str
        Either the absolute or relative path to the Excel file to be opened.

    Examples
    --------
    >>> annotations = somadata.read_annotations('path/to/annotations.xlsx')

    Returns
    -------
    annotations : Annotations
    """

    df = pd.read_excel(filepath, engine='openpyxl', dtype=object, **CONFIG)
    annotations = Annotations(data=df.values, index=df.index, columns=df.columns)
    annotations = annotations.dropna(how='all')

    return annotations
