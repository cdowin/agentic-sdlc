# tools/

Each file here is one of two kinds. An installer writes a SHIPPED file from its source under
`src/agentic_sdlc/repo/installables/`: edit the source, then run the installer with `--force`.
A `dev-only` file serves this repo only, and no installer writes it.

| file | writer | source |
|---|---|---|
| `tools/dev/agent-worktree.sh` | `install-hooks` | `src/agentic_sdlc/repo/installables/agent-worktree.sh` |
| `tools/dev/gdk_gate.sh` | `install-gates` | `src/agentic_sdlc/repo/installables/gdk_gate.sh` |
| `tools/dev/pm_migrate.py` | dev-only | a one-time PM tree migration |
| `tools/hooks/cc-git-denylist.sh` | `install-hooks` | `src/agentic_sdlc/repo/installables/cc-git-denylist.sh` |
| `tools/hooks/cc-ledger-session.sh` | `install-hooks` | `src/agentic_sdlc/repo/installables/cc-ledger-session.sh` |
| `tools/hooks/cc-ledger-subagent.sh` | `install-hooks` | `src/agentic_sdlc/repo/installables/cc-ledger-subagent.sh` |
| `tools/hooks/cc-write-confine.sh` | `install-hooks` | `src/agentic_sdlc/repo/installables/cc-write-confine.sh` |
| `tools/hooks/pre-push` | `install-hooks` | `src/agentic_sdlc/repo/installables/pre-push` |
| `tools/hooks/prepare-commit-msg` | `install-hooks` | `src/agentic_sdlc/repo/installables/prepare-commit-msg` |
| `tools/publish_index.py` | dev-only | the release workflow's package index step |
| `tools/setup-hooks.sh` | `install-hooks` | `src/agentic_sdlc/repo/installables/setup-hooks.sh` |

`tests/test_install.py` fails when a file under `tools/` has no row here.
