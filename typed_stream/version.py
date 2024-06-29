#!/usr/bin/python3
"""
This script contains the version of this package.

Update this to create a new release.
To get the current version run this script.
"""

from __future__ import annotations

import typing

__all__ = ("VERSION", "version_info")

VERSION = "0.150.0"

version_info: tuple[int, int, int] = typing.cast(
    tuple[int, int, int], tuple(map(int, VERSION.split(".")))
)
if len(version_info) != 3:
    raise AssertionError(f"Invalid version: {VERSION}")

del annotations, typing

if __name__ == "__main__":  # pragma: no cover
    print(VERSION)
