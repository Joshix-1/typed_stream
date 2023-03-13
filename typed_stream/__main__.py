# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Easy interface for streamy handling of files."""
import argparse
import dataclasses
import operator
import sys
from collections.abc import Callable

from . import Stream, functions


@dataclasses.dataclass(frozen=True, slots=True)
class Options:
    """The options for this cool program."""

    debug: bool
    bytes: bool
    keep_ends: bool
    actions: tuple[str, ...]


def run_program(options: Options) -> str | None:
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
    for index, action in enumerate(options.actions, 1):
        if action.startswith("_"):
            return f"{index}: {action!r} isn't allowed to start with '_'."
        if hasattr(stream, action):
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
            elif action in operator.__all__:
                args.append(getattr(operator, action))
                full_action_qual = f"operator.{action}"
            else:
                # pylint: disable=eval-used
                args.append(eval(action, {}))  # nosec: B307
                full_action_qual = action
            code.extend((full_action_qual, ","))
    if method:
        if code and code[-1] == ",":
            code[-1] = ")"
        else:
            code.append(")")
        stream = method(*args)

    if isinstance(stream, Stream):
        stream.for_each(print)
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
