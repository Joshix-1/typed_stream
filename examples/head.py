#!/usr/bin/env python3

# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""A simple head program."""

from __future__ import annotations

import contextlib
import sys

from typed_stream import BinaryFileStream, Stream

# pylint: disable=duplicate-code


def head(*args: str) -> None | str:
    """Print the head."""
    if not args:
        return "No file given. To read from stdin use '-'"
    if len(args) > 2:
        return "More than one file given."

    stream: Stream[bytes]
    if args[0] == "-":
        print(
            "Reading from stdin. To read from a file '-' use './-'",
            file=sys.stderr,
        )
        stream = Stream(sys.stdin.buffer)
    else:
        stream = BinaryFileStream(args[0], True)

    count = int(args[1]) if len(args) == 2 else 10
    stream.limit(count).for_each(sys.stdout.buffer.write)
    return None


if __name__ == "__main__":
    with contextlib.suppress(BrokenPipeError):
        sys.exit(head(*sys.argv[1:]))
