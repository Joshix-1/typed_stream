# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Provide the Self type."""

from __future__ import annotations

import typing

if typing.TYPE_CHECKING:  # pragma: no cover
    import sys

    if sys.version_info < (3, 11):
        from typing_extensions import Self
    else:
        Self = typing.Self
else:
    Self = getattr(typing, "Self", ...)


__all__ = ("Self",)
