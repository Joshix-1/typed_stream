# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Defaults for arguments."""

from __future__ import annotations

import typing

__all__ = (
    "DEFAULT_VALUE",
    "DefaultValueType",
)


@typing.final
class DefaultValueType:
    """Class to use as default when None is a valid value."""

    __slots__ = ()


DEFAULT_VALUE: typing.Final[DefaultValueType] = DefaultValueType()
