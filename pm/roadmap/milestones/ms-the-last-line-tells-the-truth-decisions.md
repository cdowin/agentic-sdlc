Append with `make pm ARGS='decide <grain-id>'` — never by hand; the command stamps the date and the next ordinal.

# ms-the-last-line-tells-the-truth the last line tells the truth — decisions

Durable. This log outlives the grain: it is where a choice and its rejected
alternative are recorded, and it survives close.

> Never write what is derivable. `pm status` gives tallies, `git log` gives
> history. This file holds the WHY that neither of them records.

## D1 — 2026-09-21 — an arrival gate warns and never refuses (#69)

Chris, 2026-09-21: warn. `pm story building` writes the status, runs each target in
`[pm] arrival_gates` once per call, and prints each failure as a `WARN` line. Exit stays 0.
Rejected: refuse at exit 1 with `--force`. That turns a move into a belt, and rule 9 keeps
`pm` as the verb that moves and reports.

## D2 — 2026-09-21 — no belt commits and no verb stamps a version file (#72, #68)

Chris, 2026-09-21: agreed. A belt writes one status or refuses; a git commit is neither
(rules 3, 9). `repo-hygiene` reports dirt under `[pm] root` as one WARN line with the commit
to run, the same exclusion the belts' `tree-clean` already uses. The milestone arrival prints
the version edit as a `next:` line and does not write the version file.
Rejected: the belt commits roadmap-only dirt (#72); the arrival stamps `[pm] version_file` (#68).

## D3 — 2026-09-21 — suites derived from changed files are the consumer's (#73)

Chris, 2026-09-21: agreed; #73 closed as not planned. Mapping a changed file to the suites
that read it is inference (rule 9), and the index that answers it is the consumer's (rule 8).
`verify --story` runs the declared `[verify] story` target, and that target can derive its
own suite set. Rejected: a changed-files-to-suites engine in `verify`; the old
`[[verify.narrow]]` diff engine was retired for the same reason.

## D4 — 2026-09-27 — an extra-sections key, not a template fork (#78)

Chris, 2026-09-27: `[pm.templates.<kind>] extra_sections = [...]`. `templates.load` appends one
`## <name>` heading per entry to whichever template it read, and skips a name the template
already has. Stock empty, seeded commented. Rejected: an `append` file path per kind. It carries
body text too, but it is one more file to keep in step, and the ask was headings.

## D5 — 2026-09-27 — the commit guard reads the tree the command commits in (#77)

Chris, 2026-09-27: fix the hook. `cc-commit-pathspec.sh` resolves MERGE_HEAD from the command's
own `-C <dir>` or leading `cd <dir>`, then the session cwd. The dispatch contract names the
merge finish. Rejected: document `GIT_EDITOR=true git merge --continue` only. The guard would
still misread the tree, and the next operation in progress (a cherry-pick, a rebase) would hit
the same trap.

## D6 — 2026-09-27 — a verdict block names the feature it grades (#79)

Chris, 2026-09-27: key the blocks. A verdict block may carry `feature: <id>`. When any block in
a record names a feature, a close reads only its own blocks; a block keyed to an id that does
not point `reviewed:` at the record, or a mix of keyed and unkeyed blocks, is a plain false.
A record with no keys reads as today. Rejected: one file per feature, by brief only. No code
change, but the trap stays for anyone who shares a file, and #66 now tells them to.

## D7 — 2026-09-27 — a loc hook is the consumer's (#75)

Chris, 2026-09-27: transfer to cdowin/godot-devkit. No file in this package has a `loc` hook
or a `make loc` target; the `tr(` scanner is a Godot consumer's (rule 8). Rejected: take it
here. Rejected: close as not planned, because the defect is real and has an owner.
