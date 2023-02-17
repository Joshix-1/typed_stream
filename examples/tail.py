#!/usr/bin/env python3
"""A simple tail program."""
import sys

from typed_stream import BinaryFileStream, Stream


def tail(*args: str) -> None | str:
    """Print the tail."""
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
    stream.tail(count).for_each(sys.stdout.buffer.write)
    return None


if __name__ == "__main__":
    sys.exit(tail(*sys.argv[1:]))
