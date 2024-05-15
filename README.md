# Typed Stream
![License](https://img.shields.io/pypi/l/typed-stream?label=License)
![Python](https://img.shields.io/pypi/pyversions/typed-stream?label=Python)
![Implementation](https://img.shields.io/pypi/implementation/typed-stream?label=Implementation)
![Total lines](https://img.shields.io/tokei/lines/github.com/Joshix-1/typed_stream?label=Total%20lines)
![Code size](https://img.shields.io/github/languages/code-size/Joshix-1/typed_stream)
[![Style: Black](https://img.shields.io/badge/Code%20Style-Black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/Imports-isort-1674b1.svg?labelColor=ef8336)](https://pycqa.github.io/isort)
[![Coverage](https://Joshix-1.github.io/typed_stream/coverage/badge.svg)](https://Joshix-1.github.io/typed_stream/coverage)

[![Downloads](https://pepy.tech/badge/typed-stream)](https://pepy.tech/project/typed-stream)
[![Downloads](https://pepy.tech/badge/typed-stream/month)](https://pepy.tech/project/typed-stream)
[![Downloads](https://pepy.tech/badge/typed-stream/week)](https://pepy.tech/project/typed-stream)


The Stream class is an [iterable](https://docs.python.org/3/library/collections.abc.html#collections.abc.Iterable) with utility methods for transforming it.

This library heavily uses itertools for great performance and simple code.

## Examples

<!--- BEGIN EXAMPLE --->
```py
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
>>> import typed_stream.functions
>>> # Get the longest package name from requirements-dev.txt
>>> (typed_stream.FileStream("requirements-dev.txt")
...     .filter()
...     .exclude(typed_stream.functions.method_partial(str.startswith, "#"))
...     .map(str.split, "==")
...     .starmap(lambda name, version = None: name)
...     .max(key=len))
'flake8-no-implicit-concat'
```
<!--- END EXAMPLE --->

In [examples](./examples) are more complex examples using Streams.

## Not yet asked questions

I'll try to answer questions that could occur.

### What do the versions mean?

I try to follow something similar to sem-ver. For versions before 1.0.0 this means the format is `0.<major>.<patch>`.
Any change that could be considered a breaking-change (adding things is not a breaking change) increases the `major` part. If only `patch` has changed, there was no breaking-change.
I try to avoid changes that break my own code, so even if `major` has been changed, it should probably be safe to upgrade.

### Why are there no changelogs?

I'm too lazy. I don't know of anybody using this (except me) and I don't need to write changelogs for myself.
If you need changelogs, please create an issue.

### Why EUPL-1.2-or-later?

- 🇪🇺
- AGPL3 is too long
- [Google EUPL Policy](https://opensource.google/documentation/reference/thirdparty/licenses#european_union_public_licence_eupl_not_allowed)

### Is it production-ready?

Probably.
