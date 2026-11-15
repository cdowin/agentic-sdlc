#!/bin/sh
# pin-check.sh - agentic-sdlc SessionStart hook. ON by default; it only warns.
# A pin to a tag the local marketplace clone does not have falls back to the cached version with
# no sign. This hook prints 1 line when the running plugin version differs from the v<semver> ref
# the project pins for the agentic-sdlc marketplace in .claude/settings.json. A ref that is not a
# v<semver> tag (a branch, a SHA) or no pin prints nothing.
# Stdin: hook JSON (cwd). Prints {"systemMessage": "..."} and exits 0. Fails open.
# Turn off: AGENTIC_SDLC_PIN_CHECK=0.

[ "${AGENTIC_SDLC_PIN_CHECK:-1}" = 0 ] && exit 0
input=$(cat)
root=${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}
dir=${CLAUDE_PROJECT_DIR:-}
if [ -z "$dir" ]; then
  dir=$(printf '%s' "$input" | grep -oE '"cwd"[[:space:]]*:[[:space:]]*"[^"]*"' | head -n 1 |
    sed -E 's/.*:[[:space:]]*"([^"]*)"/\1/')
  [ -n "$dir" ] || dir=$PWD
  dir=$(git -C "$dir" rev-parse --show-toplevel 2>/dev/null || printf '%s' "$dir")
fi
settings=$dir/.claude/settings.json
[ -r "$settings" ] || exit 0
# The marketplace entry is "agentic-sdlc": { "source": { ... "ref": "vX.Y.Z" } }; source holds no braces.
pin=$(tr -d '\n\r' < "$settings" |
  grep -oE '"agentic-sdlc"[[:space:]]*:[[:space:]]*\{[[:space:]]*"source"[[:space:]]*:[[:space:]]*\{[^}]*\}' |
  grep -oE '"ref"[[:space:]]*:[[:space:]]*"v[0-9]+\.[0-9]+\.[0-9]+"' | head -n 1 | sed -E 's/.*"(v[^"]*)"/\1/')
[ -n "$pin" ] || exit 0
ver=$(grep -oE '"version"[[:space:]]*:[[:space:]]*"[^"]*"' "$root/.claude-plugin/plugin.json" 2>/dev/null |
  head -n 1 | sed -E 's/.*"([^"]*)"$/\1/')
[ -n "$ver" ] || exit 0
[ "v$ver" = "$pin" ] && exit 0
printf '{"systemMessage":"agentic-sdlc: running v%s, but this repo pins %s. Run: claude plugin marketplace update agentic-sdlc, then restart."}\n' "$ver" "$pin"
exit 0
