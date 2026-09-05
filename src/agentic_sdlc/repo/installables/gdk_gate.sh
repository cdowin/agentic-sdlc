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

# gdk_gate_log <gate> — echo this run's transcript path, cleared and ready.
gdk_gate_log() {
	local gate="${1:?usage: gdk_gate_log <gate>}"
	mkdir -p "$GDK_GATE_REPORT_DIR"
	local path="$GDK_GATE_REPORT_DIR/$gate.log"
	: > "$path"
	printf '%s\n' "$path"
}

# gdk_gate_capture <logfile> -- <cmd...>
# Run <cmd>, APPENDING its combined output to <logfile> under the shared byte
# cap, and stream it to the console only under VERBOSE. Appends so a two-stage
# gate (boot, then sweep) publishes one transcript.
#
# Sets GDK_GATE_EXIT to the COMMAND's own exit code — `head -c` is the last
# pipe element and exits 0, so a caller must read that and never `$?`.
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
gdk_gate_verdict() {
	printf '[%s] %s — full log: %s\n' \
		"${1:?usage: gdk_gate_verdict <TAG> <message> <log>}" "${2-}" "${3-}"
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

_gdk_self_test() {
	local scratch verdict log body status hung lib
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
