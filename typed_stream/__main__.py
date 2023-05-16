# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Easy interface for streamy handling of standard input."""
import argparse
import dataclasses
import sys

from . import Stream
from ._cli_argument_parser import CLIArgumentParser


@dataclasses.dataclass(frozen=True, slots=True)
class Options:
    """The options for this cool program."""

    debug: bool
    bytes: bool
    keep_ends: bool
    actions: tuple[str, ...]


def run_program(options: Options) -> None:
    """Run the program with the options."""
    cli_parser = CLIArgumentParser(
        as_bytes=options.bytes, keep_ends=options.keep_ends
    )

    cli_parser.add_tokens(*options.actions)

    stream = cli_parser.run()

    if isinstance(stream, Stream):
        stream.for_each(print)
        code_fmt = "{code}.for_each(print)"
    elif stream:
        print(stream)
        code_fmt = "print({code})"
    else:
        code_fmt = "{code}"

    if options.debug:
        print(code_fmt.format(code=cli_parser.get_code()), file=sys.stderr)


def main() -> None:
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
    run_program(options)


main()
