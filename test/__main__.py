from typed_stream import Stream

tpl: tuple[int, ...] = Stream([1, 2, 3]).collect(tuple)
assert tpl == (1, 2, 3)
_set: set[int] = Stream([1, 2, 3]).collect(set)
assert _set == {1, 2, 3}
mapping: dict[int, str] = (
    Stream([1, 2, 3]).map(lambda x: (x, str(x))).collect(dict)
)
assert mapping == {1: "1", 2: "2", 3: "3"}

assert Stream([1, 2, 3]).collect(lambda x: sum(x)) == 6
int_var: int = Stream([1, 2, 3]).max()
assert int_var == 3
int_var = Stream([1, 2, 3]).min()
assert int_var == 1

str_var: str = Stream(["1", "2", "3"]).max()
assert str_var == "3"
str_var = Stream(["1", "2", "3"]).min()
assert str_var == "1"


def create_int_stream() -> Stream[int]:
    return Stream(range(10_000)).map(lambda x: x**2)


assert (
    sum(create_int_stream())
    == create_int_stream().reduce(lambda x, y: x + y)
    == create_int_stream().reduce(int.__add__)
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
assert Stream([]).limit(3).collect(list) == []
assert Stream([1]).limit(3).collect(list) == [1]
assert Stream([1, 2, 3, 4, 5]).count() == 5
assert Stream([1, 4, 5]).last() == 5
assert Stream([1, 4, 5]).first() == 1
assert Stream([True, True, True]).all()
assert Stream([]).empty()
assert not Stream([1]).empty()

assert Stream([1, 2, 3]).chain([4, 5, 6]).collect(tuple) == (1, 2, 3, 4, 5, 6)
