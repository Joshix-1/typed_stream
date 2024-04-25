# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Exception classes raised while handling Streams."""

from __future__ import annotations

from typing import Literal

__all__: tuple[
    Literal["StreamEmptyError"],
    Literal["StreamFinishedError"],
    Literal["StreamIndexError"],
] = ("StreamEmptyError", "StreamFinishedError", "StreamIndexError")


class StreamFinishedError(ValueError):
    """You cannot perform operations on a finished Stream."""

    __slots__ = ()


class StreamEmptyError(ValueError):
    """The Stream is empty."""

    __slots__ = ()


class StreamIndexError(IndexError):
    """Stream index out of range."""

    __slots__ = ()
