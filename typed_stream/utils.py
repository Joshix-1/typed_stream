# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""General utility functions."""

import inspect
from collections.abc import Callable


__all__ = ("count_required_positional_arguments",)


def count_required_positional_arguments(fun: Callable[..., object], /) -> int:
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
