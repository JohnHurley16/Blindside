"""Check that belief, policy, motor and demo cannot reach ground truth.

ARCHITECTURE.md asks for a compile-time test asserting `Policy::evaluate` cannot
reach `World`. Python has no such thing and cannot forbid reflection, so this is
the loud equivalent, in three parts:

1. Imports, by AST. Inside the clean packages every import of a `phase2` module
   must resolve to an allowed one: the clean packages themselves, `geometry`,
   `tuning`, `sensing.returns` and `eval.run_outcome`. Truth, the rig, the session
   and the evaluator are not allowed, so neither is a name re-exported through
   them. The routes round the import statement are refused by shape rather than by
   spelling, because spelling is free: the modules that hand out other modules
   (`importlib`, `builtins`, `sys`, `inspect`, `ctypes`, `gc`) may not be imported
   at all, under any alias; `__import__`, `import_module` and `.modules` are refused
   however they are written; and `import phase2` on its own is refused, because a
   handle on the package is a handle on `phase2.truth.world.World` two attributes
   later. A clean module imports the module it wants by name or not at all.
2. Loading, at runtime. A fresh interpreter imports every module of the clean
   packages and nothing else; every `phase2` module loaded by then must be
   allowed. This catches what the AST cannot see: a leak through a package
   `__init__` outside the clean set, or any other transitive route.
3. The driver. A demonstration is handed a `DriverView`, never the `Session`, so
   the object it holds for the whole run has no `world` on it
   (`match/driver_view.py`). This one is structure and a check: a duck type is
   not a boundary, so `demo.run_driver.assert_narrow` refuses at construction any
   driver offering a public name the `RunDriver` protocol does not declare, and
   the Session offers several.

WHAT THIS CANNOT SEE, stated rather than implied. Python hands every object the
whole process: `().__class__.__base__.__subclasses__()` walks to any loaded class
without importing anything, and no AST check can refuse it without refusing
ordinary code. The fresh-interpreter check in part 2 bounds it -- a clean package
that never causes `phase2.truth` to load has nothing to walk to -- but a clean
module called from a process that has loaded truth elsewhere, which is every real
run, could reach it. That route is deliberate malice, not the accident this
guards against, and Phase 3 replaces the whole arrangement with a crate boundary
the compiler enforces.

It exists to catch the "just for debugging" accessor that someone adds later,
which is exactly how this invariant dies.

THE WINDOW AND THE REPLAYS are inside the clean set, which is the point of them
being written the way they are. Neither builds a World: a run is opened through
`demo.run_source.RunSource`, and `match.run_factory.RunFactory` is the only
implementation. So `view` draws Belief and `replay` re-simulates without either of
them having a name for ground truth.

THE ONE EXCEPTION, and it is Phase 1's: the after-the-run reveal. Once a run is
over the window draws what the corridor actually was, in red, under a banner that
says so, because a player who never finds out they were fooled learns nothing from
being fooled. Truth reaches it as a `reveal.TruthSnapshot` -- a frozen record of
plain numbers with no World, no Corridor and no behaviour on it -- built by
`match.reveal_builder.RevealBuilder` and handed to the View by `__main__` as a
callable. `reveal` is on the allowed list below; `truth`, `match` and
`sensing.sensor_rig` are not, so the snapshot is the only route and it only opens
after the run it describes has ended.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

PACKAGE: str = "phase2"
CLEAN_PACKAGES: tuple[str, ...] = ("belief", "policy", "motor", "demo", "replay", "view")
# Modules outside the clean packages that they may import: stateless helpers, the
# return types, the outcome record, the shapes of the JSON the induction speaks, the
# process boundary to the induct binary, and the after-the-run reveal record.
ALLOWED_LEAVES: tuple[str, ...] = ("geometry", "tuning", "sensing.returns",
                                   "eval.run_outcome", "seam", "induct_client", "reveal")
# Packages a leaf sits inside get loaded on the way to it. Their __init__ must stay
# free of imports; check 2 verifies that by loading them.
ALLOWED_PARENTS: tuple[str, ...] = ("sensing", "eval")
# Modules whose whole job is handing out other modules. A clean package has no use
# for any of them, and each is a one-line route to `phase2.truth`, so the rule is the
# import itself rather than what is done with it -- `import sys as _s` is still `sys`.
REFLECTION_MODULES: tuple[str, ...] = ("importlib", "builtins", "sys", "inspect",
                                       "ctypes", "gc", "pkgutil", "runpy")
# `sys` is on that list for `sys.modules`, but a script in the clean set legitimately
# wants `sys.exit` and `sys.argv`. Those two files import it and use nothing else from
# it; MODULE_FETCHERS still refuses `.modules` on any name, including these.
SYS_IS_FOR_THE_CLI_IN: tuple[str, ...] = ("demo/trace_validator.py",)
# Attribute names that fetch a module regardless of what they are called on:
# `builtins.__import__(...)`, `_s.modules[...]`, `il.import_module(...)`.
MODULE_FETCHERS: tuple[str, ...] = ("__import__", "import_module", "modules")


def allowed(module: str, binds: bool = True) -> bool:
    """May code in a clean package have this module loaded?

    `binds` says whether the statement puts this name in the module's namespace.
    `import phase2` does, and is refused: the package object carries every submodule
    already imported anywhere in the process as an attribute, so a handle on it is
    `phase2.truth.world.World` with two more dots. `from .. import geometry` binds
    only `geometry` while naming `phase2` on the way, and is fine; so is `phase2`
    merely being loaded, which check 2 cannot avoid.
    """
    if module == PACKAGE:
        return not binds
    if not module.startswith(PACKAGE + "."):
        return module.split(".")[0] not in REFLECTION_MODULES
    rest = module[len(PACKAGE) + 1:]
    for prefix in CLEAN_PACKAGES + ALLOWED_LEAVES:
        if rest == prefix or rest.startswith(prefix + "."):
            return True
    return rest in ALLOWED_PARENTS


def _resolve(package_parts: list[str], level: int, module: str | None) -> str:
    """The absolute dotted name a from-import refers to."""
    if level == 0:
        return module or ""
    base = package_parts[: len(package_parts) - (level - 1)]
    return ".".join(base + ([module] if module else []))


def _is_module(base: Path, dotted: str) -> bool:
    """Does this dotted name name a module or package on disk?"""
    rel = base.parent.joinpath(*dotted.split("."))
    return rel.with_suffix(".py").is_file() or (rel / "__init__.py").is_file()


def offending_imports(root: Path | None = None) -> list[str]:
    """Check 1: 'package/module.py imports X' for every disallowed import."""
    base = root or Path(__file__).resolve().parent.parent
    problems: list[str] = []
    for package in CLEAN_PACKAGES:
        for path in sorted((base / package).rglob("*.py")):
            rel = path.relative_to(base).as_posix()
            # the package a relative import counts from: the file's directory
            parts = [PACKAGE] + list(path.relative_to(base).with_suffix("").parts)[:-1]
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    module = _resolve(parts, node.level, node.module)
                    # the parent is named but not bound; the leaves are bound
                    targets = [(module, False)] + [(f"{module}.{a.name}", True) for a in node.names
                                                   if _is_module(base, f"{module}.{a.name}")]
                    problems += [f"{rel} imports {t}" for t, binds in targets
                                 if not allowed(t, binds)]
                elif isinstance(node, ast.Import):
                    problems += [f"{rel} imports {a.name}" for a in node.names
                                 if not allowed(a.name)
                                 and not (a.name == "sys" and rel in SYS_IS_FOR_THE_CLI_IN)]
                elif isinstance(node, ast.Name) and node.id in MODULE_FETCHERS:
                    problems.append(f"{rel} uses {node.id}")
                elif isinstance(node, ast.Attribute) and node.attr in MODULE_FETCHERS:
                    # `builtins.__import__`, `_s.modules`, `il.import_module`: the
                    # attribute is the tell, whatever the thing on the left is called.
                    problems.append(f"{rel} uses .{node.attr}")
    return problems


_LOAD_SCRIPT: str = """
import importlib, json, os, pkgutil, sys
root, package, clean = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
sys.path.insert(0, root)
for name in clean:
    importlib.import_module(f"{package}.{name}")
    for info in pkgutil.walk_packages([os.path.join(root, package, name)], prefix=f"{package}.{name}."):
        importlib.import_module(info.name)
print(json.dumps(sorted(m for m in sys.modules if m == package or m.startswith(package + "."))))
"""


def leaked_modules(root: Path | None = None) -> list[str]:
    """Check 2: the disallowed `phase2` modules that loading the clean packages
    alone, in a fresh interpreter, brings in."""
    base = root or Path(__file__).resolve().parent.parent
    argv = [sys.executable, "-c", _LOAD_SCRIPT, str(base.parent), base.name, ",".join(CLEAN_PACKAGES)]
    done = subprocess.run(argv, capture_output=True, text=True)
    if done.returncode != 0:
        raise AssertionError(f"loading the clean packages failed:\n{done.stderr}")
    return [m for m in json.loads(done.stdout) if m != PACKAGE and not allowed(m)]


def assert_clean(root: Path | None = None) -> None:
    problems = offending_imports(root) + [f"loading the clean packages loads {m}" for m in leaked_modules(root)]
    if problems:
        raise AssertionError("ground truth leaked downstream of the sensor layer:\n  "
                             + "\n  ".join(problems))


if __name__ == "__main__":
    assert_clean()
    print("invariant holds: belief, policy, motor, demo, replay and view cannot reach truth")
