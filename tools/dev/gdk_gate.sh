#!/usr/bin/env bash
# gdk_gate.sh — the shared gate-framework library every gate in this repo runs
# through. Wire it as the thing your `tools/dev/*.sh` wrappers and your
# `Makefile` recipes source.
#
# SOURCE this (do not execute it), except for `--self-test` / `--help`:
#
#   source "$(dirname "${BASH_SOURCE[0]}")/gdk_gate.sh"
#   log="$(gdk_gate_log parse)"            # this gate's transcript slot
#   gdk_gate_capture "$log" -- make thing  # run it, quiet unless VERBOSE=1
#   gdk_gate_verdict PARSE "PASS (12 files)" "$log"
#
# It exists because two consumer repos grew the same shell twice and then
# drifted: quiet gate capture with a one-line verdict naming a full log, and a
# bounded-run contract that can tell a hang from a failure. One definition
# each, here, so a fix reaches both.
#
# It is LANGUAGE-NEUTRAL by contract. Everything here reads a command's exit
# code, its output stream and the clock — nothing about what the command IS.
# A language kit's own runners (the toolchain it drives, the artifacts it acts
# on, the sandbox those artifacts need) ship in that kit and source this file;
# a helper that names a toolchain does not belong in it.
#
# EVERY public function is prefixed `gdk_`; every private one `_gdk_`. A
# consumer that renames them is forking the library and stranding the next fix.
#
# --- project config (yours to edit after install — the file is your repo's) --
# Each of these is an override-able default: set it in the environment, or edit
# it here.
#
#   GDK_GATE_REPORT_DIR       where a gate's full transcript lands. Gitignore
#                             it. Bounded by construction: the slot is named by
#                             GATE and each run clears its own.
#   GDK_LOG_CAP_BYTES         hard cap on a captured stream, so a runaway
#                             command spewing to stdout cannot fill the disk.
#                             50 MB is ~1000x a normal transcript.
#   GDK_TIMEOUT_KILL_AFTER    grace period between the SIGTERM a bound fires
#                             and the SIGKILL that guarantees no orphaned
#                             child process survives.
#   VERBOSE=1                 stream every captured gate to the console too.
#
#   GDK_LEDGER_CMD            the command this library files a gate's COST row
#                             through, as a command STRING (`pm ledger record
#                             …` is appended to it). EMPTY BY DEFAULT, and an
#                             empty value spawns nothing at all — a consumer
#                             with no PM tree pays zero. A sourced library
#                             cannot see a make variable, so the Makefile that
#                             owns the pin exports it:
#                             `export GDK_LEDGER_CMD ?= $(DEVKIT)`.
#   GDK_LEDGER_TIMEOUT        seconds the recorder is allowed. A recorder that
#                             hangs must not hang every gate in a pre-push
#                             hook, so the call is bounded like any other.
#   GDK_GATE_CENSUS           how many things THIS run walked, set by the gate
#                             before its verdict. Unset is an ABSENT column,
#                             never a `0` — a `0` is a measurement, and a run
#                             over 683 files filing `census: 0` is hard rule
#                             4's cardinal sin with a number on it. The census
#                             is NEVER parsed out of the verdict's prose.
#   GDK_GATE_VERDICT          the run's outcome in the ledger's closed
#                             vocabulary (PASS|FAIL|HANG|SKIP), for a runner
#                             that publishes its own result and never went
#                             through gdk_gate_capture. Unset, it is DERIVED
#                             from what the captures against this run's LOG
#                             SLOT reported — the first failing one, or the
#                             last GDK_GATE_EXIT when none failed.
# -----------------------------------------------------------------------------

# Guard against double-sourcing: a wrapper may source us once, and some chains
# source transitively. `return` works when sourced; the `exit` is the executed
# path, which only `--self-test` / `--help` ever take.
if [ -n "${_GDK_GATE_SOURCED:-}" ]; then
	# shellcheck disable=SC2317  # the `exit` is the EXECUTED path (--self-test)
	return 0 2>/dev/null || exit 0
fi
_GDK_GATE_SOURCED=1

GDK_GATE_REPORT_DIR="${GDK_GATE_REPORT_DIR:-.gate-reports}"
GDK_LOG_CAP_BYTES="${GDK_LOG_CAP_BYTES:-52428800}"
GDK_TIMEOUT_KILL_AFTER="${GDK_TIMEOUT_KILL_AFTER:-5s}"
GDK_LEDGER_CMD="${GDK_LEDGER_CMD:-}"
GDK_LEDGER_TIMEOUT="${GDK_LEDGER_TIMEOUT:-30}"
GDK_GATE_CENSUS="${GDK_GATE_CENSUS:-}"
GDK_GATE_VERDICT="${GDK_GATE_VERDICT:-}"

# The tag every line this library prints on its OWN behalf carries, so a
# consumer can tell the library's voice from its gate's.
GDK_LIB_TAG="gdk-gate"

# --- exit-hook dispatcher ----------------------------------------------------
# Bash has ONE `trap … EXIT` slot per shell: a wrapper's own `trap cleanup EXIT`
# silently CLOBBERS anything a library installed (and vice versa, depending on
# source order). So there is exactly one EXIT trap in a wrapper — this
# dispatcher — and everything else registers a hook.
#
#   RULE: inside a wrapper that sources this library, never write a bare
#   `trap … EXIT`. Use `gdk_on_exit '<command>'`.
#
# Hooks run in registration order; a failing hook never masks the script's own
# exit status.
_GDK_EXIT_HOOKS=()

# shellcheck disable=SC2329  # invoked indirectly via `trap … EXIT`
_gdk_run_exit_hooks() {
	local status=$?
	local hook
	for hook in ${_GDK_EXIT_HOOKS[@]+"${_GDK_EXIT_HOOKS[@]}"}; do
		eval "$hook" || true
	done
	return "$status"
}

# gdk_on_exit <command> — run <command> when this shell exits.
gdk_on_exit() {
	_GDK_EXIT_HOOKS+=("${1:?usage: gdk_on_exit <command>}")
	trap _gdk_run_exit_hooks EXIT   # idempotent re-arm
}

# --- bounded-run / hang-detection contract ----------------------------------
# timeout(1) exits 124 when its own SIGTERM deadline fires and 137 (128+SIGKILL)
# when --kill-after escalates. Either means the run hung.
GDK_EXIT_SIGTERM_TIMEOUT=124
GDK_EXIT_SIGKILL_TIMEOUT=137

# timeout binary: GNU coreutils ships `timeout`; on a stock macOS with Homebrew
# coreutils it is `gtimeout`. Resolve once so every wrapper agrees. Empty if
# neither is present — callers that require it check and fail loud.
if command -v timeout >/dev/null 2>&1; then
	GDK_TIMEOUT="timeout"
elif command -v gtimeout >/dev/null 2>&1; then
	GDK_TIMEOUT="gtimeout"
else
	GDK_TIMEOUT=""
fi

# gdk_timeout_is_hang <exit_code> — true if the code is a timeout kill. A
# piped capture reads PIPESTATUS itself and cannot use gdk_run_bounded;
# this is how it tells a HANG from a failing gate without respelling the codes.
gdk_timeout_is_hang() {
	local code="${1:?usage: gdk_timeout_is_hang <exit_code>}"
	[ "$code" -eq "$GDK_EXIT_SIGTERM_TIMEOUT" ] || [ "$code" -eq "$GDK_EXIT_SIGKILL_TIMEOUT" ]
}

# gdk_run_bounded <seconds> -- <cmd...>
# Run a NON-piped command under the shared timeout contract; returns its exit
# code (124/137 on hang, 2 when no timeout binary exists). A piped capture
# keeps its own PIPESTATUS idiom and references "$GDK_TIMEOUT" directly.
gdk_run_bounded() {
	local secs="${1:?usage: gdk_run_bounded <seconds> -- <cmd...>}"; shift
	[ "${1:-}" = "--" ] && shift
	if [ -z "$GDK_TIMEOUT" ]; then
		echo "$GDK_LIB_TAG: no timeout/gtimeout on PATH — install coreutils" >&2
		return 2
	fi
	"$GDK_TIMEOUT" --kill-after="$GDK_TIMEOUT_KILL_AFTER" "${secs}s" "$@"
}

# --- gate output: a summary on the console, the full transcript on disk ------
# A gate used to STREAM its whole run to the console: `make parse` printed 273
# lines of which two mattered (the verdict, and any error line); `make
# warnings` printed 1,581. Every agent pays that on every run, so the default
# is the summary and the stream goes to a file.
#
# The report dir cannot rot the way a per-job one does: the slot is named by
# GATE, each run clears the slot it is about to write, and there is a handful
# of gate names — so the directory is bounded BY CONSTRUCTION and there is no
# reaper anyone can forget to call.

# --- the cost row: what a gate run cost, filed once, failing OPEN ------------
# A gate that nobody times is a gate that can double in cost unnoticed. So the
# funnel that already owns the transcript also owns the clock.
#
# THE FUNNEL IS THE PAIR, KEYED ON THE LOG SLOT. Not `gdk_gate_capture` (a
# publish-only runner never calls it, and a two-stage gate calls it twice) and
# not `gdk_gate_verdict` alone (a runner with five alternative exits calls that
# up to six times per run, which would file six rows for one gate). It is
# `gdk_gate_log` → the FIRST `gdk_gate_verdict` naming the same slot: the log
# is minted exactly once per run by every path that reports at all.
#
# The start time lives in a SIDECAR FILE beside the log, not in a variable,
# because the caller spelling is `log="$(gdk_gate_log parse)"` — a command
# substitution, whose shell dies with the assignment. A variable set there
# would be gone by the time the verdict reads it, on every real caller.
# The sidecar is the marker too: the first verdict consumes it, so every later
# verdict for that run finds nothing and files nothing. It is bounded the same
# way the log is — one per gate name, cleared by the next run of that gate.
#
# FAIL OPEN, OUT LOUD. Every path out of this block returns 0. A ledger that
# cannot be written is a gap in the measurement and NEVER a gate failure: this
# code is on the path of every gate in every consumer, and a bug here would red
# all of them. That is the rule `cc-ledger-session.sh` already makes for
# itself, for the same reason and in the same words. What it never does is fail
# SILENTLY — each refusal says one line on stderr, because a ledger quietly
# missing rows is hard rule 4's read-side sin with a library around it.

# _gdk_ledger_note <what> — one line, on stderr, never on the verdict's stream.
_gdk_ledger_note() {
	printf '%s: %s — no cost row for this gate\n' "$GDK_LIB_TAG" "$1" >&2
}

# _gdk_ledger_sidecar <logfile> — where THIS slot's start time is parked.
# Derived from the log path with parameter expansion rather than
# `dirname`/`basename`: two spawns per gate to compute a name is a cost the
# quiet path must not pay.
_gdk_ledger_sidecar() {
	case "$1" in
		*/*) printf '%s/.%s.gdkms' "${1%/*}" "${1##*/}" ;;
		*)   printf '.%s.gdkms' "$1" ;;
	esac
}

# The clock, resolved once. `date +%s%N` is GNU; BSD date hands back a literal
# `N` and every duration computed from it would be garbage, so the result is
# CHECKED rather than assumed. python3 is the fallback, and when neither
# answers there is no millisecond clock and no row — a second-resolution
# duration is not a cheaper answer to this question, it is a wrong one:
# fourteen of the twenty gates this feature was planned from are under a
# second, and each would file `0`.
_GDK_CLOCK=''

_gdk_now_ms() {
	local probe
	if [ -z "$_GDK_CLOCK" ]; then
		probe="$(date +%s%N 2>/dev/null)" || probe=''
		case "$probe" in
			''|*[!0-9]*) probe='' ;;
		esac
		if [ -n "$probe" ] && [ "${#probe}" -ge 16 ]; then
			_GDK_CLOCK='date'
		elif command -v python3 >/dev/null 2>&1; then
			_GDK_CLOCK='python3'
		else
			_GDK_CLOCK='none'
		fi
	fi
	case "$_GDK_CLOCK" in
		date)    echo $(( $(date +%s%N) / 1000000 )) ;;
		python3) python3 -c 'import time; print(int(time.time() * 1000))' ;;
		*)       : ;;
	esac
}

# _gdk_ledger_open <gate> <logfile> — start this slot's clock. Nothing at all
# happens without GDK_LEDGER_CMD, which is criterion "a consumer with no PM
# tree pays zero": no clock spawn, no sidecar, no subprocess.
_gdk_ledger_open() {
	[ -n "$GDK_LEDGER_CMD" ] || return 0
	local now side
	now="$(_gdk_now_ms)"
	if [ -z "$now" ]; then
		_gdk_ledger_note 'no millisecond clock here (GNU date or python3)'
		return 0
	fi
	side="$(_gdk_ledger_sidecar "$2")"
	# The `2>/dev/null` comes FIRST on purpose: redirections are applied left to
	# right, so a `>` that cannot create the file reports to an fd 2 that is
	# already /dev/null. An unwritable report dir is not a gate failure.
	printf '%s\n%s\n' "$now" "$1" 2>/dev/null > "$side" || true
	return 0
}

# _gdk_ledger_fault <logfile> <exit code> — remember, ON THE SLOT, that a
# capture against it failed.
#
# THE VERDICT IS THE SLOT'S, NOT THE LAST COMMAND'S. `gdk_gate_capture`
# publishes each command's own code in GDK_GATE_EXIT and a runner reads it
# there — that is the published contract and it stays last-write-wins. But a
# runner that captures N times against ONE `gdk_gate_log` slot (this repo's own
# `matrix` target loops one capture per interpreter) then leaves the LAST
# command's code standing when the verdict closes the row, so a matrix that
# failed on the first interpreter and passed on the last filed
# `"verdict":"PASS"` under a console line reading `FAIL on first`. A durable
# record that prints the opposite of what the gate found is hard rule 4's
# read-side sin, in the feature whose whole job is honest measurement.
#
# FIRST NON-ZERO WINS, and it is parked in the sidecar rather than a variable
# for the reason the sidecar exists at all: the state belongs to the SLOT, so
# two interleaved slots cannot read each other's, and a global would. Appending
# is the whole write — the first non-zero lands on line 3 and every later one
# lands past it, unread, so "the first thing that went wrong" needs no compare.
_gdk_ledger_fault() {
	[ -n "$GDK_LEDGER_CMD" ] || return 0
	case "${2-}" in ''|*[!0-9]*) return 0 ;; esac
	[ "$2" -ne 0 ] || return 0
	local side
	side="$(_gdk_ledger_sidecar "${1-}")"
	# No sidecar means no open slot for this log; a capture must never MINT one
	# (a row whose start time was never taken would be a fabricated duration).
	[ -f "$side" ] || return 0
	printf '%s\n' "$2" 2>/dev/null >> "$side" || true
	return 0
}

# _gdk_ledger_verdict [slot exit code] — the run's outcome in the ledger's
# CLOSED vocabulary, or nothing when this library would have to guess.
#
# The verdict never comes from the message. `gdk_gate_verdict`'s second
# argument is prose a human wrote ("PASS (12 files)", "FAIL (exit 3) — 2
# check(s) PASS"), and a durable column read out of prose is a column with five
# spellings of one outcome. GDK_GATE_EXIT is the fact: `gdk_gate_capture`
# publishes the command's own code, and 124/137 are the timeout pair the
# bounded-run contract above already names. A runner that publishes its own
# result without capturing says so in GDK_GATE_VERDICT.
#
# The argument is the SLOT's code when one was remembered (`_gdk_ledger_fault`),
# and it outranks GDK_GATE_EXIT for the reason spelled out there: a slot's
# verdict must reflect every capture against it, not the last.
_gdk_ledger_verdict() {
	case "$GDK_GATE_VERDICT" in
		PASS|FAIL|HANG|SKIP) printf '%s' "$GDK_GATE_VERDICT"; return 0 ;;
		'') ;;
		*) return 0 ;;
	esac
	local code="${1-}"
	[ -n "$code" ] || code="${GDK_GATE_EXIT:-}"
	case "$code" in
		''|*[!0-9]*) return 0 ;;
	esac
	if [ "$code" -eq 0 ]; then
		printf 'PASS'
	elif gdk_timeout_is_hang "$code"; then
		printf 'HANG'
	else
		printf 'FAIL'
	fi
}

# _gdk_ledger_run <argv...> — the recorder, BOUNDED. A broken recorder that
# hangs would otherwise hang every gate in a consumer's pre-push hook, which is
# the one failure mode worse than a missing row. With no timeout binary there
# is no bound to give, so there is no row either — said out loud, once.
#
# THE BOUND IS ONLY HALF THE ANSWER, AND IT WAS THE HALF THAT ALREADY WORKED.
# `timeout` bounds the recorder's own runtime; it does not bound how long this
# library WAITS for it, and until 0.2.0 those were different numbers. The
# caller read the recorder through `$( )`, whose pipe every grandchild
# inherits, so a recorder that backgrounded anything held the gate open for as
# long as the grandchild lived. Measured on the shipped file, GDK_LEDGER_TIMEOUT=3:
#
#   GDK_LEDGER_CMD="sh -c 'sleep 120 & exit 0'"   ->  120072 ms
#
# The deadline never even fired there. `timeout` returned 0 in under a
# millisecond, because its direct child DID exit — isolated:
#
#   timeout 2 sh -c 'sleep 20 & exit 0'                    0 s
#   out="$(timeout 2 sh -c 'sleep 20 & exit 0' 2>&1)"     20 s
#   timeout 2 sh -c 'sleep 20 & exit 0' >"$f" 2>&1         0 s
#
# So killing the process group would have fixed nothing: there was no deadline
# to fire and nothing to signal. The stall was the READER, and the fix is to
# stop reading through a pipe — see `_gdk_ledger_record`.
_gdk_ledger_run() {
	if [ -z "$GDK_TIMEOUT" ]; then
		return 1
	fi
	gdk_run_bounded "$GDK_LEDGER_TIMEOUT" -- "$@"
}

# THE VALUE IS PARSED INSIDE THE BOUND, NOT IN FRONT OF IT.
# GDK_LEDGER_CMD is a command STRING, and the stock spelling carries shell
# quoting (`uvx --from "git+https://…@$(DEVKIT_VERSION)" agentic-sdlc`), so a
# bare word split would hand `uvx` a spec with literal quote characters in it.
# `eval` into an array is the one shape that parses it the way the Makefile
# recipe next to it does, and that quoting support is not negotiable.
#
# But a value is not inert text to `eval`: every `$( )` and backtick in it
# EXECUTES while the array is built. That build used to happen in the GATE'S
# OWN shell, before `timeout` was ever invoked. Measured on the shipped file,
# GDK_LEDGER_TIMEOUT=3:
#
#   GDK_LEDGER_CMD='true $(sleep 20)'   ->  20062 ms, and NO note at all
#
# Same symptom as the fork case above — the recorder holds the gate open past
# its bound — and a different mechanism, so that fix does not reach this one:
# there the READER blocked on an inherited pipe, here the value ran during
# parse. Refusing `$(`, a backtick and `${` BY SHAPE would close the three
# spellings the review measured and not the class, because
# `eval "prefix=(a); sleep 20; x=("` carries none of them and runs just as
# long. So the parse moved inside the bound, where nothing it spells can
# outlive the deadline.
#
# `exec` is what keeps the bound honest for the recorder too: the shim's last
# act replaces itself with the recorder, so `timeout`'s direct child is still
# the recorder's own process and the signal path is the one measured above.
# 121 is the shim's OWN refusal — outside the codes a recorder plausibly
# returns, and confirmed against the message it prints, so a value this shell
# cannot parse is never reported as something the recorder did.
_GDK_LEDGER_PARSE_REFUSAL='GDK_LEDGER_CMD is not a command line this shell can parse'
# shellcheck disable=SC2016  # $1/$2/$@ are the SHIM's positionals, not ours
_GDK_LEDGER_SHIM='
eval "prefix=($1)" 2>/dev/null || { printf "%s\n" "$2" >&2; exit 121; }
shift 2
[ "${#prefix[@]}" -gt 0 ] || exit 0
exec "${prefix[@]}" "$@"
'

# _gdk_ledger_record <gate> <verdict> <duration_ms> [scratch]
#
# `scratch` is where the recorder's output is parked while it runs. It is a
# path, not a pipe, and that is the whole of the fix above: a file has no
# writer to wait for, so this returns when `timeout` returns whatever the
# recorder forked. Given empty (or a path that cannot be created), the output
# goes to /dev/null instead — a row without its refusal message is a
# degradation; a gate that will not return is not.
_gdk_ledger_record() {
	local said='' rc=0 scratch="${4-}"
	local -a argv
	argv=(pm ledger record --gate "$1" --verdict "$2" --duration-ms "$3")
	case "$GDK_GATE_CENSUS" in
		'') ;;
		*[!0-9]*)
			_gdk_ledger_note "GDK_GATE_CENSUS=\"$GDK_GATE_CENSUS\" is not a count, so the row omits it" ;;
		*) argv=("${argv[@]}" --census "$GDK_GATE_CENSUS") ;;
	esac
	# Both streams are captured: stdout must never reach the console, because a
	# consumer greps the `[TAG] … full log:` line (hard rule 6) and a chatty
	# recorder would sit in the middle of it. What the recorder said is not
	# thrown away, though — a refusal it printed is the one thing a consumer
	# needs, so its first line rides out on the note.
	#
	# TO A FILE. This was `said="$(_gdk_ledger_run … 2>&1)"` and that is the
	# defect — see `_gdk_ledger_run`'s block above for the measurement. The
	# probe is `: >"$scratch"`, run BEFORE the recorder: an unwritable report
	# dir must degrade to /dev/null rather than turn a redirection failure into
	# "the recorder exited 1", which would blame the recorder for the tree.
	# The recorder's own argv is built HERE and parsed THERE — see
	# `_GDK_LEDGER_SHIM`. Everything this file adds is a separate argv element,
	# so a gate name with a space or a metacharacter is still ONE element and
	# story 01's grammar is what refuses it.
	local -a cmd
	cmd=("${BASH:-bash}" -c "$_GDK_LEDGER_SHIM" _ \
		"$GDK_LEDGER_CMD" "$_GDK_LEDGER_PARSE_REFUSAL" "${argv[@]}")
	if [ -n "$scratch" ] && : 2>/dev/null > "$scratch"; then
		_gdk_ledger_run "${cmd[@]}" > "$scratch" 2>&1 || rc=$?
		# One line is all the note carries, so one line is all that is read —
		# a recorder that printed a megabyte does not become a shell variable.
		IFS= read -r said < "$scratch" 2>/dev/null || said="${said-}"
		# Unlinked immediately: anything the recorder forked still holds the
		# fd and writes into an inode with no name, freed when it dies.
		rm -f "$scratch" 2>/dev/null || true
	else
		_gdk_ledger_run "${cmd[@]}" > /dev/null 2>&1 || rc=$?
	fi
	if [ "$rc" -eq 121 ] && [ "$said" = "$_GDK_LEDGER_PARSE_REFUSAL" ]; then
		# The shim refused the VALUE; no recorder ever ran, so it is not the
		# recorder's exit code that gets reported.
		_gdk_ledger_note "$said"
	elif [ "$rc" -ne 0 ]; then
		_gdk_ledger_note "the recorder exited $rc: ${said%%$'\n'*}"
	fi
	return 0
}

# _gdk_ledger_close <logfile> — file this slot's row, exactly once.
_gdk_ledger_close() {
	[ -n "$GDK_LEDGER_CMD" ] || return 0
	local side start='' gate='' fault='' now duration verdict
	side="$(_gdk_ledger_sidecar "${1-}")"
	# No sidecar: either no slot was opened for this log, or this run already
	# filed its row and this is a second verdict line. Both are silent.
	[ -f "$side" ] || return 0
	# Line 3 is the first failing capture against this slot, if there was one;
	# a slot every capture passed has no line 3 and the chain simply stops.
	{ read -r start && read -r gate && read -r fault; } < "$side" 2>/dev/null || true
	rm -f "$side" 2>/dev/null || true
	case "$start" in ''|*[!0-9]*) return 0 ;; esac
	[ -n "$gate" ] || return 0
	now="$(_gdk_now_ms)"
	[ -n "$now" ] || return 0
	duration=$(( now - start ))
	[ "$duration" -ge 0 ] || duration=0
	verdict="$(_gdk_ledger_verdict "$fault")"
	if [ -z "$verdict" ]; then
		_gdk_ledger_note "gate \"$gate\" published no verdict this library can name (set GDK_GATE_VERDICT, or report through gdk_gate_capture)"
		return 0
	fi
	# The recorder's output is parked BESIDE the sidecar, which is the one
	# directory this slot has already proved it can write to: no sidecar, no
	# row (the guard above), so reaching here means `_gdk_ledger_open` created
	# a file here. A `mktemp` would be a second spawn on the quiet path, and a
	# fixed name under /tmp would be a shared-directory race.
	_gdk_ledger_record "$gate" "$verdict" "$duration" "$side.out"
	return 0
}

# gdk_gate_log <gate> — echo this run's transcript path, cleared and ready.
# It is also where the cost clock starts: this is the ONE call every reporting
# path makes exactly once per run.
gdk_gate_log() {
	local gate="${1:?usage: gdk_gate_log <gate>}"
	mkdir -p "$GDK_GATE_REPORT_DIR"
	local path="$GDK_GATE_REPORT_DIR/$gate.log"
	: > "$path"
	_gdk_ledger_open "$gate" "$path"
	printf '%s\n' "$path"
}

# gdk_gate_capture <logfile> -- <cmd...>
# Run <cmd>, APPENDING its combined output to <logfile> under the shared byte
# cap, and stream it to the console only under VERBOSE. Appends so a two-stage
# gate (boot, then sweep) publishes one transcript.
#
# Sets GDK_GATE_EXIT to the COMMAND's own exit code — `head -c` is the last
# pipe element and exits 0, so a caller must read that and never `$?`. That
# variable is LAST-WRITE-WINS and stays that way; what a failing capture also
# does is tell its LOG SLOT, so the row's verdict cannot be the last command's
# alone — see `_gdk_ledger_fault`.
#
# errexit is suspended around the pipeline and restored after. A wrapper under
# `set -euo pipefail` used to die ON this line: pipefail makes the pipeline's
# status the failing command's, `-e` then kills the shell, and GDK_GATE_EXIT is
# never read — the gate exited 3 having printed no verdict at all. Suspending
# is the only shape that keeps PIPESTATUS readable; `|| true` and `if …; then
# :; fi` both run a further simple command, which RESETS PIPESTATUS to (0) and
# would report every gate as passing.
gdk_gate_capture() {
	local log="${1:?usage: gdk_gate_capture <log> -- <cmd...>}"; shift
	[ "${1:-}" = "--" ] && shift
	local errexit_was_set=0
	case "$-" in *e*) errexit_was_set=1; set +e ;; esac
	if [ "${VERBOSE:-0}" != "0" ]; then
		"$@" 2>&1 | head -c "$GDK_LOG_CAP_BYTES" | tee -a "$log"
	else
		"$@" 2>&1 | head -c "$GDK_LOG_CAP_BYTES" >> "$log"
	fi
	# shellcheck disable=SC2034  # read by the sourcing wrapper, not here
	GDK_GATE_EXIT="${PIPESTATUS[0]}"
	# The slot remembers a failing capture, because GDK_GATE_EXIT is
	# last-write-wins and a slot's verdict is not — see `_gdk_ledger_fault`.
	# It sits BEFORE the errexit restore on purpose: after it, a bookkeeping
	# call returning non-zero would kill a wrapper under `set -e` on the line
	# that was supposed to make the gate reportable.
	_gdk_ledger_fault "$log" "$GDK_GATE_EXIT"
	[ "$errexit_was_set" -eq 0 ] || set -e
	return 0
}

# gdk_gate_publish <logfile> <transcript>
# The capture-then-PARSE shape: a gate that must hold the whole transcript in a
# variable to reconcile a test runner's counts before it can report cannot
# stream through the pipeline above. Same contract — persist capped, echo under
# VERBOSE.
gdk_gate_publish() {
	local log="${1:?usage: gdk_gate_publish <log> <transcript>}"
	printf '%s\n' "${2-}" | head -c "$GDK_LOG_CAP_BYTES" > "$log"
	[ "${VERBOSE:-0}" = "0" ] || printf '%s\n' "${2-}"
}

# gdk_gate_verdict <TAG> <message> <logfile>
# The ONE shape a gate's result line takes, so the transcript is always named
# in the same place and a failing run is one `sed -n` away:
#   [TAG] <message> — full log: <path>
#
# It also CLOSES this run's cost row — after the line, never before it. The
# verdict is the gate's result and the row is bookkeeping about it; a
# bookkeeping step in front of the result is a step that can delay or swallow
# one. `return 0` is explicit for the same reason: a wrapper under `set -e`
# must not learn about a ledger problem as its own death.
gdk_gate_verdict() {
	printf '[%s] %s — full log: %s\n' \
		"${1:?usage: gdk_gate_verdict <TAG> <message> <log>}" "${2-}" "${3-}"
	_gdk_ledger_close "${3-}"
	return 0
}

# --- --self-test — the contract, PROVEN rather than claimed ------------------
# `bash gdk_gate.sh --self-test` runs a fake gate through capture → verdict and
# checks every claim the comments above make. Same shape as the hook corpus: a
# corpus that is re-run is the only reason to trust it six months later. It
# runs entirely inside a scratch dir it makes and removes, so it can never
# write into the repo it lives in.

_GDK_ST_FAILURES=0
_GDK_ST_CASES=0

# _gdk_st_eq <what> <expected> <actual>
_gdk_st_eq() {
	_GDK_ST_CASES=$((_GDK_ST_CASES + 1))
	if [ "$2" != "$3" ]; then
		printf '  MISS — %s\n    expected: %s\n    actual:   %s\n' "$1" "$2" "$3" >&2
		_GDK_ST_FAILURES=$((_GDK_ST_FAILURES + 1))
	fi
}

# _gdk_st_true <what> <status>
_gdk_st_true() {
	_GDK_ST_CASES=$((_GDK_ST_CASES + 1))
	if [ "$2" != "0" ]; then
		printf '  MISS — %s (status %s)\n' "$1" "$2" >&2
		_GDK_ST_FAILURES=$((_GDK_ST_FAILURES + 1))
	fi
}

# _gdk_st_has <what> <haystack> <needle>
_gdk_st_has() {
	_GDK_ST_CASES=$((_GDK_ST_CASES + 1))
	case "$2" in
		*"$3"*) return 0 ;;
	esac
	printf '  MISS — %s\n    wanted: %s\n    in:     %s\n' "$1" "$3" "$2" >&2
	_GDK_ST_FAILURES=$((_GDK_ST_FAILURES + 1))
}

# _gdk_st_lacks <what> <haystack> <needle>
_gdk_st_lacks() {
	_GDK_ST_CASES=$((_GDK_ST_CASES + 1))
	case "$2" in
		*"$3"*)
			printf '  MISS — %s\n    forbidden: %s\n    in:        %s\n' \
				"$1" "$3" "$2" >&2
			_GDK_ST_FAILURES=$((_GDK_ST_FAILURES + 1)) ;;
	esac
}

# _gdk_st_gate <lib> <ledger cmd> <gate exit> — one whole gate, in a CHILD
# shell under `set -euo pipefail`, with the recorder wired to <ledger cmd>.
# Echoes what the gate said on stdout, then `exit=<its own code>`.
#
# The child is the point. This is the adversarial case against
# `gdk_gate_capture`'s own comment block, which claims the errexit
# suspend/restore is the only shape that keeps PIPESTATUS readable and that a
# further simple command would reset it — the recorder IS a further simple
# command, in that neighbourhood, and it now runs on every gate in every
# consumer. A gate whose command exits 7 has to still reach its verdict and
# still report 7 with a recorder present, whatever the recorder does.
_gdk_st_gate() {
	local out rc=0
	# shellcheck disable=SC2016  # $1/$2/$3 are the CHILD shell's positionals
	out="$(bash -c '
		set -euo pipefail
		# shellcheck source=/dev/null
		source "$1"
		GDK_LEDGER_CMD="$2"
		log="$(gdk_gate_log strict)"
		gdk_gate_capture "$log" -- sh -c "exit $3"
		status="$GDK_GATE_EXIT"
		gdk_gate_verdict STRICT "done" "$log"
		exit "$status"
	' _ "$1" "$2" "$3" 2>/dev/null)" || rc=$?
	printf '%s\nexit=%s\n' "$out" "$rc"
}

_gdk_self_test() {
	local scratch verdict log body status hung lib recorded ledger_case t0 elapsed
	# Resolved BEFORE the cd below: the sub-shell cases re-source the library
	# from a different working directory.
	lib="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
	scratch="$(mktemp -d "${TMPDIR:-/tmp}/gdk-gate-selftest.XXXXXX")" || return 1
	cd "$scratch" || return 1
	# The corpus proves BOTH settings, each pinned on its own case; the value
	# the caller happens to export is not part of it. Left to inherit, a
	# `VERBOSE=1` self-test — what the installed CI exports for the whole run —
	# streamed the cap case's eight bytes straight into this corpus's own
	# verdict line (`01234567[gdk-gate] SELF-TEST OK …`).
	VERBOSE=0
	# Re-read it from the shell: a TMPDIR with a trailing slash yields `//` in
	# the mktemp path, and every prefix comparison below would silently miss.
	scratch="$PWD"

	# --- gdk_gate_log: names the slot, creates it, clears it -----------------
	log="$(gdk_gate_log parse)"
	_gdk_st_eq 'gate_log names <dir>/<gate>.log' "$GDK_GATE_REPORT_DIR/parse.log" "$log"
	status=0; [ -f "$log" ] || status=1
	_gdk_st_true 'gate_log creates the file' "$status"
	printf 'residue from a previous run\n' > "$log"
	log="$(gdk_gate_log parse)"
	_gdk_st_eq 'gate_log clears the slot it hands back' '' "$(cat "$log")"

	# --- gdk_gate_capture: quiet by default, persists, appends ---------------
	body="$(VERBOSE=0 gdk_gate_capture "$log" -- printf 'first line\n')"
	_gdk_st_eq 'capture prints nothing when VERBOSE=0' '' "$body"
	_gdk_st_eq 'capture persists the stream' 'first line' "$(cat "$log")"
	body="$(VERBOSE=1 gdk_gate_capture "$log" -- printf 'second line\n')"
	_gdk_st_eq 'capture streams when VERBOSE=1' 'second line' "$body"
	_gdk_st_eq 'capture APPENDS (a two-stage gate is one transcript)' \
		'first line
second line' "$(cat "$log")"

	# --- gdk_gate_capture: GDK_GATE_EXIT is the COMMAND's code, not head's ---
	GDK_GATE_EXIT=''
	gdk_gate_capture "$log" -- sh -c 'exit 7' >/dev/null 2>&1
	_gdk_st_eq 'capture reports the command exit code, not the pipeline tail' \
		'7' "$GDK_GATE_EXIT"

	# --- capture survives a wrapper under `set -euo pipefail` ----------------
	# pipefail + errexit used to kill the wrapper ON the capture line: no
	# verdict, exit 3, and VERBOSE=1 showing only the stream.
	body="$(cd "$scratch" && bash -c '
		set -euo pipefail
		# shellcheck source=/dev/null
		source "$1"
		log="$(gdk_gate_log strict)"
		gdk_gate_capture "$log" -- sh -c "exit 7"
		printf "exit=%s reached-the-verdict\n" "$GDK_GATE_EXIT"
	' _ "$lib" 2>&1)"
	_gdk_st_eq 'capture under set -euo pipefail reports and returns' \
		'exit=7 reached-the-verdict' "$body"

	# --- the byte cap is real ------------------------------------------------
	# `env … bash -c`, never `( GDK_LOG_CAP_BYTES=8; … )`. A subshell
	# ASSIGNMENT to a name the library also publishes makes `shellcheck -x`
	# raise SC2031 at every CONSUMER site that reads that name — the consumer's
	# own lint reddens on a line the library wrote, and the only local repair
	# is a disable comment in a file whose author did nothing wrong. Scoping
	# the value to a child process says the same thing with no such shadow.
	log="$(gdk_gate_log capped)"
	# shellcheck disable=SC2016  # $1/$2 are the CHILD shell's positionals
	env GDK_LOG_CAP_BYTES=8 bash -c '
		# shellcheck source=/dev/null
		source "$1"
		gdk_gate_capture "$2" -- printf "0123456789abcdef"
	' _ "$lib" "$log"
	_gdk_st_eq 'the log cap truncates a runaway stream' '8' \
		"$(wc -c < "$log" | tr -d ' ')"

	# --- gdk_gate_publish: capture-then-parse takes the same slot ------------
	log="$(gdk_gate_log unit)"
	body="$(VERBOSE=0 gdk_gate_publish "$log" 'held in a variable')"
	_gdk_st_eq 'publish prints nothing when VERBOSE=0' '' "$body"
	_gdk_st_eq 'publish persists the transcript' 'held in a variable' "$(cat "$log")"
	body="$(VERBOSE=1 gdk_gate_publish "$log" 'held in a variable')"
	_gdk_st_eq 'publish streams when VERBOSE=1' 'held in a variable' "$body"

	# --- gdk_gate_verdict: ONE line, and it names the full log ---------------
	verdict="$(gdk_gate_verdict PARSE 'PASS (12 files)' '.gate-reports/parse.log')"
	_gdk_st_eq 'the verdict line shape' \
		'[PARSE] PASS (12 files) — full log: .gate-reports/parse.log' "$verdict"
	_gdk_st_eq 'the verdict is exactly one line' '1' \
		"$(gdk_gate_verdict PARSE 'PASS' 'x.log' | wc -l | tr -d ' ')"

	# --- gdk_run_bounded: passes through, and 124 means HUNG -----------------
	if [ -n "$GDK_TIMEOUT" ]; then
		status=0; gdk_run_bounded 5 -- sh -c 'exit 3' || status=$?
		_gdk_st_eq 'run_bounded returns the command exit code' '3' "$status"
		status=0; gdk_run_bounded 1 -- sleep 5 || status=$?
		hung=0
		[ "$status" = "$GDK_EXIT_SIGTERM_TIMEOUT" ] \
			|| [ "$status" = "$GDK_EXIT_SIGKILL_TIMEOUT" ] || hung=1
		_gdk_st_true 'run_bounded reports a hang as 124/137' "$hung"
	else
		status=0; gdk_run_bounded 5 -- true 2>/dev/null || status=$?
		_gdk_st_eq 'run_bounded fails loud with no timeout binary' '2' "$status"
	fi

	# --- gdk_timeout_is_hang: only the two timeout codes are a hang ----------
	status=0; gdk_timeout_is_hang "$GDK_EXIT_SIGTERM_TIMEOUT" || status=1
	_gdk_st_true 'timeout_is_hang recognises 124' "$status"
	status=0; gdk_timeout_is_hang "$GDK_EXIT_SIGKILL_TIMEOUT" || status=1
	_gdk_st_true 'timeout_is_hang recognises 137' "$status"
	status=0; gdk_timeout_is_hang 1 && status=1
	_gdk_st_true 'a failing gate (exit 1) is NOT a hang' "$status"
	status=0; gdk_timeout_is_hang 0 && status=1
	_gdk_st_true 'a passing gate (exit 0) is NOT a hang' "$status"

	# --- gdk_on_exit: registration order, and no hook masks the status -------
	# The dispatcher exists because there is ONE `trap … EXIT` slot: two
	# wrappers each writing their own is how a cleanup silently stops running.
	# Order is contract — a hook that reads what an earlier hook wrote is the
	# shape a language kit's sandbox restore depends on.
	# shellcheck disable=SC2016  # $1 is the CHILD shell's positional
	body="$(bash -c '
		# shellcheck source=/dev/null
		source "$1"
		gdk_on_exit "printf one"
		gdk_on_exit "printf two"
		exit 0
	' _ "$lib" 2>&1)"
	_gdk_st_eq 'exit hooks run in registration order' 'onetwo' "$body"

	# shellcheck disable=SC2016  # $1 is the CHILD shell's positional
	status=0
	bash -c '
		# shellcheck source=/dev/null
		source "$1"
		gdk_on_exit "false"
		gdk_on_exit "printf ran-anyway"
		exit 5
	' _ "$lib" >/dev/null 2>&1 || status=$?
	_gdk_st_eq 'a failing hook never masks the script exit status' '5' "$status"

	# --- the cost row -------------------------------------------------------
	# A recorder stub, so every case below asserts on the ARGV the library
	# actually handed on rather than on a ledger it would need a PM tree to
	# write. One line per invocation: `CALL ARG[x] ARG[y] …`.
	GDK_ST_REC_LOG="$scratch/recorder.log"
	export GDK_ST_REC_LOG
	cat > "$scratch/rec.sh" <<'REC_EOF'
#!/usr/bin/env bash
{ printf 'CALL'; for a in "$@"; do printf ' ARG[%s]' "$a"; done; printf '\n'
} >> "$GDK_ST_REC_LOG" 2>/dev/null || exit 4   # 4: the ledger is unwritable
[ -z "${GDK_ST_REC_SAY:-}" ] || printf '%s\n' "$GDK_ST_REC_SAY"
exit "${GDK_ST_REC_EXIT:-0}"
REC_EOF
	cat > "$scratch/hang.sh" <<'HANG_EOF'
#!/usr/bin/env bash
sleep 30
HANG_EOF
	# A recorder that EXITS CLEANLY and leaves something behind it. The stock
	# GDK_LEDGER_CMD is a `uvx` line, whose subprocess behaviour this package
	# does not control, so this is not a hypothetical shape.
	# THE SLEEP IS 3 s AND THE CEILING 2000 ms, AND THAT IS DELIBERATE.
	# The proof is a RATIO — a recorder that outlives its bound reddens the
	# mutant whether it outlives it by 3x or by 20x — and the suite pays the
	# difference in wall clock on every run, forever. This corpus used
	# `sleep 20` against a 10000 ms ceiling, and the two mutation tests that
	# drive it were 24 s and 23 s: half the wall clock of a 96 s suite, in two
	# cases, setting a floor no amount of parallelism could get under.
	# A bound of 1000 ms, a sleep of 3 s and a ceiling of 2000 ms keeps every
	# margin wide (3x over the bound, 1.5x over the ceiling) and costs 3 s.
	cat > "$scratch/fork.sh" <<'FORK_EOF'
#!/usr/bin/env bash
sleep 3 &
exit 0
FORK_EOF
	: > "$GDK_ST_REC_LOG"

	# UNSET SPAWNS NOTHING. A consumer with no PM tree pays zero: no clock, no
	# sidecar, no subprocess. The sentinel the recorder would have written is
	# the assertion, because "it was not configured" and "it ran and did
	# nothing" are the two answers that must never look alike.
	GDK_LEDGER_CMD=''
	log="$(gdk_gate_log quiet)"
	status=0; [ ! -f "$(_gdk_ledger_sidecar "$log")" ] || status=1
	_gdk_st_true 'an unset GDK_LEDGER_CMD opens no slot' "$status"
	GDK_GATE_EXIT=0
	gdk_gate_verdict QUIET 'PASS' "$log" >/dev/null
	_gdk_st_eq 'an unset GDK_LEDGER_CMD spawns no recorder' \
		'' "$(cat "$GDK_ST_REC_LOG")"

	# THE ROW ITSELF, and the verdict line it must not touch.
	GDK_LEDGER_CMD="bash $scratch/rec.sh"
	: > "$GDK_ST_REC_LOG"
	GDK_GATE_CENSUS=''
	log="$(gdk_gate_log check)"
	GDK_GATE_EXIT=0
	body="$(gdk_gate_verdict CHECK 'PASS (12 files)' "$log" 2>/dev/null)"
	_gdk_st_eq 'the recorder never reaches the verdict stream' \
		"[CHECK] PASS (12 files) — full log: $GDK_GATE_REPORT_DIR/check.log" \
		"$body"
	recorded="$(cat "$GDK_ST_REC_LOG")"
	_gdk_st_eq 'one gdk_gate_log slot files exactly one row' '1' \
		"$(grep -c '^CALL' "$GDK_ST_REC_LOG" | tr -d ' ')"
	_gdk_st_has 'the row names the verb' "$recorded" 'ARG[ledger] ARG[record]'
	_gdk_st_has 'the row names the gate' "$recorded" 'ARG[--gate] ARG[check]'
	_gdk_st_has 'a gate that exited 0 is a PASS' "$recorded" 'ARG[--verdict] ARG[PASS]'
	status=0
	[ -n "$(sed -n 's/.*ARG\[--duration-ms\] ARG\[\([0-9][0-9]*\)\].*/\1/p' \
		"$GDK_ST_REC_LOG")" ] || status=1
	_gdk_st_true 'the row carries an integer millisecond duration' "$status"

	# THE CENSUS IS ABSENT, NEVER ZERO — and never read out of the prose. The
	# message below is full of numbers on purpose: a regex over it is how a run
	# that walked 683 files files `census: 0`.
	_gdk_st_lacks 'an unset census is an omitted flag' "$recorded" 'ARG[--census]'
	: > "$GDK_ST_REC_LOG"
	log="$(gdk_gate_log prose)"
	gdk_gate_verdict PROSE 'PASS (683 files, 0 findings)' "$log" >/dev/null 2>&1
	_gdk_st_lacks 'no census is inferred from the message' \
		"$(cat "$GDK_ST_REC_LOG")" 'ARG[--census]'
	: > "$GDK_ST_REC_LOG"
	GDK_GATE_CENSUS=683
	log="$(gdk_gate_log counted)"
	gdk_gate_verdict COUNTED 'PASS' "$log" >/dev/null 2>&1
	_gdk_st_has 'a census the CALLER set rides on the row' \
		"$(cat "$GDK_ST_REC_LOG")" 'ARG[--census] ARG[683]'
	GDK_GATE_CENSUS=''

	# ONE ROW PER RUN, NOT ONE PER VERDICT LINE. A runner with alternative
	# exits calls the verdict up to six times against one slot; six rows for
	# one run would make the report average a gate against its own early exits.
	: > "$GDK_ST_REC_LOG"
	log="$(gdk_gate_log multi)"
	gdk_gate_verdict MULTI 'first'  "$log" >/dev/null 2>&1
	gdk_gate_verdict MULTI 'second' "$log" >/dev/null 2>&1
	gdk_gate_verdict MULTI 'third'  "$log" >/dev/null 2>&1
	_gdk_st_eq 'three verdicts on one slot file ONE row' '1' \
		"$(grep -c '^CALL' "$GDK_ST_REC_LOG" | tr -d ' ')"

	# ONE VERDICT PER SLOT, AND IT ANSWERS FOR EVERY CAPTURE — not the last.
	# A runner that loops one capture per interpreter against one slot (this
	# repo's own `matrix` target) used to leave the LAST command's code
	# standing: console `[MATRIX] FAIL on first`, row `"verdict":"PASS"`. An
	# output-only corpus cannot see that — the verdict LINE is right and the
	# durable record is inverted — so the assertion is on the recorder's argv.
	: > "$GDK_ST_REC_LOG"
	GDK_GATE_EXIT=''
	log="$(gdk_gate_log mixed)"
	gdk_gate_capture "$log" -- sh -c 'exit 1' >/dev/null 2>&1
	gdk_gate_capture "$log" -- sh -c 'exit 0' >/dev/null 2>&1
	_gdk_st_eq 'the LAST capture still publishes GDK_GATE_EXIT' '0' "$GDK_GATE_EXIT"
	gdk_gate_verdict MIXED 'FAIL on first' "$log" >/dev/null 2>&1
	_gdk_st_has 'a slot whose captures were 1 then 0 files FAIL, not PASS' \
		"$(cat "$GDK_ST_REC_LOG")" 'ARG[--verdict] ARG[FAIL]'
	_gdk_st_eq 'and a multi-capture slot is still exactly one row' '1' \
		"$(grep -c '^CALL' "$GDK_ST_REC_LOG" | tr -d ' ')"

	# ...and a slot every capture passed is still a PASS. An accumulator that
	# cannot go back to green would file hard rule 4's sin from the other side.
	: > "$GDK_ST_REC_LOG"
	log="$(gdk_gate_log allgood)"
	gdk_gate_capture "$log" -- sh -c 'exit 0' >/dev/null 2>&1
	gdk_gate_capture "$log" -- sh -c 'exit 0' >/dev/null 2>&1
	gdk_gate_verdict ALLGOOD 'PASS' "$log" >/dev/null 2>&1
	_gdk_st_has 'two passing captures on one slot file PASS' \
		"$(cat "$GDK_ST_REC_LOG")" 'ARG[--verdict] ARG[PASS]'

	# A capture against a log NO slot was opened for mints nothing: a row whose
	# start time was never taken would carry an invented duration.
	: > "$GDK_ST_REC_LOG"
	: > "$GDK_GATE_REPORT_DIR/orphan.log"
	gdk_gate_capture "$GDK_GATE_REPORT_DIR/orphan.log" -- sh -c 'exit 1' >/dev/null 2>&1
	status=0
	[ ! -f "$(_gdk_ledger_sidecar "$GDK_GATE_REPORT_DIR/orphan.log")" ] || status=1
	_gdk_st_true 'a capture never mints a slot its log never opened' "$status"
	GDK_GATE_EXIT=0

	# THE VALUE'S QUOTING SURVIVES WHATEVER BOUNDS ITS PARSE. The stock
	# GDK_LEDGER_CMD is a `uvx` line carrying a quoted spec; a bare word split
	# would hand the recorder a spec with literal quote characters in it, so
	# "parse it somewhere safer" must never become "stop parsing it".
	: > "$GDK_ST_REC_LOG"
	GDK_LEDGER_CMD="bash $scratch/rec.sh --from \"git+https://example.invalid/x@v0.0.0\" agentic-sdlc"
	log="$(gdk_gate_log quoted)"
	gdk_gate_verdict QUOTED 'PASS' "$log" >/dev/null 2>&1
	_gdk_st_has 'a quoted value arrives as ONE argv element' \
		"$(cat "$GDK_ST_REC_LOG")" \
		'ARG[--from] ARG[git+https://example.invalid/x@v0.0.0] ARG[agentic-sdlc]'
	GDK_LEDGER_CMD="bash $scratch/rec.sh"

	# THE PUBLISH-ONLY SHAPE. A runner that reconciles a transcript in a
	# variable never calls gdk_gate_capture, so nothing sets GDK_GATE_EXIT and
	# the timer cannot live there. It publishes its own verdict instead.
	: > "$GDK_ST_REC_LOG"
	GDK_GATE_EXIT=''
	GDK_GATE_VERDICT=FAIL
	log="$(gdk_gate_log published)"
	gdk_gate_publish "$log" 'held in a variable' >/dev/null
	gdk_gate_verdict PUBLISHED 'FAIL (2 of 40)' "$log" >/dev/null 2>&1
	recorded="$(cat "$GDK_ST_REC_LOG")"
	_gdk_st_has 'a gate that never captured still files its cost' \
		"$recorded" 'ARG[--gate] ARG[published]'
	_gdk_st_has 'and the verdict its runner published' \
		"$recorded" 'ARG[--verdict] ARG[FAIL]'
	GDK_GATE_VERDICT=''

	# THE VERDICT IS DERIVED FROM THE EXIT CODE, INCLUDING THE TIMEOUT PAIR.
	: > "$GDK_ST_REC_LOG"
	GDK_GATE_EXIT=3
	log="$(gdk_gate_log failed)"
	gdk_gate_verdict FAILED 'FAIL (exit 3)' "$log" >/dev/null 2>&1
	_gdk_st_has 'a non-zero exit is a FAIL' \
		"$(cat "$GDK_ST_REC_LOG")" 'ARG[--verdict] ARG[FAIL]'
	: > "$GDK_ST_REC_LOG"
	GDK_GATE_EXIT="$GDK_EXIT_SIGTERM_TIMEOUT"
	log="$(gdk_gate_log hung)"
	gdk_gate_verdict HUNG 'HUNG' "$log" >/dev/null 2>&1
	_gdk_st_has 'the timeout pair is a HANG, not a FAIL' \
		"$(cat "$GDK_ST_REC_LOG")" 'ARG[--verdict] ARG[HANG]'
	GDK_GATE_EXIT=0

	# A GATE NAME WITH A SPACE AND A METACHARACTER — one argv element, always.
	# A mis-set tag must reach story 01's grammar and be refused there, never
	# get word-split into a command this library did not mean to run.
	: > "$GDK_ST_REC_LOG"
	log="$(gdk_gate_log 'bad name;touch pwned')"
	gdk_gate_verdict BAD 'PASS' "$log" >/dev/null 2>&1
	_gdk_st_has 'a gate name is ONE argv element, metacharacters and all' \
		"$(cat "$GDK_ST_REC_LOG")" 'ARG[bad name;touch pwned]'
	status=0; [ ! -f "$scratch/pwned" ] || status=1
	_gdk_st_true 'and nothing in it was executed' "$status"

	# --- FAIL OPEN: the refusal matrix, each preserving the gate's own code --
	# This block is the risk-1 test. The recorder is an input surface — a
	# command string out of a Makefile — and it is on the path of every gate in
	# every consumer, so each way it can break gets a case, and each case
	# asserts the same two things: the verdict line still printed, and the
	# gate's own exit code came through untouched.
	: > "$GDK_ST_REC_LOG"
	for ledger_case in \
		'' \
		"$scratch/no-such-recorder" \
		"env GDK_ST_REC_EXIT=1 bash $scratch/rec.sh" \
		"env GDK_ST_REC_SAY=noise bash $scratch/rec.sh" \
		"env GDK_ST_REC_LOG=$scratch/read-only/x bash $scratch/rec.sh"
	do
		body="$(_gdk_st_gate "$lib" "$ledger_case" 7)"
		_gdk_st_eq "a broken recorder never changes a failing gate's code (${ledger_case:-unset})" \
			"[STRICT] done — full log: $GDK_GATE_REPORT_DIR/strict.log
exit=7" "$body"
		body="$(_gdk_st_gate "$lib" "$ledger_case" 0)"
		_gdk_st_eq "a broken recorder never changes a passing gate's code (${ledger_case:-unset})" \
			"[STRICT] done — full log: $GDK_GATE_REPORT_DIR/strict.log
exit=0" "$body"
	done

	# --- THE WALL-CLOCK CASES, and they are the only slow ones in here -------
	#
	# Three cases below prove a bound by WAITING for it: a recorder that hangs,
	# one that forks, and one whose value is parsed in front of the bound. Only
	# the clock can tell a fixed library from a broken one on those, so they
	# cost real seconds — about 3 of this corpus's 4.
	#
	# `GDK_ST_SKIP_TIMING=1` runs everything else. That exists because the
	# corpus is driven by NINE mutation tests, each of which reverts one line of
	# this library and asserts one specific case reddens — and seven of those
	# nine have nothing to do with timing. Paying 3 s of sleep to prove a
	# verdict-shape mutant reddens is 21 s of a suite spent proving nothing, on
	# every run, forever (hard rule 10).
	#
	# The two mutation tests that ARE about the bound run the whole corpus, and
	# so does `--self-test` with nothing set — which is what a consumer runs and
	# what `make hooks-self-test` replays. The skip is a caller's optimisation,
	# never the default: a corpus that quietly stopped covering its slowest
	# cases would be exactly the narrowing this library's own census exists to
	# refuse.
	if [ -n "$GDK_TIMEOUT" ] && [ "${GDK_ST_SKIP_TIMING:-0}" != "1" ]; then
		# EXPORTED: the bound is read by the library in the CHILD shell, and an
		# assignment this shell merely holds would never reach it — the case
		# would then take 30 s and pass for the wrong reason.
		export GDK_LEDGER_TIMEOUT=1
		body="$(_gdk_st_gate "$lib" "bash $scratch/hang.sh" 7)"
		unset GDK_LEDGER_TIMEOUT
		_gdk_st_eq 'a recorder that hangs is bounded, and the gate still reports' \
			"[STRICT] done — full log: $GDK_GATE_REPORT_DIR/strict.log
exit=7" "$body"

		# AND A RECORDER THAT FORKS. The case above bounds a recorder that
		# HANGS, and it passed all along; it is not the same question. Here the
		# recorder exits 0 immediately and the deadline never fires — what used
		# to hold the gate was the `$( )` the output was read through, whose
		# pipe the forked grandchild inherited. Measured on the shipped file at
		# GDK_LEDGER_TIMEOUT=3, `sh -c 'sleep 120 & exit 0'` cost 120072 ms; the
		# same probe after the fix cost 52 ms.
		#
		# The assertion is WALL CLOCK, because the verdict line and the exit
		# code were already correct across twelve hostile recorders and stayed
		# correct through this one — an output-only corpus cannot see this
		# defect at all. The threshold is 10 s against a 20 s sleep and a 1 s
		# bound: wide enough that a loaded machine cannot redden it, narrow
		# enough that the defect cannot hide under it.
		export GDK_LEDGER_TIMEOUT=1
		t0="$(_gdk_now_ms)"
		body="$(_gdk_st_gate "$lib" "bash $scratch/fork.sh" 7)"
		elapsed="$(_gdk_now_ms)"
		unset GDK_LEDGER_TIMEOUT
		_gdk_st_eq 'a recorder that forks still lets the gate report' \
			"[STRICT] done — full log: $GDK_GATE_REPORT_DIR/strict.log
exit=7" "$body"
		if [ -n "$t0" ] && [ -n "$elapsed" ]; then
			elapsed=$(( elapsed - t0 ))
			status=0; [ "$elapsed" -lt 2000 ] || status=1
			_gdk_st_true \
				"a recorder that forks does not hold the gate open (${elapsed} ms, bound 1000)" \
				"$status"
		else
			echo '  SKIP — no millisecond clock; the forking-recorder bound was not timed' >&2
		fi

		# AND A VALUE THAT EXECUTES WHILE IT IS PARSED. `eval` runs every
		# `$( )` in the string as the array is built, and that build used to
		# happen in the gate's own shell, in FRONT of `timeout`: measured
		# 20062 ms against a 3 s bound, with no note at all. Wall clock for the
		# third time, and for the third reason: the verdict line and the exit
		# code were correct throughout, so nothing but the clock can see it.
		export GDK_LEDGER_TIMEOUT=1
		t0="$(_gdk_now_ms)"
		body="$(_gdk_st_gate "$lib" "bash $scratch/rec.sh \$(sleep 3)" 7)"
		elapsed="$(_gdk_now_ms)"
		unset GDK_LEDGER_TIMEOUT
		_gdk_st_eq 'a substituting recorder value still lets the gate report' \
			"[STRICT] done — full log: $GDK_GATE_REPORT_DIR/strict.log
exit=7" "$body"
		if [ -n "$t0" ] && [ -n "$elapsed" ]; then
			elapsed=$(( elapsed - t0 ))
			status=0; [ "$elapsed" -lt 2000 ] || status=1
			_gdk_st_true \
				"a substitution in GDK_LEDGER_CMD is parsed UNDER the bound (${elapsed} ms, bound 1000)" \
				"$status"
		else
			echo '  SKIP — no millisecond clock; the parse-under-bound case was not timed' >&2
		fi
	else
		echo '  SKIP — no timeout binary; the bounded-recorder case did not run' >&2
	fi
	GDK_LEDGER_CMD=''
	unset GDK_ST_REC_LOG

	cd / || return 1
	rm -rf "$scratch"
	return 0
}

_gdk_usage() {
	cat <<'USAGE_EOF'
usage: source gdk_gate.sh            the normal use — a shell library
       bash gdk_gate.sh --self-test  run the contract corpus
       bash gdk_gate.sh --help       this message

Public functions: gdk_on_exit, gdk_run_bounded, gdk_timeout_is_hang,
gdk_gate_log, gdk_gate_capture, gdk_gate_publish, gdk_gate_verdict.
USAGE_EOF
}

# Executed rather than sourced? Only --self-test and --help are supported, and
# only one of them: an extra argument is a caller who thinks this takes options
# it does not, and guessing at their intent is how a gate runs the wrong thing.
if [ "${BASH_SOURCE[0]}" = "$0" ]; then
	if [ "$#" -ne 1 ]; then
		echo "$GDK_LIB_TAG: exactly one argument — got $#. See --help." >&2
		exit 2
	fi
	case "$1" in
		--self-test)
			_gdk_self_test || _GDK_ST_FAILURES=$((_GDK_ST_FAILURES + 1))
			if [ "$_GDK_ST_FAILURES" -eq 0 ]; then
				echo "[$GDK_LIB_TAG] SELF-TEST OK — $_GDK_ST_CASES case(s)"
				exit 0
			fi
			echo "[$GDK_LIB_TAG] SELF-TEST FAIL — $_GDK_ST_FAILURES of $_GDK_ST_CASES case(s), see above" >&2
			exit 1
			;;
		--help|-h) _gdk_usage; exit 0 ;;
		*)
			echo "$GDK_LIB_TAG: this is a library — source it. See --help." >&2
			exit 2
			;;
	esac
fi
