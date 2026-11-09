#!/bin/sh
# review-due and fix-attempt against a stub gh that reads and writes files in $S.
S=$(mktemp -d) || exit 1; trap 'rm -rf "$S"' EXIT
root=$(cd "$(dirname "$0")/.." && pwd); mkdir "$S/bin"
cat > "$S/bin/gh" <<'STUB'
#!/bin/sh
for a in "$@"; do q=$prev_q; prev_q=$a; [ "$q" = -q ] && expr=$a; done
case "$1 $2" in
  "issue list") jq -r "$expr" "$S/issues.json" ;;
  "pr list") jq -r "$expr" "$S/prs.json" ;;
  "pr view") case $* in *comments*) f=comments ;; *) f=checks ;; esac; jq -r "$expr" "$S/$f.json" ;;
  "pr comment") while [ "$#" -gt 1 ]; do [ "$1" = --body ] && b=$2; shift; done
    jq --arg b "$b" '.comments += [{body: $b}]' "$S/comments.json" > "$S/c.new" && mv "$S/c.new" "$S/comments.json" ;;
esac
STUB
chmod +x "$S/bin/gh"
export S; run() { env PATH="$S/bin:$PATH" "$@"; }
fail=0; chk() { [ "$2" = "$3" ] || { echo "FAIL $1: wanted [$2], got [$3]"; fail=1; }; }
# review-due: 3 PRs after the newest spin (the 2nd spin), 1 older spin, 1 non-spin issue.
echo '[{"title":"Review spin: a","closedAt":"2026-01-01T00:00:00Z"},{"title":"Review spin: b","closedAt":"2026-02-01T00:00:00Z"},{"title":"Fix x","closedAt":"2026-03-01T00:00:00Z"}]' > "$S/issues.json"
echo '[{"mergedAt":"2026-01-15T00:00:00Z"},{"mergedAt":"2026-02-02T00:00:00Z"},{"mergedAt":"2026-02-03T00:00:00Z"},{"mergedAt":"2026-02-04T00:00:00Z"}]' > "$S/prs.json"
chk "below threshold" "PRs since the last spin: 3" "$(run sh "$root/plugin/bin/review-due" o/r main)"
out=$(run env REVIEW_DUE_EVERY=3 sh "$root/plugin/bin/review-due" o/r main)
chk "at threshold" "REVIEW DUE" "$(printf '%s\n' "$out" | sed -n '2s/:.*//p')"
echo '[]' > "$S/issues.json"
chk "no spin counts all" "PRs since the last spin: 4" "$(run sh "$root/plugin/bin/review-due" o/r main | sed -n 1,1p)"
chk "default threshold 4" "REVIEW DUE" "$(run sh "$root/plugin/bin/review-due" o/r main | sed -n '2s/:.*//p')"
# fix-attempt: the 3rd attempt is refused and nothing is posted.
echo '{"comments":[{"body":"hello"}]}' > "$S/comments.json"
echo '{"statusCheckRollup":[{"name":"ci","conclusion":"FAILURE"},{"name":"lint","conclusion":"SUCCESS"}]}' > "$S/checks.json"
run sh "$root/plugin/bin/fix-attempt" o/r#7 "fix import" >/dev/null; chk "attempt 1" 0 $?
run sh "$root/plugin/bin/fix-attempt" o/r#7 "fix table row" >/dev/null; chk "attempt 2" 0 $?
out=$(run sh "$root/plugin/bin/fix-attempt" o/r#7 "third"); rc=$?
chk "attempt 3 refused" 1 $rc
case $out in *'failing checks: ci'*'fix import'*'fix table row'*) ;; *) echo "FAIL refusal report: $out"; fail=1 ;; esac
chk "no third comment" 3 "$(jq '.comments | length' "$S/comments.json")"
out=$(run env CI_FIX_MAX=3 sh "$root/plugin/bin/fix-attempt" o/r#7 "third"); chk "cap is configurable" 0 $?
exit $fail
