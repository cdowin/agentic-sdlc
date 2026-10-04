#!/bin/sh
# tests/run.sh - every test of the kit. POSIX sh; needs git, awk, sed and jq.
# Each hook runs against its fixtures: an allowed input exits 0, a refused
# input exits 2 with a reason on stderr. Then structure checks on the plugin.
# Exit 0 when all pass.
# shellcheck disable=SC2015 # ok() cannot fail, so A && ok || bad is safe
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
hooks=$root/plugin/hooks
fx=$root/tests/fixtures
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM
pass=0 fail=0
ok() { pass=$((pass + 1)); }
bad() { fail=$((fail + 1)); printf 'FAIL %s\n' "$*"; }

# expect A|R <hook> <label>: the hook reads the JSON in $tmp/in.json.
expect() {
  err=$(sh "$hooks/$2" < "$tmp/in.json" 2>&1 >/dev/null)
  rc=$?
  if [ "$1" = A ]; then
    if [ "$rc" = 0 ]; then ok; else bad "$2 should allow: $3 (exit $rc: $err)"; fi
  elif [ "$rc" = 2 ] && [ -n "$err" ]; then ok
  else bad "$2 should refuse with a reason: $3 (exit $rc)"; fi
}
# bash_json <command> <cwd>: a Bash tool call; <NL> in the command is a newline.
bash_json() {
  esc=$(printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/<NL>/\\n/g')
  printf '{"tool_name":"Bash","tool_input":{"command":"%s"},"cwd":"%s"}\n' "$esc" "$2" > "$tmp/in.json"
}
# cases <hook> <file> <cwd>: run every R/A line of a cases file.
cases() {
  while IFS= read -r line; do
    case $line in '' | '#'*) continue ;; esac
    bash_json "${line#? }" "$3"
    expect "${line%% *}" "$1" "${line#? }"
  done < "$2"
}

# Scratch repos: a (with a worktree wt), b, and a plain directory.
for r in a b; do
  git init -q "$tmp/$r" && git -C "$tmp/$r" -c user.name=t -c user.email=t@t commit -q --allow-empty -m init
done
git -C "$tmp/a" worktree add -q "$tmp/wt" -b wt 2>/dev/null
mkdir -p "$tmp/plain"

# git-denylist: on by default; AGENTIC_SDLC_GIT_DENYLIST=0 turns it off.
cases git-denylist.sh "$fx/git-denylist/cases.txt" "$tmp/a"
bash_json 'git reset --hard' "$tmp/a"
export AGENTIC_SDLC_GIT_DENYLIST=0
expect A git-denylist.sh 'off when AGENTIC_SDLC_GIT_DENYLIST=0'
unset AGENTIC_SDLC_GIT_DENYLIST
printf 'not json {{{ git' > "$tmp/in.json"
expect A git-denylist.sh 'garbage input fails open'

# commit-pathspec: opt-in.
bash_json 'git commit -m x' "$tmp/a"
expect A commit-pathspec.sh 'off by default'
export AGENTIC_SDLC_COMMIT_PATHSPEC=1
cases commit-pathspec.sh "$fx/commit-pathspec/cases.txt" "$tmp/a"
touch "$(git -C "$tmp/a" rev-parse --absolute-git-dir)/MERGE_HEAD"
bash_json 'git commit -m "merge"' "$tmp/a"
expect A commit-pathspec.sh 'a commit that finishes a merge'
unset AGENTIC_SDLC_COMMIT_PATHSPEC

# write-confine: opt-in. Fixtures name @A@, @B@, @WT@ and @PLAIN@.
wc_case() {
  sed -e "s#@A@#$tmp/a#g" -e "s#@B@#$tmp/b#g" -e "s#@WT@#$tmp/wt#g" -e "s#@PLAIN@#$tmp/plain#g" \
    "$fx/write-confine/$1.json" > "$tmp/in.json"
}
wc_case refuse-other-repo
expect A write-confine.sh 'off by default'
export AGENTIC_SDLC_WRITE_CONFINE=1
for f in "$fx"/write-confine/*.json; do
  name=$(basename "$f" .json)
  wc_case "$name"
  case $name in allow-*) expect A write-confine.sh "$name" ;; *) expect R write-confine.sh "$name" ;; esac
done
wc_case refuse-other-repo
AGENTIC_SDLC_WRITE_ROOTS="/x:$(git -C "$tmp/b" rev-parse --show-toplevel)"
export AGENTIC_SDLC_WRITE_ROOTS
expect A write-confine.sh 'a root in AGENTIC_SDLC_WRITE_ROOTS'
unset AGENTIC_SDLC_WRITE_ROOTS
unset AGENTIC_SDLC_WRITE_CONFINE

# context-budget: warns through systemMessage, never blocks.
budget() { # dir -> stdout of the hook, with small budgets
  CLAUDE_PROJECT_DIR=$1 AGENTIC_SDLC_CLAUDE_MD_MAX=3 AGENTIC_SDLC_AGENTS_MD_MAX=2 AGENTIC_SDLC_RULES_MAX=4 \
    sh "$hooks/context-budget.sh" < "$fx/context-budget/stop.json"
}
out=$(budget "$fx/context-budget/over")
rc=$?
case $out in
  *'"systemMessage"'*'CLAUDE.md 5/3'*'AGENTS.md 3/2'*'rules/*.md 5/4'*) [ "$rc" = 0 ] && ok || bad "context-budget over: exit $rc" ;;
  *) bad "context-budget over: wanted a systemMessage naming 3 files, got: $out" ;;
esac
printf '%s' "$out" | jq -e .systemMessage >/dev/null 2>&1 && ok || bad "context-budget over: stdout is not JSON"
out=$(budget "$fx/context-budget/under")
[ -z "$out" ] && ok || bad "context-budget under: wanted no output, got: $out"

# Structure.
for f in "$hooks"/*.sh "$root/tests/run.sh"; do
  sh -n "$f" && ok || bad "sh -n $f"
  if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -s sh "$f" && ok || bad "shellcheck $f"
  fi
done
for f in "$root/.claude-plugin/marketplace.json" "$root/plugin/.claude-plugin/plugin.json" "$hooks/hooks.json"; do
  jq -e . "$f" >/dev/null && ok || bad "invalid JSON: $f"
done
for s in $(jq -r '.. | .command? // empty' "$hooks/hooks.json" | sed -n 's#.*/hooks/\([a-z-]*\.sh\).*#\1#p'); do
  [ -f "$hooks/$s" ] && ok || bad "hooks.json names a missing script: $s"
done
for f in "$root"/plugin/agents/*.md; do
  n=$(basename "$f" .md)
  sed -n '2,/^---$/p' "$f" | grep -qx "name: $n" && ok || bad "$f: frontmatter name is not $n"
  sed -n '2,/^---$/p' "$f" | grep -qE '^model: (haiku|sonnet|opus)$' && ok || bad "$f: no model: line"
done
v=$(jq -r .version "$root/plugin/.claude-plugin/plugin.json")
[ "$(jq -r '.plugins[0].version' "$root/.claude-plugin/marketplace.json")" = "$v" ] && ok || bad "marketplace and plugin versions differ"
for f in plugin/skills/agents-and-models/SKILL.md codex/AGENTS.md codex/README.md; do
  grep -q "v$v" "$root/$f" && ! grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' "$root/$f" | grep -vqx "v$v" && ok ||
    bad "$f must pin the plugin version v$v and no other"
done

printf '%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
