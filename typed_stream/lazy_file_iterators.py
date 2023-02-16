"""Utilities for lazy iteration over lines of files."""
import contextlib
from collections.abc import Iterator
from io import BytesIO
from os import PathLike
from typing import (
    IO,
    TYPE_CHECKING,
    Any,
    AnyStr,
    TextIO,
    TypeGuard,
    TypeVar,
    overload,
)

PathLikeType = bytes | PathLike[bytes] | PathLike[str] | str
LFI = TypeVar("LFI", "LazyFileIterator[str]", "LazyFileIterator[bytes]")


def _is_bytes(
    lfi: "LazyFileIterator[AnyStr]",
) -> "TypeGuard[LazyFileIterator[bytes]]":
    """Return True if the lfi is LazyFileIterator[bytes]."""
    return lfi.encoding is None


class LazyFileIterator(Iterator[AnyStr]):
    """Iterate over a file line by line. Only open it when necessary.

    If you only partially iterate the file you have to call .close or use a
    with statement.

    with LazyFileIterator(...) as lfi:
        first_line = next(lfi)
    """

    path: PathLikeType
    encoding: str | None
    _iterator: Iterator[AnyStr] | None
    _file_object: IO[AnyStr] | None

    __slots__ = ("path", "encoding", "_iterator", "_file_object")

    if TYPE_CHECKING:

        @overload
        def __init__(
            self: "LazyFileIterator[str]",
            path: PathLikeType,
            *,
            encoding: str,
        ) -> None:
            """Nobody inspects the spammish repetition."""

        @overload
        def __init__(
            self: "LazyFileIterator[bytes]",
            path: PathLikeType,
        ) -> None:
            """Nobody inspects the spammish repetition."""

        @overload
        def __init__(
            self: "LazyFileIterator[bytes]",
            path: PathLikeType,
            *,
            encoding: None = None,
        ) -> None:
            """Nobody inspects the spammish repetition."""

    def __init__(
        self,
        path: PathLikeType,
        *,
        encoding: str | None = None,
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

    def __iter__(self) -> Iterator[AnyStr]:
        """Return self."""
        return self

    def __del__(self) -> None:
        """Close v."""
        self.close()

    if TYPE_CHECKING:

        @overload
        def _open_file(self: "LazyFileIterator[bytes]") -> BytesIO:
            ...

        @overload
        def _open_file(self: "LazyFileIterator[str]") -> TextIO:
            ...

    def _open_file(self) -> IO[Any]:
        """Open the underlying file."""
        if _is_bytes(self):
            return open(self.path, mode="rb")  # noqa: SIM115
        return open(self.path, encoding=self.encoding)  # noqa: SIM115

    def __next__(self) -> AnyStr:
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


class LazyFileIteratorRemovingEndsStr(LazyFileIterator[str]):
    """The same as LazyFileIterator[str] but it removes line-ends from lines."""

    def __next__(self) -> str:
        r"""Return the next line without '\n' in the end."""
        return super().__next__().removesuffix("\n")


class LazyFileIteratorRemovingEndsBytes(LazyFileIterator[bytes]):
    """The same as LazyFileIterator[bytes] but it removes line-ends from lines."""

    def __next__(self) -> bytes:
        r"""Return the next line without '\n' in the end."""
        return super().__next__().removesuffix(b"\n")
