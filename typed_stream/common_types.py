# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Helpful types."""
from abc import abstractmethod
from os import PathLike
from typing import Protocol, TypeAlias, TypeGuard, TypeVar

__all__ = (
    "PathLikeType",
    "StarCallable",
    "SupportsAdd",
    "SupportsComparison",
    "SupportsGreaterThan",
    "SupportsLessThan",
    "TypeGuardingCallable",
)

PathLikeType = bytes | PathLike[bytes] | PathLike[str] | str


T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)


class TypeGuardingCallable(Protocol[T_co]):
    """A class representing a function that type guards."""

    @abstractmethod
    def __call__(self, value: object) -> TypeGuard[T_co]:
        """Return True if value isinstance of TGC_CHECKED."""


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
