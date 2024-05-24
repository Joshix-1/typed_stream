# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Provide types."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # noqa: C901  # pragma: no cover
    import sys

    if sys.version_info < (3, 11):
        from typing_extensions import (
            Self,
            TypeVarTuple,
            Unpack,
            assert_never,
            assert_type,
        )
    else:
        from typing import Self, TypeVarTuple, Unpack, assert_never, assert_type

    if sys.version_info < (3, 12):
        from typing_extensions import override
    else:
        from typing import override
else:

    def return_arg(arg: object, *_) -> object:
        """Return the argument."""
        return arg

    def assert_never(arg: object, /) -> typing.Never:
        """Never call this."""
        raise AssertionError(f"{arg} was not never")

    Self = getattr(typing, "Self", ...)
    TypeVarTuple = getattr(typing, "TypeVarTuple", return_arg)
    Unpack = getattr(typing, "Unpack", ...)
    override = getattr(typing, "override", return_arg)
    assert_type = getattr(typing, "assert_type", return_arg)
    assert_never = getattr(typing, "assert_never", assert_never)

__all__ = (
    "Self",
    "TypeVarTuple",
    "Unpack",
    "override",
    "assert_type",
    "assert_never",
)
