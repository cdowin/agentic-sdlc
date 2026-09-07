# The protocol, as the machine runs it

<!-- Written by `agentic-sdlc install-sdlc`. Do not hand-edit: the check lists
     below are RENDERED from this repo's devkit.toml and the registry that runs
     them, so change those and re-run the verb. -->

Run it — one verb per level, and none of them is "run the biggest thing":

```
agentic-sdlc close story   <story-id>      the inner loop, seconds
agentic-sdlc close feature <feature-id>    once its stories are done
agentic-sdlc release       <version>       once its features are done
agentic-sdlc adopt         <version>       a devkit pin bump, scoped to the adoption
```

**A belt is its checks, then one write or a clean error** (D12). Every check
prints one line — `ok: <check> — <detail>`, or `error: <check>: <what is
false>` — and then the belt writes AT MOST ONE thing: the status of the grain
it was asked about, set to the first state of that kind's `done` category. All
true: the write, exit `0`. Any false: no write, exit `1`, every false check
named; `--force` writes anyway and the milestone's `ledger.jsonl` gets one
`deviation` row naming them. Exit `2` is a declaration that could not be read.
A check that cannot be decided prints `unverifiable:` and counts as false.

Nothing else is written, moved, bumped, pushed or tagged; what is yours to do
after a write is printed as `next:` lines and listed under each belt below.
Whether a false check should stop you is YOUR question — that is what
`--force` is for, on the record; `agentic-sdlc check <gate>` is what FAILS a
tree, in CI and pre-push.

<!-- STEPS -->

## The events a belt emits

`[emit]` in devkit.toml names the sink; a repo that declares none emits nothing
and behaves exactly as it did, exit codes included. A belt is its checks, then
one write, and that sentence has exactly three moments worth a row: the entry
condition was asked, one check resolved, the one write happened.

<!-- EVENTS -->

There is deliberately no fourth kind for a belt that stopped. One that writes
nothing emits its false verdicts and no `rung.leave`, and the absence IS the
signal — a row saying "the thing did not happen" is the tool narrating rather
than recording. That reading needs the `verdict` tap on: `[emit] kinds` takes
any subset, and a missing `rung.leave` means "refused" only against the
`check.verdict` rows of the same run.

The table is the BELT's own kinds, not a census of the sink. Other kinds ride
the same three taps with their own shape — `lesson.enter` and `lesson.verdict`
carry the lessons surfaced at a move — so a courier keys on the TAP and treats
the payload as the kind's. A `lesson` row itself is recorded by hand
(`agentic-sdlc lesson record`) and read back beside the check it names.

<!-- GUIDANCE -->

## Changing this document

Edit `[<operation>] steps` (or `[<operation>.commands]`) in `devkit.toml` and
re-run `agentic-sdlc install-sdlc --force`; every line above is derived.
