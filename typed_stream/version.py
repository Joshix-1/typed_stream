#!/usr/bin/python3
"""
This script contains the version of this package.

Update this to create a new release.
To get the current version run this script.
"""

from __future__ import annotations

__all__ = ("VERSION", "version_info")

version_info: tuple[int, int, int] = (0, 155, 0)
VERSION = ".".join(map(str, version_info))

if __name__ == "__main__":  # pragma: no cover
    print(VERSION)
