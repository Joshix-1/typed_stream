"""Exception classes raised while handling Streams."""

__all__ = ("StreamEmptyError", "StreamFinishedError")


class _StreamErrorBase(Exception):
    """Internal base class for StreamErrors."""


class StreamFinishedError(_StreamErrorBase):
    """You cannot perform operations on a finished Stream."""


class StreamEmptyError(_StreamErrorBase):
    """The Stream is empty."""
