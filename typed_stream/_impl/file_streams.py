# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Stream classes for streaming file data."""

from __future__ import annotations

from types import EllipsisType
from typing import AnyStr, Literal

from ._lazy_file_iterators import (
    LazyFileIterator,
    LazyFileIteratorRemovingEndsBytes,
    LazyFileIteratorRemovingEndsStr,
)
from ._types import PathLikeType
from ._typing import override
from .stream import Stream

__all__: tuple[Literal["BinaryFileStream"], Literal["FileStream"]] = (
    "BinaryFileStream",
    "FileStream",
)


class FileStreamBase(Stream[AnyStr]):
    """ABC for file streams."""

    _file_iterator: None | LazyFileIterator[AnyStr]
    __slots__ = ("_file_iterator",)

    def _close_source(self) -> None:
        """Close the source of the Stream. Used in FileStream."""
        if not self._file_iterator:
            return
        self._file_iterator.close()
        self._file_iterator = None

    @override
    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        if not self._file_iterator:
            return (...,)

        return (
            self._file_iterator.path,
            self._file_iterator.encoding,
            # pylint: disable=unidiomatic-typecheck
            type(self._file_iterator) is LazyFileIterator,
        )


class FileStream(FileStreamBase[str]):
    """Lazily iterate over a file."""

    __slots__ = ()

    def __init__(
        self,
        data: PathLikeType | EllipsisType,
        encoding: str = "UTF-8",
        keep_line_ends: bool = False,
    ) -> None:
        """Create a new FileStream.

        To create a finished FileStream do FileStream(...).
        """
        if isinstance(data, EllipsisType):
            self._file_iterator = None
            super().__init__(...)
            return

        self._file_iterator = (
            LazyFileIterator(data, encoding=encoding)
            if keep_line_ends
            else LazyFileIteratorRemovingEndsStr(data, encoding=encoding)
        )
        super().__init__(self._file_iterator, self._close_source)

    @classmethod
    @override
    def _module(cls) -> str:
        if cls == FileStream:
            return "typed_stream"
        return cls.__module__


class BinaryFileStream(FileStreamBase[bytes]):
    """Lazily iterate over the lines of a file."""

    __slots__ = ()

    def __init__(
        self,
        data: PathLikeType | EllipsisType,
        keep_line_ends: bool = False,
    ) -> None:
        """Create a new BinaryFileStream.

        To create a finished BinaryFileStream do BinaryFileStream(...).
        """
        if isinstance(data, EllipsisType):
            self._file_iterator = None
            super().__init__(...)
            return

        self._file_iterator = (
            LazyFileIterator(data)
            if keep_line_ends
            else LazyFileIteratorRemovingEndsBytes(data)
        )
        super().__init__(self._file_iterator, self._close_source)

    @classmethod
    @override
    def _module(cls) -> str:
        if cls == BinaryFileStream:
            return "typed_stream"
        return cls.__module__
