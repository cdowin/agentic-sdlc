---
id: st-the-auto-loaded-rule-is-true-at-this-version
kind: story
feature: ft-the-shipped-words-match-the-shipped-tool
milestone: "ms-a-consumer-can-take-the-bump"
name: the auto-loaded pm-execution rule is true at this version
status: building
owner: agent
depends_on: []
changelog: The installed pm-execution rule now says a story left open under a done feature is a D11 failure, not a warning, offers the feature `reviewing` state only where `[pm.states.feature]` declares it, and no longer suggests `pm list --status building,reviewing` (exit 2 on the stock vocabulary) — re-run `pm install-skills --force`.
---

# the auto-loaded pm-execution rule is true at this version

Issues: #32, and the `pm-execution.md` audit left open on #15 (consequence 3).

`pm/guidance/pm-execution.md` is installed as `.claude/rules/pm-execution.md` in every consumer. It
loads on every `pm/roadmap/**` edit and a consumer cannot edit it. Two of its sentences are false at
v0.7.0:

- step 4 (`:117`) says *"a story left behind is `check pm`'s WARN"*. Since 0.6.0, D11 FAILS a `done`
  parent over any unresolved child (`checks/pm.py:1006-1012`);
- step 3 (`:109-110`) states `pm feature reviewing <id>` unconditionally, wrapped across a line. The
  story sentence right after it defers to `pm vocabulary`; the feature sentence does not. A project
  with no `reviewing` feature state is told to run a refused command.

#15 measured that this file reaches the main session conditionally and a dispatched agent never. So
while it is open, **sort each paragraph**: a CONTRACT belongs in the role briefs or `dispatch`'s
preamble, which do reach agents, and a MECHANIC stays here or is rendered. This is a read and a sort,
not a rewrite. Where a paragraph moves, the brief or preamble that now carries it is named in the close.

## Acceptance criteria

1. The close-the-feature step says D11 FAILS a done parent over an unresolved story.
2. The feature-review sentence defers to the project's `[pm.states.feature]` the way the story
   sentence does, and names no state as unconditional.
3. Against a scratch consumer whose feature ladder omits `reviewing`, `check doc` (after
   `st-check-doc-reads-a-code-span-across-a-line-break`) finds no undeclared-state claim in the installed rule.
4. Each paragraph is tagged contract or mechanic in the close evidence. Any contract that moves is
   named with the file it moved to.
5. `.claude/rules/pm-execution.md` is re-installed with `pm install-skills --force`, and
   `installables-current` passes.

## How this is proven

| criterion | tier | the case that proves it | existing? |
|---|---|---|---|
| 1, 2 | — | read, and the close evidence quotes the new lines | n/a (text) |
| 3 | unit | the probe from the #26 story, run against the installed rule | amended there |
| 5 | unit | tests/test_install.py byte-current | yes |

## Semver

Patch: the installed text changes and no line shape does.

## Out of scope

Rendering the rule from `[pm.states.*]` at install time. That makes the file config-dependent and
breaks `test_install`'s byte-current check. Wording it to defer to `pm vocabulary` is the fix.
