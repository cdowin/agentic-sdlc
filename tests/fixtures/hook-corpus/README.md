# hook-corpus

A stand-in `tools/hooks/` for `tests/test_check_hooks.py`. Each file is a few
lines with one shape `check hooks` judges. None of them is a shipped hook: the
names are the shipped names so that the settings block `install-hooks` writes
registers them, and the bodies are fixtures.

| file | shape |
|---|---|
| `cc-commit-pathspec.sh` | a `cc-*` hook that allows everything and carries no corpus |
| `cc-git-allowlist.sh` | a `cc-*` hook that can block (`exit 2`) and replays its own corpus |
| `cc-ledger-session.sh` | a `cc-*` hook that replays a corpus, never blocks, and names `exit 2` in prose only |
| `pre-push` | a git hook, which the gate asks only to parse |

The shipped corpus is replayed ONCE, by
`test_the_shipped_corpus_armed_and_registered_passes_every_question_the_gate_asks`.
