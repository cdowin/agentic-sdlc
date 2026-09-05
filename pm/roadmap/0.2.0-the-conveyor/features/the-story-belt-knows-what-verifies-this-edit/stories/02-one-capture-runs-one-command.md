---
id: 0.2.0/the-story-belt-knows-what-verifies-this-edit/02-one-capture-runs-one-command
feature: 0.2.0/the-story-belt-knows-what-verifies-this-edit
milestone: "0.2.0"
name: Five files under one capture select one command, and a miss is named
status: reviewing
owner:
depends_on: ["0.2.0/the-story-belt-knows-what-verifies-this-edit/01-the-verify-declaration-is-read-or-refused"]
---

# Five files under one capture select one command, and a miss is named

<!-- What is observable when this ships. A story is an observation, not a task. -->

Given a set of changed paths and a parsed rule set, the selector answers with an ordered,
deduplicated list of commands — and with the list of paths that matched no rule at all.

**The miss list is the story.** The feature file names it rule 4's read-side cardinal sin
wearing a new hat: *"a narrow verifier that matches nothing and exits 0 is worse than no
verifier — it reports success for work it never checked. This is the single most dangerous
failure in the design."* The audit repeats it as a known constraint. So the selector's
return value carries the misses as a first-class value that the caller **cannot** ignore,
not as a log line it may forget to print.

## The contract this story owns

`select(rules, changed_paths) -> Selection`, where `Selection` carries:

- `commands` — ordered, deduplicated after capture substitution;
- `matched` — which path(s) produced each command, so story 04 can print them;
- `missed` — every changed path that matched no rule, in input order.

**`missed` being non-empty is not an error here** — it is a fact the caller acts on (story 04
falls back to wide and names them). But a `Selection` that is empty on BOTH counts, from a
non-empty `changed_paths`, is impossible by construction: every path lands in exactly one of
`matched` or `missed`, and that invariant is the loud-failure test below.

## Dedupe, which is what "narrow" actually means

Five files under `systems/combat/` bind `sys=combat` five times and produce ONE
`make unit SYS=combat`. Dedupe happens **after** substitution and **preserves first-match
order**, so a rule set's declaration order is the run order and two runs of the same input
give byte-identical output. Without this the narrow path re-runs the same slice per file and
stops being narrow — which is the entire 170x.

Order of rules: **first matching rule wins, per path.** A path is not fanned out across every
rule that could claim it; that would make adding a rule silently multiply the work. State it
in the docstring, and generate against it.

## Files this story may touch

- `src/agentic_sdlc/repo/verify/select.py` — new.
- `tests/test_verify_select.py` — new.

## Files it must stay out of

`src/agentic_sdlc/repo/verify/rules.py` and `src/agentic_sdlc/core/config.py` (story 01 —
consume the parsed rules, do not re-read config), `declares.py` (story 03), `main.py` and
`src/agentic_sdlc/cli.py` (story 04), `devkit.toml`, `pm/roadmap/`.

This module takes paths as an argument. **It does not call git** — story 04 owns that,
because a selector that reads the working tree cannot be tested against a fixed input.

## Acceptance criteria

1. Five changed files under one captured directory produce exactly one command. Proven by
   `tests/test_verify_select.py`, asserting `len(commands) == 1` **and** that all five paths
   appear in `matched` — a dedupe that also loses the attribution is a dedupe that cannot
   explain itself.
2. **The invariant, asserted directly:** for any rule set and any non-empty path list,
   `len(matched paths) + len(missed) == len(changed_paths)` and the two sets are disjoint.
   Proven as a property over a generated corpus of path lists, in the same file. This is the
   test that makes a silent zero-command pass unreachable rather than merely unlikely.
3. A path matching no rule appears in `missed`, verbatim, in input order, and produces no
   command. Proven by a case whose rule set deliberately misses.
4. First matching rule wins: with two rules that both match one path, the command comes from
   the earlier rule and appears once. Proven by a case.
5. Captures substitute into `run` positionally and literally — a capture bound to a value
   containing a space, a quote, a `$`, or a `;` **is refused at selection time**, naming the
   path and the rule index, rather than being interpolated into a command line. Story 01
   refuses hostile config; this refuses hostile *tree contents*, which config validation
   cannot see. Proven by a case per character class against a fixture tree carrying files
   with those names.
6. An empty `changed_paths` returns an empty `Selection` with empty `missed`, and the
   docstring says what that means (nothing changed, so nothing narrow is selected — the
   caller's business, not a pass). Proven by a case, because "it passed and I do not know
   why" is the shape of a false PASS.
7. Determinism: the same inputs produce the identical `Selection` twice, including order.
   Proven by a case.
8. Slice command for the loop: `python3 -m pytest tests/test_verify_select.py -q`.

## Refusal matrix — the changed-path list is an input surface

`changed_paths` arrives from git in story 04 and from a caller here, so the hostile inputs
are tree-shaped rather than config-shaped. Each is a case:

| input | expected |
|---|---|
| `../outside/x.py`, `/etc/passwd` | refused, naming the path — hard rule 8: nothing outside the checkout, and a `..` that MATCHED would run a command about a file this repo does not own |
| `''`, `'.'`, `'..'` | refused |
| a path containing `\n` | refused — a rename with an embedded newline is what `git diff -z` exists for, and a selector that splits on newlines would see two paths |
| `a//b`, `a/./b` | normalised or refused, never matched by accident twice |
| a path 4096+ characters long | refused |
| a path with a backslash separator | not treated as a directory separator |
| a path that is a symlink pointing outside the checkout | matched as a PATH only; nothing here follows or reads it |
| 10,000 changed paths against 50 rules | completes without quadratic blowup, and dedupe still yields the small command set |

**Adversarial cases against the docstring.** The module will claim "first matching rule wins",
"captures never span `/`", "the same command is never emitted twice", and "this module never
spawns a process". Generate against each: two rules whose globs overlap, a path whose
directory names contain the capture's own delimiter characters, a rule set where two
different rules substitute to the identical command string (must dedupe across rules, not
only within one), and a `run` containing something that would be a command if anything here
executed it (assert nothing is spawned — patch the spawn surface and assert zero calls).

## Out of scope

- The reverse (`declares`) direction — story 03. This module handles `paths`/`run` rules and
  passes reverse rules through untouched.
- Running any command, reading git, printing anything, or exit codes — story 04.
- The ratio.

## Close

done: 6e9388d — five files under one capture select one command, proven end-to-end through
the verb and not only in the selector. A path matching no rule is NAMED and the widest rung
runs: a narrow verifier that matches nothing and exits 0 is the most dangerous failure here.
