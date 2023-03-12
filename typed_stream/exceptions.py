# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Exception classes raised while handling Streams."""

__all__ = ("StreamEmptyError", "StreamFinishedError", "StreamIndexError")


class _StreamErrorBase(Exception):
    """Internal base class for StreamErrors."""

    __slots__ = ()


class StreamFinishedError(_StreamErrorBase):
    """You cannot perform operations on a finished Stream."""

    __slots__ = ()


class StreamEmptyError(_StreamErrorBase):
    """The Stream is empty."""

    __slots__ = ()


class StreamIndexError(_StreamErrorBase, IndexError):
    """Stream index out of range."""

    __slots__ = ()
