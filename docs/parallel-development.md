# Parallel development with bounded close cost

Status: release implementation, 2026-09-30. The acceptance matrix below distinguishes shipped mechanisms from work in progress.

## Incident report

A recent engine project exposes five repeatable cost sources:

| Cost source | Evidence | Consequence |
|---|---|---|
| Import copies enumerate tooling and nested checkouts | 43,733 copied paths; the editor import itself takes 24 seconds | More lanes enlarge preparation cost before useful work starts |
| Cold boots dominate integration | 56 boots consume 881.2 seconds of CPU, averaging 15.73 seconds per boot | Repeated sweeps buy startup repeatedly |
| Independent gates compete for one machine | Five affected scenarios need runner retries while other engine suites run | Load looks like regressions and creates diagnostic work |
| Resource integration happens late | Four references resolve to a script UID; 33 scenarios fail at one startup boundary | One wiring defect produces dozens of failed reports |
| Close discovers paperwork defects | A no-findings review omits its required table header | The close refuses after the expensive verification already passes |

CPU seconds are not elapsed seconds. These measurements do not establish a universal 50 percent close ratio.
The current ledger mixes different scopes and censuses. Report comparable batches and phase times before judging trends.

## Operating model

Coding, static inspection, and independent review remain parallel. Expensive runtime verification has one owner per host.
A lane owns disjoint files and a declared interface. The lead owns shared contracts and integration.
The close reads completed evidence; it does not discover the implementation, produce its first capture, or start another audit.

### 1. Dispatch an executable contract

Every brief names the grain, exact base commit, writable paths, shared interface, acceptance criteria,
scoped verification command, proof budget, merge owner, and final-gate owner.
A dependency graph determines which lanes start together. A lane that changes another lane's interface
lands the contract first, or both lanes receive the same decided contract before dispatch.
Do not parallelize two writers of one file. Bound active builders by independent ownership, not the number of available agents.

### 2. Give each lane one external worktree

Use Git worktrees sharing the object database. Resolve their parent from Git’s registered primary checkout,
so calling from any linked checkout gives the same canonical workspace identity.
Place them outside the game project. Record the exact base, branch, root, and scope marker.
Reject a conflicting existing directory or branch. Never silently reset or reuse someone else's dirty checkout.
Keep legacy checkouts discoverable until their work lands. Cleanup refuses uncommitted work and preserves unmerged branches.

Warm each lane with its own cloned cache. APFS or reflink copies may share storage until a write,
but each checkout owns the cache directory. Never symlink mutable import caches across lanes.
Track authored UIDs and import sidecars. Install locked dependencies through their existing package cache.
A fresh clone is useful for a cold-checkout test; it is not the parallel-development primitive.

### 3. Bound the import input set

The import copy includes actual project inputs, including ignored installed addons and generated runtime files.
It prunes registered linked worktrees and explicit Godot-ignored directories before descending into them.
Git-cloned runtime addons remain inputs; their Git metadata is excluded.
Its census and copy time remain visible. Adding ten unrelated worktrees must leave the input census unchanged.
The copy retains interruption, atomic cache swap, sidecar preservation, and resource-churn protections.
A changed manifest requires refresh. A worktree count alone never requires refresh.

Resource references derive identity from the target resource header, never an inner script or texture UID.
An unknown authoritative identity remains unresolved and the caller reports it. An engine import does not repair that authoring defect.

### 4. Admit one expensive gate batch per host

An OS-owned lease admits one independent engine gate. A busy caller fails promptly with the owner and gate name.
It does not wait silently or start competing engines. Child workers of the admitted integration batch inherit its lease.
The existing bounded worker pool supplies parallelism inside that batch. The OS releases the lease when its last holder exits; a surviving engine retains it until it exits.
Read-only commands, static checks, and coding continue while it runs. User-controlled editors remain untouched.
This is admission control, not a background scheduler or a larger timeout.

### 5. Integrate while lanes still build

Prove one thin runtime slice early. For visual features, inspect density, contrast, viewport size, and motion
before multiplying assets. Use the declared capture budget.

A builder hands off a frozen commit, exact changed paths, scoped gate results, review-ready artifacts,
and unresolved decisions. It stops editing that commit while the lead verifies it.
Validate each ready merge batch in a dedicated checkout frozen at its recorded commit.
Other lanes may keep building and queuing merges elsewhere. A live checkout changing during verification cannot supply final evidence.
Merge ready lanes in bounded batches. Refresh imports once after scripts or assets change.
Run one startup smoke before affected scenarios. A shared startup failure gets one diagnosis before any batch repeat.
Mutating tests own private resources. Run the combined owning-system slice before handoff when shared fixtures can interact.

### 6. Reuse evidence without weakening it

Use existing verification input declarations and printed cache reuse. Preserve tool, command, configuration,
fixture, and declared environment inputs that affect the verdict. Gates depending on Git history retain that history
in their key. A rung may opt out of HEAD only through `[verify.history_independent]`; all declared inputs, the
installed tool version, command, lockfile, project config and Python runtime remain keyed. Never equate the same
branch name with the same tested state. A fresh checkout also needs import readiness. Keep passing evidence for
unaffected inputs. Rerun only after a relevant change or an explained environment repair. Separate authoring defects,
behavioral failures, and load-related retries in the report.

The current scoped rung key also includes HEAD. A paperwork-only commit can therefore invalidate a computational rung.
The new policy requires an explicit history-independent declaration and adversarial invalidation probes;
removing HEAD globally would create false reuse for gates that read Git history.

### 7. Make close a small transaction

Validate review-record grammar and the project’s slot headers before committing the record.
A new verb, field, ledger kind, or context must update its canonical rosters, rename semantics,
help probes, and fixture builders. Run the cheap contract/unit tier before the final review freeze.
Keep the changelog, evidence, and specifications current as code lands.
Run the declared scoped proof under its named owner. Close ready stories, then close each completed
feature immediately from its recorded review. Mark DONE and move on; never accumulate finished features for a final audit. Belts reuse unchanged verification and write statuses.
PM-only transitions never justify another engine sweep. One full integration pass belongs at milestone close, before milestone DONE. Fix its failures in place; do not repeat it without a relevant repair.
If the user owns merge or final precommit, deliver the frozen lane and evidence; do not duplicate that act.

## Implementation and acceptance

| Owner | Change | Acceptance | Current state |
|---|---|---|---|
| SDLC worktree installer | External canonical roots and isolated cache warming | Primary and lane calls resolve one identity; dirty and unmerged work survives | Implemented; 15 focused integration cases pass; helper installed in the affected project |
| Engine toolkit import wrapper | Prune unrelated trees before traversal | Nested checkout growth leaves census constant; ignored runtime addon remains present | Implemented and installed; 20 self-tests pass; input census falls 82 percent |
| Engine toolkit runners | Host lease with descendant fanout | Independent competitor refuses; child proceeds; crash releases; read-only command proceeds | Implemented and installed; 4 focused runner tests pass, plus all 20 import interruption/copy regressions |
| Engine toolkit UID index | Target-header identity only | Headerless target with inner script UID refuses; real header resolves deterministically | Implemented; focused regression passes |
| SDLC workflow and shipped guidance | Ownership, frozen handoff, early proof, one final batch | Dispatch/close surfaces name these rules and tests preserve their wording | Implemented in shipped guidance; package adoption follows publication |
| Existing verification cache | History-independent scoped evidence where declared | Paperwork changes reuse; consumed code/tool/config changes invalidate | Implemented with opt-in `history_independent`, default HEAD retention, and tool/config/environment key inputs |
| Consumer adoption | Install released or immutable pinned toolkit changes | Installer diff clean; real import census falls; cold and warm startup pass | Validated helper and import patches installed from source; released package pins still pending |

## Measurement and stop criteria

For each comparable batch record: build elapsed time, handoff-to-close elapsed time, checkout creation time,
import enumeration/copy/import time, copied paths, admitted gate time, boot count, retries, and reused verdicts.
Use the existing ledger for values it already records. Add missing phase timing at the owning script, not a second reporting system.
Keep CPU time and elapsed time separate. Compare the same input census and host admission policy.

Initial regression target: adding unrelated nested checkouts changes copied runtime paths by zero.
Initial scheduling target: no independent engine boot overlaps an admitted integration batch. Integration owns its whole batch; standalone runners acquire admission per boot.
Initial close target: no runtime rerun caused solely by status writes; no duplicate final gate under two owners.
The lead reports the feature DONE when its assigned gates pass. The project declares who merges and releases it.

Measured copy results on the same 7,721-entry manifest: enumeration 0.718 seconds; clone-aware batched copy 17.844 seconds; single-process rsync 14.133 seconds. The old census was 43,451 entries, including 34,749 under an explicitly ignored agent directory. The new census excludes all registered nested worktree paths. These are copy-phase measurements, not total import timings; the five-second copy target remains unmet.

## Mechanical close enforcement (issues 111 and 112)

[Issue 112](https://github.com/cdowin/agentic-sdlc/issues/112) records merge-to-close drift: a false belt check has no mandatory next action, and separate merge, cleanup, and close verbs allow deferred closes. [Issue 111](https://github.com/cdowin/agentic-sdlc/issues/111) records wall-clock budget failures under the same parallel load the workflow recommends. The ownership prose above cannot prevent these by itself.

Enforcement implemented in the SDLC toolkit:

1. Record a failed close belt as structured `belt.blocked` evidence, with grain and failed checks; a pass or explicit recorded deviation clears it.
2. Refuse additional dispatch when a close-ready grain or unresolved blocked belt needs attention. Name the corrective command. This must be enforced in the dispatch verb as well as optional client hooks.
3. Provide a coordinated land operation with resumable phases and preserved work on failure. Do not hide a destructive cleanup behind a failed merge or gate. Existing frozen-commit evidence and the declared final-gate owner must remain authoritative.
4. Separate load-sensitive performance grading from functional push and close gates. Record comparable CPU and elapsed measurements; grade declared quiet-machine performance at the release boundary. Never convert a behavioral test failure into a load exemption.
5. Enforce feature ownership during dispatch, while allowing explicitly declared independent lanes under one feature owner. A blanket one-story-per-feature restriction would unnecessarily serialize disjoint work.

Acceptance must prove refusal before dispatch side effects, recorded failed-check recovery, resumable land after a gate failure, and successful functional checks under simulated host load. These are separate from checkout and import patches. Publication requires their focused regressions and independent review to pass.

Implementation ownership after source inspection:

| Mechanism | Owning source | Focused regression |
|---|---|---|
| Blocked-close lifecycle | `src/agentic_sdlc/repo/conveyor/driver.py`, `src/agentic_sdlc/repo/pm/ledger.py` | `test_conveyor_close.py`, `test_pm_gate.py`, ledger contracts |
| Dispatch guard using shared readiness | `src/agentic_sdlc/repo/dispatch.py`, `src/agentic_sdlc/repo/pm/ready_for.py`, client isolation hook | `test_dispatch.py`, hook payload corpus, installer sync |
| Resumable land transaction | CLI route plus `src/agentic_sdlc/repo/land.py`; existing worktree helper for cleanup last | New land fixture tests: failure at each phase, resume, dirty work preserved |
| Performance grading context | `src/agentic_sdlc/repo/checks/budget.py`, conveyor steps/driver and gate composition | `test_check_budget.py`, verify/close composition tests |

Paths above are under `src/agentic_sdlc/` and tests under `tests/`. Existing `check.verdict` records and missing `rung.leave` already describe refused belts; reuse those contracts when adding an explicit blocked lifecycle. Do not build a second readiness parser in a hook. Current gate rows record elapsed duration, not CPU time; CPU-based grading needs measurement support first.
