# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Simple helper functions for easy Stream usage."""
from typing import Any, Literal

__all__ = ("is_even", "is_odd", "noop", "one")


def noop(*args: Any) -> None:  # pylint: disable=unused-argument
    """Do nothing."""


def one(*args: Any) -> Literal[1]:  # pylint: disable=unused-argument
    """Return the smallest positive odd number."""
    return 1


def is_even(number: int) -> bool:
    """Check whether a number is even."""
    return not number % 2


def is_odd(number: int) -> bool:
    """Check whether a number is odd."""
    return not not number % 2  # noqa: SIM208  # pylint: disable=unneeded-not
