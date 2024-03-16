# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Provide the Self type."""

from __future__ import annotations

import sys
from typing import NoReturn


def _fake_self() -> NoReturn:  # pragma: no cover
    return ...  # type: ignore[misc]


if sys.version_info < (3, 11):  # noqa: C901  # pragma: no cover
    try:
        from typing_extensions import Self
    except ImportError:
        Self = _fake_self()
else:
    try:
        from typing import Self
    except ImportError:  # pragma: no cover
        try:
            from typing_extensions import Self
        except ImportError:
            Self = _fake_self()

__all__ = ("Self",)
