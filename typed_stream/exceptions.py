"""Exception classes raised while handling Streams."""

__all__ = ("StreamEmptyError", "StreamFinishedError", "StreamIndexError")


class _StreamErrorBase(Exception):
    """Internal base class for StreamErrors."""


class StreamFinishedError(_StreamErrorBase):
    """You cannot perform operations on a finished Stream."""


class StreamEmptyError(_StreamErrorBase):
    """The Stream is empty."""


class StreamIndexError(_StreamErrorBase, IndexError):
    """Stream index out of range."""
