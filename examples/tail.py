#!/usr/bin/env python3
import sys

from typed_stream import FileStream, Stream


def tail(*args: str) -> None | str:
    if not args:
        return "No file given. To read from stdin use '-'"
    if len(args) > 2:
        return "More than one file given."
    count = int(args[1]) if len(args) == 2 else 5
    if args[0] == "-":
        print(
            "Reading from stdin. To read from a file '-' use './-'",
            file=sys.stderr,
        )
        Stream(sys.stdin).tail(count).for_each(lambda x: print(x, end=""))
    else:
        FileStream(args[0]).tail(count).map(repr).for_each(print)
    return None


if __name__ == "__main__":
    sys.exit(tail(*sys.argv[1:]))
