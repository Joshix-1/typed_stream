#!/usr/bin/env python3
"""A simple unsafe calculator."""
import sys
from typing import Any

from typed_stream import Stream


def print_prompt(*args: Any) -> None:
    """Print an input prompt to stderr."""
    print("> ", end="", flush=True)


def main() -> None:
    """Query inputs."""
    print_prompt()
    Stream(sys.stdin).map(eval).peek(print).for_each(print_prompt)


if __name__ == "__main__":
    main()
