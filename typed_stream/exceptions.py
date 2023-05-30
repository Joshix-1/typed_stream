# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Exception classes raised while handling Streams."""

from __future__ import annotations

__all__ = ("StreamEmptyError", "StreamFinishedError", "StreamIndexError")


class StreamFinishedError(Exception):
    """You cannot perform operations on a finished Stream."""

    __slots__ = ()


class StreamEmptyError(Exception):
    """The Stream is empty."""

    __slots__ = ()


class StreamIndexError(IndexError):
    """Stream index out of range."""

    __slots__ = ()
