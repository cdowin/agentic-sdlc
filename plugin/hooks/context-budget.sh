#!/bin/sh
# context-budget.sh - agentic-sdlc Stop hook. ON by default; it only warns.
# Always-loaded docs cost context in every session. This hook warns when
# CLAUDE.md, AGENTS.md or all .claude/rules/*.md together pass their budget.
# Budgets (lines): AGENTIC_SDLC_CLAUDE_MD_MAX (200), AGENTIC_SDLC_AGENTS_MD_MAX
# (100), AGENTIC_SDLC_RULES_MAX (400). The reusable workflow context-budget.yml
# enforces the same budgets in CI.
# Stdin: hook JSON (cwd). Prints {"systemMessage": "..."} and exits 0.
# Turn off: AGENTIC_SDLC_CONTEXT_BUDGET=0.

[ "${AGENTIC_SDLC_CONTEXT_BUDGET:-1}" = 0 ] && exit 0
input=$(cat)

dir=${CLAUDE_PROJECT_DIR:-}
if [ -z "$dir" ]; then
  dir=$(printf '%s' "$input" | grep -oE '"cwd"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n 1 |
    sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/')
  [ -n "$dir" ] || dir=$PWD
  dir=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$dir")
fi
cd "$dir" 2>/dev/null || exit 0

lines() { cat "$@" 2>/dev/null | wc -l | tr -d ' '; }
over=""
check() { # name, lines, budget
  [ "$2" -gt "$3" ] && over="$over${over:+; }$1 $2/$3 lines"
  return 0
}
check CLAUDE.md "$(lines CLAUDE.md)" "${AGENTIC_SDLC_CLAUDE_MD_MAX:-200}"
check AGENTS.md "$(lines AGENTS.md)" "${AGENTIC_SDLC_AGENTS_MD_MAX:-100}"
check '.claude/rules/*.md' "$(lines .claude/rules/*.md)" "${AGENTIC_SDLC_RULES_MAX:-400}"

[ -n "$over" ] || exit 0
printf '{"systemMessage":"agentic-sdlc context-budget: over budget: %s. Trim the always-loaded docs (agent tech-writer)."}\n' "$over"
exit 0
