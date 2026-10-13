#!/bin/sh
# checks/checks.sh - the kit's 4 CI checks in 1 process: context-budget, test-budget, issue-link, comment-budget.
# The composite action checks/action.yml runs it as a step in the caller's job, so the checks
# cost no job of their own. POSIX sh; needs git, awk, sed and grep. Settings come from env vars:
#   CHECKS          the checks to run (default: all 4)
#   EVENT, ACTION   github.event_name and github.event.action
#   BODY_CHANGED    true when an `edited` event changed the PR body
#   BODY            the PR body (issue-link)
#   BASE_REF        the PR base branch (test-budget diffs origin/BASE_REF...HEAD)
#   CLAUDE_MD_MAX AGENTS_MD_MAX RULES_MAX WARN_ONLY   context-budget
#                   context-budget counts root CLAUDE.md, AGENTS.md and .claude/rules only.
#   TEST_GLOBS RATIO                                  test-budget: added lines (a PR only)
#   SUITE_MAX SUITE_RATIO                             test-budget: the suite cap (unset: no cap)
#   SUITE_WARN_RATIO                                  test-budget: test lines per code line that warn (SUITE_RATIO fails)
#   CODE_GLOBS                                        test-budget, comment-budget: code is a match of these globs
#                   that is not a test (default empty: every file that is not a test or docs)
#   TEST_DATA_GLOBS TEST_DATA_MAX                     test-budget: tracked test data bytes
#   COMMENT_RATIO COMMENT_WARN_RATIO                  comment-budget: comment lines per code line (limit fails, warning warns)
#   TEST_COMMENT_RATIO TEST_COMMENT_WARN_RATIO        comment-budget: comment lines per test line
# Exit 1 when context-budget, issue-link, the suite cap or the test data limit fails. The per-PR
# line ratio (default 0.5) only warns. The suite cap counts the tracked text lines at HEAD:
# SUITE_MAX is the most test lines, SUITE_RATIO the most test lines per code line.
# shellcheck disable=SC2086,SC2254 # CHECKS splits into words; test globs are case patterns
set -u
CHECKS=${CHECKS:-context-budget test-budget issue-link comment-budget}
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
# CLASSIFY_AWK: the awk functions that classify a path. It turns TEST_GLOBS into regexes once (BEGIN).
# ** and * both match any characters, / included, as a case pattern does; ? matches 1 character.
# A glob that starts with **/ also matches at the root. A test is a TEST_GLOBS match; code is neither a test nor
# docs (*.md, docs/** and .github/**). With CODE_GLOBS set, code is a match of CODE_GLOBS that is not a
# test (docs are not excluded then). Callers add a main rule that calls classify(path, lines).
CLASSIFY_AWK='
function rx(g,   out, i, c) {
  gsub(/\*\*/, "*", g)
  out = ""
  for (i = 1; i <= length(g); i++) {
    c = substr(g, i, 1)
    if (c == "*") out = out ".*"
    else if (c == "?") out = out "."
    else if (c ~ /[][\\.^$(){}+|]/) out = out "\\" c
    else out = out c
  }
  return out
}
function globrx(g,   q) {
  if (substr(g, 1, 3) == "**/") {
    q = rx(g)
    sub(/^\.\*\//, "", q)
    return "^(" q "|.*/" q ")$"
  }
  return "^" rx(g) "$"
}
BEGIN {
  n = split(ENVIRON["TEST_GLOBS"], globs, " ")
  for (i = 1; i <= n; i++) pat[i] = globrx(globs[i])
  nc = split(ENVIRON["CODE_GLOBS"], globs, " ")
  for (i = 1; i <= nc; i++) cpat[i] = globrx(globs[i])
  tests = 0; code = 0
}
# classify sets kind to t (test), c (code) or empty (docs, or not under CODE_GLOBS).
function classify(path, lines,   i, hit) {
  kind = ""
  for (i = 1; i <= n; i++) if (path ~ pat[i]) { tests += lines; kind = "t"; return }
  if (nc > 0) {
    hit = 0
    for (i = 1; i <= nc; i++) if (path ~ cpat[i]) hit = 1
    if (!hit) return
  } else if (path ~ /\.md$/ || path ~ /^docs\// || path ~ /^\.github\//) return
  code += lines; kind = "c"
}
'

test_budget() {
  ratio=${RATIO:-0.5}
  if ! git diff --numstat "origin/$BASE_REF...HEAD" > "${TMPDIR:-/tmp}/checks-numstat.$$" 2>/dev/null; then
    echo "::warning title=test-budget::Cannot diff origin/$BASE_REF...HEAD. Check out with fetch-depth: 0."
    return
  fi
  # numstat is <added> TAB <deleted> TAB <path>; a binary file adds "-".
  counts=$(TEST_GLOBS=$TEST_GLOBS CODE_GLOBS=${CODE_GLOBS:-} awk -F'\t' "$CLASSIFY_AWK"'
    $1 != "-" { p = $0; sub(/^[^\t]*\t[^\t]*\t/, "", p); classify(p, $1 + 0) }
    END { print tests, code }' "${TMPDIR:-/tmp}/checks-numstat.$$")
  rm -f "${TMPDIR:-/tmp}/checks-numstat.$$"
  tests=${counts% *} code=${counts#* }
  echo "test-budget: $tests test lines, $code code lines (budget $ratio test lines per code line)"
  echo "test-budget: $tests test lines, $code code lines, budget $ratio" >> "$out"
  if [ "$code" = 0 ] && [ "$tests" -gt 0 ]; then
    echo "::warning title=test-budget::$tests test lines added with 0 code lines."
  elif awk -v t="$tests" -v c="$code" -v r="$ratio" 'BEGIN { exit !(c > 0 && t / c > r) }'; then
    echo "::warning title=test-budget::$tests test lines for $code code lines is over $ratio per code line. Delete tests that cannot fail."
  fi
}

# ratio_ok CHECK VAR VALUE: VALUE is a non-negative decimal. A bad one is an error and fails the run.
ratio_ok() {
  awk -v r="$3" 'BEGIN { exit !(r ~ /^[0-9]+(\.[0-9]+)?$/ || r ~ /^\.[0-9]+$/) }' && return 0
  echo "::error title=$1::$2 is '$3', not a number."
  failed=1
  return 1
}

# suite: the tracked text lines at HEAD, tests against code. Over SUITE_MAX or SUITE_RATIO fails.
suite() {
  [ -n "${SUITE_MAX:-}" ] || [ -n "${SUITE_RATIO:-}" ] || [ -n "${SUITE_WARN_RATIO:-}" ] || return 0
  case ${SUITE_MAX:-0} in *[!0-9]*) echo "::error title=test-budget::SUITE_MAX is '$SUITE_MAX', not a whole number."; failed=1; return ;; esac
  [ -z "${SUITE_RATIO:-}" ] || ratio_ok test-budget SUITE_RATIO "$SUITE_RATIO" || return
  [ -z "${SUITE_WARN_RATIO:-}" ] || ratio_ok test-budget SUITE_WARN_RATIO "$SUITE_WARN_RATIO" || return
  tests=0 code=0
  # git grep -c prints <path>:<lines> for each tracked text file; the count follows the last colon.
  # core.quotePath=false keeps a non-ASCII path as it is, so the test globs match it.
  list=${TMPDIR:-/tmp}/checks-suite.$$
  # Exit 1 is no text file at all; above 1 is an error.
  git -c core.quotePath=false grep -I -c '' > "$list" 2> /dev/null
  if [ $? -gt 1 ]; then
    rm -f "$list"
    echo "::error title=test-budget::git grep cannot count the suite lines. Run the check in a git checkout."
    failed=1
    return
  fi
  # The count follows the last colon; the path is all before it.
  counts=$(TEST_GLOBS=$TEST_GLOBS CODE_GLOBS=${CODE_GLOBS:-} awk "$CLASSIFY_AWK"'
    { i = match($0, /:[0-9]*$/); if (i) classify(substr($0, 1, i - 1), substr($0, i + 1) + 0) }
    END { print tests, code }' "$list")
  rm -f "$list"
  tests=${counts% *} code=${counts#* }
  echo "test-budget: the suite has $tests test lines and $code code lines (cap: ${SUITE_MAX:-none} lines, ${SUITE_RATIO:-none} per code line)"
  echo "test-budget: suite $tests test lines, $code code lines" >> "$out"
  if [ -n "${SUITE_MAX:-}" ] && [ "$tests" -gt "$SUITE_MAX" ]; then
    echo "::error title=test-budget::The suite has $tests test lines; the cap is $SUITE_MAX. Delete tests by the keep rule before you add one."
    failed=1
  fi
  if [ -n "${SUITE_RATIO:-}" ] && over_ratio "$tests" "$code" "$SUITE_RATIO"; then
    echo "::error title=test-budget::The suite has $tests test lines for $code code lines; the cap is $SUITE_RATIO per code line. Delete tests by the keep rule before you add one."
    failed=1
  elif [ -n "${SUITE_WARN_RATIO:-}" ] && over_ratio "$tests" "$code" "$SUITE_WARN_RATIO"; then
    echo "::warning title=test-budget::The suite has $tests test lines for $code code lines; the warning level is $SUITE_WARN_RATIO per code line. Delete tests by the keep rule before you add one."
  fi
}

# Comment markers: a comment line starts (after blanks) with the marker of its file extension.
# Add an extension to one of these lists. A `#!` line is a shebang, not a comment.
HASH_EXT='*.sh *.bash *.py *.gd *.rb *.yml *.yaml *.toml'
SLASH_EXT='*.js *.ts *.mjs *.cjs *.jsx *.tsx *.c *.h *.cpp *.go *.java *.rs *.swift *.kt *.cs'

# over_ratio NUM DEN LIMIT: true when NUM > 0 and (DEN is 0 or NUM / DEN > LIMIT), as in suite().
over_ratio() { awk -v t="$1" -v c="$2" -v r="$3" 'BEGIN { exit !(t > 0 && (c == 0 || t / c > r)) }'; }

# comment_one KIND COMMENTS BASE LIMIT_VAR WARN_VAR: fail over the limit, warn over the warning level.
comment_one() {
  eval "limit=\${$4:-} warn=\${$5:-}"
  if [ -n "$limit" ] && over_ratio "$2" "$3" "$limit"; then
    echo "::error title=comment-budget::$2 comment lines in $3 $1 lines; the limit is $limit per line. Delete comments that restate the code."
    failed=1
  elif [ -n "$warn" ] && over_ratio "$2" "$3" "$warn"; then
    echo "::warning title=comment-budget::$2 comment lines in $3 $1 lines; the warning level is $warn per line. Delete comments that restate the code."
  fi
}

# comment_budget: comment lines in code files per code line, and in test files per test line.
comment_budget() {
  [ -n "${COMMENT_RATIO:-}${COMMENT_WARN_RATIO:-}${TEST_COMMENT_RATIO:-}${TEST_COMMENT_WARN_RATIO:-}" ] || return 0
  bad=0
  for v in COMMENT_RATIO COMMENT_WARN_RATIO TEST_COMMENT_RATIO TEST_COMMENT_WARN_RATIO; do
    eval "val=\${$v:-}"
    [ -z "$val" ] || ratio_ok comment-budget "$v" "$val" || bad=1
  done
  [ "$bad" = 0 ] || return 0
  lines=${TMPDIR:-/tmp}/checks-lines.$$ marks=${TMPDIR:-/tmp}/checks-marks.$$
  git -c core.quotePath=false grep -I -c '' > "$lines" 2> /dev/null
  if [ $? -gt 1 ]; then
    rm -f "$lines"
    echo "::error title=comment-budget::git grep cannot count the lines. Run the check in a git checkout."
    failed=1
    return
  fi
  # shellcheck disable=SC2016 # the regex is for grep
  {
    (set -f; git -c core.quotePath=false grep -I -c -E '^[[:space:]]*#([^!]|$)' -- $HASH_EXT 2> /dev/null)
    (set -f; git -c core.quotePath=false grep -I -c -E '^[[:space:]]*//' -- $SLASH_EXT 2> /dev/null)
  } > "$marks"
  counts=$(TEST_GLOBS=$TEST_GLOBS CODE_GLOBS=${CODE_GLOBS:-} awk "$CLASSIFY_AWK"'
    { i = match($0, /:[0-9]*$/); if (!i) next; p = substr($0, 1, i - 1); k = substr($0, i + 1) + 0 }
    FILENAME == ARGV[1] { classify(p, k); next }
    { classify(p, 0); if (kind == "t") ct += k; else if (kind == "c") cc += k }
    END { print tests, code, ct + 0, cc + 0 }' "$lines" "$marks")
  rm -f "$lines" "$marks"
  set -- $counts
  tests=$1 code=$2 tcom=$3 ccom=$4
  echo "comment-budget: $ccom comment lines in $code code lines, $tcom comment lines in $tests test lines"
  echo "comment-budget: $ccom comment lines in $code code lines, $tcom comment lines in $tests test lines" >> "$out"
  comment_one code "$ccom" "$code" COMMENT_RATIO COMMENT_WARN_RATIO
  comment_one test "$tcom" "$tests" TEST_COMMENT_RATIO TEST_COMMENT_WARN_RATIO
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
has comment-budget && comment_budget
if [ "$pr" = true ]; then
  has test-budget && test_budget
  has issue-link && issue_link
fi
exit "$failed"
