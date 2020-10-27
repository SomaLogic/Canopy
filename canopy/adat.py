from __future__ import annotations
from typing import List, Dict
import pandas as pd
from .base import AdatMetaHelpers
from . import io

try:
    from cnorm import AdatNormalization
except ModuleNotFoundError:
    AdatNormalization = object


class Adat(AdatMetaHelpers, pd.DataFrame, AdatNormalization):
    """A Pandas `DataFrame` object with additional functionality to help with handling the adat file format.

    The adat file is stored as dataframe where the column and row metadata are stored as Pandas multiindices.
    While multiindices are not the most optimal solution for metadata that are continuous (e.g., scale factors),
    additional helper functions have been made to make accessing/modifying these data more end-user friendly and
    more consistent. The metadata outside of dataframe (header metadata in the adat) is stored in the 'header_metadata'
    class variable and handled via the '_metadata' Pandas keyword/variable.

    Modeled after:
    https://github.com/geopandas

    On subclassing the pandas dataframe:
    https://pandas.pydata.org/pandas-docs/stable/development/extending.html#subclassing-pandas-data-structures
    """
    _metadata = ['header_metadata']

    def __init__(self, *args, **kwargs) -> None:
        self.header_metadata = kwargs.pop('header_metadata', None)
        super(Adat, self).__init__(*args, **kwargs)

    @property
    def _constructor(self) -> Adat:
        return Adat

    @classmethod
    def from_file(cls, filepath: str) -> Adat:
        """Returns an Adat from the filepath/name.

        Parameters
        ----------
        filepath: str
            Either the absolute or relative path to the file to be opened.

        Returns
        -------
        adat : Adat

        Examples
        --------
        >>> adat = Adat.from_file('path/to/file.adat')
        """
        return io.file.read_file(filepath)

    @classmethod
    def from_features(cls, rfu_matrix: List[List[float]], row_metadata: Dict[str, List[str]],
                      column_metadata: Dict[str, List[str]], header_metadata: Dict[str, str]) -> Adat:

        """Returns an Adat from the component adat file format sections.

        Parameters
        ----------
        rfu_matrix : List[List[float]]
            An nSample x nSomamer matrix of the RFU data (by row) where each sub-array corresponds to a sample.

        row_metadata : Dict[str, List[str]]
            A dictionary of each column of the row metadata where the key-value
            pairs are column-name and an array of each sample's corresponding metadata

        column_metadata : Dict[str, List[str]]
            A dictionary of each row of the adat column metdata where the key-value pairs are
            row-name and an array of each somamer's corresponding metadata.

        header_metadata : Dict[str, str]
            A dictionary of each row of the header_metadata corresponds to a key-value pair.

        Returns
        -------
        adat : Adat

        Examples
        --------
        >>> adat = Adat.from_features(rfu_matrix, row_metadata, col_metadata, header_metadata)
        """

        index = pd.MultiIndex.from_arrays(list(row_metadata.values()), names=list(row_metadata.keys()))
        columns = pd.MultiIndex.from_arrays(list(column_metadata.values()), names=list(column_metadata.keys()))
        return Adat(data=rfu_matrix, index=index, columns=columns, header_metadata=header_metadata)

    def to_file(self, path: str, round_rfu: bool = True, convert_to_v3_seq_ids: bool = False) -> None:
        """Writes the adat to an adat formatted file with the given filename.

        Parameters
        ----------
        path : str
            Path that the file will be written to

        round_rfu : bool
            Rounds the file rfu matrix if set to True (default),
            otherwise leaves the matrix as-is.

        convert_to_v3_seq_ids : bool
            Combines the column metadata for SeqId and
            SeqIdVersion to the V3 style (12345-6_7)

        Returns
        -------
        None

        Examples
        --------
        >>> Adat.to_file('path/to/file.adat')
        """
        io.file.write_file(self, path, round_rfu)
