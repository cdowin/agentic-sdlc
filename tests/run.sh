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
for f in plugin/skills/agents-and-models/SKILL.md codex/AGENTS.md README.md; do
  grep -q "v$v" "$root/$f" && ! grep -oE 'v[0-9]+\.[0-9]+\.[0-9]+' "$root/$f" | grep -vqx "v$v" && ok ||
    bad "$f must pin the plugin version v$v and no other"
done

# checks/checks.sh: the 3 CI checks. chk <want-exit> <label> [VAR=value ...] runs it in $tmp/c.
git init -q "$tmp/c" && printf 'a\nb\nc\n' > "$tmp/c/CLAUDE.md"
git -C "$tmp/c" add . && git -C "$tmp/c" -c user.name=t -c user.email=t@t commit -q -m base
git -C "$tmp/c" update-ref refs/remotes/origin/main HEAD
mkdir "$tmp/c/tests" && seq 1 9 > "$tmp/c/tests/t.sh"
git -C "$tmp/c" add . && git -C "$tmp/c" -c user.name=t -c user.email=t@t commit -q -m tests
chk() {
  want=$1 label=$2; shift 2
  got=$(cd "$tmp/c" && env -i PATH="$PATH" EVENT=pull_request BASE_REF=main BODY='Closes #1' "$@" \
    sh "$root/checks/checks.sh" > "$tmp/chk.out" 2>&1; echo $?)
  [ "$got" = "$want" ] && ok || bad "checks.sh: $label (exit $got, want $want)"
}
chk 0 'all pass'
chk 1 'CLAUDE.md over budget fails' CLAUDE_MD_MAX=2
chk 0 'warn_only does not fail' CLAUDE_MD_MAX=2 WARN_ONLY=true
chk 1 'no issue link fails' BODY='no link'
chk 0 'Issue: none passes' BODY='Issue: none (hotfix). Intent: x.'
chk 0 'push skips issue-link' EVENT=push BODY=''
chk 0 'edited, body unchanged: nothing runs' ACTION=edited BODY='' CLAUDE_MD_MAX=2
chk 1 'edited, body changed: issue-link runs' ACTION=edited BODY_CHANGED=true BODY=''
chk 0 'edited runs only issue-link' ACTION=edited BODY_CHANGED=true CLAUDE_MD_MAX=2
chk 0 'test-budget only warns' CHECKS=test-budget
grep -q 'title=test-budget::9 test lines added with 0 code lines' "$tmp/chk.out" && ok ||
  bad 'checks.sh: test-budget warns on tests with 0 code lines'

# plugin/workflows/*.js: syntax only, no fixtures. A workflow starts with `export const meta` and
# its body may use top-level await and return, so no single node flag parses it. The check strips
# `export `, wraps the file in an async function and runs `node --check` on the copy.
# It also requires line 1 to open the meta literal. The check skips when node is absent.
if command -v node > /dev/null 2>&1; then
  for f in "$root"/plugin/workflows/*.js; do
    [ -f "$f" ] || continue
    head -n 1 "$f" | grep -q '^export const meta = {' && ok || bad "$f: must begin with export const meta = {"
    { printf '(async () => {\n'; sed 's/^export //' "$f"; printf '\n})\n'; } > "$tmp/wf.js"
    node --check "$tmp/wf.js" 2> "$tmp/wf.err" && ok || bad "$f: syntax error: $(head -n 3 "$tmp/wf.err")"
  done
fi

# plugin/contract: the shared SDLC contract. jq parses the 2 JSON files. With node: each fixture
# <shape>.ok*.json is valid and each <shape>.bad-*.json is not (judged at a fixed time, against the
# claim comments in claim-comments.json); each runtime profile is valid and lists its guesses;
# --graph, --ids and --repo work; tests/workflows.js pins the workflows to the contract.
contract=$root/plugin/contract
for f in "$contract/sdlc.schema.json" "$contract/runtimes.json"; do
  jq -e . "$f" >/dev/null && ok || bad "invalid JSON: $f"
done
if command -v node > /dev/null 2>&1; then
  chk_contract() { node "$contract/check.js" "$@"; }
  for f in "$fx"/contract/*.ok*.json "$fx"/contract/*.bad-*.json; do
    name=$(basename "$f" .json)
    out=$(chk_contract "${name%%.*}" "$f" --now 2026-10-09T00:00:00Z --claims "$fx/contract/claim-comments.json")
    rc=$?
    case $name in
      *.bad-*) [ "$rc" = 1 ] && [ -n "$out" ] && ok || bad "check.js should refuse $name (exit $rc)" ;;
      *) [ "$rc" = 0 ] && ok || bad "check.js should accept $name: $out" ;;
    esac
  done
  for p in $(jq -r 'keys[]' "$contract/runtimes.json"); do
    out=$(jq ".$p" "$contract/runtimes.json" | chk_contract runtime -) && ok || bad "runtimes.json $p: $out"
  done
  out=$(jq .codex "$contract/runtimes.json" | chk_contract runtime -)
  [ -z "$out" ] && ok || bad "Codex profile should have no unverified values: $out"
  jq '.codex | .tiers.bounded.verified = false' "$contract/runtimes.json" | chk_contract runtime - | grep -q '^unverified: tiers.bounded: ' && ok ||
    bad 'check.js runtime: should list an explicitly unverified tier'

  # --graph: the graph's rework_limit bounds the round. --ids: the review scores each result.
  jq '.rework_limit = 1' "$fx/contract/graph.ok.json" > "$tmp/g1.json"
  jq '.round = 1' "$fx/contract/report.ok.json" | chk_contract report - --graph "$tmp/g1.json" > /dev/null && ok ||
    bad 'check.js --graph: round 1 within rework_limit 1 should pass'
  jq '.round = 2' "$fx/contract/report.ok.json" | chk_contract report - --graph "$tmp/g1.json" > /dev/null &&
    bad 'check.js --graph: round 2 over rework_limit 1 should fail' || ok
  chk_contract review "$fx/contract/review.ok.json" --ids read,write > /dev/null && ok || bad 'check.js --ids: the full batch should pass'
  chk_contract review "$fx/contract/review.ok.json" --ids read,write,load > /dev/null && bad 'check.js --ids: an unscored result should fail' || ok
  chk_contract review "$fx/contract/review.ok.json" --ids read > /dev/null && bad 'check.js --ids: a score outside the batch should fail' || ok

  # needs: a claim of a task that needs a capability fails for a runtime that lacks it.
  jq '.tasks[0].needs = ["image_generation"]' "$fx/contract/graph.ok.json" > "$tmp/gneeds.json"
  jq '.claude | .provider = "has-art" | .capabilities.image_generation = {status: "enforced", evidence: "test"}' \
    "$contract/runtimes.json" > "$tmp/rt-art.json"
  jq .claude "$contract/runtimes.json" > "$tmp/rt-claude.json"
  chk_contract claim "$fx/contract/claim.ok-first.json" --graph "$tmp/gneeds.json" --runtime "$tmp/rt-claude.json" > /dev/null &&
    bad 'check.js --runtime: a claim by a runtime without a needed capability should fail' || ok
  chk_contract claim "$fx/contract/claim.ok-first.json" --graph "$tmp/gneeds.json" --runtime "$tmp/rt-art.json" > /dev/null && ok ||
    bad 'check.js --runtime: a claim by a runtime with the capability should pass'
  chk_contract claim "$fx/contract/claim.ok-first.json" --graph "$fx/contract/graph.ok.json" --runtime "$tmp/rt-claude.json" > /dev/null && ok ||
    bad 'check.js --runtime: a task with no needs is open to any runtime'

  # --repo: a report SHA must be the remote branch head; a takeover needs a quiet branch.
  git init -q --bare "$tmp/remote.git" && git -C "$tmp/b" remote add origin "$tmp/remote.git"
  git -C "$tmp/b" push -q origin HEAD:refs/heads/t1
  remote_report() { # <branch> <sha> -> exit of check.js report --repo
    jq --arg b "$1" --arg s "$2" '.branch = $b | .sha = $s' "$fx/contract/report.ok.json" |
      chk_contract report - --repo "$tmp/b" > /dev/null
  }
  first=$(git -C "$tmp/b" rev-parse HEAD)
  remote_report t1 "$first" && ok || bad 'check.js --repo: the remote head should pass'
  git -C "$tmp/b" -c user.name=t -c user.email=t@t commit -q --allow-empty -m local
  second=$(git -C "$tmp/b" rev-parse HEAD)
  remote_report t1 "$second" && bad 'check.js --repo: an unpushed SHA should fail' || ok
  git -C "$tmp/b" push -q origin HEAD:refs/heads/t1
  remote_report t1 "$first" && bad 'check.js --repo: an SHA behind the remote head should fail' || ok
  remote_report gone "$second" && bad 'check.js --repo: a missing branch should fail' || ok
  jq '[.[] | .created_at = "2000-01-01T00:00:00Z"]' "$fx/contract/claim-comments.json" > "$tmp/old-claims.json"
  takeover() { # [--now <time>] -> exit of check.js claim --repo for a takeover of t1 at its head
    jq --arg s "$second" '.branch = "t1" | .resume_sha = $s | .at = "2000-01-02T00:00:00Z"' "$fx/contract/claim.ok.json" |
      chk_contract claim - --repo "$tmp/b" --claims "$tmp/old-claims.json" "$@" > /dev/null
  }
  takeover && bad 'check.js claim: a takeover of a branch with a fresh commit should fail' || ok
  takeover --now 2100-01-01T00:00:00Z && ok || bad 'check.js claim: a takeover of a quiet branch should pass'
  node "$root/tests/workflows.js" > "$tmp/wf.out" && ok || bad "tests/workflows.js: $(grep FAIL "$tmp/wf.out")"
fi

if command -v node > /dev/null 2>&1; then
  node "$root/tests/codex-adapter.js" > "$tmp/adapter.out" 2>&1 && ok || bad "Codex adapter: $(tail -n 6 "$tmp/adapter.out")"
fi

printf '%s passed, %s failed\n' "$pass" "$fail"
[ "$fail" = 0 ]
