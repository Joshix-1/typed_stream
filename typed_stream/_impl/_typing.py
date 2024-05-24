# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Provide types."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # noqa: C901  # pragma: no cover
    import sys

    if sys.version_info < (3, 11):
        from typing_extensions import Self, TypeVarTuple, Unpack
    else:
        from typing import Self, TypeVarTuple, Unpack

    if sys.version_info < (3, 12):
        from typing_extensions import assert_never, assert_type, override
    else:
        from typing import assert_never, assert_type, override
else:

    def return_arg(arg: object, *_) -> object:
        """Return the argument."""
        return arg

    def assert_never(arg: object, /) -> typing.Never:
        """Should never be called."""
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
