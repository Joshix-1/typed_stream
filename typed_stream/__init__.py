# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Typed Stream classes for easier handling of iterables.

Examples:
>>> import typed_stream
>>> # Get sum of 10 squares
>>> typed_stream.Stream.range(stop=10).map(lambda x: x * x).sum()
285
>>> # same as above
>>> sum(typed_stream.Stream.counting().limit(10).map(pow, 2))
285
>>> # sum first 100 odd numbers
>>> typed_stream.Stream.counting(start=1, step=2).limit(100).sum()
10000
>>> (typed_stream.Stream.counting()
...     .filter(typed_stream.functions.is_odd).limit(100).sum())
10000
>>> (typed_stream.Stream.counting()
...     .exclude(typed_stream.functions.is_even).limit(100).sum())
10000
>>> # Get the longest package name from requirements-dev.txt
>>> (typed_stream.FileStream("requirements-dev.txt")
...     .filter()
...     .exclude(lambda line: line.startswith("#"))
...     .map(str.split, "==")
...     .starmap(lambda name, version = None: name)
...     .max(key=len))
'flake8-no-implicit-concat'
"""
# isort:skip_file

from . import _impl, version
from . import functions  # noqa: F401
from ._impl.exceptions import *  # noqa: F401, F403
from ._impl.file_streams import *  # noqa: F401, F403s
from ._impl.stream import *  # noqa: F401, F403
from ._impl.streamable import *  # noqa: F401, F403

__all__ = _impl.__all__
__version__ = version.VERSION

# fmt: off
(_impl.Stream(__all__)  # noqa: F405
    .map(globals().__getitem__)
    .map(setattr, "__module__", "typed_stream")
    .for_each())
# fmt: on
