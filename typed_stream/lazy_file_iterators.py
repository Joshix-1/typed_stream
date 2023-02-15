"""Utilities for lazy iteration over lines of files."""
import contextlib
from os import PathLike
from collections.abc import Iterator
from typing import Any, TextIO, TypeVar

PathLikeType = bytes | PathLike[bytes] | PathLike[str] | str
LFI = TypeVar("LFI", bound="LazyFileIterator")


class LazyFileIterator(Iterator[str]):
    """Iterate over a file line by line. Only open it when necessary.

    If you only partially iterate the file you have to call .close or use a
    with statement.

    with LazyFileIterator(...) as lfi:
        first_line = next(lfi)
    """

    path: PathLikeType
    encoding: str
    _iterator: Iterator[str] | None
    _file_object: TextIO | None

    __slots__ = ("path", "encoding", "_iterator", "_file_object")

    def __init__(
        self,
        path: PathLikeType,
        encoding: str = "UTF-8",
    ) -> None:
        """Create a LazyFileIterator."""
        self.path = path
        self.encoding = encoding
        self._iterator = None
        self._file_object = None

    def close(self) -> None:
        """Close the underlying file."""
        if self._file_object:
            self._file_object.close()
            self._file_object = None
            self._iterator = None

    def __iter__(self) -> Iterator[str]:
        """Return self."""
        return self

    def __del__(self) -> None:
        """Close v."""
        self.close()

    def _open_file(self) -> TextIO:
        """Open the underlying file."""
        return open(self.path, mode="r", encoding=self.encoding)  # noqa: SIM115

    def __next__(self) -> str:
        """Get the next line."""
        if self._iterator is None:
            self._file_object = self._open_file()
            self._iterator = iter(self._file_object)

        try:
            return next(self._iterator)
        except BaseException:
            with contextlib.suppress(Exception):
                self.close()
            raise

    def __enter__(self: LFI) -> LFI:
        """Return self."""
        return self

    def __exit__(self, *args: Any) -> None:
        """Close self."""
        self.close()


class LazyFileIteratorRemovingEnds(LazyFileIterator):
    """The same as LazyFileIterator but it removes line-ends from lines."""

    def __next__(self) -> str:
        r"""Return the next line without '\n' in the end."""
        return super().__next__().removesuffix("\n")
