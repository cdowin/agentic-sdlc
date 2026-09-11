---
id: st-every-verb-answers-its-own-help
kind: story
feature: ft-the-pm-surface-has-no-dead-ends
milestone: "ms-a-consumer-can-take-the-bump"
name: every verb answers its own --help, and adopt's describes the belt that ships
status: planning
owner:
depends_on: []
changelog:
---

# every verb answers its own --help, and adopt's describes the belt that ships

Issue: #25.

**`pm <verb> --help` is a usage error.** Measured at v0.7.0: `pm set --help`, `pm new --help` and
`pm get --help` exit 2 with `[pm] ERROR — usage:` and the whole ~480-line roster. `pm add --help`
answers `unknown flag '--help'`. The router (`pm/cli.py:3174`) only treats help as `argv[0]`.
`agentic-sdlc --help`, `adopt --help` and `dispatch --help` all answer at exit 0.

**`adopt --help` documents a write the belt never makes.** `conveyor/driver.py:400-423` renders the
generic belt help for every belt: `<version>` is "a grain id", the verdicts are `ok — <grain> →
<state>` and `forced — …`, and "after a write, `next:` lines". The same help says adopt writes nothing
and refuses `--force`. `_writes()` (`:463`) is the only part that knows this. The run line, *"nothing
recorded … there is no milestone 'v0.7.0' in pm/roadmap/ to land one in"*, reads as though it would
write if one existed.

## Acceptance criteria

1. `pm <verb> --help` (and `-h`), anywhere in argv, prints that verb's own block from the router table
   and exits 0. Parametrised over every verb in the table, so a new verb is covered by default.
2. `adopt --help` describes a version argument, a checks-only belt, and the verdict line(s) it can
   actually print, with no grain id, no `forced` and no `next:`-after-write.
3. `adopt`'s run line does not suggest a write is possible.
4. The belt help renderer asks `_writes()` (or its equivalent), so the next checks-only belt is
   described correctly without a special case.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1 | unit | one parametrised case over the router table | search the pm CLI tests; amend if a help case exists |
| 2, 4 | unit | a render of the adopt belt help | amend the driver help case |

## Semver

`--help` exiting 0 instead of 2 changes an exit code (rule 6), though no consumer can depend on
`--help` failing. Call it minor, to be safe.

## Out of scope

`bg-the-gate-help-names-one-of-its-four-rule-families`, the same shape on `check pm`. It is bound to
this milestone as its own bug and ordered right after this feature.
