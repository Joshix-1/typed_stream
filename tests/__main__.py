# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12
# pylint: disable=too-many-lines

"""The tests for the Stream."""

from __future__ import annotations

import doctest
import importlib
import operator
import sys
import traceback
import types
from collections import Counter
from collections.abc import Callable
from functools import partial
from numbers import Number, Real
from operator import add
from pathlib import Path
from types import EllipsisType
from typing import Any

from typed_stream import (
    BinaryFileStream,
    FileStream,
    Stream,
    StreamableSequence,
    StreamEmptyError,
    StreamFinishedError,
    StreamIndexError,
    _impl,
)
from typed_stream._impl._iteration_utils import (
    IterWithCleanUp,
    Peeker,
    sliding_window,
)
from typed_stream._impl._lazy_file_iterators import (
    LazyFileIteratorRemovingEndsBytes,
)
from typed_stream._impl._typing import assert_type
from typed_stream._impl._utils import IndexValueTuple
from typed_stream._impl.functions import method_partial
from typed_stream.functions import is_even, is_odd

from .test_functions import (
    is_bool,
    is_complex,
    is_float,
    is_int,
    is_none,
    is_not_none,
    is_number,
    is_real_number,
    is_str,
    noop,
)

for export in Stream(_impl.__all__).map(partial(getattr, _impl)):  # noqa: F405
    # pylint: disable-next=protected-access
    assert export._module() == "typed_stream", f"{export!r}"  # nosec: B101
    del export


def testmod(
    mod: types.ModuleType,
    optionflags: int = doctest.DONT_ACCEPT_TRUE_FOR_1,
) -> tuple[int, int]:
    """Test modules.

    Like doctest.testmod, but smaller.
    """
    runner = doctest.DocTestRunner(optionflags=optionflags)

    for test in doctest.DocTestFinder().find(mod, mod.__name__, mod):
        runner.run(test)

    return runner.failures, runner.tries


def run_doc_tests() -> None:  # noqa: C901
    """Run the doctests in the typed_stream package."""
    dir_ = Path(__file__).resolve().parent.parent / "typed_stream"
    acc_fails, acc_tests = 0, 0
    for mod in sorted(
        Stream(dir_.rglob("*.py"))
        .map(lambda p: p.relative_to(dir_).as_posix())
        .map(str.removesuffix, "/__init__.py")
        .map(str.removesuffix, ".py")
        .map(str.replace, "/", "."),
        key=lambda s: (s.count("."), len(s)),
        reverse=True,
    ):
        full_mod = f"typed_stream.{mod}" if mod else "typed_stream"
        fails, tests = testmod(importlib.import_module(full_mod))
        acc_fails += fails
        acc_tests += tests
        if tests:
            print(
                f"{full_mod}: {tests - fails} / {tests} doctests successful",
                file=sys.stderr,
            )

    print(
        f"SUMMARY: {acc_tests - acc_fails} / {acc_tests} doctests successful",
        file=sys.stderr,
    )
    if acc_fails == 1 and sys.implementation.name == "rustpython":
        print("ignoring 1 failure", file=sys.stderr)
    elif acc_fails:
        sys.exit(1)


run_doc_tests()


def typed_nwise_stuff() -> None:
    """Test whether the Stream.nwise overloads work."""
    one: Stream[tuple[str]] = Stream("abc").nwise(1)
    assert one.map("".join).collect("".join) == "abc"

    two: Stream[tuple[str, str]] = Stream("abc").nwise(2)
    assert two.map("".join).collect("".join) == "abbc"

    three: Stream[tuple[str, ...]] = Stream("abcd").nwise(3)
    assert three.map("".join).collect("".join) == "abcbcd"


typed_nwise_stuff()


# pylint: disable=unnecessary-lambda, protected-access


def assert_raises(exc: type[BaseException], fun: Callable[[], object]) -> None:
    """Assert that fun raises exc."""
    try:
        val = fun()
    except exc:
        return
    except BaseException:  # pragma: no cover
        print(f"{fun} did not raise {exc}", file=sys.stderr)
        raise
    raise AssertionError(
        f"{fun} did not raise {exc} and instead returned {val}"
    )


assert_raises(AssertionError, lambda: assert_raises(Exception, lambda: None))
assert_raises(TypeError, lambda: hash(Stream(...)))
assert_raises(TypeError, lambda: hash(Stream([0, 1])))

assert_raises(ValueError, lambda: sliding_window([], -1))
assert_raises(ValueError, lambda: sliding_window((), 0))
assert_raises(ValueError, lambda: Stream([]).nwise(0))
assert_raises(ValueError, lambda: Stream(()).nwise(-1))

assert_raises(ValueError, Stream("1a2b3c4d5").map(int).sum)
assert_raises(ValueError, Stream("1a2b3c4d5").map(int).catch(TypeError).sum)
assert_raises(ValueError, lambda: Stream(()).catch(StopIteration))
assert_raises(ValueError, lambda: Stream(()).catch(StopIteration, TypeError))
assert_raises(ValueError, lambda: Stream(()).catch(ValueError, StopIteration))
assert (
    assert_type(
        Stream("1a2b3c4d5e6f7g8h9").map(int).catch(ValueError).sum(), int
    )
    == 45
)
assert (
    assert_type(
        Stream("1a2b3c4d5e6f7g8h9").map(int).catch(Exception).sum(), int
    )
    == 45
)

assert assert_type(Stream("abbccc122333").collect(Counter), Counter[str]) == {
    "a": 1,
    "b": 2,
    "c": 3,
    "1": 1,
    "2": 2,
    "3": 3,
}

assert Stream.range(10).conditional_map(
    is_even, lambda x: x, lambda x: -x
).collect() == (0, -1, 2, -3, 4, -5, 6, -7, 8, -9)
assert assert_type(
    Stream.range(10)
    .conditional_map(is_even, lambda x: x * 2, lambda x: -x)
    .collect(),
    StreamableSequence[int],
) == (0, -1, 4, -3, 8, -5, 12, -7, 16, -9)
assert assert_type(
    Stream.range(10).conditional_map(is_odd, lambda x: -x, lambda x: x * 2),
    Stream[int],
).collect() == (0, -1, 4, -3, 8, -5, 12, -7, 16, -9)
assert (
    assert_type(
        Stream.range(10)
        .conditional_map(is_even, lambda _: ..., lambda x: None)
        .collect(),
        StreamableSequence[None | EllipsisType],
    )
    == (..., None) * 5
)
assert assert_type(
    Stream.range(10).conditional_map(is_odd, lambda x: -x), Stream[int]
).collect() == (
    -1,
    -3,
    -5,
    -7,
    -9,
)
assert (
    assert_type(
        Stream.range(10).conditional_map(is_even, lambda _: ...).collect(),
        StreamableSequence[EllipsisType],
    )
    == (...,) * 5
)


def raise_exceptions(number: int) -> int:
    """Raise different exceptions."""
    if number == 1:
        raise ValueError("1")
    if number == 3:
        raise TypeError("3")
    if number == 5:
        raise ZeroDivisionError("5")
    return number


assert assert_type(
    Stream.range(6)
    .map(raise_exceptions)
    .catch(ValueError, TypeError, ZeroDivisionError, default=lambda: -1)
    .collect(),
    StreamableSequence[int],
) == (0, -1, 2, -1, 4, -1)

assert assert_type(
    Stream.range(6)
    .map(raise_exceptions)
    .catch(ValueError, TypeError, ZeroDivisionError)
    .collect(),
    StreamableSequence[int],
) == (0, 2, 4)

assert assert_type(
    Stream.range(6)
    .map(raise_exceptions)
    .map(str)
    .catch(
        ValueError,
        TypeError,
        ZeroDivisionError,
        default=lambda _: f"E{_.args[0]}",
    )
    .collect(),
    StreamableSequence[str],
) == ("0", "E1", "2", "E3", "4", "E5")

assert (
    assert_type(
        Stream.range(20)
        .map(raise_exceptions)
        .catch(ValueError, TypeError, ZeroDivisionError)
        .sum(),
        int,
    )
    == sum(range(20)) - 1 - 3 - 5
)
assert (
    assert_type(
        Stream.range(20)
        .map(raise_exceptions)
        .catch(ValueError, TypeError, ZeroDivisionError, default=lambda: 0)
        .sum(),
        int,
    )
    == sum(range(20)) - 1 - 3 - 5
)
assert (
    assert_type(
        Stream.range(20)
        .map(raise_exceptions)
        .catch(ValueError, TypeError, ZeroDivisionError, default=lambda _: 0)
        .sum(),
        int,
    )
    == sum(range(20)) - 1 - 3 - 5
)


errors: list[ValueError] = []
assert (
    assert_type(
        Stream("1a2b3c4d5e6f7g8h9")
        .map(int)
        .catch(ValueError, handler=errors.append, default=lambda: 100)
        .sum(),
        int,
    )
    == 845
)
assert (
    assert_type(Stream(errors).map(type).collect(list), list[type])
    == [ValueError] * 8
)
errors = []
assert (
    assert_type(
        Stream("1x2x3x4x5x6x7x8x9")
        .map(int)
        .catch(
            ValueError,
            handler=errors.append,
            default=lambda _: len(_.args) * 1000,
        )
        .sum(),
        int,
    )
    == 8045
)
value_error: ValueError
try:
    int("x")
except ValueError as _:
    value_error = _
else:
    raise AssertionError("x is int")
assert Stream(errors).map(type).collect(list) == [ValueError] * 8
assert (
    Stream(errors).flat_map(lambda _: _.args).distinct().collect()
    == value_error.args
)

optional_float_list: list[float | None] = list(
    Stream.range(3)
    .map((5).__truediv__)
    .catch(ZeroDivisionError, default=lambda: None)
)
assert optional_float_list == [None, 5.0, 2.5]

assert (
    Stream.range(69).collect()
    == Stream.range(69).nwise(1).sum()
    == Stream.range(69).map(lambda x: (x,)).sum()
    == Stream.range(69).nwise(1).flat_map(lambda x: x).collect(tuple)
    == Stream.range(69).map(lambda x: (x,)).flat_map(lambda x: x).collect(tuple)
)
assert (
    Stream.range(69).collect(list)
    == Stream.range(69).map(lambda x: [x]).sum()
    == Stream.range(69).map(lambda x: [x]).flat_map(lambda x: x).collect(list)
)
assert Stream.range(10).enumerate(-10).sum() == Stream.range(10).enumerate(
    -10
).flat_map(lambda x: x).collect(tuple)

assert " ".join(Stream("ABCDEFG").nwise(1).map("".join)) == "A B C D E F G"
assert Stream("ABCDEFG").nwise(1).collect() == (
    ("A",),
    ("B",),
    ("C",),
    ("D",),
    ("E",),
    ("F",),
    ("G",),
)

assert " ".join(Stream("ABCDEFG").nwise(2).map("".join)) == "AB BC CD DE EF FG"
assert Stream("ABCDEFG").nwise(2).collect() == (
    ("A", "B"),
    ("B", "C"),
    ("C", "D"),
    ("D", "E"),
    ("E", "F"),
    ("F", "G"),
)
assert (
    " ".join(Stream("ABCDEFG").nwise(3).map("".join)) == "ABC BCD CDE DEF EFG"
)
assert Stream("ABCDEFG").nwise(3).collect() == (
    ("A", "B", "C"),
    ("B", "C", "D"),
    ("C", "D", "E"),
    ("D", "E", "F"),
    ("E", "F", "G"),
)
assert (
    " ".join(Stream("ABCDEFG").nwise(4).map("".join)) == "ABCD BCDE CDEF DEFG"
)
assert Stream("ABCDEFG").nwise(4).collect() == (
    ("A", "B", "C", "D"),
    ("B", "C", "D", "E"),
    ("C", "D", "E", "F"),
    ("D", "E", "F", "G"),
)
assert " ".join(Stream("ABCDEFG").nwise(5).map("".join)) == "ABCDE BCDEF CDEFG"
assert Stream("ABCDEFG").nwise(5).collect() == (
    ("A", "B", "C", "D", "E"),
    ("B", "C", "D", "E", "F"),
    ("C", "D", "E", "F", "G"),
)
assert " ".join(Stream("ABCDEFG").nwise(6).map("".join)) == "ABCDEF BCDEFG"
assert Stream("ABCDEFG").nwise(6).collect() == (
    ("A", "B", "C", "D", "E", "F"),
    ("B", "C", "D", "E", "F", "G"),
)
assert " ".join(Stream("ABCDEFG").nwise(7).map("".join)) == "ABCDEFG"
assert Stream("ABCDEFG").nwise(7).collect() == (
    ("A", "B", "C", "D", "E", "F", "G"),
)
assert Stream("").nwise(1).collect() == ()
assert Stream("A").nwise(2).collect() == ()
assert Stream("AB").nwise(3).collect() == ()
assert Stream("ABC").nwise(4).collect() == ()
assert Stream("ABCDEFG").nwise(8).collect() == ()

assert 0 in Stream.counting()
assert 1 in Stream([1])
assert 2 not in Stream.range(1, 100, 2)
assert 3 not in Stream.range(3)

assert "0" in Stream.counting().map(str)
assert "1" in Stream([1]).map(str)
assert "2" not in Stream.range(1, 100, 2).map(str)
assert "3" not in Stream.range(3).map(str)

assert assert_type("".join(reversed(Stream("abc"))), str) == "cba"
assert tuple(reversed(Stream([1, 2, 3, 4]))) == (4, 3, 2, 1)

assert assert_type(Stream([1, 2, 3]).collect(tuple), tuple[int, ...]) == (
    1,
    2,
    3,
)
assert assert_type(Stream([1, 2, 3]).collect(set), set[int]) == {1, 2, 3}
mapping: dict[int, str] = (
    Stream([1, 2, 3]).map(lambda x: (x, str(x))).collect(dict)
)
assert mapping == {1: "1", 2: "2", 3: "3"}

assert assert_type(Stream([1, 2, 3]).sum(), int) == 6
assert assert_type(Stream([1, 2, 3]).max(), int) == 3
assert assert_type(Stream([1, 2, 3]).min(), int) == 1
assert assert_type(Stream([1, 2, 3]).min(default=0), int) == 1

assert assert_type(Stream(["1", "2", "3"]).max(), str) == "3"
assert assert_type(Stream(["1", "2", "3"]).min(), str) == "1"
assert assert_type(Stream(["1", "2", "3"]).min(default="a"), str) == "1"

_stream1 = Stream.from_value(69).enumerate().nwise(3).catch()
assert isinstance(
    _stream2 := eval(  # pylint: disable=eval-used
        repr(_stream1),
        {
            "typed_stream": __import__("typed_stream"),
            "repeat": __import__("itertools").repeat,
        },
    ),
    Stream,
)
assert _stream1.limit(1000).collect() == _stream2.limit(1000).collect()
assert (
    repr(iter(Stream.from_value(69)))
    == "typed_stream._impl._iteration_utils.IterWithCleanUp"
    + "(<bound method StreamABC.close of typed_stream.Stream"
    + "(repeat(69))>,repeat(69))"
)
try:
    assert (
        repr(Peeker(print))
        == "typed_stream._impl._iteration_utils.Peeker(<built-in function print>)"
    )
except AssertionError:  # pragma: no cover
    if sys.implementation.name == "rustpython":
        traceback.print_exc()
    else:
        raise
else:  # pragma: no cover
    if sys.implementation.name == "rustpython":
        raise AssertionError("Doesn't fail anymore on RustPython")


assert str(Stream(...)) == "typed_stream.Stream(...)"
assert repr(Stream(...)) == "typed_stream.Stream(...)"
assert repr(FileStream(...)) == "typed_stream.FileStream(...)"

assert_raises(StreamFinishedError, lambda: Stream(...)._data)
assert_raises(StreamFinishedError, lambda: BinaryFileStream(...)._data)
assert_raises(StreamFinishedError, lambda: FileStream(...)._data)

assert assert_type(
    Stream.range(5).map(str).enumerate(), Stream[IndexValueTuple[str]]
).collect(tuple) == (
    (0, "0"),
    (1, "1"),
    (2, "2"),
    (3, "3"),
    (4, "4"),
)


assert assert_type(
    Stream.range(5).map(str).enumerate().map(lambda x: x.idx).collect(list),
    list[int],
) == list(range(5))
enumeration_stream = assert_type(
    Stream.range(5).map(str).enumerate(), Stream[IndexValueTuple[str]]
)
assert assert_type(
    enumeration_stream.map(lambda x: x.val).collect(list), list[str]
) == list(map(str, range(5)))
assert assert_type(
    Stream.range(5).map(str).enumerate().map(lambda x: x.val).collect(list),
    list[str],
) == list(map(str, range(5)))
assert assert_type(
    Stream.range(5).map(str).enumerate().collect(dict), dict[int, str]
) == {0: "0", 1: "1", 2: "2", 3: "3", 4: "4"}

assert assert_type(
    list(Stream.range(999).enumerate().starmap(int.__eq__).distinct()),
    list[bool],
) == [True]
assert assert_type(
    list(Stream.range(999).enumerate().starmap(operator.eq).distinct()),
    list[Any],
) == [True]
assert (
    assert_type(Stream.range(10).nwise(1).starmap(str).sum(), str)
    == "0123456789"
)
assert (
    assert_type(Stream.range(6).nwise(2).starmap(int.__mul__).sum(), int) == 40
)
assert (
    assert_type(Stream.range(6).nwise(2).starmap(operator.mul).sum(), Any) == 40
)

STRING = "pjwa  nsvoidnvifbp  s,cpvmodo nngfibogfmjv in"
assert (
    assert_type(Stream(STRING).distinct().collect("".join), str)
    == "pjwa nsvoidfb,cmg"
)
assert (
    assert_type(Stream(STRING).distinct(use_set=False).sum(), str)
    == "pjwa nsvoidfb,cmg"
)


def create_int_stream() -> Stream[int]:
    """Create an int stream."""
    return Stream.range(10_000).map(operator.pow, 2)


assert (
    333283335000
    == assert_type(sum(create_int_stream()), int)
    == assert_type(create_int_stream().reduce(lambda x, y: x + y), int)
    == assert_type(create_int_stream().reduce(int.__add__), int)
    == assert_type(create_int_stream().reduce(add, 0), int)
    == assert_type(create_int_stream().reduce(add), int)
    == assert_type(create_int_stream().sum(), int)
    == assert_type(create_int_stream().collect(lambda x: sum(x)), int)
    == assert_type(create_int_stream().collect(sum), int)
)

assert assert_type(Stream([1, 2, 3, -1]).max(), int) == 3
assert assert_type(
    Stream([{0, 1}, {2}, {3, 4, 5}, {6}]).max(key=len), set[int]
) == {3, 4, 5}
assert assert_type(Stream([1, 2, -1, 3]).min(), int) == -1
assert assert_type(
    Stream([{0, 1}, {2}, {3, 4, 5}, {6}]).min(key=len), set[int]
) == {2}

assert assert_type(Stream([1, 2, 3]).max(default=None), None | int) == 3
assert not assert_type(Stream([1]).limit(0).max(default=None), None | int)
assert assert_type(Stream([1, 2, 3]).first(default=None), None | int) == 1
assert not assert_type(Stream([1]).limit(0).first(default=None), None | int)
assert assert_type(Stream([1, 2, 3]).min(default=None), None | int) == 1
assert not assert_type(Stream([1]).limit(0).min(default=None), None | int)

assert assert_type(Stream([1, 2, 3]).max(default="None"), str | int) == 3
assert (
    assert_type(Stream([1]).limit(0).max(default="None"), str | int) == "None"
)
assert assert_type(Stream([1, 2, 3]).first(default="None"), str | int) == 1
assert (
    assert_type(Stream([1]).limit(0).first(default="None"), str | int) == "None"
)
assert assert_type(Stream([1, 2, 3]).min(default="None"), str | int) == 1
assert (
    assert_type(Stream([1]).limit(0).min(default="None"), str | int) == "None"
)

assert Stream((1,)).drop(100).reduce(add, 1) == 1
assert Stream("").reduce(add, "x") == "x"
assert_raises(StreamEmptyError, Stream("").sum)

assert tuple(Stream([1, 2, 2, 2, 3]).distinct()) == (1, 2, 3)
assert tuple(Stream([1, 2, 1, 1, 2, 1, 2, 3, 3, 3, 2, 2, 1]).distinct()) == (
    1,
    2,
    3,
)

assert Stream([1, 4, 7]).flat_map(lambda x: [x, x + 1, x + 2]).collect(
    list
) == [1, 2, 3, 4, 5, 6, 7, 8, 9]
assert Stream([1, 2, 3, 4, 5]).limit(3).collect(list) == [1, 2, 3]
assert not Stream([]).limit(3).collect(list)
assert Stream([1]).limit(3).collect(list) == [1]
assert Stream([1, 2, 3, 4, 5]).count() == 5
assert Stream([1, 4, 5]).last() == 5
assert Stream([1, 4, 5]).first() == 1
assert Stream([True, True, True]).all()
assert Stream([]).empty()
assert not Stream([1]).empty()

assert Stream([1, 2, 3]).chain([4, 5, 6]).collect(tuple) == (1, 2, 3, 4, 5, 6)
assert Stream.range(25).chunk(5).map(lambda x: list(x)).collect(tuple) == (
    [0, 1, 2, 3, 4],
    [5, 6, 7, 8, 9],
    [10, 11, 12, 13, 14],
    [15, 16, 17, 18, 19],
    [20, 21, 22, 23, 24],
)
assert_raises(ValueError, lambda: Stream(()).chunk(0))

int_list: list[int] = Stream([None, 1, 2, 3, 4, 0, 23]).filter().collect(list)
assert int_list == [1, 2, 3, 4, 23]
int_list = Stream([None, 1, 2, 3, None]).filter(is_not_none).collect(list)
assert int_list == [1, 2, 3]
int_list = Stream([None, 1, 2, 3, None]).exclude(is_none).collect(list)
assert int_list == [1, 2, 3]
int_list = []
Stream([None, 1, 2, 3, None]).exclude(is_none).for_each(int_list.append)
assert int_list == [1, 2, 3]

assert len(Stream.from_value("x").limit(1000).tail(10)) == 10

assert not Stream("").count()
assert Stream.range(10_000).chunk(100).count() == 100
assert list(Stream.range(10_000).chunk(100).map(len).distinct()) == [100]

assert Stream.counting().take_while((100).__gt__).count() == 100
assert list(Stream.counting().take_while((5).__gt__)) == [0, 1, 2, 3, 4]
assert list(Stream.range(10).drop_while((5).__gt__)) == [5, 6, 7, 8, 9]
assert Stream.range(10).tail(5) == (5, 6, 7, 8, 9)


str_stream: Stream[str] = Stream([None, "1", "2", "3", 4, 0, 23]).filter(is_str)
assert str_stream.collect(list) == ["1", "2", "3"]

assert (
    repr(FileStream("file.txt", "Utf-8", False))
    == "typed_stream.FileStream('file.txt','Utf-8',False)"
)
assert (
    repr(FileStream("file.txt", "Utf-8", True))
    == "typed_stream.FileStream('file.txt','Utf-8',True)"
)

INPUT_TXT = Path(__file__).parent / "input.txt"

assert (
    FileStream(INPUT_TXT)
    .filter(lambda string: string and not string.startswith("#"))
    .map(int)
    .sum()
    == 7
)
assert (
    FileStream(INPUT_TXT)
    .filter()
    .exclude(method_partial(str.startswith, "#"))
    .map(int)
    .sum()
    == 7
)
assert FileStream(INPUT_TXT).map(int).catch(ValueError).sum() == 7

assert FileStream(INPUT_TXT, keep_line_ends=True).map(
    lambda x: x[-1]
).distinct().collect(tuple) == ("\n",)

fs = FileStream(INPUT_TXT)
assert fs.chain(" ").last() == " "
assert fs._file_iterator is None
fs.close()  # closing twice shouldn't fail
assert fs._file_iterator is None

fs = FileStream(INPUT_TXT, keep_line_ends=True)
for line in fs:
    assert line.endswith("\n")

assert fs._file_iterator is None
fs = FileStream(INPUT_TXT)
for line in fs:
    assert not line.endswith("\n")

assert fs._file_iterator is None

fs = FileStream(INPUT_TXT)
assert fs.map(lambda _: ...).limit(1).collect(list) == [...]
assert fs._file_iterator is None

fs = FileStream(INPUT_TXT)
assert (
    fs.limit(10).map(repr).map(len).peek(lambda _: ...).map((1).__add__).count()
    == 10
)
assert fs._file_iterator is None

with FileStream(INPUT_TXT) as fs:
    assert isinstance(next(iter(fs)), str)
assert fs._file_iterator is None

fs = FileStream(INPUT_TXT)
assert fs.take_while(len).count() == 4
assert fs._file_iterator is None


assert BinaryFileStream(INPUT_TXT, keep_line_ends=True).map(
    lambda x: x[-1]
).distinct().collect(tuple) == (b"\n"[0],)

bfs: BinaryFileStream = BinaryFileStream(INPUT_TXT)
assert bfs.chain([b" "]).last() == b" "
assert bfs._file_iterator is None

bfs = BinaryFileStream(INPUT_TXT)
assert list(bfs.map(lambda _: ...).limit(1)) == [...]
assert bfs._file_iterator is None

bfs = BinaryFileStream(INPUT_TXT)
assert (
    bfs.limit(10)
    .map(repr)
    .map(len)
    .peek(lambda _: ...)
    .map((1).__add__)
    .count()
    == 10
)
assert bfs._file_iterator is None

bfs = BinaryFileStream(INPUT_TXT)
assert bfs.take_while(len).count() == 4
assert bfs._file_iterator is None

bfs = BinaryFileStream(INPUT_TXT)
first = bfs.first()
assert bfs._file_iterator is None

with BinaryFileStream(INPUT_TXT) as bfs:
    assert first == next(iter(bfs))
assert bfs._file_iterator is None

with LazyFileIteratorRemovingEndsBytes(INPUT_TXT) as lfireb:
    assert first == next(lfireb)
assert not lfireb._file_object
lfireb.close()
assert not lfireb._file_object
lfireb = LazyFileIteratorRemovingEndsBytes(INPUT_TXT)
assert next(lfireb) == first
assert lfireb._file_object
lfireb.close()
assert lfireb._file_object is None

bfs = BinaryFileStream(INPUT_TXT)  # type: ignore[unreachable]
fs = FileStream(INPUT_TXT)
assert tuple(bfs) == tuple(fs.map(str.encode, "UTF-8").collect(tuple))
assert bfs._file_iterator is None
assert fs._file_iterator is None

int_list_begin: list[int] = []
int_list_end: list[int] = []
int_stream: Stream[int] = (
    Stream.range(10_000)
    .peek(int_list_begin.append)
    .limit(1000)
    .drop_while(lambda x: x < 500)
    .exclude(lambda x: x % 2)
    .flat_map(range)
    .filter(lambda x: x % 2)
    .map(operator.pow, 2)
    .peek(int_list_end.append)
)
assert not int_list_begin  # the above code did nothing
assert not int_list_end
assert list(int_stream) == int_list_end
assert int_list_end  # list(int_stream) consumed the stream
assert len(int_list_begin) == 1000

assert repr(int_stream) == "typed_stream.Stream(...)"

assert Stream(["abc", "def", "ghijk"]).flat_map(str.encode, "ASCII").map(
    operator.sub, 97
).collect(tuple) == (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)

stream = (
    Stream.range(10000000000000000000000000000000000000000000000000000000000000)
    .peek(noop)
    .map(str)
    .flat_map(str.encode, "ASCII")
    .map(operator.sub, ord("0"))
    .limit(100)
    .map(operator.mul, 10)
    .drop_while((10).__gt__)
    .take_while((90).__gt__)
    .filter(operator.truth)
    .exclude(operator.not_)
)

for i in range(100):
    assert Stream.range(10_000)[i] == i
    assert Stream.range(10_000).nth(i) == i
    if not i:
        continue
    assert Stream.range(10_000)[-i] == 10_000 - i
    assert Stream.range(10_000).nth(-i) == 10_000 - i


for name in dir(Stream(...)):  # noqa: C901  # pylint: disable=too-complex
    if name in {
        "__class__",
        "__class_getitem__",
        "__del__",
        "__delattr__",
        "__dir__",
        "__enter__",
        "__eq__",
        "__exit__",
        "__format__",
        "__ge__",
        "__getattribute__",
        "__getstate__",
        "__gt__",
        "__init__",
        "__init_subclass__",
        "__le__",
        "__lt__",
        "__ne__",
        "__new__",
        "__reduce__",
        "__reduce_ex__",
        "__repr__",
        "__setattr__",
        "__sizeof__",
        "__str__",
        "__subclasshook__",
        "_close_source",
        "_data",
        "_finish",
        "_full_class_name",
        "_get_args",
        "_module",
        "_StreamABC__data",
        "close",
        "collect_and_await_all",
        "collect_async_to_awaited_tasks",
        "counting",
        "from_value",
        "range",
    }:
        continue
    if (
        sys.implementation.name == "rustpython"
        and getattr(Stream(...), name, None) is None
    ):
        print(f"ignoring Stream.{name}")
        continue
    if isinstance(method := getattr(Stream(...), name), Callable):
        args: tuple[Any, ...]
        if name == "chain":
            args = ([],)
        elif name in {
            "chunk",
            "drop",
            "limit",
            "nth",
            "nwise",
            "tail",
            "__contains__",
            "__getitem__",
        }:
            args = (2,)
        elif name in {
            "concurrent_map",
            "drop_while",
            "exclude",
            "flat_map",
            "map",
            "peek",
            "reduce",
            "starcollect",
            "starmap",
            "take_while",
        }:
            args = (lambda: ...,)
        elif name == "catch":
            args = (Exception,)
        elif name == "conditional_map":
            args = (lambda _: ..., lambda _: ..., lambda _: ...)
        else:
            args = ()
        try:
            assert_raises(StreamFinishedError, partial(method, *args))
        except NotImplementedError:
            if sys.implementation.name == "rustpython":
                traceback.print_exc()
            else:
                raise


assert_raises(StreamIndexError, lambda: Stream.range(10)[10])
assert_raises(StreamIndexError, lambda: Stream.range(10)[-11])
assert_raises(StreamIndexError, lambda: Stream(())[-1])
assert_raises(StreamIndexError, lambda: Stream(())[0])
assert_raises(StreamIndexError, lambda: Stream(())[1])
assert_raises(StreamIndexError, lambda: Stream(()).nth(-1))
assert_raises(StreamIndexError, lambda: Stream(()).nth(0))
assert_raises(StreamIndexError, lambda: Stream(()).nth(1))

assert_raises(StreamEmptyError, lambda: Stream(()).first())
assert_raises(StreamEmptyError, lambda: Stream([]).first())
assert_raises(StreamEmptyError, lambda: Stream(()).last())
assert_raises(StreamEmptyError, lambda: Stream([]).last())


assert Stream.range(100).nth(1_000, default=None) is None
assert Stream.range(100).nth(-1_000, default=None) is None
assert Stream(()).nth(1, default=None) is None
assert Stream(()).nth(-1, default=None) is None

assert Stream.range(100)[:10] == tuple(range(10))
assert Stream.range(100)[90:] == tuple(range(90, 100))
assert Stream.range(1000)[90:100] == tuple(range(90, 100))
assert Stream.range(1000)[90:100:2] == tuple(range(90, 100, 2))

assert Stream.range(1000)[20:44:5] == tuple(range(20, 44, 5))

assert list(Stream.range(10)) == list(range(10))
assert list(Stream.range(stop=10)) == list(range(10))
assert list(Stream.range(0, 20)) == list(range(0, 20))
assert list(Stream.range(0, stop=20)) == list(range(0, 20))
assert list(Stream.range(start=0, stop=20)) == list(range(0, 20))
assert list(Stream.range(0, 20, 3)) == list(range(0, 20, 3))
assert list(Stream.range(0, 20, step=3)) == list(range(0, 20, 3))
assert list(Stream.range(0, stop=20, step=3)) == list(range(0, 20, 3))
assert list(Stream.range(start=0, stop=20, step=3)) == list(range(0, 20, 3))


# ints_and_strs: list[int | str] = [1, "2", 3, "4"]
# str_list: list[str] = list(Stream(ints_and_strs).exclude(is_int))
# assert str_list == ["2", "4"]
# int_list: list[str] = list(Stream(ints_and_strs).exclude(is_str))
# assert int_list == [1, 3]


source: list[str | int | float | complex | bool | None] = [
    None,
    True,
    "2",
    3,
    4.2,
    5j,
]
assert assert_type(Stream(source).filter(is_str).collect(list), list[str]) == [
    "2"
]
assert assert_type(Stream(source).filter(is_int).collect(list), list[int]) == [
    True,
    3,
]
assert assert_type(
    Stream(source).filter(is_float).collect(list), list[float]
) == [4.2]
assert assert_type(
    Stream(source).filter(is_complex).collect(list), list[complex]
) == [5j]
assert assert_type(
    Stream(source).filter(is_bool).collect(list), list[bool]
) == [True]
assert assert_type(
    Stream(source).filter(is_number).collect(list), list[Number]
) == [True, 3, 4.2, 5j]
assert assert_type(
    Stream(source).filter(is_real_number).collect(list), list[Real]
) == [True, 3, 4.2]
assert assert_type(
    Stream(source).filter(is_none).collect(list), list[None]
) == [None]
assert assert_type(
    Stream(source).filter(is_not_none).collect(list),
    list[str | int | float | complex | bool],
) == [True, "2", 3, 4.2, 5j]


assert assert_type(
    Stream(source).exclude(is_str).collect(list),
    list[int | float | complex | bool | None],
) == [None, True, 3, 4.2, 5j]
assert assert_type(
    Stream(source).exclude(is_int).collect(list),
    list[str | float | complex | bool | None],
) == [None, "2", 4.2, 5j]
assert assert_type(
    Stream(source).exclude(is_float).collect(list),
    list[str | int | complex | bool | None],
) == [None, True, "2", 3, 5j]
assert assert_type(
    Stream(source).exclude(is_complex).collect(list),
    list[str | int | float | bool | None],
) == [None, True, "2", 3, 4.2]
assert assert_type(
    Stream(source).exclude(is_bool).collect(list),
    list[str | int | float | complex | None],
) == [None, "2", 3, 4.2, 5j]
assert assert_type(
    Stream(source).exclude(is_number).collect(list), list[str | None]
) == [None, "2"]
assert assert_type(
    Stream(source).exclude(is_real_number).collect(list),
    list[str | None | complex],
) == [None, "2", 5j]
assert assert_type(
    Stream(source).exclude(is_none).collect(list),
    list[str | int | float | complex | bool],
) == [True, "2", 3, 4.2, 5j]
assert assert_type(
    Stream(source).exclude(is_not_none).collect(list), list[None]
) == [None]

assert not Stream(()).count()
assert Stream(range(100)).drop(10).count() == 90
assert Stream(range(100)).drop(10).collect() == tuple(range(10, 100))
assert Stream("abc").drop(2).collect() == ("c",)
assert Stream("abc")[::] == ("a", "b", "c") == tuple("abc")[::]
assert Stream("abc")[-2::] == ("b", "c") == tuple("abc")[-2::]
assert Stream("abc")[::-1] == ("c", "b", "a") == tuple("abc")[::-1]
assert Stream("abc")[::2] == ("a", "c") == tuple("abc")[::2]
assert Stream("abc")[:2:] == ("a", "b") == tuple("abc")[:2:]
assert Stream("abc")[:-1:] == ("a", "b") == tuple("abc")[:-1:]
assert Stream("abc")[-1:-1:-1] == () == tuple("abc")[-1:-1:-1]
assert Stream("abc")[-2:-1:-1] == () == tuple("abc")[-2:-1:-1]
assert Stream("abc")[-1:-2:-1] == ("c",) == tuple("abc")[-1:-2:-1]
assert Stream("abc")[-1:-3:-1] == ("c", "b") == tuple("abc")[-1:-3:-1]
assert Stream("abc")[-1:] == ("c",) == tuple("abc")[-1:]
assert Stream("abc")[-2:] == ("b", "c") == tuple("abc")[-2:]
assert Stream("abc")[-3:] == ("a", "b", "c") == tuple("abc")[-3:]
assert Stream("abc")[-2:None:None] == ("b", "c") == tuple("abc")[-2:None:None]


assert isinstance(StreamableSequence() * 4, StreamableSequence)
assert isinstance(4 * StreamableSequence(), StreamableSequence)
assert isinstance(() + StreamableSequence(), tuple)
assert isinstance(StreamableSequence() + (), StreamableSequence)
assert isinstance(
    StreamableSequence() + StreamableSequence(), StreamableSequence
)
assert isinstance(StreamableSequence()[::], StreamableSequence)
assert StreamableSequence("a")[0] == "a"

assert StreamableSequence("ab") + ("c", "d") == ("a", "b", "c", "d")
assert ("c", "d") + StreamableSequence("ab") == ("c", "d", "a", "b")

str_stream = Stream("abc")
assert str_stream.last() == "c"
assert_raises(StreamFinishedError, str_stream.collect)
str_stream = Stream(())
assert_raises(StreamEmptyError, str_stream.first)

try:
    assert (
        Stream("abc").map(str.upper).sum()
        == Stream("abc").concurrent_map(str.upper).sum()
        == "ABC"
    )
except NotImplementedError:
    if sys.implementation.name == "rustpython":
        traceback.print_exc()
    else:
        raise

assert_raises(StreamEmptyError, lambda: Stream(()).sum())

int_list = []
assert (
    assert_type(
        Stream.counting(-100)
        .drop(100)
        .drop_while((1000).__gt__)
        .take_while((100_000).__gt__)
        .filter(is_odd)
        .map(operator.pow, 3)
        .peek(int_list.append)
        .enumerate()
        .flat_map(operator.mul, 2)
        .exclude(is_even)
        .limit(10_000)
        .distinct()
        .chunk(30)
        .map(sum)
        .sum(),
        int,
    )
    == 432028881523605
)
assert sum(int_list) == 432028878744716
assert len(int_list) - 1 == 3333

try:  # pylint: disable=too-many-try-statements
    int_list.clear()
    assert (
        assert_type(
            Stream.counting(-100)
            .drop(100)
            .drop_while((1000).__gt__)
            .take_while((100_000).__gt__)
            .filter(is_odd)
            .map(operator.pow, 3)
            .peek(int_list.append)
            .enumerate()
            .flat_map(operator.mul, 2)
            .exclude(is_even)
            .limit(10_000)
            .distinct()
            .chunk(30)
            .concurrent_map(sum)
            .sum(),
            int,
        )
        == 432028881523605
    )
    assert sum(int_list) == 432028878744716
    assert len(int_list) - 1 == 3333
except NotImplementedError:
    if sys.implementation.name == "rustpython":
        traceback.print_exc()
    else:
        raise

assert Stream("abc").starcollect(lambda *args: args) == ("a", "b", "c")

try:  # pylint: disable=too-many-try-statements
    int_list = []
    it_w_cl: IterWithCleanUp[int] = IterWithCleanUp(
        Stream.counting(1), lambda: int_list.append(1)
    )
    assert next(it_w_cl) == 1
    assert not int_list
    with it_w_cl as _it:
        assert next(_it) == 2
        assert not int_list
    assert int_list == [1]

    with it_w_cl as _it:
        assert not next(_it, None)
        assert int_list == [1]

    assert int_list == [1]
except TypeError:
    if sys.implementation.name == "rustpython":
        traceback.print_exc()
    else:
        raise
