# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Java-like typed Stream class for easier handling of generators."""

from __future__ import annotations

from typing import cast

from . import exceptions, streamable, streams
from .exceptions import *  # noqa: F401, F403
from .streamable import *  # noqa: F401, F403
from .streams import *  # noqa: F401, F403
from .version import VERSION

__version__ = VERSION
__all__ = streams.__all__ + streamable.__all__ + exceptions.__all__

version_info: tuple[int, int, int] = cast(
    tuple[int, int, int], tuple(map(int, VERSION.split(".")))
)
if len(version_info) != 3:
    raise AssertionError(f"Invalid version: {VERSION}")

del annotations, cast
