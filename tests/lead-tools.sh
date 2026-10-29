#!/bin/sh
# tests/lead-tools.sh - the self-test of plugin/bin/cloud-worker and plugin/bin/wait-reports.
# LEAD_SH is the shell that runs each tool (default sh): run.sh passes sh, bash and
# `zsh --emulate sh` when present. A dry-run worker launches against a local bare origin, a planted
# report is found, and a planted stale branch fires the stall alarm. Prints FAIL lines; exit 0 when all pass.
# shellcheck disable=SC2015,SC2016 # ok() cannot fail, so A && ok || bad is safe; backticks are literal
set -u
root=$(cd "$(dirname "$0")/.." && pwd)
bin=$root/plugin/bin
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' INT TERM
export GIT_CONFIG_GLOBAL=/dev/null # a user push.negotiate breaks a push to a local bare repo
fail=0
ok() { :; }
bad() { fail=$((fail + 1)); printf 'FAIL [%s] %s\n' "${LEAD_SH:-sh}" "$*"; }
# shellcheck disable=SC2086 # LEAD_SH may hold flags
run() { t=$1; shift; exec ${LEAD_SH:-sh} "$bin/$t" "$@"; } # call it in a subshell

# cloud-worker: a clone of a bare origin; the gate holds characters sed and awk would mangle.
git init -q --bare "$tmp/origin.git"
git init -q "$tmp/w" && git -C "$tmp/w" -c user.name=t -c user.email=t@t commit -q --allow-empty -m base
git -C "$tmp/w" remote add origin "$tmp/origin.git" && git -C "$tmp/w" push -q origin HEAD:refs/heads/main
base=$(git -C "$tmp/w" rev-parse HEAD)
printf 'Fix the save menu.\n' > "$tmp/brief.txt"
gate='make test && echo "a|b" & \1 /x/'
out=$(cd "$tmp/w" && run cloud-worker --dry-run --gate "$gate" --gate 'sh tests/run.sh' 'o/r#7' 7-save main "$tmp/brief.txt" 2>&1)
case $out in
  "dry-run: would push $base to origin 7-save"*'Fix the save menu.'*'Repo o/r, issue #7, branch `7-save` (pushed, cut from '"$base"*"- \`$gate\`
- \`sh tests/run.sh\`"*'WORKER REPORT'*) ok ;;
  *) bad "cloud-worker --dry-run: wanted the push line, the brief and the filled tail, got: $out" ;;
esac
case $out in *@[A-Z]*@*) bad "cloud-worker --dry-run: a placeholder is left: $out" ;; esac
[ -z "$(git -C "$tmp/origin.git" for-each-ref refs/heads/7-save)" ] && ok || bad 'cloud-worker --dry-run pushed a branch'
(cd "$tmp/w" && run cloud-worker 'o/r#7' 7-save main "$tmp/brief.txt" > /dev/null 2>&1); [ "$?" = 2 ] && ok ||
  bad 'cloud-worker: no CLOUD_WORKER_START and no --dry-run should exit 2'
(cd "$tmp/w" && export CLOUD_WORKER_START="cat > '$tmp/prompt.txt'" && run cloud-worker --gate "$gate" 'o/r#7' 7-save main "$tmp/brief.txt" > /dev/null 2>&1) &&
  [ "$(git -C "$tmp/origin.git" rev-parse refs/heads/7-save)" = "$base" ] &&
  grep -qF "Push after every commit to \`7-save\`" "$tmp/prompt.txt" && ok ||
  bad "cloud-worker: should push 7-save at the base and pipe the prompt to CLOUD_WORKER_START"

# wait-reports: the stub gh reads $WR_FX/<api path with / as _>.json.
fx=$tmp/fx && mkdir "$fx" "$tmp/ghbin" && cp "$root/tests/fixtures/wait-reports/gh" "$tmp/ghbin/gh"
now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
issue() { printf '{"state":"%s","created_at":"2000-01-01T00:00:00Z"}' "$2" > "$fx/repos_o_r_issues_$1.json"; }
commit() { printf '{"sha":"%s","commit":{"committer":{"date":"%s"}}}' "$2" "$3" > "$fx/repos_o_r_commits_$1.json"; }
issue 7 open; issue 8 open; issue 9 open; issue 10 closed
printf '[{"id":1,"created_at":"2000-01-01T00:00:00Z","html_url":"u1","body":"claim"},{"id":2,"created_at":"%s","html_url":"u2","body":"WORKER REPORT head abc"}]' "$now" > "$fx/repos_o_r_issues_7_comments.json"
printf '{"body":"WORKER REPORT head abc"}' > "$fx/repos_o_r_issues_comments_2.json"
for n in 8 9 10; do echo '[]' > "$fx/repos_o_r_issues_${n}_comments.json"; done
commit old s8 2000-01-01T00:00:00Z; commit fresh s9 "$now"
printf '{"default_branch":"main"}' > "$fx/repos_o_r.json"; printf '{"ahead_by":3}' > "$fx/repos_o_r_compare_main...s8.json"
# wr runs wait-reports with a 20 s watchdog, so a missed event fails the test instead of hanging it.
wr() {
  (
    PATH=$tmp/ghbin:$PATH WR_FX=$fx WAIT_REPORTS_SEEN=$tmp/seen WAIT_REPORTS_INTERVAL=0
    export PATH WR_FX WAIT_REPORTS_SEEN WAIT_REPORTS_INTERVAL
    run wait-reports "$@"
  ) &
  p=$!
  (sleep 20; kill "$p") > /dev/null 2>&1 &
  w=$!
  wait "$p"; rc=$?
  kill "$w" 2> /dev/null
  return "$rc"
}
out=$(wr 'o/r#7' 2>&1)
[ "$out" = "o/r#7: REPORT u2
WORKER REPORT head abc" ] && ok || bad "wait-reports: should print the planted report, got: $out"
out=$(wr 'o/r#7' 'o/r#8@old' 'o/r#9@fresh' 2>&1)
case $out in
  'o/r#8: STALL silent '*' min, no report (branch old at s8)') ok ;;
  *) bad "wait-reports: only the stale branch should fire, got: $out" ;;
esac
out=$(wr --status 'o/r#7' 'o/r#8@old' 'o/r#9@fresh' 'o/r#10' 2>&1)
case $out in
  'o/r#7: reported 0 min ago
o/r#8: silent '*' min, branch old ahead 3
o/r#9: silent 0 min, branch fresh ahead ?
o/r#10: closed') ok ;;
  *) bad "wait-reports --status: got: $out" ;;
esac
out=$(wr 'o/r#10' 'o/r#7' 2>&1)
[ "$out" = "o/r#10: CLOSED" ] && ok || bad "wait-reports: a closed issue is an event once, got: $out"
wr > /dev/null 2>&1; [ "$?" = 2 ] && ok || bad 'wait-reports: no args should exit 2'
wr 'o/r#7x' > /dev/null 2>&1; [ "$?" = 2 ] && ok || bad 'wait-reports: a bad issue spec should exit 2'
[ "$fail" = 0 ]
