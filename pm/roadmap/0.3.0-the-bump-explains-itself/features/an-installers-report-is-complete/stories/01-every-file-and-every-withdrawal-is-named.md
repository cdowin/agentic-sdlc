---
id: 0.3.0/an-installers-report-is-complete/01-every-file-and-every-withdrawal-is-named
feature: 0.3.0/an-installers-report-is-complete
milestone: "0.3.0"
name: every file gets a header and every withdrawal is named
status: done
owner:
depends_on: []
---

# every file gets a header and every withdrawal is named

Three findings, all about silence: a `--diff` that headers a NEW file and not a
MODIFIED one, so the obvious `grep '^\[install\]'` reported one file and omitted
the most consequential; seven make targets dropped between two pins with nothing
said; and a removed verb FLAG that no gate anywhere could find.

## Acceptance criteria

1. Every file an installer owns gets one header line in `--diff` and in a real
   run, whatever its disposition — added, modified, already current.
2. An installer reports `no longer shipped` for the targets it used to ship over
   the span between the installed stamp and this version.
3. The same report names retired verb FLAGS over that span — a flag lives only
   in prose on the consumer side, so the tool saying it is the only way anyone
   finds out.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | the header-shape cases in `tests/test_install.py` | the installers had refusal and idempotence cases; every one asserted on FILES WRITTEN, never on the report's completeness — a diff that omitted a file passed |
| 2, 3 | unit | the withdrawal-record cases | new; the registry is data-shaped, seeded honestly with the real 0.2.0 span (which withdrew nothing) rather than an invented removal |

Verified end-to-end by the orchestrator, since the builder was stopped before
reporting: `install-gates --diff` headers both owned files (`already current`),
and with one file edited it prints `Makefile.devkit exists and differs from what
this would write` — the exact silence that hid it. 73 unit cases green.

## Out of scope

Back-filling a withdrawal record for versions before 0.2.0. The mechanism ships;
inventing history it did not observe would be the lie rule 4 forbids.

## Close

done: 1285784 — every disposition gets a header line, and an installer says what
it withdrew. Built by a dispatched builder; verified against the tree, not its
narration, because the builder was stopped for running wide gates before it
reported.
