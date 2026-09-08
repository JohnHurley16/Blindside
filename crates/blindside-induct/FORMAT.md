# blindside-induct: the seam

The Python side (the toy corridor sim, its window and its evaluator; throwaway) and this
crate (the induction; kept as `blindside-induct`) talk through JSON files only. This file
is the contract between them. Both sides implement it exactly. Field names are final; a
builder who needs a field that is not here adds it as OPTIONAL and says so in its report.

The second half states what the induction guarantees, as implemented.

## The contract

```
blocks.json  (the block list; the only place the day-one items are enumerated on either side)
{ "predicates": [ {"id": "unexplored_branch_exists", "label": "a branch here that leads to
                                                                unexplored ground", "stage": 1},
                  {"id": "uncertainty_exceeds",      "label": "lost", "param": "theta",
                                                     "provisional": 3.0, "stage": 2},
                  {"id": "carrying_cargo",           "label": "carrying", "stage": 2} ],
  "actions":    [ {"id": "take_branch",       "label": "take a branch", "stage": 1},
                  {"id": "return_to_beacon",  "label": "go back", "stage": 2} ] }
A predicate with "param" is parametric: its boolean is a function of a raw number and a parameter.
A parametric predicate may carry "provisional": the value of its parameter a demonstration reads
its boolean with before the induction has fitted the real one. It is a number, it is optional,
and it is refused on a predicate that has no "param".

WHY "provisional" IS ON THE BLOCK AND NOT IN A TUNING FILE. A block is a data change plus its
evaluator (docs/DESIGN-PRINCIPLES.md 1). A parametric block used to be that plus a value in the
Python side's tuning file, keyed by the parameter's name -- the tuning file names no block, so
that was the only key it had -- and that third edit was the one every demonstration mode refused
to start without. The value belongs beside the block it is for, so that it travels with it. The
number should sit LOW: a demonstration stops when a predicate crosses its provisional threshold,
so a player can never teach a threshold below the one the bot stops at. The bot asks early, the
player says carry on until they mean it, and the induction fits the boundary between the
carry-ons and the reactions. Two predicates never share a value now, whatever their parameters
are called. (On the Python side a tree that runs a demonstration sets its own values for the
predicates it reads, and the provisional ones stand for any other enabled predicate.)

WHAT IS CONTRACT AND WHAT IS NOT. The ids, the shape and the presence of "param" are the
contract: both sides must agree on them or nothing works. A "label" is content -- the words a
player reads -- and either side may change one without telling the other, because nothing is
keyed on it; the induction prints whatever label it is handed and never a bare id, which is the
whole reason labels travel in this file. "stage" and "provisional" are optional and
Python-side: the staged tutorial (docs/PHASE-2-OPEN-QUESTIONS.md (a)) uses "stage" to decide
which blocks exist in which run, and a demonstration reads a parametric predicate's boolean at
its "provisional" value. The induction ignores both. It reads each trace's own
"enabled_predicates" and "params" instead, which are the fields that must agree.

trace.json  (one demonstration)
{ "seed": 7,
  "enabled_predicates": ["unexplored_branch_exists"], "enabled_actions": ["take_branch"],
  "params": {"uncertainty_exceeds": {"theta": 3.0}},
  "steps": [ {"tick": 120, "junction": 3,
              "predicates": {"unexplored_branch_exists": true, "uncertainty_exceeds": false, "carrying_cargo": false},
              "raw": {"uncertainty_exceeds": 2.31},
              "action": "take_branch"} ],
  "outcome": {"success": true, "ticks": 900, "lost": false} }
"predicates" are the booleans as evaluated during the demonstration with "params"; "raw" carries the
number behind every parametric predicate so the threshold can be re-fitted. Disabled predicates are
absent from both maps.

tree.json  (a decision tree = a policy)
{ "params": {"uncertainty_exceeds": {"theta": 2.9}},
  "root": {"predicate": "carrying_cargo",
           "yes": {"action": "return_to_beacon"},
           "no":  {"predicate": "uncertainty_exceeds",
                   "yes": {"action": "return_to_beacon"},
                   "no":  {"predicate": "unexplored_branch_exists",
                           "yes": {"action": "take_branch"},
                           "no":  {"action": "return_to_beacon"}}}} }
A node is either {"action": id} or {"predicate": id, "yes": node, "no": node}. "params" holds a
value only for the parametric predicates the tree tests; a reader must not expect one for any other.

induct CLI (Rust) -- all output on stdout as JSON, exit 0 unless usage/IO error (2):
  induct induce --blocks blocks.json --out tree.json TRACE.json [TRACE.json ...]
     -> {"consistent": true|false, "tree": <tree or null>,
         "conflicts": [[{"trace": "path", "index": 3}, {"trace": "path", "index": 7}], ...],
         "query": {"pair": [stepref, stepref], "text": "..."} | null }
  induct render tree.json --blocks blocks.json     -> {"lines": ["..."], "sentence": "..."}
  induct decide tree.json --blocks blocks.json     reads one step JSON (the "predicates"+"raw" of a
                                                    step) on stdin -> {"action": id}
  induct diff --blocks blocks.json A.json B.json   A and B are {"choices": [action ids]} ->
     {"first_difference": n | null, "a": id | null, "b": id | null}
```

"provisional" on a predicate is the one optional field added since the contract was first
written; the Python side needed it and this side accepts and ignores it. This side has added none.

## What the induction guarantees

**Blocks are a list.** The crate never names a predicate or action. Every id, label and
parameter name it prints comes from `blocks.json`. A predicate's position in the block list
is its column in every predicate vector.

**How a stop is read.** For every predicate in the block list, at every stop:

- parametric, with a raw value at the stop and a value for its parameter: `raw > value`;
- otherwise, the boolean the stop recorded under that predicate id;
- absent from both maps: **false**. The block did not exist in that run, so its condition
  did not hold. This is what makes a tutorial run with fewer blocks evidence rather than a
  contradiction. `enabled_predicates` is not consulted; the maps are. (The example trace
  above records all three predicates while enabling one; both forms are accepted.)

`decide` reads a stop the same way, with the tree's own `params`. So a tree decides
identically on the traces it was induced from and on live stops.

**Consistency.** A tree is consistent with a trace set when, at every stop of every trace,
walking the tree on that stop's vector reaches the recorded action.

**Minimality.** When a consistent tree exists, the one returned has the fewest internal
(predicate) nodes of any consistent tree over the block list. Ties are broken by fewest
distinct predicates, then by the lexicographically smallest preorder sequence of predicate
ids (so, of two otherwise equal trees, the one whose root id sorts first). Those three
criteria identify a single tree. The search is exact: a memoised recursion over the subset
of distinct vectors a node sees gives the minimum size; it is repeated per allowed
predicate subset to settle the distinct-predicate tie; the lexical tie is settled root
first, which is exact because subtree sizes are fixed once the root is. It is written for
about six predicates and refuses a block list with more than eight (`tuning.rs` says
why); past that the search needs a different algorithm.

**Threshold fitting.** For each parametric predicate, the distinct raw values recorded
across all traces cut the line into bands: one below the smallest, one between each
consecutive pair, one above the largest. Every threshold within a band reads the recorded
stops identically, so one threshold per band is all the search tries. Every combination of
bands across parametric predicates is tried; predicates are re-evaluated from raw under
each. The combination chosen is the one that admits the smallest tree (by the three
criteria above), then the widest band (the narrowest band across parametric predicates,
when there are several), then the smallest values. The two outer bands are unbounded --
nothing was ever recorded past the ends -- and are taken to reach half the smallest gap
past the end reading (one unit when only one value was ever recorded), so they never win
on width unless every gap is that tight. A parametric predicate with no raw value anywhere
keeps the first value any trace's `params` gives it, or has no entry.

**The tree's `params` carries values only for the predicates the tree tests.** Every
parametric predicate with readings is fitted during the search, because the search has to
know what tree each threshold admits; but a value for a predicate the chosen tree never asks
about was not fitted *to* anything, and a value nobody fitted is not a fit, so it is not
written. `render`, `decide` and `diff` take a tree that has no entry for a predicate it does
not test (`diff` never reads a tree at all), and `decide` on a stop that carries a reading
for such a predicate never consults it, so needs no threshold for it.
`tests/untested_params.rs` is that property.

**The threshold reported is the roundest number in the chosen band.** Not the band's
midpoint: the shortest decimal strictly inside the band, and of two equally short the one
nearer the middle, and of those the smaller. A midpoint of two readings is a sixteen-digit
number, three digits of which reach the player through the render -- so the number on the
panel would not be the number in the file, and a stop between them would decide one way in
the sim and the other in the tree. Choosing a round number when the threshold is fitted,
rather than rounding one when it is printed, is what makes `induce`, `render` and `decide`
agree on a reading that sits exactly on the boundary. `tests/fitted_numbers.rs` is that
property.

**What the threshold fit guarantees, and what it does not.** It guarantees that the
reported threshold reads every recorded stop exactly as the search's candidate did, so the
tree reproduces every recorded choice and `decide` agrees with `induce` on all of them;
that the threshold is a round number, and a pure function of the traces. It guarantees
nothing about where the true threshold was within the bracket the demonstrations left it,
because the demonstrations do not say: every threshold in the bracket reproduces them
equally well. Measured over the corridor sweep in `tests/threshold_fit.rs` (270 runs at ten
non-round thresholds, 200 unseen stops each), the widest-band rule decides 94.85% of unseen
stops the way the generating tree would, against 94.83% for a threshold put at the exact
middle of the bracket, and lands 2.7 cells from the true threshold on average; a rule that
reports the middle of the bracket measured within noise of it on unseen decisions and was
not kept. What is left is the width of the bracket, and no rule that reads only the
demonstrations can do better than the bracket allows. `tests/round_trip.rs` bounds the
fit's error as a fraction of the bracket.

**Conflicts.** Two stops conflict when their vectors are identical and their actions
differ. When no candidate combination is free of conflicts, `consistent` is false, `tree`
is null and `--out` is not written. The conflicts reported are those under the combination
that would need the fewest stops disowned to become consistent (within each vector class,
every stop outside its majority action). Pairs are listed with the earlier stop first
(trace order as given on the command line, then stop index) and sorted.

Which band the threshold is reported from matters most here, because several bands usually
tie on the count of stops to disown and they do not report the same pairs. On data where
every band ties, a threshold below every reading makes every stop read alike, and a flipped
choice is then reported as contradicting every other stop -- including the ones whose
readings sit the other side of it, which is not a pair anyone can act on. So among the
tying bands -- all of them, not only those next to the one the search found, since the tie
set need not be contiguous -- the one reported from is the one whose conflict pairs are
between the closest readings: pairs are compared by how far apart their two readings are,
widest first, so the band whose widest pair is narrowest wins, then the one whose next
widest is, and so on, and a band that has no pair left to compare beats one that has more.
A stop with no reading for the predicate is at no distance from anything, since its reading
did not enter into the pair. Of bands that compare equal, the widest, then the lowest. The
threshold reported is the roundest number in that band, as above. The contradiction shown
is then the one a player would name: it turned back at this reading and kept going at a
higher one. `tests/contradiction.rs` holds the cases, including the tie sets that are not
contiguous.

**The query.** The pair asked about is the conflicting pair whose resolution removes the
most conflicts. Resolving a pair means one of its two stops takes the other's action; a
pair's score is the larger net reduction of its two resolutions. Within a class of
identical vectors, moving one stop from action *x* to action *y* removes
`count(y) - count(x) + 1` conflicts (negative when it creates more than it removes), so
the pair from the most lopsided class wins: the one where a single stop is most clearly
the odd one out. Earliest pair on a tie. Its `text` shows the two stops side by side:
where each was (`stop <index> of <trace> (junction, tick)`), every predicate's label with
its value at that stop and, for a parametric one, the raw reading in brackets
(`lost: no (2.31)`), or `not in this run` for a block absent there; then `you chose:
<action label>`; then the question *Which one would you do differently?* Ids never appear
in the text.

**Render.** `lines` is one line per node: a branch is `label?`, or
`label (param = value)?` when the tree carries a value for it; its children follow,
indented by two, prefixed `yes: ` and `no: `. `sentence` flattens the tree into an ordered
list of clauses, one per leaf, yes branch first. Each clause names only the predicates
that held on its path, since *otherwise* excludes everything listed before it. A chain
reads *If carrying, go back. Otherwise if lost, go back. Otherwise if an unexplored branch
here, take a branch. Otherwise go back.*; a nested yes branch reads *If carrying and lost,
go back. Otherwise if carrying, take a branch. ...*; a single leaf reads *Always go back.*
Numbers are shown to three decimals with trailing zeros trimmed.

**Diff.** `first_difference` is the first index at which the choice lists differ, or at
which one ends and the other does not; `a` and `b` are the choices there, null for a list
that has ended. All three are null when the lists are identical.

**Determinism.** Every command is a pure function of its input files: no clock, no
randomness, and every map whose order reaches the output is a `BTreeMap`. Identical input
gives byte-identical output.

**What is refused.** A file that is quietly misread is worse than one that is rejected,
because the Python side cannot tell the difference: it gets an answer either way. So every
document read by any subcommand -- block list, trace, tree, choice list, and the stop
`decide` reads on stdin -- must be a JSON **object**, never a positional array, and so must
everything the contract nests inside one (a predicate, an action, a stop, an outcome, a
node); no object anywhere in the document may **repeat a key**; and no object may carry a
**field this file does not name**. The exceptions are the two Python-side fields the
contract above names, both read and ignored: `"stage"` on a predicate or an action, which
must be an integer, and `"provisional"` on a parametric predicate, which must be a number
and is refused on a predicate with no `"param"`. A node carrying both `"action"` and
`"predicate"` is a typed error rather than
an action with its branch silently dropped, and a node carrying `"predicate"` must carry
both `"yes"` and `"no"`. `decide` checks the stop it is handed exactly as `induce` checks a
trace's stops: every predicate id it reads must be in the block list.

**Exit codes.** 0 with JSON on stdout; 2 with a message on stderr for a usage error, an
unreadable or unwritable file, JSON that does not match the contract, an id that is not
in the block list, a trace set with no stops at all, or a block list with more predicates
than the search is written for. The algorithm itself cannot fail.

## Examples

`examples/` holds one file of each kind the CLI reads: `blocks.json`; `demo-1.json` (a
tutorial run with one predicate and one action), `demo-2.json` and `demo-3.json` (full
runs); `demo-3-flipped.json` (`demo-3` with its first stop's choice flipped, so that
inducing it beside `demo-2` shows the inconsistent output and the query); `tree.json`
(the contract's example); `stop.json` (one stop for `decide`); `choices-a.json` and
`choices-b.json` (for `diff`).

`tests/threshold_fit.rs` measures the fit against a known tree over the corridor
`phase2/tuning.py` describes; run it with `cargo test --test threshold_fit -- --nocapture`
to see the tables. `tests/round_trip.rs` prints, under `--nocapture`, how far the fit lands
from the true threshold as a fraction of the bracket, beside what the bracket's middle and
its edges would score.
