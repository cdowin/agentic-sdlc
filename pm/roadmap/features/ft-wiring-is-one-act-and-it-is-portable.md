---
id: ft-wiring-is-one-act-and-it-is-portable
kind: feature
milestone: "ms-a-move-is-an-event"
name: wiring is one act, and it is portable
status: done
reviewed: docs/reviews/2026-09-07-0.5.0-wiring-is-one-act-and-it-is-portable.md
depends_on: []
consumed_by: []
---

# wiring is one act, and it is portable

GitHub issue #13. **Asked to make telemetry paramount, this milestone's own build recorded nothing —
because wiring the couriers is a hand-paste with three unchecked assumptions.**

`ft-telemetry-proves-the-path-not-the-config` (#11) makes that silence LOUD. It does not make the
recording happen. This is the other half, and without it the first half only tells you sooner that
you are stuck.

## The three coupled assumptions

    1  install-hooks PRINTS settings entries and will not write them, and they
       carry RELATIVE paths: `bash tools/hooks/cc-ledger-subagent.sh`. Those
       resolve only when the harness cwd IS the repo root.

    2  the courier derives the tree from the harness's session cwd:
         REPO_ROOT="$(git -C "$SESSION_CWD" rev-parse --show-toplevel …)"
       no GDK_LEDGER_ROOT, no config key. A session rooted at a parent that is
       not itself a git repo gets no row — correctly, by the courier's own
       contract, and unfixably from outside it.

    3  telemetry-live verifies the FILE it told you to write, not the path.

Fixing (1) alone does not work: an absolute script path still leaves `SESSION_CWD` outside a repo
and the courier still exits without a row. **Both must move, which is why this is one feature.**

## The inconsistency that is the tell

`install-ci` writes `.github/workflows/` — a harness's config file — without hesitation.
`install-hooks` refuses to write `.claude/settings.json` and prints a fragment for a human to paste.
Both are harness config. **The one the package declines to write is the one that silently does
nothing when pasted wrong**, and the paste is the step no gate observes.

Rule 11's own test: *could someone hand-roll a thing this package already does, and would anything
have stopped them?* The operator hand-pastes the wiring, gets it wrong invisibly, and every surface
reports success.

## Ship criterion

`install-hooks` emits ABSOLUTE script paths and NAMES the settings file the wiring belongs in —
never a fragment with no destination. Writing that file is OFFERED, the way `--force` is offered
elsewhere; refusing to write it by default stays, because a package that silently edits a harness
config is worse than one that does not (rule 3).

The courier accepts an explicit tree root — `GDK_LEDGER_ROOT` in the environment or a config key —
and falls back to session cwd. **A courier wired from any scope files its row.** That is what "wire
it once at the beginning" requires and what today's design forbids.

`pm ledger record --grain` accepts `--tokens-total`, explicitly not a split, because hand-recording
is the fallback whenever the hook path is unavailable, and today that fallback can only be lossy or
false.

## Proof budget

  cases: 4
  tier: pyunit + shell
  lands in: `tests/test_install.py` for the emitted wiring, and the courier's own `--self-test`
    corpus for the root override — that corpus is what `check hooks` replays, so a fix with no
    corpus row is untested by the thing that exists to test it.
  what already covers this: the hook corpus harness gained a row pattern this milestone
    (`bg-the-commit-hook-dedupes-on-an-exact-string`); this is another row on it.

## Out of scope

Choosing the consumer's session root. Rule 8 — this package knows nothing about its consumers. This
makes the wiring work from wherever they stand; where they stand is theirs.

`pm ledger record --grain --tokens-total`, named in the criterion above and duplicated verbatim
in the sibling feature, so neither declared an owner and it shipped under neither. It lives in
`pm/ledger.py` + `pm/cli.py`, which is neither feature's surface — deferred by name to
`bg-a-hand-recorded-dispatch-cannot-carry-a-total`.
