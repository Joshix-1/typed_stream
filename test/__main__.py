"""The tests for the Stream."""
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
    == create_int_stream().sum()
    == create_int_stream().collect(lambda x: sum(x))
)

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


def is_str(value: object) -> TypeGuard[str]:
    """Type guard strings."""
    return isinstance(value, str)


str_stream: Stream[str] = Stream([None, "1", "2", "3", 4, 0, 23]).filter(is_str)
assert str_stream.collect(list) == ["1", "2", "3"]


assert (
    FileStream(Path(__file__).parent / "input.txt")
    .map(str.strip)
    .filter(lambda string: string and not string.startswith("#"))
    .map(int)
    .sum()
    == 7
)
