# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Java-like typed Stream class for easier handling of generators."""

from __future__ import annotations

from .exceptions import StreamEmptyError, StreamFinishedError, StreamIndexError
from .stream_abc import StreamABC
from .streamable import Streamable, StreamableSequence
from .streams import BinaryFileStream, FileStream, Stream
from .version import VERSION

__version__ = VERSION
__all__ = (
    "BinaryFileStream",
    "FileStream",
    "Stream",
    "StreamABC",
    "StreamEmptyError",
    "StreamFinishedError",
    "StreamIndexError",
    "Streamable",
    "StreamableSequence",
    "VERSION",
    "version_info",
)

version_info: tuple[int, ...] = tuple(Stream(VERSION.split(".")).map(int))
