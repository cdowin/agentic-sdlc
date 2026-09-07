---
id: ft-a-sink-wired-and-silent-is-a-finding
kind: feature
milestone: "ms-a-move-is-an-event"
name: a sink wired and silent is a finding
status: planning
reviewed:
depends_on: []
consumed_by: []
---

# a sink wired and silent is a finding

`recording-is-on-or-the-gate-is-red` (0.4.0) exists because the ledger couriers were wired,
executable, and recorded **nothing for the whole of 0.3.0, and nobody could tell**. The cause was a
fail-open courier with no fail-loud counterpart.

**The emit sink is the same trap, one release later, on a fresh surface.** A declared `[emit]` whose
sink has never been written to looks exactly like a tree that opted out.

## The rule this is an instance of

Hard rule 11: *"something the tree needs and does not have gets a NAMED line, never silence."* The
existing family is the model — a milestone past `todo` with no handoff, a grain with no binding, a
courier wired to write and writing nothing. This adds one member and joins `check pm`'s WARN family
rather than inventing a reporting shape.

    U2 today   couriers wired, ledgers empty
    this       [emit] declared, sink never written

**Opting out stays quiet.** A tree with no `[emit]` is not broken and gets no line. The finding is
*declared and silent* — a contradiction the tree is holding, not an absence of configuration. That
distinction is the rule: express what the project declared, report where the tree disagrees with it.

## Ship criterion

`check pm` names a declared sink never written to, as a WARN with its own rule id, reachable from
`pm vocabulary` so a consumer bumping the pin sees the rule before it fires. A tree declaring no
`[emit]` produces no line at all.

The check READS the tree — it never writes a probe row to find out, because a gate that mutates to
measure is a gate that lies about what it measured.

## Proof budget

  cases: 3
  tier: pyunit
  lands in: `tests/test_check_pm.py`, beside U2's cases
  what already covers this: U2's "wired and empty" case is the same shape with a different subject;
    these are rows on that harness, not a new family.

## Out of scope

Making emission mandatory. Rule 5's posture for telemetry — *clearly available and warned when
absent, never mandatory* — applies unchanged.
