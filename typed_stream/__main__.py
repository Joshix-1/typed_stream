# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Easy interface for streamy handling of files."""

from __future__ import annotations

import argparse
import builtins
import collections
import dataclasses
import inspect
import json
import operator
import sys
import textwrap
import traceback
from collections.abc import Callable, Mapping
from typing import cast

from ._impl import Stream, functions
from ._impl._utils import count_required_positional_arguments

MODULES = (builtins, collections, functions, operator)
MODULE_FULL_NAMES: Mapping[str, str] = {
    mod.__name__: (
        "typed_stream.functions" if mod is functions else mod.__name__
    )
    for mod in MODULES
}
EVAL_GLOBALS: Mapping[str, object] = dict(
    Stream(MODULES[1:])
    .flat_map(lambda mod: ((name, getattr(mod, name)) for name in mod.__all__))
    .chain((mod.__name__, mod) for mod in MODULES)
)


@dataclasses.dataclass(frozen=True, slots=True)
class Options:
    """The options for this cool program."""

    debug: bool
    bytes: bool
    keep_ends: bool
    no_eval: bool
    actions: tuple[str, ...]


def run_program(options: Options) -> str | None:  # noqa: C901
    # pylint: disable=too-complex, too-many-branches, too-many-locals, too-many-statements, line-too-long
    """Run the program with the options.

    >>> import contextlib, io
    >>> in_ = sys.stdin
    >>> sys.stdin = io.StringIO("200\\n1000\\n30\\n4")
    >>> with contextlib.redirect_stderr(io.StringIO()) as err:
    ...     run_program(Options(
    ...         debug=True,
    ...         bytes=False,
    ...         keep_ends=False,
    ...         no_eval=False,
    ...         actions=("map", "int", "sum"),
    ...     ))
    1234
    >>> print("\\n".join(err.getvalue().split("\\n")[-2:]))
    import sys,typed_stream;print(typed_stream.Stream(sys.stdin).map(str.removesuffix, "\\n").map(int).sum())
    <BLANKLINE>
    >>> sys.stdin = io.StringIO("300\\n1000\\n20\\n4")
    >>> with contextlib.redirect_stderr(io.StringIO()) as err:
    ...     run_program(Options(
    ...         debug=True,
    ...         bytes=False,
    ...         keep_ends=False,
    ...         no_eval=False,
    ...         actions=("map", "int", "collect", "builtins.sum")
    ...     ))
    1324
    >>> print("\\n".join(err.getvalue().split("\\n")[-2:]))
    import builtins,sys,typed_stream;print(typed_stream.Stream(sys.stdin).map(str.removesuffix, "\\n").map(int).collect(builtins.sum))
    <BLANKLINE>
    >>> sys.stdin = io.StringIO("")
    >>> with contextlib.redirect_stderr(io.StringIO()) as err:
    ...     ret = run_program(Options(
    ...         debug=True,
    ...         bytes=False,
    ...         keep_ends=False,
    ...         no_eval=False,
    ...         actions=("map", "int", "(°_°)")
    ...     ))
    >>> assert not err.getvalue()
    >>> assert isinstance(ret, str)
    >>> assert "SyntaxError" in ret
    >>> assert "(°_°)" in ret
    >>> sys.stdin = io.StringIO("")
    >>> with contextlib.redirect_stderr(io.StringIO()) as err:
    ...     ret = run_program(Options(
    ...         debug=True,
    ...         bytes=False,
    ...         keep_ends=False,
    ...         no_eval=False,
    ...         actions=("map", "xxx")
    ...     ))
    >>> assert not err.getvalue()
    >>> assert isinstance(ret, str)
    >>> assert "NameError" in ret
    >>> assert "xxx" in ret
    >>> sys.stdin = io.StringIO("")
    >>> with contextlib.redirect_stderr(io.StringIO()) as err:
    ...     ret = run_program(Options(
    ...         debug=True,
    ...         bytes=False,
    ...         keep_ends=False,
    ...         no_eval=True,
    ...         actions=("map", "xxx")
    ...     ))
    >>> assert not err.getvalue()
    >>> print(ret)
    Can't parse 'xxx' without eval.
    >>> sys.stdin = io.StringIO("")
    >>> with contextlib.redirect_stderr(io.StringIO()) as err:
    ...     ret = run_program(Options(
    ...         debug=True,
    ...         bytes=False,
    ...         keep_ends=False,
    ...         no_eval=True,
    ...         actions=("map", "int", "collect", "sum")
    ...     ))
    >>> assert not err.getvalue()
    >>> print(ret)
    StreamableSequence object has no attribute 'sum'. \
To pass it as argument to Stream.collect use 'builtins.sum'.
    >>> sys.stdin = io.TextIOWrapper(io.BytesIO(b"200\\n1000\\n30\\n4"))
    >>> with contextlib.redirect_stderr(io.StringIO()) as err:
    ...     run_program(Options(
    ...         debug=True,
    ...         bytes=True,
    ...         keep_ends=True,
    ...         no_eval=True,
    ...         actions=("flat_map", "iter", "map", "hex", "collect", "Counter")
    ...     ))
    {"0x32": 1, "0x30": 6, "0xa": 3, "0x31": 1, "0x33": 1, "0x34": 1}
    >>> print("\\n".join(err.getvalue().split("\\n")[-2:]))
    import collections,json,sys,typed_stream;print(json.dumps(dict(typed_stream.Stream(sys.stdin.buffer).flat_map(iter).map(hex).collect(collections.Counter))))
    <BLANKLINE>
    >>> sys.stdin = io.TextIOWrapper(io.BytesIO(b"1\\n2\\n3\\n4"))
    >>> with contextlib.redirect_stderr(io.StringIO()) as err:
    ...     run_program(Options(
    ...         debug=True,
    ...         bytes=False,
    ...         keep_ends=True,
    ...         no_eval=True,
    ...         actions=("map", "int", "filter", "is_even", "map", "mul", "10")
    ...     ))
    20
    40
    >>> f"\\n{err.getvalue()}".endswith(
    ...     "Stream(sys.stdin).map(int).filter(typed_stream.functions.is_even)"
    ...     ".map(operator.mul,10).for_each(print)\\n"
    ... )
    True
    >>> sys.stdin = in_
    """  # noqa: D301
    imports: set[str] = {"typed_stream", "sys"}
    code: list[str]
    stream: Stream[bytes] | Stream[str] | object
    if options.bytes:
        stream = Stream(sys.stdin.buffer)
        code = ["typed_stream.Stream(sys.stdin.buffer)"]
        if not options.keep_ends:
            code.append(r""".map(bytes.removesuffix, b"\n")""")
            stream = stream.map(bytes.removesuffix, b"\n")
    else:
        stream = Stream(sys.stdin)
        code = ["typed_stream.Stream(sys.stdin)"]
        if not options.keep_ends:
            code.append(r""".map(str.removesuffix, "\n")""")
            stream = stream.map(str.removesuffix, "\n")

    method: None | Callable[[object], object] = None
    args: list[object] = []
    for index, action in Stream(options.actions).enumerate(1):
        if action.lstrip().startswith("_"):
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
                if not hasattr(stream, action):
                    type_name = (
                        type(stream).__qualname__ or type(stream).__name__
                    )
                    meth_name = method.__qualname__ or method.__name__
                    if hasattr(builtins, action):
                        fix = f"builtins.{action}"
                        confident = True
                    else:
                        fix = f"({action})"
                        confident = action in EVAL_GLOBALS
                    use = "use" if confident else "try"
                    return (
                        f"{type_name} object has no attribute {action!r}. "
                        f"To pass it as argument to {meth_name} {use} {fix!r}."
                    )
            method = getattr(stream, action)
            code.append(f".{action}(")
        else:
            if not method:
                return f"{action!r} needs to be a Stream method."
            full_action_qual: str
            if action.isspace():
                args.append(action)
                full_action_qual = repr(action)
            elif action.isdigit():
                args.append(int(action))
                full_action_qual = action
            elif action in functions.__all__:
                args.append(getattr(functions, action))
                full_action_qual = f"typed_stream.functions.{action}"  # TODO??
            elif action in collections.__all__:
                args.append(getattr(collections, action))
                full_action_qual = f"collections.{action}"
                imports.add("collections")
            elif action in operator.__all__:
                args.append(getattr(operator, action))
                full_action_qual = f"operator.{action}"
                imports.add("operator")
            elif hasattr(builtins, action):
                args.append(getattr(builtins, action))
                full_action_qual = f"{action}"
            elif options.no_eval:
                return f"Can't parse {action!r} without eval."
            else:
                try:
                    # pylint: disable-next=eval-used
                    arg = eval(action, dict(EVAL_GLOBALS))  # nosec: B307
                    # pylint: disable-next=broad-except
                except BaseException as exc:  # noqa: B036
                    err = traceback.format_exception_only(exc)[-1].strip()
                    return f"Failed to evaluate {action!r}: {err}"

                imports.update(
                    {
                        full
                        for mod, full in MODULE_FULL_NAMES.items()
                        if action.startswith(f"{mod}.")
                    }
                )
                args.append(arg)
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
    elif isinstance(stream, Mapping):
        imports.add("json")
        print(json.dumps(dict(stream)))
        code.insert(0, "print(json.dumps(dict(")
        code.append(")))")
    elif stream:
        print(stream)
        code.insert(0, "print(")
        code.append(")")

    code.insert(0, f"import {','.join(sorted(imports))};")

    sys.stdout.flush()

    if options.debug:
        print("".join(code), file=sys.stderr, flush=True)
    return None


def main() -> str | None:  # noqa: C901
    """Parse arguments and then run the program."""
    arg_parser = argparse.ArgumentParser(
        prog="typed_stream",
        description="Easy interface for streamy handling of files.",
        epilog="Do not run this with arguments from an untrusted source.",
    )
    arg_parser.add_argument("--debug", action="store_true")
    arg_parser.add_argument("--bytes", action="store_true")
    arg_parser.add_argument("--keep-ends", action="store_true")
    # arg_parser.add_argument("--no-eval", action="store_true")
    arg_parser.add_argument("actions", nargs="+")

    args = arg_parser.parse_args()
    options = Options(
        debug=bool(args.debug),
        bytes=bool(args.bytes),
        keep_ends=bool(args.keep_ends),
        no_eval=False,
        actions=tuple(map(str, args.actions)),
    )
    if options.actions and options.actions[0] == "help":
        if not (methods := options.actions[1:]):
            arg_parser.parse_args([sys.argv[0], "--help"])

        for i, name in enumerate(methods):
            if i:
                print()
            print(f"Stream.{name}:")
            if not (method := getattr(Stream, name, None)):
                to_print = "Does not exist."
            elif not (doc := cast(str, getattr(method, "__doc__", ""))):
                to_print = "No docs."
            else:
                to_print = inspect.cleandoc(doc)

            print(textwrap.indent(to_print, " " * 4))
        return None

    return run_program(options)


if __name__ == "__main__":
    sys.exit(main())
