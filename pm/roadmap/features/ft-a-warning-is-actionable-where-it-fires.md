---
id: ft-a-warning-is-actionable-where-it-fires
kind: feature
milestone: "ms-the-rule-reaches-the-work"
name: a warning is actionable where it fires
status: building
reviewed:
depends_on: []
consumed_by: []
---

# a warning is actionable where it fires

351 of 359 warnings on a real consumer tree are unactionable (#12). Rule 11 says absence is a
finding; it does not say every finding must be shouted forever. A surface people learn to scroll
past is a surface that has stopped working.

## The census, taken on this repo before anything was changed

`uv run -q agentic-sdlc check pm` on `milestone/0.6.0-the-rule-reaches-the-work`: **exit 0, 61
lines, 52 `WARN` lines, 10,958 characters of warning text.** Sorted by whether the operator who
just ran the gate can do something about the line *where they are standing*:

| family | lines | the grain it fires on | actionable HERE? |
|---|---|---|---|
| READY — no `## Proof budget` | 15 | all 15 in `done` | no |
| READY — feature with no stories | 22 | all 22 in `done` | no |
| READY — no `## Ship criterion` | 8 | 7 in `done`, 1 `building` | 1 of 8 |
| READY — milestone with no `branch:` | 1 | `ms-0.1.0`, `done` | no |
| READY — milestone with no `handoff.md` | 1 | `building` | yes |
| U1 — declared state never held | 3 | one wall per grain kind | yes, but three times |
| U5 — arrival with no disposition | 1 | names both grains | yes |
| U4 — couriers wired, nothing recorded | 1 | 839 chars, ~11 wrapped lines | yes, at the end |

**45 of 52 fire on a grain in the `done` category.** Nobody is going to write a `## Ship
criterion` for `ft-the-extraction-finishes`, which shipped in 0.1.0. That is not information; it
is the 351. The remaining 7 are all actionable, and they were sitting under a 45-line wall.

The boundary is already drawn ONCE in this module and it is D12's: `_changelog_answered` excludes
shipped milestones, and its own docstring says why — *"168 grains closed before the field existed,
and asking them all for a sentence nobody will write is 351-of-359 again."* READY never got that
treatment because it predates the sentence.

## What this feature does, and what it refuses to do

Rule 11's floor is absolute: **no family is deleted and no absence goes silent.** Three moves,
each one of the three shapes the rule permits — a different rung, a rolled-up count, a message
that names the fix where it fires.

1. **READY grades a grain while its section can still change what ships.** The family's gate was
   `left_todo` — `in_progress` OR `done`. It becomes `in_progress`. A `## Ship criterion` is a
   promise about work that has not happened; on a `done` grain it is retro-fiction, and the rung
   where writing one still changes an outcome is the rung the grain is standing on while it is
   built. What a closed grain would have earned becomes ONE counted `READY` line carrying both
   halves of the census — the gaps named on live grains, and the gaps counted on closed ones.
   The line prints whenever the family graded anything, including at zero, because a walk that
   graded nothing has to say so (rule 4).

2. **U1 is one line for one fact.** Three near-identical paragraphs, one per grain kind, saying
   the same sentence about `[pm.states.*]`. They roll into one line that names every unused state
   under its kind and keeps the in-use count. Same fact, same names, one third of the text.

3. **U4 names the fix in its second sentence.** It fires on every run in a wired checkout and it
   is right to — the operator can act on it — but the fix sat at the end of 839 characters,
   behind a thirteen-kind row census. The census becomes its three largest kinds plus a count and
   a pointer at `pm ledger report`, which is the verb that already breaks them down; rule 11's
   read side, naming the capability in the surface someone is standing in.

Nothing is retired, so `model.RETIRED_CHECKS` is untouched and no rule id moves. `READY` is
ungated by design (it has no `[pm] checks` id) and stays that way.

## Ship criterion

`check pm` on this repo prints **5 warning lines, not 52**, at exit 0, and every one of the five
names a fix its reader can perform from where it fired: two READY gaps on grains that are
`building`, one U1 line, one U5 line, one U4 line.

**No family is deleted and no absence is silent.** Every READY gap on a closed grain is carried by
one counted `READY` line that states how many there are and why they are not named; the line
prints even when the count is zero, so the family can never go quiet by grading nothing.

**The narrowed rules still bite.** A tree that earns a READY warning while `in_progress` still
gets it, named, at the same line shape as before — proved by planting an empty section on a
`building` grain and on a `done` one in the same fixture and asserting the first warns and the
second is counted. Deleting the narrowing flips the counted line's numbers; deleting the section
check flips the WARN.

**Rule 6 is paid.** Three output shapes change — the READY gate's grain population, U1's three
lines becoming one, U4's WARN text — and each is named in `changelog:`. `check pm`'s module
docstring and the one sentence in `guidance/pm-operations.md` that describes the WARN population
follow the code, or `check doc` and the install census have a shipped sentence contradicting
shipped behaviour, which is the defect this milestone exists to end.

## Proof budget

  cases: 3 amended, 1 new
  tier: pyunit (`make unit`) — every case is a function call against a temp tree, no spawn
  lands in: `tests/test_pm_gate.py`, in the two classes that already own these families:
    `ReadyIsAStampWithACheck` and `D7ADeclaredStateNobodyUses`
  what already covers this:
    `test_each_warning_fires_on_the_scaffold_and_is_silent_on_a_filled_grain` already writes an
    empty section on a `done` story and asserts it WARNS — it is the case that encodes the old
    boundary, so it is the case that has to move, and amending it is cheaper and more honest than
    a second case asserting the opposite beside it. `test_it_names_the_unused_states_with_the_count_in_use`
    already asserts U1's per-kind phrasing and moves with the roll-up.
    Neither covers the ROLL-UP itself — that nothing goes silent — so one new case plants an
    empty section on a `building` grain and a `done` grain in one tree and holds both halves of
    the counted line, which is the only assertion that fails if the narrowing quietly drops the
    closed grains instead of counting them.

## Out of scope

U2, U3 and V7's counted lines: they do not fire on this repo, so there is no measurement behind
changing them, and rule 10 says a change that cannot be shown to bite is not warranted.

Any `--verbose` flag on `check pm`: it would need a route in `cli.py`, which this feature does not
own, and the counted line answers the same question without a new surface.
