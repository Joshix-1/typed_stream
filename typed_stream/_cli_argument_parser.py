# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""Utilities for an easy interface for streamy handling of standard input."""

import builtins
import inspect
import operator
import sys
from collections.abc import Callable
from itertools import chain
from typing import Final, NamedTuple

from . import Stream, functions
from ._utils import count_required_positional_arguments

__all__ = (
    "CLIArgumentParser",
    "InvalidTokenError",
)

FINISHED_STREAM: Final[Stream[object]] = Stream(...)

MODULES: Final[tuple[tuple[str, object, frozenset[str]], ...]] = (
    ("", builtins, frozenset(_ for _ in dir(builtins) if _[0] != "_")),
    ("operator.", operator, frozenset(operator.__all__)),
    ("typed_stream.functions.", functions, frozenset(functions.__all__)),
)
NAMES_IN_MODULES: Final[tuple[str, ...]] = tuple(
    sorted(frozenset(chain.from_iterable(tokens for _, _, tokens in MODULES)))
)


def is_stream_method(method_name: str) -> bool:
    """Check if a string is the name of a public stream method."""
    if method_name.startswith("_"):
        return False
    if not (method := getattr(FINISHED_STREAM, method_name, None)):
        return False
    return inspect.ismethod(method)


STREAM_METHODS: Final[tuple[str, ...]] = tuple(
    sorted({name for name in dir(Stream) if is_stream_method(name)})
)


def count_required_stream_method_args(method_name: str) -> int:
    """Count the required arguments of a stream method."""
    method = getattr(FINISHED_STREAM, method_name)
    return count_required_positional_arguments(method)


class Argument(NamedTuple):
    """An argument for a stream operation."""

    string: str
    value: object

    @classmethod
    def from_token(cls, token: str) -> "Argument":
        """Parse a token as an argument."""
        for qual, mod, tokens in MODULES:
            if token in tokens:
                return cls(f"{qual}{token}", getattr(mod, token))
        return cls(
            # TODO: Figure out how to do this in a safer way without
            #       losing too much functionality (e.g. for lambdas)
            token,
            eval(token, {}),  # nosec: B307  # pylint: disable=eval-used
        )


class InvalidTokenError(ValueError):
    """Raised when a token is not valid."""

    token: str
    expected: str
    possible_values: tuple[str, ...] | None

    __slots__ = ("token", "expected", "possible_values")

    def __init__(
        self, token: str, expected: str, possible_values: tuple[str, ...] | None
    ) -> None:
        """Set the token as attribute of self."""
        super().__init__(f"Invalid token {token!r}, expected {expected}")
        self.token = token
        self.expected = expected
        self.possible_values = possible_values


class StreamOperation(NamedTuple):
    """A stream operation."""

    method: str
    args: tuple[Argument, ...]

    def copy_with_new_args(self, *args: Argument) -> "StreamOperation":
        """Return a copy of self with new args."""
        return StreamOperation(self.method, self.args + args)

    def __str__(self) -> str:
        """Return a string representation of self."""
        return f".{self.method}({', '.join(arg.string for arg in self.args)})"


class CLIArgumentParser:
    """Parse code."""

    input_words: list[str]
    resulting_code: list[str]
    init_stream: Callable[[], Stream[object]]
    stream_init_code: str
    stream_operations: list[StreamOperation]
    current_operation: None | StreamOperation

    def __init__(self, *, as_bytes: bool, keep_ends: bool) -> None:
        """Initialize the CodeParser."""
        self.input_words = []
        self.resulting_code = []
        self.stream_operations = []
        self.current_operation = None
        if as_bytes:
            self.init_stream = lambda: Stream(sys.stdin.buffer)
            self.stream_init_code = "Stream(sys.stdin.buffer)"
            if not keep_ends:
                self.stream_operations.append(
                    StreamOperation(
                        "map",
                        (
                            Argument("bytes.removesuffix", bytes.removesuffix),
                            Argument(r'b"\n"', b"\n"),
                        ),
                    )
                )
        else:
            self.init_stream = lambda: Stream(sys.stdin)
            self.stream_init_code = "Stream(sys.stdin)"
            if not keep_ends:
                self.stream_operations.append(
                    StreamOperation(
                        "map",
                        (
                            Argument("str.removesuffix", str.removesuffix),
                            Argument(r'"\n"', "\n"),
                        ),
                    )
                )

    def get_code(self) -> str:
        """Return the python code."""
        return (
            self.stream_init_code
            + "".join(map(str, self.stream_operations))
            + (str(self.current_operation) if self.current_operation else "")
        )

    def run(self) -> object:
        """Run the parsed code."""
        stream: object = self.init_stream()
        for operation in chain(
            self.stream_operations,
            ((self.current_operation,) if self.current_operation else ()),
        ):
            stream = getattr(stream, operation.method)(
                *(arg.value for arg in operation.args)
            )
        return stream

    def _get_arguments_left(self) -> int:
        """Return the amount of arguments left for the current operation."""
        if (cop := self.current_operation) is None:
            return 0
        return count_required_stream_method_args(cop.method) - len(cop.args)

    def _auto_complete(self) -> tuple[str, ...]:
        """Return a sorted tuple of possible tokens."""
        if self._get_arguments_left() <= 0:
            # could be a new method
            return STREAM_METHODS
        return NAMES_IN_MODULES

    def auto_complete(self, token: str = "") -> tuple[str, ...]:  # nosec: B107
        """Return a sorted tuple of possible tokens."""
        if not token:
            return self._auto_complete()
        return tuple(
            possible_value
            for possible_value in self._auto_complete()
            if possible_value.startswith(token)
        )

    def _add_token(self, token: str) -> None:
        """Add another token to parse."""
        is_method = is_stream_method(token)
        if self.current_operation is None:
            if not is_method:
                raise InvalidTokenError(
                    token, "a stream method", STREAM_METHODS
                )
            self.current_operation = StreamOperation(token, ())
            return None
        if self._get_arguments_left() <= 0 and is_method:
            self.stream_operations.append(self.current_operation)
            self.current_operation = None
            return self._add_token(token)
        self.current_operation = self.current_operation.copy_with_new_args(
            Argument.from_token(token)
        )
        return None

    def add_tokens(self, *tokens: str) -> None:
        """Add more tokens to parse."""
        for token in tokens:
            self._add_token(token)
