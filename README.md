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

```py
from typed_stream import FileStream, Stream

# Get sum of 10 squares
print(Stream.range(stop=10).map(lambda x: x * x).sum())
# same as above
print(sum(Stream.counting().limit(10).map(pow, 2)))

# sum first 100 odd numbers
print(Stream.counting(start=1, step=2).limit(100).sum())

# Get all the package names from requirements-dev.txt
package_names: tuple[str, ...] = FileStream("requirements-dev.txt")\
    .filter()\
    .exclude(lambda line: line.startswith("#"))\
    .map(str.split, "==", 1)\
    .starmap(lambda name, version = None: name)\
    .collect()
print(package_names)
```

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
