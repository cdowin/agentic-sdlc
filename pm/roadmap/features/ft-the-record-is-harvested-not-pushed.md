---
id: ft-the-record-is-harvested-not-pushed
kind: feature
milestone: "ms-nothing-is-hand-rolled"
name: the record is harvested, not pushed
status: planning
reviewed:
depends_on: []
consumed_by: []
changelog:
---

# the record is harvested, not pushed

**The one thing worth taking from `orca-sdlc-kit`**, and it closes a defect this tree carried for
five milestones. Full reading:
[`docs/research/2026-09-08-orca-sdlc-kit.md`](../../../docs/research/2026-09-08-orca-sdlc-kit.md) §2.2.

## The bet we made, and the measurement that it failed

`tools/hooks/cc-ledger-subagent.sh:284` takes the transcript path out of the hook payload
(`agent_transcript_path`). No hook fires → no path → no row. That is a **push** architecture: the
harness must hand us the path at the moment the agent stops.

`0.6.0/D8` measured it failing. The session that closed 0.6.0 had a project root above the checkout,
so `.claude/settings.json` was never loaded, no `SubagentStop` fired, and the four dispatch rows in
that milestone's ledger were **typed by hand**. `check pm` U4 has been correct about this for five
milestones and nobody could act on it.

## What Orca does instead

It **pulls**. After a run it scans `~/.claude/projects/<slug>/*.jsonl` and
`~/.codex/sessions/YYYY/MM/DD/`, filters on an mtime window plus an exact `cwd` match against the
worktree, and attributes a session to a step by spec-head substring containment.

**The principle, which is what transfers:** a record that depends on something firing at the START
is a record you will not have; a record reconstructed at the END from what the harness already wrote
is one you will.

Their limits are real and we should state them rather than inherit them blind: subagent attribution
is by time-window containment only, so their own shipped parallel group loses subagent tokens to an
unattributed bucket; and only two agents have adapters, so their shipped `opencode` step is
permanently unmeasured.

## The shape here, and why it is smaller than theirs

**`pm ledger record --from-transcript <path>` already exists.** The missing piece is a way to FIND
the transcript. That is a locator, not a capability — rule 11's cheapest layer.

And our attribution problem is easier: their target is a STEP the tool must infer; ours is a GRAIN
the operator already knows and passes on `--grain`.

**It emits; it does not write.** The verb LISTS candidates — path, cwd, time span, size — and the
operator pipes what they choose into the record verb we already have. `0.5.0/D1` applied to
discovery. A harvester that writes rows on its own would be inferring which dispatch was which,
which is rule 9's line.

**Rule 8 is the collision and `[emit]`/`[dispatch]` are the precedent.** No file reads a path outside
this checkout — so the project DECLARES where its transcripts live and the reader refuses BY NAME
when the section is absent. That is the WORKFLOW-key pattern of rule 5, and it keeps rule 8's intent
exactly: the package still knows nothing about consumers, it reads what one told it.

Steal their honest-null discipline verbatim: `u.total > 0 ? {...} : null` and
`heads.size > 1 → return null; // ambiguous — never guess`. That is our own rule 11 arrived at
independently, and it is why the first thing this must do is print `—` with a reason rather than a
zero.

## Ship criterion

A read verb lists candidate transcripts for a grain — cwd-matched and time-windowed — naming its
columns in order, printing an honest `—` with a reason where it cannot tell, and counting what it
could not attribute rather than dropping it.

It writes nothing, spawns nothing, and reads only what `[ledger] transcripts` declares; an absent
section refuses by name.

A row it produces is one `pm ledger record --from-transcript` ACCEPTS — proven by lifting the
rendered line out and running it in a scratch tree, the way `TheDispatchCanBeRECORDED` already does.

The next milestone's dispatch rows are not typed by hand, and `pm ledger report` says so.

## Proof budget

  cases: 4
  tier: pyunit + one shell
  lands in: `tests/test_pm_ledger*.py`; the pasteable-line case belongs beside
    `TheDispatchCanBeRECORDED` in `tests/test_dispatch.py`, which is the precedent for it
  what already covers this: `test_the_record_line_it_prints_is_one_the_verb_ACCEPTS` (0.6.0) is
    exactly this contract for the other half of the pair.

## Out of scope

Making the tool export anything, fire a hook, or write a row it inferred. Hard rule 2, rule 9, and
0.5.0/D1 — the same three that scoped the 0.6.0 half of this.

Fixing the harness's project-root behaviour. Not ours; U4 already names it.
