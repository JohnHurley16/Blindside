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
                  {"id": "uncertainty_exceeds",      "label": "lost", "param": "theta", "stage": 2},
                  {"id": "carrying_cargo",           "label": "carrying", "stage": 2} ],
  "actions":    [ {"id": "take_branch",       "label": "take a branch", "stage": 1},
                  {"id": "return_to_beacon",  "label": "go back", "stage": 2} ] }
A predicate with "param" is parametric: its boolean is a function of a raw number and a parameter.

WHAT IS CONTRACT AND WHAT IS NOT. The ids, the shape and the presence of "param" are the
contract: both sides must agree on them or nothing works. A "label" is content -- the words a
player reads -- and either side may change one without telling the other, because nothing is
keyed on it; the induction prints whatever label it is handed and never a bare id, which is the
whole reason labels travel in this file. "stage" is optional and Python-side: the staged
tutorial (docs/PHASE-2-OPEN-QUESTIONS.md (a)) uses it to decide which blocks exist in which
run. The induction ignores it and reads each trace's own "enabled_predicates" instead, which
is the field that must agree.

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
A node is either {"action": id} or {"predicate": id, "yes": node, "no": node}.

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

No optional fields have been added by this side.

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

**Threshold fitting.** For each parametric predicate, the candidate values are the
midpoints between consecutive distinct raw values across all traces, plus one below the
minimum and one above the maximum (half the smallest gap outside; one unit when only one
value was ever recorded). Each candidate's margin is its distance to the nearest recorded
value. Every combination of candidates across parametric predicates is tried; predicates
are re-evaluated from raw under each. The combination chosen is the one that admits the
smallest tree (by the three criteria above), then the widest margin (the smallest margin
across parametric predicates, when there are several), then the smallest values. A
parametric predicate with no raw value anywhere keeps the first value any trace's
`params` gives it, or has no entry.

**Conflicts.** Two stops conflict when their vectors are identical and their actions
differ. When no candidate combination is free of conflicts, `consistent` is false, `tree`
is null and `--out` is not written. The conflicts reported are those under the combination
that would need the fewest stops disowned to become consistent (within each vector class,
every stop outside its majority action), then the widest margin, then the smallest values.
Pairs are listed with the earlier stop first (trace order as given on the command line,
then stop index) and sorted.

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
