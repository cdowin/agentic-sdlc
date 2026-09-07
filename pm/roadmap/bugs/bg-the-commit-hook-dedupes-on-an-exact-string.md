---
id: bg-the-commit-hook-dedupes-on-an-exact-string
kind: bug
milestone: "ms-a-move-is-an-event"
name: the commit hook dedupes on an exact string, so agent commits get two trailers
status: closed
caused_by:
---

# the commit hook dedupes on an exact string

GitHub issue #9, found by a dispatched agent while working this milestone — **the hook was
double-stamping that agent's own commits while it worked.**

`tools/hooks/prepare-commit-msg` guards against double-stamping with a fixed-string match:

    TRAILER="Co-Authored-By: Claude <noreply@anthropic.com>"
    if grep -qF "$TRAILER" "$MSG_FILE"; then exit 0; fi

That holds only while this hook is the ONLY thing writing a trailer. It is not: a harness instructs
its session to sign off, and that line names the MODEL —
`Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` — which `grep -F` does not match. So the
hook appends a second trailer and the commit ends with both.

## Why it stayed invisible

`is_agent_context` gates the hook, so it never fires on the trunk tree. It only fires on dispatched
work, **which is the work whose raw commit message nobody reads.** 59 of the last 60 commits in the
consumer repo checked carry the model-named line.

And it gets MORE likely the better the stock value is: a consumer who happens to set `TRAILER` to a
model-named string matches what agents write today; a consumer on the stock model-less string never
does. The default is the broken case.

## Fix

Split identity from recognition — what the hook WRITES is not what counts as already-written:

    TRAILER="Co-Authored-By: Claude <noreply@anthropic.com>"
    TRAILER_RE='^Co-Authored-By: Claude.*<noreply@anthropic\.com>'
    if grep -qE "$TRAILER_RE" "$MSG_FILE"; then exit 0; fi

`check hooks` replays the corpus each hook asserts about itself; this needs a corpus row for the
model-named input, or the fix is untested by the gate that exists to test it.

## Why it belongs in THIS milestone

It is a hook in the corpus this milestone is about to extend with an event courier. A courier added
beside a hook whose own idempotence guard is broken inherits the same class of defect — the guard
that only holds while nothing else writes.
