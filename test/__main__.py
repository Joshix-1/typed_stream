# Licensed under the EUPL-1.2 or later.
# You may obtain a copy of the licence in all the official languages of the
# European Union at https://joinup.ec.europa.eu/collection/eupl/eupl-text-eupl-12

"""The tests for the Stream."""
import operator
import pickle
import sys
from collections.abc import Callable
from functools import partial
from numbers import Number, Real
from operator import add
from pathlib import Path
from typing import Any

from typed_stream import (
    BinaryFileStream,
    FileStream,
    Stream,
    StreamableSequence,
)
from typed_stream.exceptions import (
    StreamEmptyError,
    StreamFinishedError,
    StreamIndexError,
)
from typed_stream.functions import is_even, is_odd
from typed_stream.iteration_utils import IndexValueTuple, IterWithCleanUp
from typed_stream.lazy_file_iterators import LazyFileIteratorRemovingEndsBytes

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

# pylint: disable=unnecessary-lambda, unsubscriptable-object, protected-access


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

# pylint: disable=unsupported-membership-test
assert 0 in Stream.counting()
assert 1 in Stream([1])
assert 2 not in Stream.range(1, 100, 2)
assert 3 not in Stream.range(3)

assert "0" in Stream.counting().map(str)
assert "1" in Stream([1]).map(str)
assert "2" not in Stream.range(1, 100, 2).map(str)
assert "3" not in Stream.range(3).map(str)

assert "".join(reversed(Stream("abc"))) == "cba"
assert tuple(reversed(Stream([1, 2, 3, 4]))) == (4, 3, 2, 1)

tpl: tuple[int, ...] = Stream([1, 2, 3]).collect(tuple)
assert tpl == (1, 2, 3)
_set: set[int] = Stream([1, 2, 3]).collect(set)
assert _set == {1, 2, 3}
mapping: dict[int, str] = (
    Stream([1, 2, 3]).map(lambda x: (x, str(x))).collect(dict)
)
assert mapping == {1: "1", 2: "2", 3: "3"}

assert Stream([1, 2, 3]).sum() == 6
int_var: int = Stream([1, 2, 3]).max()
assert int_var == 3
int_var = Stream([1, 2, 3]).min()
assert int_var == 1

str_var: str = Stream(["1", "2", "3"]).max()
assert str_var == "3"
str_var = Stream(["1", "2", "3"]).min()
assert str_var == "1"

assert isinstance(
    eval(  # pylint: disable=eval-used
        repr(Stream.from_value(69)),
        {"typed_stream": __import__("typed_stream")},
    ),
    Stream,
)

assert str(Stream(...)) == "typed_stream.streams.Stream(Ellipsis)"
assert repr(Stream(...)) == "typed_stream.streams.Stream(Ellipsis)"

assert Stream(...)._is_finished()
assert BinaryFileStream(...)._is_finished()
assert FileStream(...)._is_finished()


assert Stream.range(5).map(str).enumerate().collect(tuple) == (
    (0, "0"),
    (1, "1"),
    (2, "2"),
    (3, "3"),
    (4, "4"),
)

indices: list[int] = (
    Stream.range(5).map(str).enumerate().map(lambda x: x.idx).collect(list)
)
assert indices == list(range(5))
enumeration_stream: Stream[IndexValueTuple[str]] = (
    Stream.range(5).map(str).enumerate()
)
values: list[str] = enumeration_stream.map(lambda x: x.val).collect(list)
assert values == list(map(str, range(5)))
values = Stream.range(5).map(str).enumerate().map(lambda x: x.val).collect(list)
assert values == list(map(str, range(5)))
key_value_dict: dict[int, str] = (
    Stream.range(5).map(str).enumerate().collect(dict)
)
assert key_value_dict == {0: "0", 1: "1", 2: "2", 3: "3", 4: "4"}


STRING = "pjwa  nsvoidnvifbp  s,cpvmodo nngfibogfmjv in"
assert Stream(STRING).distinct().collect("".join) == "pjwa nsvoidfb,cmg"
assert Stream(STRING).distinct(use_set=False).sum() == "pjwa nsvoidfb,cmg"


def create_int_stream() -> Stream[int]:
    """Create an int stream."""
    return Stream.range(10_000).map(operator.pow, 2)


assert (
    333283335000
    == sum(create_int_stream())
    == create_int_stream().reduce(lambda x, y: x + y)
    == create_int_stream().reduce(int.__add__)
    == create_int_stream().reduce(add, 0)
    == create_int_stream().reduce(add)
    == create_int_stream().sum()
    == create_int_stream().collect(lambda x: sum(x))
)

max_: int = Stream([1, 2, 3, -1]).max()
assert max_ == 3
min_: int = Stream([1, 2, -1, 3]).min()
assert min_ == -1

assert Stream(()).reduce(add, 1) == 1
assert Stream(()).reduce(add, "x") == "x"

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

assert Stream.range(10_000).chunk(100).count() == 100
assert list(Stream.range(10_000).chunk(100).map(len).distinct()) == [100]

assert Stream.counting().take_while((100).__gt__).count() == 100
assert list(Stream.counting().take_while((5).__gt__)) == [0, 1, 2, 3, 4]
assert list(Stream.range(10).drop_while((5).__gt__)) == [5, 6, 7, 8, 9]
assert Stream.range(10).tail(5) == (5, 6, 7, 8, 9)


str_stream: Stream[str] = Stream([None, "1", "2", "3", 4, 0, 23]).filter(is_str)
assert str_stream.collect(list) == ["1", "2", "3"]

INPUT_TXT = Path(__file__).parent / "input.txt"

assert (
    FileStream(INPUT_TXT)
    .filter(lambda string: string and not string.startswith("#"))
    .map(int)
    .sum()
    == 7
)

assert FileStream(INPUT_TXT, keep_line_ends=True).map(
    lambda x: x[-1]
).distinct().collect(tuple) == ("\n",)

fs = FileStream(INPUT_TXT)
assert fs.chain(" ").last() == " "
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
assert not lfireb._file_object

bfs = BinaryFileStream(INPUT_TXT)
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
assert repr(int_stream) == "typed_stream.streams.Stream(Ellipsis)"

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
assert tuple(pickle.loads(pickle.dumps(stream))) == tuple(range(10, 90, 10))
assert tuple(stream) == tuple(range(10, 90, 10))

stream = Stream.from_value(0).chunk(9)
assert pickle.loads(pickle.dumps(stream)).first() == (0, 0, 0, 0, 0, 0, 0, 0, 0)
assert tuple(stream.limit(1000)) == ((0, 0, 0, 0, 0, 0, 0, 0, 0),) * 1000

iterator = iter(Stream.from_value(1).limit(5))
assert tuple(pickle.loads(pickle.dumps(iterator))) == (1, 1, 1, 1, 1)
assert tuple(iterator) == (1, 1, 1, 1, 1)

for i in range(100):
    assert Stream.range(10_000)[i] == i
    assert Stream.range(10_000).nth(i) == i
    if not i:
        continue
    assert Stream.range(10_000)[-i] == 10_000 - i
    assert Stream.range(10_000).nth(-i) == 10_000 - i


for name in dir(Stream(...)):  # noqa: C901
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
        "_finish",
        "_get_args",
        "_is_finished",
        "close",
        "counting",
        "from_value",
        "range",
    }:
        continue
    if isinstance(
        method := getattr(Stream(...), name), Callable  # type: ignore[arg-type]
    ):
        args: tuple[Any, ...]  # type: ignore[misc]
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
            "take_while",
        }:
            args = (lambda: ...,)
        else:
            args = ()
        assert_raises(StreamFinishedError, partial(method, *args))

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

# pylint: disable=positional-only-arguments-expected, redundant-keyword-arg
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
strs: list[str] = Stream(source).filter(is_str).collect(list)
assert strs == ["2"]
ints: list[int] = Stream(source).filter(is_int).collect(list)
assert ints == [True, 3]
floats: list[float] = Stream(source).filter(is_float).collect(list)
assert floats == [4.2]
complexs: list[complex] = Stream(source).filter(is_complex).collect(list)
assert complexs == [5j]
bools: list[bool] = Stream(source).filter(is_bool).collect(list)
assert bools == [True]
numbers: list[Number] = Stream(source).filter(is_number).collect(list)
assert numbers == [True, 3, 4.2, 5j]  # type: ignore[comparison-overlap]
real_numbers: list[Real] = Stream(source).filter(is_real_number).collect(list)
assert real_numbers == [True, 3, 4.2]
nones: list[None] = Stream(source).filter(is_none).collect(list)
assert nones == [None]
# nnones: list[str | int | float | complex | bool] = (
#     Stream(source).filter(is_not_none).collect(list)
# )
# assert nnones == [True, "2", 3, 4.2, 5j]

# not_strs: list[int | float | complex | bool | None] = (
#     Stream(source).exclude(is_str).collect(list)
# )
# assert not_strs == [None, True, 3, 4.2, 5j]
# not_ints: list[str | float | complex | bool | None] = (
#     Stream(source).exclude(is_int).collect(list)
# )
# assert not_ints == [None, "2", 4.2, 5j]
# not_floats: list[str | int | complex | bool | None] = (
#     Stream(source).exclude(is_float).collect(list)
# )
# assert not_floats == [None, True, "2", 3, 5j]
# not_complexs: list[str | int | float | bool | None] = (
#     Stream(source).exclude(is_complex).collect(list)
# )
# assert not_complexs == [None, True, "2", 3, 4.2]
# not_bools: list[str | int | float | complex | None] = (
#     Stream(source).exclude(is_bool).collect(list)
# )
# assert not_bools == [None, "2", 3, 4.2, 5j]
# not_numbers: list[str | None] = Stream(source).exclude(is_number).collect(list)
# assert not_numbers == [None, "2"]  # type: ignore[comparison-overlap]
# not_real_numbers: list[str | None | complex] = list(
#     Stream(source).exclude(is_real_number)
# )
# assert not_real_numbers == [None, "2", 5j]
# not_nones: list[str | int | float | complex | bool] = (
#     Stream(source).exclude(is_none).collect(list)
# )
# assert not_nones == [True, "2", 3, 4.2, 5j]

# not_nnones: list[None] = Stream(source).exclude(is_not_none).collect(list)
# assert not_nnones == [None]

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

assert (
    Stream("abc").map(str.upper).sum()
    == Stream("abc").concurrent_map(str.upper).sum()
    == "ABC"
)
assert_raises(StreamEmptyError, lambda: Stream(()).sum())

int_list = []
assert (
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
    .sum()
    == 432028881523605
)
assert sum(int_list) == 432028878744716
assert len(int_list) - 1 == 3333

assert Stream("abc").starcollect(lambda *args: args) == ("a", "b", "c")

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
