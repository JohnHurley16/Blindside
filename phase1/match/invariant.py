"""Prove that nothing downstream of the sensor layer can reach ground truth.

ARCHITECTURE.md asks for a compile-time test asserting `Policy::evaluate` cannot reach
`World`. Python has no such thing, so this is the cheap equivalent: walk the source and
fail if any of it can name what it must not.

Eight rules, SPECTATOR-DISPLAY.md section 4.2. Rules 1 and 2 are the ones that actually
protect the policy; the rest exist because the previous version of this file scanned two
packages for one thing, and `phase1/view` was not scanned at all -- `View.__init__` stored
`self.sim` and `Sim.world` was a live `World`, so the renderer could have read ground truth
any afternoon and this file would still have printed "invariant holds".

  1. `belief` and `policy` may not import `truth`.
  2. `belief` and `policy` may not import `match`, so a policy cannot name StageFrame.
  3. `view` and `audio` may not import `truth`.
  4. `view` and `audio` may not contain the attribute access `.world`, `._world`, `.__sim`
     or `._MatchView__sim`, nor a getattr for any of them.
  5. Only six files in `phase1` may import `truth` at all.
  6. `match/stage_builder.py` may not import `belief` or `policy`: the exporter cannot
     see belief, so it cannot be tricked into feeding it.
  7. Every dataclass in `match/stage_frame.py` is frozen and slotted, and every field is
     a plain type -- so "just pass the World through here" fails at the declaration.
  8. Structure, not spelling: `Sim` has no `world`, the renderer is handed a `MatchView`,
     a frame cannot be built from inside a tick or with the channel off, and every array
     in a real frame is a copy that cannot be written through.

What this does not prove is in section 4.3, and the short version is reflection: Python
hands every object the whole process, and `().__class__.__base__.__subclasses__()` walks
to any loaded class without importing anything. That is deliberate malice, not the
accident this guards against.
"""
from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import numpy as np

PACKAGE: str = "phase1"
RULE_COUNT: int = 8

CLEAN_PACKAGES: tuple[str, ...] = ("belief", "policy")
CLEAN_FORBIDDEN: tuple[str, ...] = ("truth", "match")
RENDER_PACKAGES: tuple[str, ...] = ("view", "audio")
RENDER_FORBIDDEN: tuple[str, ...] = ("truth",)
FORBIDDEN_ATTRS: tuple[str, ...] = ("world", "_world", "__sim", "_MatchView__sim")
# Modules whose whole job is handing out other modules. No clean or render package has a use
# for one, and each is a one-line route to truth, so the rule is the import itself rather than
# what is done with it -- `import sys as _s` is still `sys`. (Ported from phase2, where a
# verifier defeated the by-name version four ways.)
REFLECTION_MODULES: tuple[str, ...] = ("importlib", "builtins", "sys", "inspect",
                                       "ctypes", "gc", "pkgutil", "runpy")
# Attribute names that fetch a module or an attribute regardless of what they are called on:
# `builtins.__import__(..)`, `_s.modules[..]`, `il.import_module(..)`, `vars(x)`, `x.__dict__`,
# `object.__getattribute__(x, ..)`.
MODULE_FETCHERS: tuple[str, ...] = ("__import__", "import_module", "modules",
                                    "__dict__", "__getattribute__")
FETCHER_CALLS: tuple[str, ...] = ("getattr", "vars", "eval", "exec")
TRUTH_READERS: tuple[str, ...] = (
    "truth", "sensing",                 # packages
    "match/sim.py", "match/headless.py", "match/reveal.py", "match/stage_builder.py")
PLAIN_TYPES: tuple[str, ...] = ("float", "int", "bool", "str", "tuple", "None", "ndarray")
# The dotted forms of TRUTH_READERS' files, for the render-package rule above.
_TRUTH_READER_MODULES: tuple[str, ...] = tuple(
    r[:-3].replace("/", ".") for r in TRUTH_READERS if r.endswith(".py"))


# ---- source walking -------------------------------------------------------------------
def _sources(base: Path) -> list[Path]:
    return sorted(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _imported_names(tree: ast.Module) -> list[str]:
    """Every dotted name this module imports, relative levels folded in as dots.

    An `ImportFrom` contributes its module AND every name it binds, because
    `from .. import truth` binds the truth *package* while its module is only "..".
    Recording the module alone was the hole that let a policy reach ground truth in one
    line, and it is the same shape as the bug phase2's checker was hardened against.
    """
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            out.append(module)
            sep = "" if module.endswith(".") else "."
            out += [f"{module}{sep}{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Import):
            out += [alias.name for alias in node.names]
    return out


def _touches(dotted: str, package: str) -> bool:
    return package in dotted.split(".")


def _rel(path: Path, base: Path) -> str:
    return path.relative_to(base).as_posix()


# ---- rules 1, 2, 3 ---------------------------------------------------------------------
def _import_rules(base: Path) -> list[str]:
    """What a clean or render package may import.

    Three separate refusals, because a verifier walked past the first one alone:
    the forbidden packages by name; the reflection modules under any alias, since each
    hands out modules and none has an honest use here; and a BINDING `import phase1`,
    because the package object carries every submodule already loaded anywhere in the
    process, so a handle on it is `phase1.truth.world.World` three dots later. A
    `from .. import x` names the package on the way without binding it, and is fine.
    """
    problems: list[str] = []
    for packages, forbidden in ((CLEAN_PACKAGES, CLEAN_FORBIDDEN),
                                (RENDER_PACKAGES, RENDER_FORBIDDEN)):
        for package in packages:
            for path in _sources(base / package):
                rel = _rel(path, base)
                tree = _tree(path)
                for dotted in _imported_names(tree):
                    for bad in forbidden:
                        if _touches(dotted, bad):
                            problems.append(f"{rel} imports {dotted}")
                    # A render package may import `match` -- it needs the facade and the
                    # frame types -- but not the modules inside it that read truth, which
                    # bind World, AgentTruth and cave at module level. This is the hole the
                    # truth channel itself opened: `from ..match.stage_builder import World`
                    # handed the renderer the World class, verified live.
                    if package in RENDER_PACKAGES:
                        tail = dotted.lstrip(".")
                        for reader in _TRUTH_READER_MODULES:
                            if tail == reader or tail.startswith(reader + "."):
                                problems.append(f"{rel} imports {dotted}, which reads truth")
                    root = dotted.lstrip(".").split(".")[0]
                    if root in REFLECTION_MODULES:
                        problems.append(f"{rel} imports {root}, which hands out modules")
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        problems += [f"{rel} imports the bare {PACKAGE} package"
                                     for a in node.names if a.name == PACKAGE]
    return problems


# ---- rule 4 -----------------------------------------------------------------------------
def _attribute_rule(base: Path) -> list[str]:
    """`self.sim.world` is not an import, so the import scan never saw it."""
    problems: list[str] = []
    for package in RENDER_PACKAGES:
        for path in _sources(base / package):
            for node in ast.walk(_tree(path)):
                if isinstance(node, ast.Attribute) and node.attr in MODULE_FETCHERS:
                    problems.append(f"{_rel(path, base)} uses .{node.attr}")
                elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                      and node.func.id in FETCHER_CALLS
                      and not (len(node.args) > 1 and isinstance(node.args[1], ast.Constant))):
                    # `getattr(x, "_wor" + "ld")` and `vars(x)` defeat a literal check, and
                    # nothing in a render package needs a computed attribute name.
                    problems.append(f"{_rel(path, base)} calls {node.func.id} "
                                    f"with a computed name")
                elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
                    problems.append(f"{_rel(path, base)} reads .{node.attr}")
                elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                        and node.func.id == "getattr" and len(node.args) >= 2
                        and isinstance(node.args[1], ast.Constant)
                        and node.args[1].value in FORBIDDEN_ATTRS):
                    problems.append(f"{_rel(path, base)} getattrs {node.args[1].value!r}")
    return problems


# ---- rule 5 -----------------------------------------------------------------------------
def _allowlist_rule(base: Path) -> list[str]:
    """A package-by-package scan only catches leaks in the packages someone thought of.
    An allowlist makes every new truth reader a deliberate edit to one line in one file."""
    problems: list[str] = []
    for path in _sources(base):
        rel = _rel(path, base)
        if rel.split("/")[0] in TRUTH_READERS or rel in TRUTH_READERS:
            continue
        for dotted in _imported_names(_tree(path)):
            if _touches(dotted, "truth"):
                problems.append(f"{rel} imports {dotted} and is not an allowed truth reader")
    return problems


# ---- rule 6 -----------------------------------------------------------------------------
def _exporter_rule(base: Path) -> list[str]:
    path = base / "match" / "stage_builder.py"
    return [f"match/stage_builder.py imports {dotted}"
            for dotted in _imported_names(_tree(path))
            if _touches(dotted, "belief") or _touches(dotted, "policy")]


# ---- rule 7 -----------------------------------------------------------------------------
def _annotation_ok(node: ast.expr, local: set[str]) -> bool:
    """float | int | bool | str | tuple[...] | ndarray | None, or a dataclass declared
    in the same module. Anything else -- a World, an Ancient, a callable -- is a leak."""
    if isinstance(node, ast.Constant) and node.value is None:
        return True
    if isinstance(node, ast.Name):
        return node.id in PLAIN_TYPES or node.id in local
    if isinstance(node, ast.Attribute):          # np.ndarray
        return node.attr in PLAIN_TYPES
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return _annotation_ok(node.left, local) and _annotation_ok(node.right, local)
    if isinstance(node, ast.Subscript):          # tuple[X, ...]
        if not _annotation_ok(node.value, local):
            return False
        inner = node.slice.elts if isinstance(node.slice, ast.Tuple) else [node.slice]
        return all(isinstance(e, ast.Constant) and e.value is Ellipsis
                   or _annotation_ok(e, local) for e in inner)
    return False


def _frame_shape_rule(base: Path) -> list[str]:
    problems: list[str] = []
    tree = _tree(base / "match" / "stage_frame.py")
    declared = {n.name for n in tree.body if isinstance(n, ast.ClassDef)}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        frozen = slots = False
        for deco in node.decorator_list:
            if isinstance(deco, ast.Call):
                for kw in deco.keywords:
                    if kw.arg == "frozen" and getattr(kw.value, "value", False) is True:
                        frozen = True
                    if kw.arg == "slots" and getattr(kw.value, "value", False) is True:
                        slots = True
        if not (frozen and slots):
            problems.append(f"stage_frame.{node.name} is not frozen=True, slots=True")
        for field in node.body:
            if isinstance(field, ast.AnnAssign) and not _annotation_ok(field.annotation, declared):
                name = getattr(field.target, "id", "?")
                problems.append(f"stage_frame.{node.name}.{name} is not plain data")
    return problems


# ---- rule 8 -------------------------------------------------------------------------------
def _structure_rule() -> list[str]:
    """Removes the reachability rather than detecting the reach, then checks a real frame."""
    from .match_view import MatchView
    from .sim import Sim

    problems: list[str] = []
    sim = Sim(stage=True)
    if hasattr(sim, "world"):
        problems.append("Sim still exposes .world")

    match = MatchView(sim)
    public = {n for n in dir(match) if not n.startswith("_")}
    if public != set(MatchView.MEMBERS):
        problems.append(f"MatchView exposes {sorted(public ^ set(MatchView.MEMBERS))}")

    if not _raises(lambda: Sim(stage=False).stage()):
        problems.append("Sim(stage=False).stage() did not refuse")
    sim._in_tick = True
    if not _raises(sim.stage):
        problems.append("stage() built a frame from inside a tick")
    sim._in_tick = False

    match.advance_to(3.0)
    frame = match.stage()
    for field in dataclasses.fields(frame):
        value = getattr(frame, field.name)
        problems += _plain(f"StageFrame.{field.name}", value)
    return problems


def _plain(where: str, value: object) -> list[str]:
    if isinstance(value, np.ndarray):
        return [] if not value.flags.writeable else [f"{where} is a writeable array"]
    if isinstance(value, (bool, int, float, str)) or value is None:
        return []
    if isinstance(value, tuple):
        return [p for i, v in enumerate(value) for p in _plain(f"{where}[{i}]", v)]
    if dataclasses.is_dataclass(value):
        return [p for f in dataclasses.fields(value)
                for p in _plain(f"{where}.{f.name}", getattr(value, f.name))]
    return [f"{where} is a {type(value).__name__}, not plain data"]


def _raises(call: object) -> bool:
    try:
        call()                                        # type: ignore[operator]
    except AssertionError:
        return True
    return False


# ---- the whole thing -----------------------------------------------------------------------
def offending_imports(root: Path | None = None) -> list[str]:
    """Every violation of all eight rules, as one list of readable lines."""
    base = root or Path(__file__).resolve().parent.parent
    return (_import_rules(base) + _attribute_rule(base) + _allowlist_rule(base)
            + _exporter_rule(base) + _frame_shape_rule(base) + _structure_rule())


def assert_clean() -> None:
    problems = offending_imports()
    if problems:
        raise AssertionError("ground truth leaked downstream of the sensor layer:\n  "
                             + "\n  ".join(problems))


def summary() -> str:
    return (f"invariant holds ({RULE_COUNT} rules): belief and policy cannot import truth "
            "or match, view and audio cannot import truth or name a World, only truth/, "
            "sensing/ and four files in match/ may read truth, the exporter cannot see "
            "belief, and every field of a live StageFrame is frozen plain data")


if __name__ == "__main__":
    assert_clean()
    print(summary())
