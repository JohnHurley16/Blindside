"""Shell out to the `induct` binary. The whole of this side of the seam.

The induction is Rust and is kept (`crates/blindside-induct`, the crate
ARCHITECTURE.md names); the corridor sim, this window and the evaluator are
throwaway Python. Copied from phase2 unchanged but for this note. The two sides talk through JSON files and this process
boundary, and through nothing else -- so nothing here reimplements induction,
rendering, deciding or diffing, and when the two disagree the Rust side is right.

The binary's path comes from `tuning.INDUCT_BIN`, overridable by the environment
variable INDUCT_BIN.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from . import tuning as T
from .seam.choice_diff import ChoiceDiff
from .seam.induction import Induction
from .seam.rendered import Rendered

STEP_FIELDS: tuple[str, ...] = ("tick", "junction", "predicates", "raw", "action")   # FORMAT.md


class InductClient:
    """One block list, one binary, one scratch directory for the files it passes."""

    def __init__(self, blocks: Path, binary: Path | None = None,
                 workdir: Path | None = None) -> None:
        self.blocks: Path = Path(blocks)
        self.binary: Path = Path(binary) if binary is not None else self.default_binary()
        self.workdir: Path = Path(workdir) if workdir is not None else Path(
            tempfile.mkdtemp(prefix="phase1-seam-"))
        self.workdir.mkdir(parents=True, exist_ok=True)
        self.calls: int = 0

    @staticmethod
    def default_binary() -> Path:
        override = os.environ.get("INDUCT_BIN")
        return Path(override) if override else T.INDUCT_BIN

    def available(self) -> bool:
        return self.binary.is_file()

    def require(self) -> None:
        if not self.available():
            raise FileNotFoundError(
                f"no induct binary at {self.binary.as_posix()}: build it with "
                f"`cargo build --release` in crates/blindside-induct, or set INDUCT_BIN")

    # ---- the four commands ----------------------------------------------------------------
    def induce(self, traces: Sequence[Path], out: Path) -> Induction:
        """Every demonstration in, the smallest consistent tree out -- or the
        conflicts and the question that resolves them.

        The crate refuses a field it does not know (`strict.rs`: every type carries
        `deny_unknown_fields`), and the cave's trace carries one optional, Python-side
        field per step, `reason` (CAVE-BLOCKS.md 5). So the binary is handed a copy of
        each trace holding the contract's fields and nothing else, under the same file
        name in `workdir/contract/`; the conflicts and the query it reports name those
        copies, which is the same name. The trace on disk keeps its `reason`.
        """
        argv = ["induce", "--blocks", str(self.blocks), "--out", str(out)]
        argv += [str(self._contract_copy(p)) for p in traces]
        return Induction.parse(self._run(argv), out)

    def _contract_copy(self, trace: Path) -> Path:
        data = json.loads(Path(trace).read_text(encoding="utf-8"))
        data["steps"] = [{k: step[k] for k in STEP_FIELDS if k in step} for step in data["steps"]]
        folder = self.workdir / "contract"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / Path(trace).name
        path.write_text(json.dumps(data, indent=1), encoding="utf-8")
        return path

    def render(self, tree: Path) -> Rendered:
        return Rendered.parse(self._run(["render", str(tree), "--blocks", str(self.blocks)]))

    def decide(self, tree: Path, predicates: Mapping[str, bool],
               raw: Mapping[str, float]) -> str:
        """The action this tree takes at one stop. The authority on what a tree does."""
        stop = json.dumps({"predicates": dict(predicates), "raw": dict(raw)})
        data = self._run(["decide", str(tree), "--blocks", str(self.blocks)], stdin=stop)
        return str(data["action"])

    def diff(self, a: Sequence[str], b: Sequence[str], name: str = "diff") -> ChoiceDiff:
        """Where two lists of choices first part company. The lists are written out
        as the contract's {"choices": [...]} files, because that is what the CLI reads."""
        path_a = self._write(f"{name}-a.json", {"choices": list(a)})
        path_b = self._write(f"{name}-b.json", {"choices": list(b)})
        return ChoiceDiff.parse(self._run(["diff", "--blocks", str(self.blocks),
                                           str(path_a), str(path_b)]))

    # ---- the process ------------------------------------------------------------------------
    def _write(self, name: str, payload: dict[str, Any]) -> Path:
        path = self.workdir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def _run(self, argv: list[str], stdin: str | None = None) -> dict[str, Any]:
        self.require()
        self.calls += 1
        done = subprocess.run([str(self.binary), *argv], input=stdin,
                              capture_output=True, text=True)
        if done.returncode != 0:
            raise RuntimeError(f"induct {argv[0]} exited {done.returncode}: "
                               f"{done.stderr.strip() or '(no message)'}")
        return json.loads(done.stdout)
