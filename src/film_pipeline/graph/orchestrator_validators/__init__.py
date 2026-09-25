"""Compatibility aliases for the gate validators, now owned by ``governance``.

The whole validator surface is re-exported from the owner so the old import
path keeps resolving without duplicating the export list.
"""

from film_pipeline.governance.validators import *  # noqa: F403
from film_pipeline.governance.validators import __all__ as __all__
