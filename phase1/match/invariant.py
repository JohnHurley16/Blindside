"""Check that belief and policy cannot reach ground truth.

ARCHITECTURE.md asks for a compile-time test asserting `Policy::evaluate` cannot
reach `World`. Python has no such thing, so this is the cheap equivalent: walk the
source of the packages that must stay clean and fail if any of them imports the
truth package. It exists to catch the "just for debugging" accessor that someone
adds later, which is exactly how this invariant dies.
"""
from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN: tuple[str, ...] = ("truth",)
CLEAN_PACKAGES: tuple[str, ...] = ("belief", "policy")


def offending_imports(root: Path | None = None) -> list[str]:
    """Return a list of 'package/module.py imports truth' violations."""
    base = root or Path(__file__).resolve().parent.parent
    problems: list[str] = []
    for package in CLEAN_PACKAGES:
        for path in (base / package).rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    dotted = "." * node.level + module
                    if any(part in FORBIDDEN for part in dotted.split(".")):
                        problems.append(f"{package}/{path.name} imports {dotted}")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(part in FORBIDDEN for part in alias.name.split(".")):
                            problems.append(f"{package}/{path.name} imports {alias.name}")
    return problems


def assert_clean() -> None:
    problems = offending_imports()
    if problems:
        raise AssertionError("ground truth leaked downstream of the sensor layer:\n  "
                             + "\n  ".join(problems))


if __name__ == "__main__":
    assert_clean()
    print("invariant holds: belief and policy cannot reach truth")
