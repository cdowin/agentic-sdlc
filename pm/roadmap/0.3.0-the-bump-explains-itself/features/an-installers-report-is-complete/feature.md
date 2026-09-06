---
id: 0.3.0/an-installers-report-is-complete
milestone: "0.3.0"
name: An installer reports every file it touched and every target it removed
status: done
reviewed: docs/reviews/0.3.0-an-installers-report-is-complete.md
phase:
depends_on: []
consumed_by: []
---


# An installer reports every file it touched and every target it removed

**Three findings from two adoptions, all about silence.**

**1. `--diff` prints no header for a MODIFIED file.** `install-gates --diff` emits
`[install] <path> does not exist — the whole file is an addition` for a new file, then a bare
unified diff for a changed one. Summarising a 1,211-line diff with `grep '^\[install\]'` — the
obvious move, and the one the agent made — reported exactly one file and silently omitted
`Makefile.devkit`, the most consequential file in the whole split. The agent only found it by
counting lines and looking for `+++` markers.

**2. The split dropped seven targets in silence.** `autoloads`, `doctor`, `orphans`, `refs`,
`scene`, `scene-diff` and `pm-scan` existed in the v0.24.0 include and exist in neither half now.
`pm-scan` is named in that consumer's `[gates] extra`, so `make check` simply broke with
`No rule to make target 'pm-scan'`. The other six were cited by name across ten agent briefs and
surfaced only because that repo runs a `check doc` that validates make targets — a gate in the
CONSUMER, doing the installer's job.

**3. A removed FLAG has no equivalent, and no gate can find one.** `pm feature done --cascade`
existed at v0.24.0 and does not now; the flag is simply not in the parser. NullBound's
`.claude/rules/execution.md` documented it as *the* way stories close ("flips every `reviewing`
story under the feature + the feature itself to `done` together"), and that sentence survived the
bump intact and green. `check doc` validates make targets, file paths and links — it cannot read a
sentence about a flag. Same class as finding 2, one level down: the package knows what it removed
and does not say, and here the consumer has no gate that could compensate.

## Ship criterion

Every file an installer owns gets one header line in `--diff` and in a real run, whatever its
disposition — added, modified, already current. And an installer knows which targets it used to
ship: a run reports `no longer shipped: <targets>` for the versions between the installed stamp
and this one, so a consumer learns it from the tool rather than from a broken build. The same
report names RETIRED VERB FLAGS over that span — a flag lives only in prose on the consumer side,
so the tool saying it is the only way anyone finds out.

## Proof budget

  cases: 4-5
  tier: pyunit for the header shape; one shell case for the removed-target report
  lands in: `tests/test_installers.py`
  what already covers this: the installers have refusal and idempotence cases, but every one
    asserts on the FILES written, never on the report's completeness. A diff that omits a file
    passes today.
