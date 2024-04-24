# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Typed Stream classes for easier handling of iterables."""

from __future__ import annotations

from typing import cast

from . import exceptions, file_streams, stream, streamable
from .exceptions import *  # noqa: F401, F403
from .file_streams import *  # noqa: F401, F403
from .stream import *  # noqa: F401, F403
from .streamable import *  # noqa: F401, F403
from .version import VERSION

__version__ = VERSION
__all__ = (
    stream.__all__
    + streamable.__all__
    + exceptions.__all__
    + file_streams.__all__
)

version_info: tuple[int, int, int] = cast(
    tuple[int, int, int], tuple(map(int, VERSION.split(".")))
)
if len(version_info) != 3:
    raise AssertionError(f"Invalid version: {VERSION}")

del annotations, cast
