"""Input readers: turn prepared local files into validated objects.

This layer never touches the network. Downloading and standardising met-ocean data is a
separate project's job (see ``docs/environment-data-format.md``); ``water-path`` only reads
the file it produces.
"""

from waterpath.io.environment import ConditionsInputError, open_conditions, to_components
from waterpath.io.routes import NetworkInputError, load_network

__all__ = [
    "load_network",
    "NetworkInputError",
    "open_conditions",
    "to_components",
    "ConditionsInputError",
]
