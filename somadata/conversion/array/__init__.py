"""Array-specific ADAT v2.0 conversion sub-package.

Public API
----------
ArrayConversionContext : dataclass
    Shared state passed between header, COL_DATA, and ROW_DATA conversion
    functions so that values extracted in the header step are available to
    the sample-annotation step.
"""

from __future__ import annotations

from somadata.conversion.array.context import ArrayConversionContext

__all__ = ['ArrayConversionContext']
