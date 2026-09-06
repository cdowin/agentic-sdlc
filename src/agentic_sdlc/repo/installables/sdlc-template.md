# The protocol, as the machine runs it

<!-- Written by `agentic-sdlc install-sdlc`. Do not hand-edit: the check
     lists below are RENDERED from `[story]`, `[feature]`, `[release]` and
     `[adopt]` steps in this repo's devkit.toml, from the registry that runs
     them, and from `[pm.states.<kind>] done`, so the only way to change them
     is to change the config or the code and re-run the verb. A hand-written
     document describing the checks is the second home for the protocol, and
     a second home drifts — which is the failure this file exists to end. -->

Run it — one verb per level, and none of them is "run the biggest thing":

```
agentic-sdlc close story   <story-id>      the inner loop, seconds
agentic-sdlc close feature <feature-id>    once its stories are done
agentic-sdlc release       <version>       once its features are done
agentic-sdlc adopt         <version>       a devkit pin bump, scoped to the adoption
```

**A belt is its checks, then one write or a clean error** (D12). Every check
in the list runs and prints one line — `ok: <check> — <detail>`, or
`error: <check>: <what is false>` — and then the belt writes AT MOST ONE
thing: the status of the grain it was asked about, set to the first state of
that kind's `done` category, as this repo declares it. All true → the write,
exit `0`. Any false → no write, exit `1`, every false check named. `--force`
writes anyway, and the milestone's `ledger.jsonl` gets one `deviation` row
naming the checks that were false. Exit `2` is the declaration that could not
be read — a bad id, an unknown check name, a config value of the wrong shape.

Nothing else is written, moved, bumped, retitled, pushed or tagged. What is
yours to do after a write is printed as `next:` lines and listed under each
belt below. A check that cannot be decided — a callee that exited 2, a record
that does not parse — prints `unverifiable:` and counts as false: a write over
a question nobody answered is the one thing this machine will not do.

This tool reads and writes the PM tree and says what it saw. Whether a false
check should stop you is YOUR question: the engine cannot know whether it is
wrong (descoped? a hotfix? deliberate?), which is what `--force` is for, on
the record. `agentic-sdlc check <gate>` is the thing that FAILS a tree, in CI
and pre-push, with an exit-code contract for exactly that.

<!-- STEPS -->

<!-- GUIDANCE -->

## Changing this document

Edit `[<operation>] steps` (or `[<operation>.commands]`) in `devkit.toml` and
re-run `agentic-sdlc install-sdlc --force`. There is nothing to edit here:
every line of the lists above is derived from the config and the registry
that runs it.
