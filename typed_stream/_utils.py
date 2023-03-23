# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""General utility classes and functions."""

import inspect
from collections.abc import Callable
from typing import Final, Generic, NoReturn, TypeVar

__all__ = (
    "DEFAULT_VALUE",
    "DefaultValueType",
    "FunctionWrapperIgnoringArgs",
    "IndexValueTuple",
    "count_required_positional_arguments",
    "raise_exception",
)


T = TypeVar("T")


def count_required_positional_arguments(  # type: ignore[misc]
    fun: Callable[..., object], /  # noqa: W504
) -> int:
    """Count the required positional arguments."""
    return len(
        [
            param
            for param in inspect.signature(fun).parameters.values()
            if param.kind
            in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            }
            if param.default == inspect.Parameter.empty
        ]
    )


def raise_exception(exc: BaseException, /) -> NoReturn:
    """Raise the exception."""
    raise exc


class DefaultValueType:
    """Class to use as default when None is a valid value."""

    __slots__ = ()


DEFAULT_VALUE: Final[DefaultValueType] = DefaultValueType()


class FunctionWrapperIgnoringArgs(Generic[T]):
    """Wrap a function that takes no arguments."""

    _callable: Callable[[], T]

    __slots__ = ("_callable",)

    def __init__(self, fun: Callable[[], T], /) -> None:
        """Set the callable as attribute of self."""
        self._callable = fun

    def __call__(self, *_: object) -> T:
        """Call the callable while ignoring all arguments."""
        return self._callable()


class IndexValueTuple(tuple[int, T], Generic[T]):
    """A tuple to hold index and value."""

    __slots__ = ()

    @property
    def idx(self: tuple[int, object]) -> int:
        """The index."""
        return self[0]

    @property
    def val(self: tuple[int, T]) -> T:
        """The value."""
        return self[1]
