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
# pytest's FAILED/ERROR lines and its `E   ` assertion lines, and the matrix's.
GDK_GATE_FAIL_RE := ^(FAILED|ERROR)|^E +|  DRIFT |\] FAIL|MATRIX FAIL|^  (MISS|FALSE POSITIVE)

include Makefile.devkit
