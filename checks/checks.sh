#!/bin/sh
# checks/checks.sh - the kit's 3 CI checks in 1 process: context-budget, test-budget, issue-link.
# The composite action checks/action.yml runs it as a step in the caller's job, so the checks
# cost no job of their own. POSIX sh; needs git, awk, sed and grep. Settings come from env vars:
#   CHECKS          the checks to run (default: all 3)
#   EVENT, ACTION   github.event_name and github.event.action
#   BODY_CHANGED    true when an `edited` event changed the PR body
#   BODY            the PR body (issue-link)
#   BASE_REF        the PR base branch (test-budget diffs origin/BASE_REF...HEAD)
#   CLAUDE_MD_MAX AGENTS_MD_MAX RULES_MAX WARN_ONLY   context-budget
#   TEST_GLOBS RATIO                                  test-budget: added lines (a PR only)
#   SUITE_MAX SUITE_RATIO                             test-budget: the suite cap (unset: no cap)
#   TEST_DATA_GLOBS TEST_DATA_MAX                     test-budget: tracked test data bytes
# Exit 1 when context-budget, issue-link, the suite cap or the test data limit fails. The per-PR
# line ratio (default 0.5) only warns. The suite cap counts the tracked text lines at HEAD:
# SUITE_MAX is the most test lines, SUITE_RATIO the most test lines per code line.
# shellcheck disable=SC2086,SC2254 # CHECKS splits into words; test globs are case patterns
set -u
CHECKS=${CHECKS:-context-budget test-budget issue-link}
EVENT=${EVENT:-} ACTION=${ACTION:-} BODY_CHANGED=${BODY_CHANGED:-false}
out=${GITHUB_STEP_SUMMARY:-/dev/null}
failed=0

pr=false
case $EVENT in pull_request | pull_request_target) pr=true ;; esac

# An `edited` PR event only re-checks the issue link, and only when the body changed.
if [ "$ACTION" = edited ]; then
  [ "$BODY_CHANGED" = true ] || { echo "PR edited, body unchanged: no check runs."; exit 0; }
  CHECKS=$(printf '%s\n' $CHECKS | grep -x issue-link || true)
fi

has() { printf '%s\n' $CHECKS | grep -qx "$1"; }

context_budget() {
  lines() { cat "$@" 2>/dev/null | wc -l | tr -d ' '; }
  level=error; [ "${WARN_ONLY:-false}" = true ] && level=warning
  over=0
  one() {
    echo "context-budget: $1 has $2 lines (budget $3)"
    if [ "$2" -gt "$3" ]; then
      echo "::$level title=context-budget::$1 has $2 lines; the budget is $3. Trim it or move detail to a doc loaded on demand."
      over=1
    fi
  }
  one CLAUDE.md "$(lines CLAUDE.md)" "${CLAUDE_MD_MAX:-200}"
  one AGENTS.md "$(lines AGENTS.md)" "${AGENTS_MD_MAX:-100}"
  # shellcheck disable=SC2046 # the glob must expand
  one '.claude/rules/*.md' "$(lines .claude/rules/*.md)" "${RULES_MAX:-400}"
  if [ "$over" = 1 ] && [ "${WARN_ONLY:-false}" != true ]; then failed=1; fi
}

TEST_GLOBS=${TEST_GLOBS:-"tests/** test/** **/*_test.* **/*.test.* **/test_*.*"}
# is_test <path>: the path matches a glob of TEST_GLOBS. ** matches any path.
is_test() {
  set -f
  for g in $TEST_GLOBS; do
    p=$(printf '%s' "$g" | sed 's#\*\*#*#g')
    case $g in '**/'*) q=${p#\*/}; case $1 in $q | */$q) set +f; return 0 ;; esac ;; esac
    case $1 in $p) set +f; return 0 ;; esac
  done
  set +f
  return 1
}
# is_code <path>: not a test and not docs. Code lines exclude *.md, docs/** and .github/**.
is_code() {
  is_test "$1" && return 1
  case $1 in *.md | docs/* | .github/*) return 1 ;; esac
  return 0
}

test_budget() {
  ratio=${RATIO:-0.5}
  if ! git diff --numstat "origin/$BASE_REF...HEAD" > "${TMPDIR:-/tmp}/checks-numstat.$$" 2>/dev/null; then
    echo "::warning title=test-budget::Cannot diff origin/$BASE_REF...HEAD. Check out with fetch-depth: 0."
    return
  fi
  tests=0 code=0
  while IFS="$(printf '\t')" read -r added _ path; do
    [ "$added" = - ] && continue
    if is_test "$path"; then tests=$((tests + added)); elif is_code "$path"; then code=$((code + added)); fi
  done < "${TMPDIR:-/tmp}/checks-numstat.$$"
  rm -f "${TMPDIR:-/tmp}/checks-numstat.$$"
  echo "test-budget: $tests test lines, $code code lines (budget $ratio test lines per code line)"
  echo "test-budget: $tests test lines, $code code lines, budget $ratio" >> "$out"
  if [ "$code" = 0 ] && [ "$tests" -gt 0 ]; then
    echo "::warning title=test-budget::$tests test lines added with 0 code lines."
  elif awk -v t="$tests" -v c="$code" -v r="$ratio" 'BEGIN { exit !(c > 0 && t / c > r) }'; then
    echo "::warning title=test-budget::$tests test lines for $code code lines is over $ratio per code line. Delete tests that cannot fail."
  fi
}

# suite: the tracked text lines at HEAD, tests against code. Over SUITE_MAX or SUITE_RATIO fails.
suite() {
  [ -n "${SUITE_MAX:-}" ] || [ -n "${SUITE_RATIO:-}" ] || return 0
  tests=0 code=0
  # git grep -c prints <path>:<lines> for each tracked text file; the count follows the last colon.
  list=${TMPDIR:-/tmp}/checks-suite.$$
  git grep -I -c '' > "$list" 2> /dev/null
  while IFS= read -r line; do
    n=${line##*:} path=${line%:*}
    if is_test "$path"; then tests=$((tests + n)); elif is_code "$path"; then code=$((code + n)); fi
  done < "$list"
  rm -f "$list"
  echo "test-budget: the suite has $tests test lines and $code code lines (cap: ${SUITE_MAX:-none} lines, ${SUITE_RATIO:-none} per code line)"
  echo "test-budget: suite $tests test lines, $code code lines" >> "$out"
  if [ -n "${SUITE_MAX:-}" ] && [ "$tests" -gt "$SUITE_MAX" ]; then
    echo "::error title=test-budget::The suite has $tests test lines; the cap is $SUITE_MAX. Delete tests by the keep rule before you add one."
    failed=1
  fi
  if [ -n "${SUITE_RATIO:-}" ] && awk -v t="$tests" -v c="$code" -v r="$SUITE_RATIO" 'BEGIN { exit !(t > 0 && (c == 0 || t / c > r)) }'; then
    echo "::error title=test-budget::The suite has $tests test lines for $code code lines; the cap is $SUITE_RATIO per code line. Delete tests by the keep rule before you add one."
    failed=1
  fi
}

# test_data: the tracked bytes at HEAD under the test data globs (goldens, snapshots, fixtures).
# A glob becomes an ERE: **/ is any directories, ** is any path, * is 1 path segment.
test_data() {
  globs=${TEST_DATA_GLOBS:-"**/goldens/** **/golden/** **/snapshots/** **/__snapshots__/** **/testdata/** **/fixtures/** **/baselines/** **/recordings/**"}
  max=${TEST_DATA_MAX:-5000000}
  # shellcheck disable=SC2016 # $ is a literal in the regex
  re=$(set -f; printf '%s\n' $globs | sed -e 's/[.+^$(){}|]/\\&/g' -e 's#\*\*/#@D@#g' -e 's#\*\*#@A@#g' \
    -e 's#\*#[^/]*#g' -e 's#@D@#(.*/)?#g' -e 's#@A@#.*#g' | paste -s -d '|' -)
  list=${TMPDIR:-/tmp}/checks-testdata.$$
  git ls-tree -r -l HEAD 2> /dev/null |
    RE="^($re)\$" awk -F '\t' '{ split($1, m, " ") } m[2] == "blob" && $2 ~ ENVIRON["RE"] { print m[4] "\t" $2 }' |
    sort -rn > "$list"
  total=$(awk -F '\t' '{ s += $1 } END { printf "%.0f", s }' "$list")
  echo "test-budget: $total bytes of test data (limit $max). Largest:"
  head -n 10 "$list" | sed 's/^/  /'
  rm -f "$list"
  echo "test-budget: $total bytes of test data, limit $max" >> "$out"
  if [ "$total" -gt "$max" ]; then
    echo "::error title=test-budget::$total bytes of test data is over the limit of $max. Keep 1 case per kind plus the edges; delete the rest."
    failed=1
  fi
}

issue_link() {
  ref='([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[0-9]+'
  if printf '%s\n' "${BODY:-}" | grep -qiE "(closes|fixes|part of) $ref|issue: none \("; then
    echo "issue-link: the PR body links an issue."
  else
    echo "::error title=issue-link::The PR body needs 'Closes #N', 'Fixes #N', 'Part of #N', 'Part of owner/repo#N' or 'Issue: none (<reason>)'."
    failed=1
  fi
}

has context-budget && context_budget
has test-budget && suite
has test-budget && test_data
if [ "$pr" = true ]; then
  has test-budget && test_budget
  has issue-link && issue_link
fi
exit "$failed"
