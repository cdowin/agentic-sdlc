Cold-start only. Everything derivable is a command — never restate `pm status`, `git log` or `pm ledger report`.

# ms-the-ledger-is-a-stamp the ledger is a stamp — handoff

## 1. Where the work lives

| | |
|---|---|
| **Branch** | `milestone/0.9.0-the-ledger-is-a-stamp` (the stamp in `branch:`). **Not created yet**: cut it from `main` AFTER v0.8.0 is merged and tagged (PR #38) |
| **Version** | 0.9.0, bumped at CLOSE (D8 is off here). `__version__` is 0.8.0 until the release commit |
| **Tree** | `/Users/cdowin/workspace/agentic-sdlc`, the only checkout. Builders under the parallel mode get their own worktrees through `tools/dev/agent-worktree.sh`; the orchestrator never enters one |
| **Mode** | **PARALLEL, by contract** (SDLC.md §2). This milestone is the experiment: its own telemetry is meant to answer serial vs parallel |

## 2. Where to pick up

0.8.0 must ship first: see `ms-a-consumer-can-take-the-bump-handoff.md` §2 (merge #38, tag, prove).
Then:

```bash
git checkout main && git pull --ff-only && git checkout -b milestone/0.9.0-the-ledger-is-a-stamp
make pm ARGS='status ms-the-ledger-is-a-stamp'
make pm ARGS='milestone building ms-the-ledger-is-a-stamp'
```

Reading order, before anything else:

1. `SDLC.md` §2: the two modes, the one contract, the orchestrator's git rules.
2. This milestone's document and its five features. Its northstar is Chris's own sentence.
3. `docs/reviews/2026-09-11-ledger-telemetry-audit.md`, the evidence the ledger features came from
   (defects D-A and D-B, the gap table).
4. `ms-a-consumer-can-take-the-bump-handoff.md` §3, the traps 0.8.0 paid for.

**The first action is a spec scout, BEFORE any dispatch** (a `milestone-reviewer` over the milestone
and its features, against the code at that point). 0.8.0 ran its scout in parallel with the build,
and it cost a rework dispatch. Then decompose each feature into stories with `pm new story`.

**Build `ft-the-flow-is-boring-by-construction` FIRST.** It is the git allowlist guard, the leader
confinement and `dispatch` learning the mode, so the rest of 0.9.0 runs under its own guards.

**Every dispatch brief is `make sdlc ARGS='dispatch --grain <id> --role <role>'` output, verbatim**,
plus only what the grain file cannot know. The subagent type is the role brief. Do not hand-write
briefs.

The loop, as the next action every time: slice merged → `close story`; a feature's last story →
`pm feature reviewing` + its review; record lands → commit it; MAJOR+ landed, the rest dispositioned
→ `close feature` → close its GH issues (hash, not branch) → next feature.

Pool bugs worth binding when you decompose (not bound yet): `bg-a-pasted-fork-answer-records-nothing`
and `bg-install-skills-has-no-withdrawal-report`, both from 0.8.0's reviews.

## 3. Traps this milestone has already sprung

None yet: it has not started. The traps it inherits are 0.8.0's §3. The ones most likely to recur
here are the harness worktree option (it bases on `main`, so use `agent-worktree.sh`), a leader doing an agent's
debugging, and hand-written briefs.
