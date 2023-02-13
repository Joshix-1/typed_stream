"""The tests for the Stream."""
from operator import add
from pathlib import Path
from typing import TypeGuard

from typed_stream import FileStream, Stream

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


def create_int_stream() -> Stream[int]:
    """Create an int stream."""
    return Stream(range(10_000)).map(lambda x: x**2)


STRING = "pjwa  nsvoidnvifbp  s,cpvmodo nngfibogfmjv in"
assert Stream(STRING).distinct().sum() == "pjwa nsvoidfb,cmg"

assert (
    sum(create_int_stream())
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

assert Stream.from_value("x").limit(1000).tail(10).count() == 10


def is_str(value: object) -> TypeGuard[str]:
    """Type guard strings."""
    return isinstance(value, str)


str_stream: Stream[str] = Stream([None, "1", "2", "3", 4, 0, 23]).filter(is_str)
assert str_stream.collect(list) == ["1", "2", "3"]


assert (
    FileStream(Path(__file__).parent / "input.txt")
    .filter(lambda string: string and not string.startswith("#"))
    .map(int)
    .sum()
    == 7
)

assert FileStream(Path(__file__).parent / "input.txt", keep_line_ends=True).map(
    lambda x: x[-1]
).distinct().collect(tuple) == ("\n",)

fs = FileStream(Path(__file__).parent / "input.txt")
assert fs.chain(" ").last() == " "
assert not hasattr(fs, "_file_iterator")

fs = FileStream(Path(__file__).parent / "input.txt")
assert hasattr(fs, "_close_source_callable")
fs_ = fs.map(lambda _: ...)
assert hasattr(fs, "_file_iterator")
assert hasattr(fs_, "_close_source_callable")
fs_ = fs_.limit(1)
assert hasattr(fs, "_file_iterator")
assert hasattr(fs_, "_close_source_callable")
assert fs_.collect(list) == [...]
fs._close_source_callable()
assert not hasattr(fs, "_file_iterator")

fs = FileStream(Path(__file__).parent / "input.txt")
assert (
    fs.limit(10).map(repr).map(len).peek(lambda _: ...).map((1).__add__).count()
    == 10
)
assert not hasattr(fs, "_file_iterator")
