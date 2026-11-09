#!/bin/sh
# wide-gate.sh - agentic-sdlc PreToolUse hook for Bash. OPT-IN: runs only when
# AGENTIC_SDLC_GATE_WIDE is set to an ERE that names the wide (full-suite) command.
# The wide gate's one run is CI. This hook refuses a Bash command that matches the ERE,
# so an agent runs its fast tests instead. `gate wide <cmd>` (plugin/bin/gate) is allowed:
# it is the machine-locked route for a lane CI cannot run.
# Stdin: hook JSON with tool_input.command. Exit 0 = allow. Exit 2 = refuse, with a
# 1-line reason on stderr. Fails open.

re=${AGENTIC_SDLC_GATE_WIDE:-}
[ -n "$re" ] || exit 0
input=$(cat) || exit 0
cmd=$(printf '%s' "$input" | sed -n 's/.*"command"[ ]*:[ ]*"\([^"\\]*\(\\.[^"\\]*\)*\)".*/\1/p' | sed -n 1p) || exit 0
[ -n "$cmd" ] || exit 0
case $cmd in
  *bin/gate\ wide* | gate\ wide* | sh\ gate\ wide*) exit 0 ;;
esac
printf '%s\n' "$cmd" | grep -Eq -e "$re" 2>/dev/null || exit 0
printf 'agentic-sdlc wide-gate: the wide gate runs in CI (or via bin/gate wide); run your fast tests\n' >&2
exit 2
