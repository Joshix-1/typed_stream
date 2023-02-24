"""The tests for the Stream."""
import operator
import pickle
from collections.abc import Callable
from numbers import Number, Real
from operator import add
from pathlib import Path

from typed_stream import BinaryFileStream, FileStream, Stream
from typed_stream.exceptions import StreamEmptyError, StreamIndexError
from typed_stream.iteration_utils import IndexValueTuple

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

# pylint: disable=positional-only-arguments-expected, redundant-keyword-arg
# pylint: disable=unnecessary-lambda, unsubscriptable-object


def assert_raises(exc: type[BaseException], fun: Callable[[], object]) -> None:
    """Assert that fun raises exc."""
    try:
        val = fun()
    except exc:
        return
    raise AssertionError(
        f"{fun} did not raise {exc} and instead returned {val}"
    )


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
    eval(repr(Stream.from_value(69))),  # pylint: disable=eval-used
    Stream,
)

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


def create_int_stream() -> Stream[int]:
    """Create an int stream."""
    return Stream.range(10_000).map(operator.pow, 2)


STRING = "pjwa  nsvoidnvifbp  s,cpvmodo nngfibogfmjv in"
assert Stream(STRING).distinct().sum() == "pjwa nsvoidfb,cmg"

assert (
    333283335000
    == sum(create_int_stream())
    == create_int_stream().reduce(lambda x, y: x + y)
    == create_int_stream().reduce(int.__add__)
    == create_int_stream().reduce(add)
    == create_int_stream().sum()
    == create_int_stream().collect(lambda x: sum(x))
)

max_: int = Stream([1, 2, 3, -1]).max()
assert max_ == 3
min_: int = Stream([1, 2, -1, 3]).min()
assert min_ == -1

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

int_list: list[int] = Stream([None, 1, 2, 3, 4, 0, 23]).filter().collect(list)
assert int_list == [1, 2, 3, 4, 23]
int_list = Stream([None, 1, 2, 3, None]).filter(is_not_none).collect(list)
assert int_list == [1, 2, 3]
int_list = Stream([None, 1, 2, 3, None]).exclude(is_none).collect(list)
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
assert not hasattr(fs, "_file_iterator")

fs = FileStream(INPUT_TXT)
assert fs.map(lambda _: ...).limit(1).collect(list) == [...]
assert not hasattr(fs, "_file_iterator")

fs = FileStream(INPUT_TXT)
assert (
    fs.limit(10).map(repr).map(len).peek(lambda _: ...).map((1).__add__).count()
    == 10
)
assert not hasattr(fs, "_file_iterator")

fs = FileStream(INPUT_TXT)
assert fs.take_while(len).count() == 4
assert not hasattr(fs, "_file_iterator")


assert BinaryFileStream(INPUT_TXT, keep_line_ends=True).map(
    lambda x: x[-1]
).distinct().collect(tuple) == (b"\n"[0],)

bfs: BinaryFileStream = BinaryFileStream(INPUT_TXT)
assert bfs.chain([b" "]).last() == b" "
assert not hasattr(bfs, "_file_iterator")

bfs = BinaryFileStream(INPUT_TXT)
assert list(bfs.map(lambda _: ...).limit(1)) == [...]
assert not hasattr(bfs, "_file_iterator")

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
assert not hasattr(bfs, "_file_iterator")

bfs = BinaryFileStream(INPUT_TXT)
assert bfs.take_while(len).count() == 4
assert not hasattr(bfs, "_file_iterator")


bfs = BinaryFileStream(INPUT_TXT)
fs = FileStream(INPUT_TXT)
assert tuple(bfs) == tuple(fs.map(str.encode, "UTF-8").collect(tuple))
assert not hasattr(bfs, "_file_iterator")
assert not hasattr(fs, "_file_iterator")

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
assert repr(int_stream) == "Stream(...)"

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
