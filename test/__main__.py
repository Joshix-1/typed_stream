"""The tests for the Stream."""
import operator
import pickle
from operator import add
from pathlib import Path
from typing import TypeGuard

from typed_stream import BinaryFileStream, FileStream, Stream

from .test_functions import noop

# pylint: disable=unnecessary-lambda


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

assert Stream(range(5)).map(str).enumerate().collect(tuple) == (
    (0, "0"),
    (1, "1"),
    (2, "2"),
    (3, "3"),
    (4, "4"),
)

indices: list[int] = (
    Stream(range(5)).map(str).enumerate().map(lambda x: x.idx).collect(list)
)
assert indices == list(range(5))
values: list[str] = (
    Stream(range(5)).map(str).enumerate().map(lambda x: x.val).collect(list)
)
assert values == list(map(str, range(5)))
key_value_dict: dict[int, str] = (
    Stream(range(5)).map(str).enumerate().collect(dict)
)
assert key_value_dict == {0: "0", 1: "1", 2: "2", 3: "3", 4: "4"}


def create_int_stream() -> Stream[int]:
    """Create an int stream."""
    return Stream(range(10_000)).map(operator.pow, 2)


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
assert Stream(range(25)).chunk(5).map(lambda x: list(x)).collect(tuple) == (
    [0, 1, 2, 3, 4],
    [5, 6, 7, 8, 9],
    [10, 11, 12, 13, 14],
    [15, 16, 17, 18, 19],
    [20, 21, 22, 23, 24],
)

int_list: list[int] = Stream([None, 1, 2, 3, 4, 0, 23]).filter().collect(list)
assert int_list == [1, 2, 3, 4, 23]

assert len(Stream.from_value("x").limit(1000).tail(10)) == 10

assert Stream(range(10_000)).chunk(100).count() == 100
assert list(Stream(range(10_000)).chunk(100).map(len).distinct()) == [100]

assert Stream.counting().take_while((100).__gt__).count() == 100
assert list(Stream.counting().take_while((5).__gt__)) == [0, 1, 2, 3, 4]
assert list(Stream(range(10)).drop_while((5).__gt__)) == [5, 6, 7, 8, 9]
assert Stream(range(10)).tail(5) == (5, 6, 7, 8, 9)


def is_str(value: object) -> TypeGuard[str]:
    """Type guard strings."""
    return isinstance(value, str)


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
    Stream(range(10_000))
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
    Stream(range(1000000000000000000000000000000000000000000000000000000000000))
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
