---
id: st-adopt-probes-whether-this-tree-records
feature: ft-telemetry-arrives-with-the-bump
milestone: "ms-0.4.0"
name: adopt says whether telemetry is live, by probing
status: done
owner: claude
depends_on: ["st-the-gate-sees-a-courier-writing-nothing", "st-the-word-is-where-you-are-standing"]
kind: story
---

# adopt says whether telemetry is live, by probing
A consumer that bumps the pin can ask **"am I recording?"** and get an answer. `adopt` gains one
check of the kind it already runs — are the couriers wired, does the vehicle answer, is there a
ledger to write into — and it PROBES rather than inspects.

The posture is D5's and it decides every question here: **clearly available, warned when absent,
never mandatory.** A consumer that has not wired the couriers is not broken; it opted out. What it
must never be is silently opted out, which is the state this tree was in for the whole of 0.3.0.

## Acceptance criteria

1. `adopt` reports whether telemetry is live in the tree it runs in, and **names which of the three
   failure modes it hit**: the settings entries were never pasted; the `pm` target is not `.PHONY`
   or does not pass its environment, so `make` exits 0 without reaching the verb; `[pm.states.*]`
   is undeclared, so the CLI is inert. Each produces zero rows and zero complaint today.
2. **It is a probe, not an inspection.** Reading `.claude/settings.json` proves a string is
   present; running a courier's own `--self-test` against the consumer's vehicle proves the path
   works end to end. **Every courier already ships `--self-test` and `adopt` does not call it** —
   the capability exists, which makes this the cheap half.
3. It WARNS and never refuses. `adopt` writes nothing (D12), so this is a check line and an exit
   code the belt already owns.
4. The words are close to *"no ledger setup for milestone, no telemetry"* — the plain sentence a
   consumer needs, not a rule id.
5. `install-hooks` prints the settings block as it does **and then says it is not yet in force** —
   "these are not wired; `adopt` will report that until they are." A printed block that reads as
   informational is how step 1 gets skipped.
6. The CHANGELOG tells a bumping consumer what to run and what "live" means.
7. **NullBound and godot-devkit are the verification**, before the milestone closes — two real
   trees, not a fixture standing in for them. Report what each said.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | integration | `test_conveyor_adopt.py` already parametrizes the adopt checks — three rows, one per mode, plus all-green | amend |
| 2 | integration | the same rows, asserting the self-test actually RAN (its output, not a file read) | amend |
| 3 | integration | exit code unchanged when only this check is false | amend |
| 5 | unit | `test_install.py` pins the printed block | amend |
| 7 | — | not a case: two real trees, reported in the close | — |

If the probe reaches for anything this tree has and a consumer does not,
`tests/test_consumer_independence.py` is where that case belongs.

## Out of scope

Writing `.claude/settings.json` on a consumer's behalf — `install.py`'s reasoning stands (*"hand
maintained and there is no merge"*); this story makes the omission visible, it does not overturn
the decision. Any change to what the couriers record.

## Close

done: c4685d1 — `telemetry-live` is adopt's eighth check and it PROBES: the courier's own
`--self-test` against the consumer's real vehicle, which is the only thing that answers whether
`make -s pm ARGS=…` reaches the verb.
finding: the review's "adopt does not call `--self-test`" was already half wrong — `hooks-self-test`
delegates to `check hooks`, which replays the corpus. What was genuinely missing is the WIRING
question, which no check asked.
NOT DONE — AC7: NullBound and godot-devkit were not run against. They are other repos and this
session was scoped to this one; `adopt 0.4.0` here reports `ok: telemetry-live`, which proves the
check and not the reach. Named rather than quietly dropped.
