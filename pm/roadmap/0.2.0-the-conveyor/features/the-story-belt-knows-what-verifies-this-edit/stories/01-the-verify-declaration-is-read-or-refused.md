---
id: 0.2.0/the-story-belt-knows-what-verifies-this-edit/01-the-verify-declaration-is-read-or-refused
feature: 0.2.0/the-story-belt-knows-what-verifies-this-edit
milestone: "0.2.0"
name: A verify rule set is read once, and an unusable one exits 2
status: building
owner:
depends_on: []
---

# A verify rule set is read once, and an unusable one exits 2

<!-- What is observable when this ships. A story is an observation, not a task. -->

`[verify]` in `devkit.toml` becomes a typed, validated rule set with exactly one reader.
Every hostile spelling of `wide`, `paths`, `run`, `declares` and `scan` is refused with exit
2 and a message naming the rule's own index — never a rule quietly dropped from the list.

**This story is the foundation the other three build on.** `run` is a shell command read
from config and later executed (the feature's risk 1), and this package has already shipped a
false PASS from a config value read carelessly — `tuple(cfg.get(...))`, seven gates, v0.9.0
(risk 2, CLAUDE.md § *Where things live*). The parser is the feature.

## The shape being parsed

```toml
[verify]
wide = "make check test"           # required. One command. The close.

[[verify.narrow]]                  # FORWARD: a glob with a named capture
paths = "src/agentic_sdlc/repo/pm/**"
run   = "python3 -m pytest tests/test_pm_*.py"

[[verify.narrow]]
paths = "tests/test_<name>.py"
run   = "python3 -m pytest tests/test_<name>.py"

[[verify.narrow]]                  # REVERSE: the test declares its own coverage
declares = "## covers:"
scan     = "tests/integration/**"
run      = "make scenario NAME=<stem>"
```

## Three grammar questions the feature file leaves open. Rule them here, in the docstring

1. **`<name>` never spans a path separator.** A capture matches one segment's worth of
   characters and stops at `/`, the way a shell glob's `*` does. Otherwise
   `tests/test_<name>.py` matching `tests/a/b/test_c.py` binds `name` to `a/b/test_c`, and
   that value is then interpolated into a command line.
2. **A rule is FORWARD or REVERSE, never both and never neither.** `paths`+`run` is forward;
   `declares`+`scan`+`run` is reverse. Any other combination of keys is refused, naming the
   index. A rule carrying `paths` AND `declares` has two meanings and the reader must not
   pick one.
3. **`<stem>` is the reverse direction's only capture**, and it is derived (the matched
   file's stem), not declared. A `<stem>` in a forward rule's `run` is refused.

## Files this story may touch

- `src/agentic_sdlc/core/config.py` — the coercion for an array-of-tables
  (`[[verify.narrow]]`). CLAUDE.md: *"Every config value goes through
  `core/config.py`."* **No other story in this feature may edit this file.**
- `src/agentic_sdlc/repo/verify/__init__.py` — new package (it lives under `repo/` because it
  reads git, config and paths and knows nothing about a `.tscn`; nothing in it may import
  `godot/` — `tests/test_boundaries.py` is the gate).
- `src/agentic_sdlc/repo/verify/rules.py` — new: the reader, the grammar, the refusals.
- `tests/test_verify_rules.py` — new.

## Files it must stay out of

`src/agentic_sdlc/repo/verify/select.py` (story 02), `declares.py` (story 03), `main.py` and
`src/agentic_sdlc/cli.py` (story 04), `devkit.toml` (story 04 self-hosts the section),
README / CHANGELOG (orchestrator applies proposed wording), `pm/roadmap/`.

## Acceptance criteria

1. A valid mixed rule set parses into an ordered tuple of typed rules whose captures are
   already extracted, with `wide` beside it. Proven by `tests/test_verify_rules.py`.
2. **The bare-string trap.** `narrow = "paths = x"` (a string where a table array belongs),
   and a `paths` value given as a list, each raise `ConfigError` and exit 2 — never iterate a
   string into characters. Proven by two cases naming v0.9.0's defect shape explicitly.
3. **An empty rule list is refused**, not treated as "nothing to do", following
   `config.str_tuple`'s existing rule that an empty list usually means the opposite of
   nothing. Message tells the author to remove the section. Proven by a case.
4. Every refusal names **the rule's own index** (`[verify.narrow] #2: …`). Proven by
   asserting the index appears in the message for a rule-set whose second and fourth rules
   are both bad — with only the first index named, an author fixes one and re-runs blind.
5. **Exit 2, never 1.** A `[verify]` mistake is a config error and CI must never read it as
   drift found. Proven by a case per class asserting the code.
6. Slice command for the loop: `python3 -m pytest tests/test_verify_rules.py -q`.

## Refusal matrix — `[verify]` is a new input surface (SDLC.md §5)

Each row is one test case, and each asserts the reader refuses **without executing anything**
— nothing in this module ever spawns a process, and that is a claim its docstring will make,
so it gets hostile input generated against it.

`run` — executed later, so the narrowest grammar of the three:

| input | why |
|---|---|
| `run = ""` | a rule that verifies nothing |
| `run = "make x; rm -rf /"`, `` run = "make `id`" ``, `run = "make $(id)"`, `run = "a \| b"`, `run = "a && b"`, `run = "a > f"` | command chaining and substitution: a rule set is a tracked file, but a rule that CHAINS is a rule whose second half nobody reviewed |
| `run = "make x <undeclared>"` | a capture in `run` that no `paths` in the same rule declares — the single most dangerous typo here, because the placeholder would otherwise be passed through to a shell literally |
| `run = "<stem> foo"` in a FORWARD rule | `<stem>` is the reverse direction's capture |
| `run` longer than 512 characters | a pasted paragraph in a command slot |
| `run = $'make x\nmake y'` | an embedded newline is two commands |
| `run` absent | every rule must say what it runs |

`paths` / `scan` — globs matched against tracked files:

| input | why |
|---|---|
| `paths = "../../etc/**"`, `paths = "/etc/**"` | traversal and absolute path — hard rule 8: nothing reads outside the checkout |
| `paths = "~/x"`, `paths = "file:///x"`, `paths = "https://x"` | home expansion and schemes |
| `paths = ""`, `paths = "."`, `paths = ".."`, `paths = "a//b"`, `paths = "a/./b"` | empty and dot segments |
| `paths = "src\\pm\\**"` | backslash separators |
| `paths = "<a><b>"`, `paths = "<>"`, `paths = "<a"` | malformed or adjacent captures — an unterminated `<` must refuse, not match literally |
| `paths = "**"` alone | matches the entire tree, which makes "narrow" a synonym for "wide" and hides the fact |
| duplicate capture name in one `paths` | which binding wins is not a thing this reader may pick |
| `paths` longer than 256 characters | |

`wide`: absent (refused — the feature file says *"Always defined"*), empty, a list, a
non-string, and the same chaining/newline cases as `run`. **`wide` absent is exit 2, and
story 04 proves that reaches the verb** — a repo with no wide command has no close, and
falling back to "run nothing" would be the silent zero-command pass criterion 4 of the
feature forbids.

`declares` / `scan`: `declares` without `scan`, `scan` without `declares`, `declares = ""`,
`declares` containing a regex metacharacter (it is a literal line prefix, not a pattern —
say so in the docstring and prove `.*` is treated literally), `declares` longer than 64
characters.

Structural: an unknown key inside a rule (refused, naming it — a typo'd `path` for `paths`
would otherwise make the rule match nothing forever), a rule that is not a table, `[verify]`
present but not a table.

## Out of scope

- Matching anything. Story 02 owns the forward matcher, story 03 the reverse scan.
- Reading git, or knowing what changed.
- The verb, its flags, its exit codes, or the ratio — story 04.
- Validating that a `run` names a target that EXISTS. That is `verify --check`, story 04:
  it needs the make/target world, and this module deliberately never spawns.

## Close

done: 6afa35d — [verify] read through one coercion in core/config.py; 112 hostile inputs;
every malformed rule reported at once naming its own index, because a rule dropped in silence
is a caller verifying less than it thinks. Seven mutations run to prove the matrix bites; the
first probe did not, and was rewritten until it did.
