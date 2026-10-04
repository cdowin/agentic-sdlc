#!/bin/sh
# git-denylist.sh - agentic-sdlc PreToolUse hook for Bash. ON by default.
# Refuses git that destroys local work the server cannot see:
#   push --force / -f / --force-with-lease / --mirror / +refspec, reset --hard,
#   clean -f, a whole-tree discard (checkout -- . / restore .), git -c,
#   a GIT_CONFIG_*= assignment, config --global.
# Everything else passes. A push to a protected branch passes: rulesets refuse it.
# Reads each ; && | $( ) part, heredocs skipped, and the script of sh -c / eval.
# Stdin: hook JSON with tool_input.command. Exit 0 = allow.
# Exit 2 = refuse, with a 1-line reason on stderr. Fails open.
# Turn off: AGENTIC_SDLC_GIT_DENYLIST=0.

[ "${AGENTIC_SDLC_GIT_DENYLIST:-1}" = 0 ] && exit 0
input=$(cat) || exit 0
case $input in *git*|*GIT_CONFIG_*) ;; *) exit 0 ;; esac

# shellcheck disable=SC2016 # the awk program stays literal
prog='
function jstr(s, key,   p, j, n, c, out) {
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
# scan: split a command line into simple commands; judge each. Returns a reason or "".
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
function judge(W, nw, depth,   i, j, k, b, s, rest, nr, R, opts, longs, shorts, pos, np, P, dd, x) {
  i = 1
  while (i <= nw && W[i] ~ /^[A-Za-z_][A-Za-z0-9_]*=/) {
    if (W[i] ~ /^GIT_CONFIG_[A-Za-z0-9_]*=/) return "GIT_CONFIG_* sets git config this hook cannot read; run the git command plainly"
    i++
  }
  if (i > nw) return ""
  b = base(W[i])
  if (b ~ /^(export|declare|typeset|readonly|local|env)$/)
    for (j = i + 1; j <= nw; j++) if (W[j] ~ /^GIT_CONFIG_[A-Za-z0-9_]*=/) return "GIT_CONFIG_* sets git config this hook cannot read; run the git command plainly"
  if (b ~ /^(sh|bash|zsh|dash|ksh)$/ && depth < 3)
    for (j = i + 1; j < nw; j++) if (W[j] ~ /^-[a-z]*c[a-z]*$/) return scan(W[j + 1], depth + 1)
  if (b == "eval" && depth < 3) {
    s = ""; for (j = i + 1; j <= nw; j++) s = s " " W[j]
    return scan(s, depth + 1)
  }
  for (j = i; j <= nw && base(W[j]) != "git"; j++) ;
  if (j > nw) return ""
  for (k = j + 1; k <= nw && W[k] ~ /^-/; k++) {
    if (W[k] ~ /^-c/ || W[k] ~ /^--config-env/) return "git -c sets config for one command; run it without -c"
    if (W[k] ~ /^(-C|--git-dir|--work-tree|--namespace)$/) k++
  }
  if (k > nw) return ""
  s = W[k]; nr = 0; dd = 0; longs = " "; shorts = ""; np = 0
  for (k++; k <= nw; k++) {
    R[++nr] = W[k]
    if (dd) { P[++np] = W[k]; continue }
    if (W[k] == "--") { dd = 1; np = 0; continue }
    if (W[k] ~ /^--./) { x = substr(W[k], 3); sub(/=.*/, "", x); longs = longs x " " }
    else if (W[k] ~ /^-./) shorts = shorts substr(W[k], 2)
    else P[++np] = W[k]
  }
  if (s == "push") {
    if (longs ~ / (force|force-with-lease|force-if-includes|mirror)[^ ]* / || shorts ~ /f/)
      return "a force push rewrites history others may hold; push a new commit instead"
    for (k = 1; k <= np; k++) if (P[k] ~ /^\+/) return "a +refspec is a force push; push a new commit instead"
  }
  if (s == "reset" && longs ~ / hard /) return "reset --hard discards uncommitted work; commit it, or restore one named path"
  if (s == "clean" && (shorts ~ /f/ || longs ~ / force /) && !(shorts ~ /n/ || longs ~ / dry-run /))
    return "clean -f deletes untracked files for good; rm the paths you mean"
  if (s == "checkout" || s == "restore") {
    if (s == "restore" && (shorts ~ /S/ || longs ~ / staged /) && !(shorts ~ /W/ || longs ~ / worktree /)) return ""
    for (k = 1; k <= np; k++)
      if (P[k] ~ /^(\.|\.\/|:\/|:\/\.|\*|:)$/) return "a whole-tree discard drops every uncommitted change; name the paths"
  }
  if (s == "config" && longs ~ / (global|system) /) return "config --global changes git for every repo on this machine; use repo config"
  return ""
}
{ doc = doc $0 "\n" }
END { cmd = jstr(doc, "command"); if (cmd != "") print scan(cmd, 0) }
'

reason=$(printf '%s\n' "$input" | awk "$prog" 2>/dev/null) || exit 0
[ -n "$reason" ] || exit 0
printf 'agentic-sdlc git-denylist: %s\n' "$reason" >&2
exit 2
