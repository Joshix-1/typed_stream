# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Helpful types."""

from __future__ import annotations

import abc
from abc import abstractmethod
from collections.abc import Callable, Iterable, Iterator
from os import PathLike
from typing import Generic, Protocol, TypeAlias, TypeGuard, TypeVar

from ._typing import override

__all__ = (
    "ClassWithCleanUp",
    "Closeable",
    "IteratorProxy",
    "PathLikeType",
    "PrettyRepr",
    "StarCallable",
    "SupportsAdd",
    "SupportsComparison",
    "SupportsGreaterThan",
    "SupportsLessThan",
    "TypeGuardingCallable",
)

PathLikeType = bytes | PathLike[bytes] | PathLike[str] | str

T = TypeVar("T")
V = TypeVar("V")
T_co = TypeVar("T_co", covariant=True)
V_contra = TypeVar("V_contra", contravariant=True)


class TypeGuardingCallable(Protocol[T_co, V_contra]):
    """A class representing a function that type guards."""

    @abstractmethod
    def __call__(self, value: V_contra) -> TypeGuard[T_co]:
        """Return True if value isinstance of T_co."""


# pylint: disable=invalid-name
SC_IN_contra = TypeVar("SC_IN_contra", contravariant=True)
SC_OUT_co = TypeVar("SC_OUT_co", covariant=True)
# pylint: enable=invalid-name


class StarCallable(Protocol[SC_IN_contra, SC_OUT_co]):
    """A class representing a function, that takes many arguments."""

    @abstractmethod
    def __call__(self, *args: SC_IN_contra) -> SC_OUT_co:
        """Handle the arguments."""


class SupportsLessThan(Protocol):
    """A class that supports comparison with less than."""

    @abstractmethod
    def __lt__(self: T, other: T) -> bool:
        """Compare to another instance of the same type."""


class SupportsGreaterThan(Protocol):
    """A class that supports comparison with less than."""

    @abstractmethod
    def __gt__(self: T, other: T) -> bool:
        """Compare to another instance of the same type."""


SupportsComparison: TypeAlias = SupportsGreaterThan | SupportsLessThan


class SupportsAdd(Protocol):
    """A class that supports addition."""

    @abstractmethod
    def __add__(self: T, other: T) -> T:
        """Add another instance of the same type to self."""


class Closeable(abc.ABC):
    """Class that can be closed."""

    __slots__ = ()

    @abc.abstractmethod
    def close(self) -> None:
        """Run clean-up if not run yet."""

    def __del__(self) -> None:
        """Run close."""
        self.close()

    def __enter__(self: T) -> T:
        """Return self."""
        return self

    def __exit__(self, *args: object) -> None:
        """Run close."""
        self.close()


class PrettyRepr(abc.ABC):
    """ABC to inherit from to get a better repr."""

    __slots__ = ()

    @override
    def __repr__(self) -> str:
        """Return the string representation of self."""
        args = ",".join(
            [("..." if arg is ... else repr(arg)) for arg in self._get_args()]
        )
        return (
            f"{self.__class__.__module__}.{self.__class__.__qualname__}({args})"
        )

    @abc.abstractmethod
    def _get_args(self) -> tuple[object, ...]:  # pragma: no cover
        """Return the args used to initializing self."""


class ClassWithCleanUp(Closeable, PrettyRepr):
    """A class that has a cleanup_fun and a close method."""

    cleanup_fun: Callable[[], object | None] | None

    __slots__ = ("cleanup_fun",)

    def __init__(self, cleanup_fun: Callable[[], object | None]) -> None:
        """Initialize this class."""
        self.cleanup_fun = cleanup_fun

    @override
    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return (self.cleanup_fun,)

    @override
    def close(self) -> None:
        """Run clean-up if not run yet."""
        if self.cleanup_fun:
            self.cleanup_fun()
            self.cleanup_fun = None


class IteratorProxy(Iterator[V], Generic[V, T], PrettyRepr, abc.ABC):
    """Proxy an iterator."""

    _iterator: Iterator[T]
    __slots__ = ("_iterator",)

    def __init__(self, iterable: Iterable[T]) -> None:
        """Init self."""
        self._iterator = iter(iterable)

    @override
    def __iter__(self) -> Iterator[V]:
        """Return self."""
        return self

    @override
    @abc.abstractmethod
    def __next__(self) -> V:
        """Return the next element."""

    @override
    def _get_args(self) -> tuple[object, ...]:
        """Return the args used to initializing self."""
        return (self._iterator,)
