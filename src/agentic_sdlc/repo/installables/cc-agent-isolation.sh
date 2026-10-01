#!/usr/bin/env bash
# cc-agent-isolation.sh — Claude Code PreToolUse hook (matcher `Agent|Task`):
# refuse a subagent dispatch that asks the harness for `isolation: "worktree"`.
# The harness bases that worktree on the default branch, not the milestone's
# declared `branch:`, and writes no scope marker, so the agent builds on the
# wrong base where no guard knows it is an agent. The one mechanism is
# tools/dev/agent-worktree.sh, run by the agent itself; every other dispatch
# passes untouched. `bash cc-agent-isolation.sh --self-test` replays the
# dispatch corpus. Stdin: the PreToolUse JSON (tool_name, tool_input.isolation).
# Exit 0 = allow, 2 = block; failures exit 0.
set -eu
trap 'exit 0' ERR

# hook_json_field <payload> <dotted.key> — echo a STRING field, or nothing.
# Inline, and a real JSON parser: a prompt embeds escaped quotes, which a grep
# extractor truncates at.
hook_json_field() {
	local payload="$1" key="$2"
	if command -v python3 >/dev/null 2>&1; then
		printf '%s' "$payload" | python3 -c '
import json, sys
try:
	node = json.load(sys.stdin)
except Exception:
	sys.exit(0)
for part in sys.argv[1].split("."):
	if not isinstance(node, dict) or part not in node:
		sys.exit(0)
	node = node[part]
if isinstance(node, str):
	sys.stdout.write(node)
' "$key" 2>/dev/null || true
	elif command -v jq >/dev/null 2>&1; then
		printf '%s' "$payload" \
			| jq -r --arg k "$key" 'getpath($k | split(".")) | select(type == "string")' 2>/dev/null || true
	fi
}

# --- --self-test — the dispatch corpus ----------------------------------------
HOOK_NAME="cc-agent-isolation.sh"

# case <want exit> <label> <payload> — a block must also name the worktree tool.
self_test_case() {
	local want="$1" label="$2" out rc=0 miss="" hook_path sandbox
	hook_path="$(cd "$(dirname "$0")" && pwd -P)/$(basename "$0")"
	sandbox="$(mktemp -d "${TMPDIR:-/tmp}/cc-agent-isolation.XXXXXX")" || return 1
	out="$(printf '%s' "$3" | (cd "$sandbox" && bash "$hook_path") 2>&1)" || rc=$?
	rm -rf "$sandbox"
	if [ "$rc" != "$want" ]; then
		miss="wanted exit $want, got $rc"
	elif [ "$want" = 2 ]; then
		case "$out" in
			*"tools/dev/agent-worktree.sh new"*) ;;
			*) miss="blocked without naming tools/dev/agent-worktree.sh" ;;
		esac
	fi
	[ -n "$miss" ] || return 0
	printf '  MISS — %s: %s\n    %s\n' "$label" "$miss" "${out//$'\n'/ | }" >&2
	return 1
}

self_test() {
	local rc=0
	if ! command -v python3 >/dev/null 2>&1 && ! command -v jq >/dev/null 2>&1; then
		echo "[$HOOK_NAME] SELF-TEST FAIL — neither python3 nor jq is on PATH, so this guard reads no payload and guards nothing" >&2
		return 1
	fi
	self_test_case 2 'an Agent dispatch asking for a harness worktree' \
		'{"tool_name":"Agent","tool_input":{"subagent_type":"developer","prompt":"build it","isolation":"worktree"}}' || rc=1
	self_test_case 2 'the same dispatch under the older Task name' \
		'{"tool_name":"Task","tool_input":{"prompt":"build it","isolation":"worktree"}}' || rc=1
	self_test_case 0 'an Agent dispatch with no isolation' \
		'{"tool_name":"Agent","tool_input":{"subagent_type":"developer","prompt":"run bash tools/dev/agent-worktree.sh new x"}}' || rc=1
	self_test_case 0 'a prompt that merely MENTIONS isolation: worktree' \
		'{"tool_name":"Agent","tool_input":{"prompt":"never pass \"isolation\": \"worktree\""}}' || rc=1
	self_test_case 0 'a Bash call is not a dispatch' \
		'{"tool_name":"Bash","tool_input":{"command":"echo isolation","isolation":"worktree"}}' || rc=1

	if [ "$rc" -eq 0 ]; then
		echo "[$HOOK_NAME] SELF-TEST OK — a harness worktree is refused under either tool name, naming tools/dev/agent-worktree.sh; every other dispatch passes"
	else
		echo "[$HOOK_NAME] SELF-TEST FAIL — see the case(s) above" >&2
	fi
	return "$rc"
}

if [ "${1:-}" = "--self-test" ]; then
	# Through `||`, so the fail-open ERR trap cannot turn a self-test failure into exit 0.
	self_test_rc=0
	self_test || self_test_rc=$?
	exit "$self_test_rc"
fi

# --- the hook -----------------------------------------------------------------
INPUT="$(cat)"

# Fast path: pure shell for payloads that cannot be an agent dispatch.
case "$INPUT" in
	*isolation*|*'"tool_name"'*) ;;
	*) exit 0 ;;
esac

case "$(hook_json_field "$INPUT" tool_name)" in
	Agent|Task) ;;
	*) exit 0 ;;
esac

# A declared project guard is evaluated before any subagent starts. The stamp
# is accepted only as a complete line and only with the grain-id alphabet.
if [ -f Makefile ]; then
	PROMPT="$(hook_json_field "$INPUT" tool_input.prompt)"
	GRAIN="$(printf '%s' "$PROMPT" | python3 -c '
import re, sys
text = sys.stdin.read()
match = re.search(r"(?m)^GDK-STAMP grain=([A-Za-z0-9._/-]+)(?: issue=[A-Za-z0-9][A-Za-z0-9._+-]*)*$", text)
if match:
    print(match.group(1))
' 2>/dev/null || true)"
	GUARD_ARGS="dispatch --preflight"
	if [ -n "$GRAIN" ]; then
		GUARD_ARGS="$GUARD_ARGS --grain $GRAIN"
	fi
	if ! GUARD_OUT="$(make -s sdlc ARGS="$GUARD_ARGS" 2>&1)"; then
		{
			echo "BLOCKED (dispatch guard): this project refused to start the agent."
			printf '  %s\n' "$GUARD_OUT"
		} >&2
		exit 2
	fi
elif [ -f devkit.toml ] && awk '
	/^[[:space:]]*#/ { next }
	/^[[:space:]]*\[/ {
		in_dispatch = ($0 ~ /^[[:space:]]*\[dispatch\][[:space:]]*(#.*)?$/)
		next
	}
	in_dispatch && /^[[:space:]]*guard[[:space:]]*=[[:space:]]*true[[:space:]]*(#.*)?$/ { enabled = 1 }
	END { exit !enabled }
' devkit.toml; then
	{
		echo "BLOCKED (dispatch guard): [dispatch] guard = true, but this project has no Makefile."
		echo "  Add a Makefile with an 'sdlc' target so the dispatch preflight can run."
	} >&2
	exit 2
fi

[ "$(hook_json_field "$INPUT" tool_input.isolation)" = "worktree" ] || exit 0

{
	echo "BLOCKED (agent isolation): this dispatch asks the harness for \`isolation: \"worktree\"\`."
	echo "  The harness bases that worktree on the default branch, not the milestone's"
	echo "  declared \`branch:\`, and writes no scope marker — so the agent builds on the"
	echo "  wrong base, and no guard knows an agent is working there."
	echo ""
	echo "  Instead: dispatch WITHOUT \`isolation\`, and have the agent run"
	echo "    bash tools/dev/agent-worktree.sh new <slug>"
	echo "  first — it bases on the milestone's declared \`branch:\` and writes the marker —"
	echo "  then build, commit by pathspec, merge its branch back, and finish with"
	echo "    bash tools/dev/agent-worktree.sh done <slug>"
} >&2
exit 2
