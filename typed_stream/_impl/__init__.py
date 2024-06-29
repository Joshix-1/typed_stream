# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""The internal implementations of typed_stream."""

from __future__ import annotations

from . import file_streams, stream
from .file_streams import *  # noqa: F401, F403
from .stream import *  # noqa: F401, F403

__all__ = (
    *stream.__all__,
    *file_streams.__all__,
)
