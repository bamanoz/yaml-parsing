#!/usr/bin/env python3

from __future__ import annotations

import argparse
import glob
import re
import sys
from pathlib import Path


INCLUDE_RE = re.compile(r"^(?P<indent>[ \t]*)!include:\s*(?P<target>.+?)\s*$")
BLOCK_SCALAR_RE = re.compile(r"^(?P<indent>[ \t]*)(?:-\s*)?(?:.*:\s*)?[|>][-+0-9]*\s*$")


def strip_yaml_comment(line: str) -> str:
    newline = "\n" if line.endswith("\n") else ""
    content = line[:-1] if newline else line
    result: list[str] = []
    in_single = False
    in_double = False
    i = 0

    while i < len(content):
        char = content[i]

        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            backslashes = 0
            j = i - 1
            while j >= 0 and content[j] == "\\":
                backslashes += 1
                j -= 1
            if backslashes % 2 == 0:
                in_double = not in_double
        elif char == "#" and not in_single and not in_double and (i == 0 or content[i - 1].isspace()):
            break

        result.append(char)
        i += 1

    stripped = "".join(result).rstrip()
    if not stripped:
        return newline if not content.strip() else ""

    return f"{stripped}{newline}"


def resolve_include_paths(target: str, current_dir: Path, root_dir: Path) -> list[Path]:
    cleaned = strip_yaml_comment(target).strip().strip('"\'')
    candidate_patterns = [current_dir / cleaned, root_dir / cleaned]
    resolved_matches: list[Path] = []
    seen: set[Path] = set()

    for pattern in candidate_patterns:
        for match in sorted(glob.glob(str(pattern), recursive=True)):
            resolved_match = Path(match).resolve()
            if not resolved_match.is_file() or resolved_match in seen:
                continue

            seen.add(resolved_match)
            resolved_matches.append(resolved_match)

    if resolved_matches:
        return resolved_matches

    tried = ", ".join(str(path) for path in candidate_patterns)
    raise FileNotFoundError(f"include target '{cleaned}' not found; tried: {tried}")


def indent_block(text: str, indent: str) -> str:
    if not indent:
        return text

    lines = text.splitlines(keepends=True)
    return "".join(f"{indent}{line}" if line.strip() else line for line in lines)


def is_block_scalar_header(line: str) -> bool:
    return bool(BLOCK_SCALAR_RE.match(line.rstrip()))


def line_indent_width(line: str) -> int:
    return len(line) - len(line.lstrip(" \t"))


def materialize(path: Path, root_dir: Path, stack: tuple[Path, ...]) -> str:
    resolved_path = path.resolve()
    if resolved_path in stack:
        cycle = " -> ".join(str(item) for item in (*stack, resolved_path))
        raise ValueError(f"include cycle detected: {cycle}")

    result: list[str] = []
    block_scalar_indent: int | None = None

    for line in resolved_path.read_text(encoding="utf-8").splitlines(keepends=True):
        if block_scalar_indent is not None:
            if not line.strip() or line_indent_width(line) > block_scalar_indent:
                result.append(line)
                continue

            block_scalar_indent = None

        match = INCLUDE_RE.match(line)
        if not match:
            stripped_line = strip_yaml_comment(line)
            if stripped_line:
                result.append(stripped_line)
                if is_block_scalar_header(stripped_line):
                    block_scalar_indent = line_indent_width(stripped_line)
            continue

        include_paths = resolve_include_paths(
            match.group("target"),
            resolved_path.parent,
            root_dir,
        )
        for include_path in include_paths:
            included = materialize(include_path, root_dir, (*stack, resolved_path))
            if included and not included.endswith("\n"):
                included += "\n"
            result.append(indent_block(included, match.group("indent")))

    return "".join(result)


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize a YAML file with recursive !include support.")
    parser.add_argument("input", type=Path, help="Root YAML file to materialize")
    parser.add_argument("-o", "--output", type=Path, help="Optional output file path")
    args = parser.parse_args()

    input_path = args.input.resolve()
    output = materialize(input_path, input_path.parent, ())

    if args.output is not None:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
