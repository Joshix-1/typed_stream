# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Easy interface for streamy handling of files."""

from __future__ import annotations

import argparse
import collections
import dataclasses
import operator
import sys
from collections.abc import Callable

from . import Stream, functions
from ._utils import count_required_positional_arguments


@dataclasses.dataclass(frozen=True, slots=True)
class Options:
    """The options for this cool program."""

    debug: bool
    bytes: bool
    keep_ends: bool
    actions: tuple[str, ...]


def run_program(options: Options) -> str | None:  # noqa: C901
    # pylint: disable=too-complex, too-many-branches, too-many-statements
    """Run the program with the options."""
    code: list[str]
    stream: Stream[bytes] | Stream[str] | object
    if options.bytes:
        stream = Stream(sys.stdin.buffer)
        code = ["Stream(sys.stdin.buffer)"]
        if not options.keep_ends:
            code.append(r""".map(bytes.removesuffix, b"\n")""")
            stream = stream.map(bytes.removesuffix, b"\n")
    else:
        stream = Stream(sys.stdin)
        code = ["Stream(sys.stdin)"]
        if not options.keep_ends:
            code.append(r""".map(str.removesuffix, "\n")""")
            stream = stream.map(str.removesuffix, "\n")

    method: None | Callable[[object], object] = None
    args: list[object] = []
    for index, action in Stream(options.actions).map(str.strip).enumerate(1):
        if action.startswith("_"):
            return f"{index}: {action!r} isn't allowed to start with '_'."
        args_left = (
            count_required_positional_arguments(method) - len(args)
            if method
            else 0
        )
        if (not args_left or args_left < 0) and hasattr(stream, action):
            if method:
                stream = method(*args)  # pylint: disable=not-callable
                args.clear()
                if code and code[-1] == ",":
                    code[-1] = ")"
                else:
                    code.append(")")
            method = getattr(stream, action)
            code.append(f".{action}(")
        else:
            if not method:
                return f"{action!r} needs to be a Stream method."
            full_action_qual: str
            if action in functions.__all__:
                args.append(getattr(functions, action))
                full_action_qual = f"typed_stream.functions.{action}"
            elif action in collections.__all__:
                args.append(getattr(collections, action))
                full_action_qual = f"collections.{action}"
            elif action in operator.__all__:
                args.append(getattr(operator, action))
                full_action_qual = f"operator.{action}"
            else:
                args.append(
                    eval(action, {})  # nosec: B307  # pylint: disable=eval-used
                )
                full_action_qual = action
            code.extend((full_action_qual, ","))
    if method:
        if code and code[-1] == ",":
            code[-1] = ")"
        else:
            code.append(")")
        stream = method(*args)

    if isinstance(stream, Stream):
        # pytype: disable=attribute-error
        stream.for_each(print)
        # pytype: enable=attribute-error
        code.append(".for_each(print)")
    elif stream:
        print(stream)
        code.insert(0, "print(")
        code.append(")")

    if options.debug:
        print("".join(code), file=sys.stderr)
    return None


def main() -> str | None:
    """Parse arguments and then run the program."""
    arg_parser = argparse.ArgumentParser(
        prog="typed_stream",
        description="Easy interface for streamy handling of files.",
        epilog="Do not run this with arguments from an untrusted source.",
    )
    arg_parser.add_argument("--debug", action="store_true")
    arg_parser.add_argument("--bytes", action="store_true")
    arg_parser.add_argument("--keep_ends", action="store_true")
    arg_parser.add_argument("actions", nargs="+")

    args = arg_parser.parse_args()
    options = Options(
        debug=bool(args.debug),
        bytes=bool(args.bytes),
        keep_ends=bool(args.keep_ends),
        actions=tuple(map(str, args.actions)),
    )
    return run_program(options)


sys.exit(main())
