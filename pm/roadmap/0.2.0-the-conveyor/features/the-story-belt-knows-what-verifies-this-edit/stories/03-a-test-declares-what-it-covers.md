---
id: 0.2.0/the-story-belt-knows-what-verifies-this-edit/03-a-test-declares-what-it-covers
feature: 0.2.0/the-story-belt-knows-what-verifies-this-edit
milestone: "0.2.0"
name: A test that declares its coverage is selected by a changed path
status: building
owner:
depends_on: ["0.2.0/the-story-belt-knows-what-verifies-this-edit/01-the-verify-declaration-is-read-or-refused"]
---

# A test that declares its coverage is selected by a changed path

<!-- What is observable when this ships. A story is an observation, not a task. -->

The reverse direction. A rule declaring `declares = "## covers:"` and `scan =
"tests/integration/**"` reads that header out of each scanned file, and a changed path listed
under it selects that test's `run`. **A scan that finds no declaring file at all is a loud
zero-census, never an empty pass** — the feature's risk 3, and the same shape as a gate
scanning 0 files.

Both directions ship; neither is chosen over the other. Forward suits unit tests, where the
mapping is structural. Reverse suits integration, where only the test knows what it
exercises and no path rule could infer it.

## The header grammar, ruled here because the feature file does not

`declares` is a **literal line prefix**, not a regex (story 01 refuses metacharacters in it
and proves `.*` is literal). The block it opens is:

```
## covers: src/agentic_sdlc/repo/pm/ledger.py src/agentic_sdlc/repo/pm/report.py
```

- One line. Paths are whitespace-separated. A path is matched against changed paths as a
  **prefix on segment boundaries**, so a declared directory covers the files under it and
  `src/a` never covers `src/ab`.
- `<stem>` in `run` binds to the declaring FILE's stem — the only capture this direction has.
- A declaring file whose header lists nothing is a **finding**, not an empty coverage set: a
  test that declares it covers nothing has a header somebody meant to fill.

## Files this story may touch

- `src/agentic_sdlc/repo/verify/declares.py` — new.
- `tests/test_verify_declares.py` — new.
- `tests/fixtures/` — a vendored tree of declaring and non-declaring files. Rule 8: the
  corpus is committed here, never read from a tree outside this checkout, or the answer
  differs per machine.

## Files it must stay out of

`rules.py` and `core/config.py` (story 01), `select.py` (story 02), `main.py` and
`src/agentic_sdlc/cli.py` (story 04), `devkit.toml`, `pm/roadmap/`.

Consume the parsed reverse rules; do not re-read config, and do not call git.

## Acceptance criteria

1. A changed path listed in one fixture file's header selects that file's `run` with `<stem>`
   bound to the file's stem; a changed path listed in none selects nothing from this
   direction and is reported as unmatched so story 04's caller can fold it into `missed`.
   Proven by `tests/test_verify_declares.py`.
2. **The zero-census failure, and it is the reason this story exists.** A `scan` glob that
   matches files, none of which carry the `declares` prefix, returns a result the caller
   cannot mistake for "nothing to run": it carries `scanned = N, declaring = 0` and the
   caller is required to surface it. Proven by a fixture directory of files with no header,
   asserting both numbers and that the result is distinguishable from a scan that matched
   nothing.
3. **A `scan` glob matching ZERO files is a distinct, louder case** — `scanned = 0` — because
   a rule pointed at a directory that was renamed away rots into a rule that quietly matches
   nothing forever. Proven by a fixture with a glob over an absent directory. Story 04's
   `--check` is what turns this into a finding; this story makes it visible.
4. Prefix matching is segment-bounded: a header declaring `src/a` covers `src/a/b.py` and
   does **not** cover `src/ab.py`. Proven by a case with both files present — this is the
   off-by-one that silently over-selects.
5. A declaring file with an empty header list is reported as a finding with its path, not as
   a file covering nothing. Proven by a fixture case.
6. Reading is bounded: a scanned file is read once, the header is taken from the first
   matching line, and a file larger than a stated cap is reported rather than read whole.
   Stdlib only (hard rule 1), and no `subprocess` — the audit measured `pm-shape-scan`
   spending 34.8 s on four spawns per file across 683 markdown files, and that defect is the
   reason this feature exists at all. Proven by a case asserting no spawn.
7. Determinism and idempotence: same fixture, same result, twice, in the same order. Proven
   by a case.
8. Slice command for the loop: `python3 -m pytest tests/test_verify_declares.py -q`.

## Refusal matrix — the header is a payload parser (SDLC.md §5)

The header content is written by whoever wrote the test, so it is untrusted input to a value
that ends up in a command line. Each is a fixture case; each must refuse or contain, and none
may write anything:

| header content | expected |
|---|---|
| `## covers: ../../etc/passwd`, `## covers: /etc/passwd` | refused, naming the declaring file — hard rule 8 |
| `## covers: ~/x`, `## covers: file:///x` | refused |
| `## covers: .`, `## covers: ..`, `## covers: a//b` | refused |
| `## covers: $(id)`, ``## covers: `id` ``, `## covers: a;b`, `` `## covers: a\|b` `` | refused: these reach `run` through nothing today, but a covered path that is a shell fragment is one refactor away from being interpolated |
| a header line 100 KB long | bounded and refused, not read into memory whole |
| a header repeated twice in one file | refused, naming both line numbers — which one wins is not a thing this parser may pick |
| a header inside a fenced code block | **must not** be read as a declaration; a documentation example of the syntax is not a declaration. This is the `verdict.py` near-miss problem already solved once in this package — read how it does it |
| a declaring file that is a symlink out of the checkout | not followed |
| a file that is not UTF-8 decodable | reported by path, never crashing the scan and never silently skipped |
| `## covers:` with a capture placeholder `<name>` in it | refused; captures are declared in config, not in the tree |

**Adversarial cases against the docstring.** The module will claim the prefix is literal, that
matching is segment-bounded, that a fenced example is never a declaration, and that it never
spawns a process. Generate against each — especially a `declares` value chosen to look like a
regex (`## covers.*:`) against a file containing `## coversXYZ:`, which must NOT match.

## Out of scope

- The forward direction — story 02.
- The verb, its exit codes, the fallback to wide, the ratio — story 04.
- Turning a stale rule into a gate finding — that is `verify --check`, story 04. This story
  ships the numbers that make it possible.
- Any change to how `pm-shape-scan` or any existing gate reads files.

## Close

done: 6e9388d — the reverse direction: a test declaring its own coverage is selected by a
changed path. Segment-bounded, because an unbounded prefix is the off-by-one that silently
over-selects.
