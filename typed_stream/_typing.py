# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Provide types."""

from __future__ import annotations

import typing

from .functions import return_arg

if typing.TYPE_CHECKING:  # pragma: no cover
    import sys

    if sys.version_info < (3, 11):
        from typing_extensions import Self, TypeVarTuple, Unpack
    else:
        from typing import Self, TypeVarTuple, Unpack

    if sys.version_info < (3, 12):
        from typing_extensions import override
    else:
        from typing import override
else:
    Self = getattr(typing, "Self", ...)  # pylint: disable=invalid-name
    TypeVarTuple = getattr(typing, "TypeVarTuple", return_arg)
    Unpack = getattr(typing, "Unpack", ...)  # pylint: disable=invalid-name
    override = getattr(typing, "override", return_arg)

__all__ = ("Self", "TypeVarTuple", "Unpack", "override")
