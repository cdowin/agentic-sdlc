# agentic-sdlc — the scripted path.
#
# This file exists because its absence was measurable. With no scripted entry
# point, every agent working on this package invented its own pytest incantation
# and then hand-rolled censuses, replays and fuzzers around it — apparatus that
# ran once inside one agent's context and was thrown away. A target is the
# cheapest possible fix: the work is written down, it is rerunnable, and nobody
# has to be told the command.
#
# EVERY GATE PRINTS ONE LINE. The default output of a target here is its
# verdict, naming the full transcript on disk; `VERBOSE=1` streams the whole
# thing. That is not a local convention — it is `gdk_gate_capture` /
# `gdk_gate_verdict` out of installables/gdk_gate.sh, the library this
# package ships to its consumers, sourced straight from the source tree. The
# devkit is its own first consumer: an agent running `make milestone` here used
# to pipe it through a hand-invented five-shape grep to find the verdicts, and
# a toolkit whose own targets need that has not proven the thing it sells.
#
# GNU make 3.81 (what macOS ships) is the floor. Nothing here needs more.

.DEFAULT_GOAL := help

# The library is bash: arrays, PIPESTATUS, `local`. macOS bash 3.2 is the floor
# and the library holds that line.
SHELL := /bin/bash

# The package is stdlib-only. The TEST run needs one thing it does not ship:
# pytest. 3.11 is the declared floor and where the fast loop runs; the matrix
# is every interpreter the package claims.
PY_FLOOR  ?= 3.11
PY_MATRIX ?= 3.11 3.12 3.13 3.14
UV        ?= uv
# xdist is a TEST-time dependency, exactly like pytest. Hard rule 1 governs the
# RUNTIME — a consumer's pre-push hook resolves neither. The suite is
# spawn-bound rather than compute-bound (measured: 150 s of CPU in 240 s of
# wall), so parallelism is the difference between a gate you run and a gate you
# work around.
TEST_DEPS ?= --with pytest --with pytest-xdist
# `auto` is the machine's core count. Overridable, because a shared CI runner
# and a laptop are not the same machine.
# `loadgroup`, not the default `load`: tests carrying an `xdist_group` mark are
# dispatched to the same worker, which is how the handful that spawn `make`
# against THIS repo serialise against each other without serialising the suite.
PYTEST_N  ?= -n auto --dist loadgroup
PYTEST    ?= $(UV) run --python $(PY_FLOOR) $(TEST_DEPS) python -m pytest
PYTEST_Q  ?= -q

# The GATES run the WORKING TREE, never an installed build: a gate that checks
# the last release tells you nothing about the change in front of you. For the
# gates alone: no wheel build, no venv, no network — the package imports from
# src/ with the stdlib. (The test targets above DO use uv, for pytest.)
# `env` is load-bearing: the gate helper runs an ARGV, not a shell line, so a
# leading VAR=value assignment needs a command to carry it.
PY        ?= python3
DEVKIT    ?= env PYTHONPATH=$(CURDIR)/src $(PY) -m agentic_sdlc.cli

# The shipped library, sourced from source. Self-hosting, the same way
# .github/workflows/verify.yml is installed rather than hand-written: if the
# gate helpers regress, this repo's own targets are the first thing to notice.
GATE_LIB := src/agentic_sdlc/repo/installables/gdk_gate.sh

# VERBOSE reaches the capture helper as an ENVIRONMENT variable, so exporting
# it here is what makes `make gates VERBOSE=1` work as well as `VERBOSE=1 make
# gates`. Both spellings get typed; neither should silently do nothing.
VERBOSE ?= 0
export VERBOSE

# How the gate library reaches the ledger. `gdk_gate.sh` is SOURCED, so it
# cannot see a make variable at all — this one line is the whole bridge, and
# every gate's cost row rides over it. The same line Makefile.devkit gives a
# consumer; self-hosting means it is spelled here too. Empty it
# (`make gates GDK_LEDGER_CMD=`) and nothing is recorded and nothing is spawned
# — which is what the suite does, so a test run never writes to the real tree.
export GDK_LEDGER_CMD ?= $(DEVKIT)

# What a FAILING run shows on the console before its verdict: the lines that
# say what broke, in the tools this repo runs. Everything else stays in the log.
GATE_FAIL_RE   := ^(FAILED|ERROR)|^E +|  DRIFT |\] FAIL|MATRIX FAIL|^  (MISS|FALSE POSITIVE)
GATE_FAIL_LINES := 20

# Each target's one-line summary, read back out of its own transcript. The
# leading `[tag]` a tool prints is stripped: the verdict line supplies the tag.
SUM_PYTEST := grep -aoE '[0-9]+ (passed|failed)[^|]*' "$$log" | tail -1
# HOW MANY CASES RAN, for the `gate` row's census. Read off the same summary
# line the verdict is, so the number in the row and the number a human sees
# cannot disagree. A run with failures is already a FAIL, so `passed` alone is
# the count of what actually ran to completion.
CENSUS_PYTEST := grep -aoE '[0-9]+ passed' "$$log" | tail -1 | grep -oE '[0-9]+'
# `[a-z-]`, not `[a-z]`: a HYPHENATED gate name is a real gate name — `check
# grain-shape` (0.2.0) and `check repo-hygiene` both have one — and the old
# class matched neither, so the verdict counted 4 of 5 PASS lines and reported
# a green run as one gate smaller than it was. The shipped Makefile.devkit
# already spelled it correctly; this copy had drifted, which is what a second
# spelling of one fact does.
SUM_GATES  := printf '%s check(s) PASS' "$$(grep -acE '^\[check:[a-z-]+\] PASS' "$$log")"
SUM_HOOKS  := printf '%s hook(s) SELF-TEST OK' "$$(grep -ac 'SELF-TEST OK' "$$log")"

# $(call gate,<log slot>,<TAG>,<summary command>,<argv...>)
# Run a command through the shipped capture helper: quiet by default, the full
# transcript on disk, one verdict line naming it, and the command's own exit
# code preserved (the helper reads PIPESTATUS, so `$$?` would be the cap's).
# `$(5)`, when a target passes one, is the CENSUS: a command that prints how
# many things this run walked. `gdk_gate_verdict` files it on the `gate` row,
# and `check budget` compares it to `[tests] cases`.
#
# It closes L3 of the 0.2.0 release review — "nothing sets GDK_GATE_CENSUS" —
# and it exists because a duration cannot see the growth that matters: a tier
# holds its wall clock while doubling in size, because parallelism and a faster
# machine both absorb it, and the number that then goes wrong is the reader's.
define gate
@set -o pipefail; . $(GATE_LIB); \
log="$$(gdk_gate_log $(1))"; \
gdk_gate_capture "$$log" -- $(4); \
status="$$GDK_GATE_EXIT"; \
summary="$$($(3))"; \
$(if $(5),GDK_GATE_CENSUS="$$($(5))"; export GDK_GATE_CENSUS;) \
if [ "$$status" -ne 0 ]; then \
	grep -aE '$(GATE_FAIL_RE)' "$$log" | head -$(GATE_FAIL_LINES) \
		|| tail -$(GATE_FAIL_LINES) "$$log"; \
	summary="FAIL (exit $$status) — $$summary"; \
fi; \
gdk_gate_verdict $(2) "$$summary" "$$log"; \
exit "$$status"
endef

.PHONY: help unit integration test matrix fuzz budget gates hooks hooks-self-test precommit milestone pm

help:
	@echo 'agentic-sdlc — make targets'
	@echo
	@echo '  make unit        the inner loop: no subprocess, one process, seconds'
	@echo '  make integration everything that spawns — a real repo, make, a hook corpus'
	@echo '  make test        both tiers on the $(PY_FLOOR) floor'
	@echo '  make matrix      every claimed interpreter ($(PY_MATRIX)): $(PY_FLOOR) runs the whole suite, the rest -m "not shell" (a spawn is not interpreter-sensitive)'
	@echo '  make fuzz        the committed seeded harnesses (differential + replay)'
	@echo '  make gates       agentic-sdlc check all, on this repo'
	@echo '  make hooks       ARM this checkout: point git at tools/hooks/ and restore the exec bits'
	@echo '  make hooks-self-test  the installed hooks that ship a corpus, replayed (the two ledger couriers)'
	@echo
	@echo '  make pm ARGS="…"  the pm tracker from SOURCE, never a cached wheel (the ledger couriers call this)'
	@echo
	@echo '  make precommit   gates + hooks-self-test + test           the per-change gate'
	@echo '  make milestone   gates + hooks-self-test + matrix        the full gate, and what CI runs'
	@echo
	@echo 'Every gate prints ONE verdict line naming its full log under'
	@echo '.gate-reports/. VERBOSE=1 streams the transcript as well.'

# The pm tracker over THIS repo's tree, from source (CLAUDE.md: never verify
# through a cached wheel). .PHONY matters: a pm/ directory at the root would
# otherwise satisfy the target silently and the ledger couriers would record
# nothing (0.23.0/usage-capture, reviewer U1).
pm:
	PYTHONPATH=src python3 -m agentic_sdlc.cli pm $(ARGS)

# THE LADDER, and it is the whole of decision D10.
#
# `unit` is the inner loop: no subprocess, no git, no make, ~7 s in one
# process. `integration` is everything that spawns — a real repo, a real
# `make`, an installed hook corpus — and it is minutes-adjacent, so it is not
# something an edit should pay for. `test` is both, and it is what a close
# runs.
#
# The tier is the `shell` mark, DERIVED by tests/conftest.py from what the
# source reaches. It already existed to let the matrix skip spawning modules on
# three of four interpreters; what it never had was a target, so the fast half
# was unreachable from the command line and `precommit` ran everything.
unit: export GDK_TEST_TIER = unit
unit:
	$(call gate,unit,UNIT,$(SUM_PYTEST),$(PYTEST) $(PYTEST_Q) -m "not shell",$(CENSUS_PYTEST))

integration: export GDK_TEST_TIER = integration
integration:
	$(call gate,integration,INTEGRATION,$(SUM_PYTEST),$(PYTEST) $(PYTEST_Q) $(PYTEST_N) -m shell,$(CENSUS_PYTEST))

test: export GDK_TEST_TIER = test
test:
	$(call gate,test,TEST,$(SUM_PYTEST),$(PYTEST) $(PYTEST_Q) $(PYTEST_N),$(CENSUS_PYTEST))

# The seeded harnesses on their own, for when one of them is what you changed.
# `make test` runs them too — they are tests, not a side quest, and a fuzz that
# only runs when somebody remembers it is a fuzz that does not run.
fuzz:
	$(call gate,fuzz,FUZZ,$(SUM_PYTEST),$(PYTEST) $(PYTEST_Q) -m fuzz)

gates:
	$(call gate,gates,GATES,$(SUM_GATES),$(DEVKIT) check all)

# ARM this checkout. `install-hooks` writes the corpus; writing it is not arming
# it, and git runs nothing under tools/hooks/ until core.hooksPath points there.
# This repo told its consumers the corpus was self-hosted here while that config
# was unset in every checkout of it, for two releases, because there was no
# target to run and none that looked
# (0.24.0/bugs/self-hosting-has-no-arm-or-verify-target).
#
# This is the one command that FIXES an unarmed tree; `check hooks` — inside
# `make gates`, and so inside `precommit` and `milestone` — is what reports one.
# Not a gate, so it prints what the script prints: it is asked for a repair and
# the two lines are the repair.
hooks:
	@bash tools/setup-hooks.sh

# The hooks this repo self-hosts that ship their own block/allow corpus: the
# two ledger couriers. Replayed here so an edit to a courier cannot quietly
# change a verdict — the same wiring the README asks of a consumer: a
# `hooks-self-test`-shaped target inside its own static gate.
#
# The list SHRANK in 0.2.0 (the engine-boot guard left with the language kit
# it guards — decisions D2), and a shrinking census is exactly the shape rule 4
# is about: the old recipe's `for h in <nothing>` ran zero corpora, exited 0,
# and $(SUM_HOOKS) reported `0 hook(s) SELF-TEST OK` as a PASS. So the census
# is counted BEFORE the loop and an empty one is a usage error (exit 2), not a
# quiet green. Proven by `make hooks-self-test HOOKS_WITH_CORPUS=`.
# SECOND SCOREBOARD, KNOWN AND PENDING (0.2.0, story 02): `check hooks` now
# replays this same corpus, DERIVED from which hooks declare `--self-test`
# rather than named here, and `check hooks` is in this repo's `[checks] all` —
# so `make gates` already covers everything this target does. This target
# cannot be deleted from the same change that made it redundant: `precommit`
# and `milestone` name it, `tests/test_consumer_independence.py` asserts
# `milestone`'s member list verbatim, and `tools/hooks/cc-stop-gate.sh` runs it
# as its GATE_UNIT. Until those three move together, the list below is held
# equal to the gate's derived set by
# `tests/test_check_hooks.py::test_this_repos_makefile_names_the_same_corpus…`,
# because a hand roster beside a derived one that nothing compares is how this
# list emptied out and kept passing in the first place.
HOOKS_WITH_CORPUS := tools/hooks/cc-ledger-subagent.sh tools/hooks/cc-ledger-session.sh
hooks-self-test:
	$(call gate,hooks-self-test,HOOKS,$(SUM_HOOKS),sh -c 'set -- $(HOOKS_WITH_CORPUS); if [ "$$#" -eq 0 ]; then echo "HOOKS_WITH_CORPUS names 0 hook(s) — a corpus that empties out must not pass"; exit 2; fi; for h in "$$@"; do bash "$$h" --self-test || exit 1; done')

# Every interpreter in one target, and it reports which one failed. A matrix
# that stops at the first failure hides the difference between "3.14 only" and
# "everywhere", which is the whole question a matrix is asked. It writes its own
# loop rather than $(call gate,...) because it captures N runs into ONE
# transcript — but it ends the same way, with one verdict line naming that log.
#
# The FLOOR runs the whole suite; every other interpreter runs `-m "not shell"`.
# ~85% of this suite's wall clock is `subprocess` — bash, make, git, the
# installed hook corpora — and a spawn is not something a Python version
# changes, so four interpreters replaying it bought minutes and no information.
# The `shell` mark is DERIVED per module in tests/conftest.py from what the
# source does, never a list here: a roster in this file is a roster that goes
# stale, and a module that quietly leaves it stops running on three
# interpreters with nothing going red.
#
# A PY_FLOOR that is not in PY_MATRIX is refused BEFORE the first interpreter —
# the slice would then be run by nobody and the matrix would print PASS over a
# suite that never ran, which is worse than the sixteen minutes this saves.
# Membership is decided by the same word splitting the loop uses, so the guard
# and the run cannot disagree; a `case` pattern would call a 3.1 floor a member
# of a 3.11 matrix. (PY_FLOOR/PY_MATRIX are operator configuration: the guard
# is against bumping one and not the other, not against shell injection
# through a make variable.)
matrix:
	@set -o pipefail; . $(GATE_LIB); \
	log="$$(gdk_gate_log matrix)"; fail=''; floor=''; full=''; \
	for v in $(PY_MATRIX); do [ "$$v" = "$(PY_FLOOR)" ] && floor="$$v"; done; \
	if [ -z "$$floor" ]; then \
		echo 'PY_FLOOR "$(PY_FLOOR)" is not in PY_MATRIX "$(PY_MATRIX)"' >> "$$log"; \
		gdk_gate_verdict MATRIX 'REFUSED: PY_FLOOR "$(PY_FLOOR)" is not in PY_MATRIX "$(PY_MATRIX)", so no interpreter would run the whole suite' "$$log"; \
		exit 2; \
	fi; \
	for v in $(PY_MATRIX); do \
		if [ -z "$$full" ] && [ "$$v" = "$(PY_FLOOR)" ]; then \
			full="$$v"; slice=(); ran='the whole suite'; \
		else \
			slice=(-m 'not shell'); ran='-m "not shell"'; \
		fi; \
		echo "=== python $$v ($$ran) ===" >> "$$log"; \
		[ "$$VERBOSE" = "0" ] || echo "=== python $$v ($$ran) ==="; \
		gdk_gate_capture "$$log" -- \
			$(UV) run --python $$v $(TEST_DEPS) python -m pytest $(PYTEST_Q) "$${slice[@]}" || true; \
		[ "$$GDK_GATE_EXIT" -eq 0 ] || fail="$$fail $$v"; \
	done; \
	if [ -n "$$fail" ]; then \
		grep -aE '$(GATE_FAIL_RE)' "$$log" | head -$(GATE_FAIL_LINES) || true; \
		gdk_gate_verdict MATRIX "FAIL on$$fail" "$$log"; \
		exit 1; \
	fi; \
	gdk_gate_verdict MATRIX "PASS on $(PY_MATRIX)" "$$log"

# The per-change gate, and it is the NARROW rung. Gates first: they take under
# a second and they are what catches a doc or a PM-tree edit the suite has no
# opinion about. A composition prints its members' verdicts — one line each,
# nothing of its own.
#
# It used to run `test` — the whole suite, 240 s at the time — after every
# edit, which is the same 170x this milestone exists to end, one layer down and
# in the file that names it. The integration tier runs at the CLOSE, through
# `verify --feature`, and everything runs at `milestone`.
precommit: gates hooks-self-test unit

# The full gate, and what CI runs. The matrix subsumes `test`, so it is not
# listed twice.
# The budget is asked ONCE, here, and never in the per-change gate: it grades
# the LAST recorded run of each tier, so putting it in `check all` would let a
# slow afternoon redden the next person's edit over a number they cannot act
# on. It is also inherently one run behind — the row it reads is written by the
# run before this one — which is why it catches a DOUBLING rather than a wobble.
budget:
	$(call gate,budget,BUDGET,$(SUM_GATES),$(DEVKIT) check budget)

milestone: gates hooks-self-test matrix budget
