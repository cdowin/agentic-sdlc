#!/bin/sh
# commit-pathspec.sh - agentic-sdlc PreToolUse hook for Bash. OPT-IN:
# runs only when AGENTIC_SDLC_COMMIT_PATHSPEC=1.
# In a tree that several agents share, a bare `git commit` commits the whole
# index, including what another agent staged. This hook refuses a `git commit`
# that names no paths, and `git commit -a`.
# Passes: a pathspec (`-- <paths>`, a bare path, --pathspec-from-file), --amend,
# --dry-run, --help, --interactive, --patch, and a commit that finishes a merge,
# rebase, cherry-pick or revert.
# Stdin: hook JSON with tool_input.command and cwd. Exit 0 = allow.
# Exit 2 = refuse, with a 1-line reason on stderr. Fails open.

[ "${AGENTIC_SDLC_COMMIT_PATHSPEC:-0}" = 1 ] || exit 0
input=$(cat) || exit 0
case $input in *commit*) ;; *) exit 0 ;; esac

# The JSON reader and the command splitter are the same as in git-denylist.sh.
# shellcheck disable=SC2016 # the awk program stays literal
prog='
function jstr(s, key,   j, n, c, out) {
  if (!match(s, "\"" key "\"[ \t\r\n]*:[ \t\r\n]*\"")) return ""
  out = ""; n = length(s)
  for (j = RSTART + RLENGTH; j <= n; j++) {
    c = substr(s, j, 1)
    if (c == "\\") {
      j++; c = substr(s, j, 1)
      if (c == "n") out = out "\n"; else if (c == "t") out = out "\t"
      else if (c == "u") { out = out "?"; j += 4 } else if (c != "r") out = out c
    } else if (c == "\"") break
    else out = out c
  }
  return out
}
function base(w) { sub(/.*\//, "", w); return w }
function scan(t, depth,   n, i, c, w, inw, skip, nw, W, r, delim, q, line, e, k) {
  n = length(t); w = ""; inw = 0; nw = 0; skip = 0; delim = ""
  for (i = 1; i <= n + 1; i++) {
    c = (i <= n) ? substr(t, i, 1) : "\n"
    if (c == "\047" && i <= n) {
      e = index(substr(t, i + 1), "\047"); if (e == 0) e = n - i + 1
      w = w substr(t, i + 1, e - 1); i += e; inw = 1; continue
    }
    if (c == "\"" && i <= n) {
      for (i++; i <= n; i++) {
        q = substr(t, i, 1)
        if (q == "\\" && i < n) { i++; w = w substr(t, i, 1); continue }
        if (q == "\"") break
        w = w q
      }
      inw = 1; continue
    }
    if (c == "\\" && i < n) { i++; if (substr(t, i, 1) != "\n") { w = w substr(t, i, 1); inw = 1 }; continue }
    if (c == "#" && !inw) { while (i <= n && substr(t, i, 1) != "\n") i++; i--; continue }
    if (c == "<" && substr(t, i, 2) == "<<" && substr(t, i, 3) != "<<<") {
      if (inw) { if (!skip) W[++nw] = w; skip = 0; w = ""; inw = 0 }
      i += 2; if (substr(t, i, 1) == "-") i++
      while (substr(t, i, 1) ~ /[ \t]/) i++
      if (substr(t, i, 1) ~ /["\047]/) i++
      delim = ""
      while (substr(t, i, 1) ~ /[A-Za-z0-9_]/) { delim = delim substr(t, i, 1); i++ }
      if (substr(t, i, 1) ~ /["\047]/) i++
      i--; continue
    }
    if (c ~ /[ \t\r]/ || c ~ /[<>;&|()`\n]/ || (c == "$" && substr(t, i + 1, 1) == "(")) {
      if (inw) {
        if (skip) skip = 0
        else W[++nw] = w
        w = ""; inw = 0
      }
      if (c ~ /[<>]/) { if (nw > 0 && W[nw] ~ /^[0-9]+$/) nw--; skip = 1; continue }
      if (c == "$") { i++; c = ";" }
      if (c ~ /[;&|()`\n]/) {
        skip = 0
        if (nw > 0) { r = judge(W, nw, depth); if (r != "") return r }
        for (k in W) delete W[k]; nw = 0
      }
      if (c == "\n" && delim != "") {
        while (i < n) {
          e = index(substr(t, i + 1), "\n"); if (e == 0) e = n - i + 1
          line = substr(t, i + 1, e - 1); i += e
          gsub(/^[ \t]+|[ \t\r]+$/, "", line)
          if (line == delim) break
        }
        delim = ""
      }
      continue
    }
    w = w c; inw = 1
  }
  return ""
}
# judge: print "<dir>\t<reason>" for a commit that names no paths; dir is its -C or "".
function judge(W, nw, depth,   i, j, k, b, s, dir, x, all) {
  i = 1
  while (i <= nw && W[i] ~ /^[A-Za-z_][A-Za-z0-9_]*=/) i++
  if (i > nw) return ""
  b = base(W[i])
  if (b ~ /^(sh|bash|zsh|dash|ksh)$/ && depth < 3)
    for (j = i + 1; j < nw; j++) if (W[j] ~ /^-[a-z]*c[a-z]*$/) return scan(W[j + 1], depth + 1)
  for (j = i; j <= nw && base(W[j]) != "git"; j++) ;
  if (j > nw) return ""
  dir = ""
  for (k = j + 1; k <= nw && W[k] ~ /^-/; k++)
    if (W[k] ~ /^(-C|-c|--git-dir|--work-tree|--namespace|--config-env)$/) { if (W[k] == "-C") dir = W[k + 1]; k++ }
  if (k > nw || W[k] != "commit") return ""
  all = 0
  for (k++; k <= nw; k++) {
    x = W[k]
    if (x == "--") return (k < nw) ? "" : dir "\tgit commit -- names no paths"
    if (x ~ /^--(amend|dry-run|help|interactive|patch|pathspec-from-file)/) return ""
    if (x == "--all") { all = 1; continue }
    if (x ~ /^--(message|file|author|date|template|reuse-message|reedit-message|fixup|squash|trailer|cleanup|gpg-sign)$/) { k++; continue }
    if (x ~ /^--/) continue
    if (x ~ /^-./) {
      for (j = 2; j <= length(x); j++) {
        b = substr(x, j, 1)
        if (b ~ /[ph]/) return ""
        if (b == "a") all = 1
        if (b ~ /[mFCct]/) { if (j == length(x)) k++; break }
        if (b ~ /[Su]/) break
      }
      continue
    }
    return ""
  }
  if (all) return dir "\tgit commit -a stages every changed tracked file, including other agents work; name your paths: git commit -m <msg> -- <path>..."
  return dir "\tgit commit names no paths, so it commits the whole index; name them: git commit -m <msg> -- <path>..."
}
{ doc = doc $0 "\n" }
END { cmd = jstr(doc, "command"); if (cmd != "") { print scan(cmd, 0); print jstr(doc, "cwd") } }
'

out=$(printf '%s\n' "$input" | awk "$prog" 2>/dev/null) || exit 0
verdict=$(printf '%s\n' "$out" | sed -n 1p)
[ -n "$verdict" ] || exit 0
cwd=$(printf '%s\n' "$out" | sed -n 2p)
tab=$(printf '\t')
dir=${verdict%%"$tab"*}
reason=${verdict#*"$tab"}
if [ -n "$cwd" ] && [ -d "$cwd" ]; then cd "$cwd" || exit 0; fi
[ -n "$dir" ] && { cd "$dir" 2>/dev/null || exit 0; }
# A commit that finishes a merge, rebase, cherry-pick or revert takes the whole index.
for state in MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD rebase-merge rebase-apply; do
  p=$(git rev-parse --git-path "$state" 2>/dev/null) || exit 0
  [ -e "$p" ] && exit 0
done
printf 'agentic-sdlc commit-pathspec: %s\n' "$reason" >&2
exit 2
