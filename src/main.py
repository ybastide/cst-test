#!/usr/bin/env python3.7

import argparse
import difflib
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import libcst as cst

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.checker import Checker
from src.modernizer import Modernizer


def expand_paths(paths: List[Path]) -> Iterable[Path]:
    expanded_paths = []
    for path in paths:
        i = next((i for i, p in enumerate(path.parts) if "*" in p), -1)
        if i >= 0:
            expanded_paths += Path(*path.parts[:i]).glob("/".join(path.parts[i:]))
        elif path.is_dir():
            expanded_paths += path.glob("*.py")
        else:
            expanded_paths.append(path)
    return sorted(expanded_paths, key=lambda path: (len(path.parts), path))


def main() -> Optional[int]:
    parser = argparse.ArgumentParser(description="Test things.")
    parser.add_argument("file", nargs="+")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose output.")
    parser.add_argument("-q", "--quiet", action="store_true", help="no output.")
    parser.add_argument(
        "-x",
        "--exitfirst",
        action="store_true",
        help="exit instantly on first error or failed test.",
    )
    parser.add_argument("--ignore", nargs="*", help="errors to ignore.")
    args = parser.parse_args()
    paths = expand_paths([Path(name).expanduser() for name in args.file])
    errors = False
    for path in paths:
        if path.is_dir() or path.suffix != ".py":
            continue
        if args.verbose:
            print(f"Checking {path}")
        py_source = path.read_text()
        module = cst.parse_module(py_source)
        wrapper = cst.MetadataWrapper(module)
        checker = Checker(path, args.verbose, args.ignore)
        wrapper.visit(checker)
        if checker.errors:
            if args.exitfirst:
                return 1
            errors = True
        modernizer = Modernizer(path)
        modified_tree = wrapper.visit(modernizer)
        if modernizer.errors:
            if args.exitfirst:
                return 1
            errors = True
        if not args.quiet:
            diff = "".join(
                difflib.unified_diff(
                    py_source.splitlines(True),
                    modified_tree.code.splitlines(True),
                    fromfile=f"a{path}",
                    tofile=f"b{path}",
                )
            )
            if diff:
                print(diff)
    if errors:
        return 1


if __name__ == "__main__":
    sys.exit(main() or 0)
