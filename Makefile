# agentic-sdlc — this package is its own first consumer.
#
# A consumer's Makefile is a pin and an include. This one is the include and
# the command the pin would resolve to: `uv run` installs THIS working tree on
# itself (editable, into .venv, re-synced on every run) and runs it, so the
# gates below always run the code in front of you and never a cached build.
# Everything else — `check`, `precommit`, `milestone`, `pm`, the one-verdict-
# line gate capture — is Makefile.devkit, byte-current with the installable
# `install-gates` writes, and the Python tiers this project adds are
# Makefile.tiers, hung off the same seam a language kit uses.
UV     ?= uv
DEVKIT := $(UV) run -q agentic-sdlc

# What a FAILING gate shows before its verdict, in the tools this repo runs:
# pytest's FAILED/ERROR lines and its `E   ` assertion lines, the matrix's, and
# ruff's concise `path:line:col: CODE` finding lines.
GDK_GATE_FAIL_RE := ^(FAILED|ERROR)|^E +|  DRIFT |\] FAIL|MATRIX FAIL|^  (MISS|FALSE POSITIVE)|:[0-9]+:[0-9]+: [A-Z]+[0-9]+

include Makefile.devkit

# `lint` is this repo's own gate, run by `make check` through `[gates] extra`
# in devkit.toml. ruff is a `dev` dependency pinned in pyproject.toml, never a
# runtime one (hard rule 1); its rule set is `[tool.ruff.lint]` there. The
# census is the files ruff walks, so a run that lints nothing says so.
RUFF       := $(UV) run -q ruff
LINT_PATHS := src tests tools
# ruff's own verdict line, never its trailing `--fix` hint.
SUM_RUFF   := grep -aoE '^(All checks passed!|Found [0-9]+ errors?)' "$$log" | tail -1

.PHONY: lint
lint: ## Lint gate: ruff over src tests tools, rules in pyproject.toml [tool.ruff.lint]
	$(call gdk_gate,lint,LINT,$(SUM_RUFF),$(RUFF) check --output-format concise $(LINT_PATHS),$(RUFF) check --show-files $(LINT_PATHS) | grep -c .)
