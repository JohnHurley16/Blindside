"""What one correction produced: a demonstration rewritten from a stop, and the rule
induced over the set as it now stands."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..seam.induction import Induction
from ..seam.rendered import Rendered


@dataclass(slots=True, frozen=True)
class CorrectionResult:
    """`index` is the stop the rewrite began at, 0-based as the command line counts
    (the window says `index + 1`). `kept` steps before it are the old run's; the
    `replaced` old steps from it are gone and `new` ones stand in their place.
    `rendered` is the re-induced tree in words, or None when no consistent rule fits."""
    path: Path                      # the rewritten trace, at the demonstration's own name
    backup: Path                    # where the old one went
    index: int
    kept: int
    replaced: int
    new: int
    changed: bool                   # the new choices differ from the old ones
    induction: Induction
    rendered: Rendered | None

    @property
    def consistent(self) -> bool:
        return self.induction.consistent and self.induction.path is not None

    def sentence(self) -> str:
        """One line for a footer: the rule now, or why there is none."""
        if self.rendered is not None:
            # The footer is one strip sixty pixels tall, and a corrected rule is usually
            # a clause longer than the one it replaced -- a three-clause rule ran off the
            # right edge unread. Two lines fit; anything past them is on the terminal and
            # in tree.json, and the ellipsis says so.
            import textwrap
            lines = textwrap.wrap(f"the rule now: {self.rendered.sentence}", width=96)
            if len(lines) > 2:
                lines = lines[:2]
                lines[1] = lines[1][:93].rstrip() + " ..."
            return "\n".join(lines)
        query = self.induction.query
        first = query.text.splitlines()[0] if query is not None and query.text else ""
        return "no one rule fits everything you did" + (f": {first}" if first else "")
