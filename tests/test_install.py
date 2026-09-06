"""test_install.py — the install-* verbs, and the one property they all rest on.

An install verb writes a file. Once. If the destination is there and differs it
refuses, names the path and names `--force`; `--diff` shows what would change
and writes nothing. There is no manifest, no drift tracking and no merge — the
whole relationship is those four sentences, and each one is a test below.

The property that is not obvious from the verb's description is ATOMICITY: an
install either happens whole or does not happen. A refusal raised mid-plan left
a half-installed repo behind and still claimed nothing was written.

The hook installables carry one more: they are STANDALONE. The forked copies in
both consumers `source tools/hooks/_scope.sh` for a project-name-prefixed JSON
reader; a `source` of a file a fresh project does not have fails OPEN, and a
guard that fails open is a guard that is not there. So the corpus is pinned to
carry its parser INLINE here, and tests/test_hooks_payloads.py installs it
into an empty repo with no library of any kind and RUNS it.

**Selection criterion (hard rule 10, 0.2.0/the-proof-is-named-in-the-criterion):**
this module spawns NOTHING and sits in the unit tier. `install.main` reads and
writes files, so every case here is a temp tree; the four cases that ran bash
or git moved to the module whose subject that is (the installed corpus, run:
test_hooks_payloads.py; install day's gates: test_fresh_project.py) or were
already proven there. A claim about the installables' PROSE is not asserted;
a claim about what a write did to the disk is.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import re
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support import consumers

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo import install  # noqa: E402


@contextlib.contextmanager
def repo(files: dict[str, str] | None = None):
    """An empty repo, cwd'd into. `.git` is a MARKER directory: `repo_root`
    walks up for it and never asks git, so `git init` here was a process
    per case that bought nothing (tests/support/pm.py `_mark`)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        root.mkdir()
        for rel, body in (files or {}).items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        (root / '.git').mkdir()
        previous = Path.cwd()
        os.chdir(root)
        repo_root.cache_clear()
        load_config.cache_clear()
        try:
            yield root
        finally:
            os.chdir(previous)
            repo_root.cache_clear()
            load_config.cache_clear()


def run(command: str, *argv: str) -> tuple[int, str]:
    """Exit code + STDOUT."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = install.main(command, list(argv))
    return code, buffer.getvalue()


def refuse(command: str, *argv: str) -> tuple[int, str]:
    """Exit code + both streams, for the runs that print their refusal."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = install.main(command, list(argv))
    return code, buffer.getvalue()


WORKFLOW = '.github/workflows/verify.yml'
# The set a project runs on a push. verify.yml is the one this repo itself
# carries; the other two mint and gate a TAG, and this repo's release protocol
# tags by hand — a second tagger on the same mainline is the reason those two
# are installed everywhere and self-hosted nowhere. uid-guard.yml left in 0.2.0
# with the gate it ran (decision D2).
WORKFLOWS = (WORKFLOW,
             '.github/workflows/semver-gate.yml',
             '.github/workflows/auto-tag.yml')
AGENTS = ('.claude/agents/verification-reviewer.md',
          '.claude/agents/verification-builder.md',
          '.claude/agents/architect.md',
          '.claude/agents/po.md',
          '.claude/agents/developer.md',
          '.claude/agents/reviewer.md',
          '.claude/agents/milestone-reviewer.md',
          '.claude/agents/simplifier.md',
          '.claude/agents/test-writer.md',
          '.claude/agents/tech-writer.md',
          '.claude/agents/changelog-writer.md',
          '.claude/agents/doc-hygiene.md',
          '.claude/agents/pm-operator.md')
# The verification pair carries the review/build CONTRACT and predates the
# roster; the rest are the base ROSTER — generalized from the two consumers,
# each carrying model/effort frontmatter and an editable project-config
# section. The split matters below: the contract tests pin the pair's
# sentences, the roster tests pin the parameterization story.
ROSTER = AGENTS[2:]
HOOKS = ('tools/hooks/cc-commit-pathspec.sh',
         'tools/hooks/cc-stop-gate.sh',
         'tools/hooks/cc-write-confine.sh',
         # The two ledger couriers (0.22.0). They guard nothing; they carry a
         # stop event's transcript path to `pm ledger record` and exit 0.
         'tools/hooks/cc-ledger-subagent.sh',
         'tools/hooks/cc-ledger-session.sh',
         'tools/hooks/pre-push',
         'tools/hooks/prepare-commit-msg',
         'tools/dev/agent-worktree.sh',
         'tools/setup-hooks.sh')
# The gate FRAMEWORK, and the whole of it: the library that gives every gate one
# verdict line, and the include that calls it. It was `install-runners` through
# 0.1.0 and carried twelve engine runners besides — the gate framework and one
# language's roster under one verb, which is what blocked splitting this package
# in two (decision D2). A language kit installs its own runners and a
# `Makefile.tiers` that hangs them off this include's `-include` seam.
GATES = ('tools/dev/gdk_gate.sh',
         'Makefile.devkit')
# The fifth verb, and the only one whose body is GENERATED: the release
# protocol rendered from `[release] steps` and the registry that walks them.
# One destination, so it is never a whole-set `--force` story.
SDLC = ('docs/sdlc-protocol.md',)
DESTINATIONS = {'install-ci': WORKFLOWS,
                'install-agents': AGENTS,
                'install-hooks': HOOKS,
                'install-gates': GATES,
                'install-sdlc': SDLC}
VERBS = tuple(DESTINATIONS)
# The table above is spelled out so a test READS as the contract, but it is
# not allowed to become a second roster: a verb added to PLANS and not here
# would be a verb every parametrized test below silently skips.
assert {verb: tuple(rel for _, rel in entries)
        for verb, entries in install.PLANS.items()} == DESTINATIONS


# --- the four sentences, once per verb ---------------------------------------
@pytest.mark.parametrize('command', VERBS)
def test_the_verb_writes_its_files_and_a_second_run_is_a_no_op(command):
    """One install, asked three things of: the files landed with the mode
    each deserves, a second run is byte-identical and says `already current`
    for every entry, and `--diff` over that tree shows no hunk.

    The exec bit: 0.20.0 MAJOR-1, and the 0.19.0 NIT it subsumes. Scripts
    were written -rw-r--r-- and the next step told the operator to `chmod +x`
    them; a fan-out that exec'd one directly got 126 with nothing under it.
    The mode is part of the write now, in `core.apply`, and it is asked of
    the DESTINATION suffix per verb so a `.sh` added to any plan tomorrow is
    covered the day it lands — and nothing that is not a script gets the bit.
    """
    with repo() as root:
        code, out = run(command)
        assert code == 0, out
        bodies = {rel: (root / rel).read_text(encoding='utf-8')
                  for rel in DESTINATIONS[command]}
        assert all(bodies.values()), 'a destination was written empty'
        not_runnable = [rel for rel in DESTINATIONS[command]
                        if rel.endswith('.sh') and not os.access(root / rel, os.X_OK)]
        runnable = [rel for rel in DESTINATIONS[command]
                    if not rel.endswith('.sh') and os.access(root / rel, os.X_OK)]
        assert not not_runnable, (
            f'{command} wrote {not_runnable} without an execute bit — a caller '
            f'exec\'ing one gets 126, and `Permission denied` is a diagnosis no '
            f'gate summary matches')
        assert not runnable, (
            f'{command} made {runnable} executable; only `.sh` is a script here')
        code, out = run(command)
        assert code == 0, out
        assert out.count('already current') == len(DESTINATIONS[command]), out
        assert {rel: (root / rel).read_text(encoding='utf-8')
                for rel in DESTINATIONS[command]} == bodies
        code, out = run(command, '--diff')
        assert code == 0
        assert out.count('already current') == len(DESTINATIONS[command]), out
        assert '@@' not in out, out


@pytest.mark.parametrize('command', VERBS)
def test_a_destination_that_differs_is_refused_and_the_refusal_names_force(
        command):
    """`--force` is the whole remedy vocabulary, so the refusal must say it:
    a refusal that names no repair sends the operator to the source."""
    first = DESTINATIONS[command][0]
    mine = 'my own version, deliberately\n'
    with repo({first: mine}) as root:
        code, out = refuse(command)
        assert code == 1, out
        assert first in out and '--force' in out, out
        assert (root / first).read_text(encoding='utf-8') == mine


@pytest.mark.parametrize('command', VERBS)
def test_force_overwrites_every_entry(command):
    """The whole-or-nothing decision must not have turned --force into a
    refusal: an explicit flag is documented to clobber."""
    mine = 'my own version, deliberately\n'
    with repo({rel: mine for rel in DESTINATIONS[command]}) as root:
        code, out = run(command, '--force')
        assert code == 0, out
        for name, rel in install.PLANS[command]:
            # `resolve_body`, not `body_of`: one entry's body is RENDERED, and
            # asking the wrong one would compare the destination against a
            # template nobody installs.
            assert ((root / rel).read_text(encoding='utf-8')
                    == install.resolve_body(name, rel)), rel


# --- what a release is allowed to TELL a consumer to do -----------------------
# `--force` is whole-set (the test above pins it) and there is no per-file
# option, so a consumer who edited one file of a plan loses it. Measured on two
# real adoptions when this was found: one installed `verify.yml` had grown into
# a deliberate two-job sharded workflow 177 lines from the installable, whose
# own header says why it does not run `make milestone`; another installed
# `auto-tag.yml` differed by one path filter. The release notes said
# "`install-ci --diff` then `--force`, re-applying nothing", which told the
# first of those to delete its CI.
#
# The trigger is the paragraph that IS the instruction — the one carrying
# "follow-up" — never prose that merely mentions the flag. CHANGELOG.md is
# scoped to `## Unreleased`: a released section is a RECORD and is never
# rewritten to satisfy a rule written after it.
INSTRUCTION_SITES = ('CHANGELOG.md', '.claude/skills/release/SKILL.md')
INSTRUCTION_MARKER = 'follow-up'
# The cost, in any of the words somebody would reach for. A closed list, so
# what the gate accepts is reviewable rather than guessed at.
NAMES_THE_COST = ('per-file', 'per file', 'PER FILE', 'whole-set', 'whole set',
                  'all four')
# Claims that are FALSE of a whole-set --force, in the spellings this package
# has actually used. Closed, and each one earns its place by having shipped.
COST_FREE_CLAIMS = ('re-applying nothing', 're-applies nothing',
                    'nothing to re-apply')


def unreleased(text: str) -> str:
    """The section that becomes the next release's notes."""
    at = text.index('## Unreleased')
    rest = text[at + len('## Unreleased'):]
    end = rest.find('\n## ')
    return rest if end < 0 else rest[:end]


def test_no_shipped_instruction_offers_force_without_naming_what_it_costs():
    """A release note is read once, acted on, and not re-read. So the sentence
    that sends a consumer to `--force` has to carry the one fact that decides
    whether they should: the verb writes a SET, and a file they edited on
    purpose is in it."""
    whole_set = {verb for verb, entries in install.PLANS.items()
                 if len(entries) > 1}
    assert whole_set, 'no verb writes a set — this rule has no subject'
    checked = 0
    for rel in INSTRUCTION_SITES:
        text = (REPO_ROOT / rel).read_text(encoding='utf-8')
        body = unreleased(text) if rel.endswith('CHANGELOG.md') else text
        for number, para in enumerate(body.split('\n'), 1):
            named = [verb for verb in whole_set
                     if verb in para or 'install-*' in para]
            if '--force' not in para or not named:
                continue
            if INSTRUCTION_MARKER not in para.lower():
                continue
            checked += 1
            where = f'{rel} (paragraph {number}), naming {sorted(named)}'
            assert '--diff' in para, (
                f'{where}: sends a consumer to --force without --diff first')
            assert any(word in para for word in NAMES_THE_COST), (
                f'{where}: `--force` is whole-set and has no per-file option, '
                f'so this has to say so — one of {NAMES_THE_COST}')
            for claim in COST_FREE_CLAIMS:
                assert claim not in para, (
                    f'{where}: "{claim}" is false of a whole-set --force')
    assert checked, ('no consumer follow-up instruction was found in '
                     f'{INSTRUCTION_SITES} — the rule scanned nothing')


@pytest.mark.parametrize('command', VERBS)
def test_diff_prints_a_unified_diff_and_writes_nothing(command):
    first = DESTINATIONS[command][0]
    mine = 'my own version, deliberately\n'
    with repo({first: mine}) as root:
        code, out = run(command, '--diff')
        assert code == 0, out
        # A real unified diff of the DIFFERING file …
        assert f'--- a/{first}' in out and f'+++ b/{first}' in out, out
        assert '-my own version, deliberately' in out, out
        # … and the ABSENT ones named as additions rather than shown as noise.
        for rel in DESTINATIONS[command][1:]:
            assert f'{rel} does not exist' in out, out
        # Nothing on disk moved: the differing file is untouched and the
        # absent ones are still absent.
        assert (root / first).read_text(encoding='utf-8') == mine
        for rel in DESTINATIONS[command][1:]:
            assert not (root / rel).exists(), rel


def test_an_unknown_flag_is_a_usage_error():
    with repo():
        code, _ = refuse('install-ci', '--yolo')
        assert code == 2


# --- the report and the disk are one thing ------------------------------------
def test_a_collision_on_a_LATER_entry_withholds_that_file_and_nothing_else():
    """The defect this replaced: `install-agents` wrote the reviewer, THEN
    refused on the builder, and reported `nothing was written` about a repo
    that now held one of the two files. The claim was the bug — not the write.

    A collision is the operator's own file, deliberately theirs, and it
    withholds ITS destination; the entries with nothing in their way land, and
    the run reports exactly what it did. The whole-plan decision is proven
    where it belongs, on a DEFECT (below): that one still writes nothing.
    `install-hooks` is proven in the same shape by
    `test_a_new_hook_lands_on_a_consumer_whose_headers_are_edited`."""
    command = 'install-agents'
    rels = DESTINATIONS[command]
    mine = 'my own version, deliberately\n'
    with repo({rels[-1]: mine}) as root:
        code, out = refuse(command)
        assert code == 1, out
        for earlier in rels[:-1]:
            assert (root / earlier).is_file(), (
                f'{earlier} was withheld by a collision on {rels[-1]}')
            assert f'wrote {earlier}' in out, out
        assert (root / rels[-1]).read_text(encoding='utf-8') == mine
        assert rels[-1] in out, out
        assert f'wrote {rels[-1]}' not in out, out
        assert 'nothing was written' not in out, out


def test_every_collision_is_named_in_one_refusal():
    """Two collisions, one run: an operator must not have to re-install to
    discover the next file they need to move aside — and the sentence about
    the disk is built from the disk, not asserted."""
    with repo({AGENTS[0]: 'mine\n', AGENTS[1]: 'mine too\n'}) as root:
        code, message = refuse('install-agents')
        for rel in AGENTS[:2]:
            assert rel in message, message
            assert (root / rel).read_text(encoding='utf-8').startswith('mine')
        for rel in AGENTS[2:]:
            assert (root / rel).is_file(), rel
    assert code == 1
    assert 'nothing was written' not in message, message
    assert f'{len(AGENTS) - 2} file(s) with nothing in the way' in message


@pytest.mark.skipif(hasattr(os, 'geteuid') and os.geteuid() == 0,
                    reason='root ignores the write bit, so there is no '
                           'read-only destination to refuse')
def test_a_read_only_destination_is_a_refusal_that_writes_nothing():
    with repo() as root:
        assert run('install-agents')[0] == 0
        keep = (root / AGENTS[0]).read_text(encoding='utf-8')
        for rel in AGENTS:
            (root / rel).write_text('stale\n', encoding='utf-8')
        (root / AGENTS[1]).chmod(0o444)
        try:
            code, out = refuse('install-agents', '--force')
        finally:
            (root / AGENTS[1]).chmod(0o644)
        assert code == 1, out
        assert 'is not writable' in out, out
        # The first entry is the one that proves it: with --force it WOULD have
        # been rewritten, and a refusal decided up front leaves it alone.
        assert (root / AGENTS[0]).read_text(encoding='utf-8') == 'stale\n'
        assert keep


def test_a_non_utf8_destination_is_a_collision_and_force_overwrites_it():
    """Undecodable bytes cannot be compared with an installable, so the file is
    somebody else's — the same answer as any other differing file, not a
    crash."""
    with repo() as root:
        (root / AGENTS[1]).parent.mkdir(parents=True, exist_ok=True)
        (root / AGENTS[1]).write_bytes(b'\xff\xfe\x00not utf-8')
        code, out = refuse('install-agents')
        assert code == 1, out
        assert '--force' in out, out
        # Withheld, not overwritten — and the entries with nothing in their
        # way still land, which is what makes the exit code the only signal a
        # replacement was held back.
        assert (root / AGENTS[1]).read_bytes() == b'\xff\xfe\x00not utf-8'
        assert (root / AGENTS[0]).is_file(), out
        code, out = refuse('install-agents', '--diff')
        assert code == 0, out
        assert 'not text this can diff' in out, out
        code, out = refuse('install-agents', '--force')
        assert code == 0, out
        assert ((root / AGENTS[1]).read_text(encoding='utf-8')
                == install.body_of('verification-builder.md'))


# --- install-agents: the roster's two deliveries --------------------------------
def test_every_roster_agent_carries_model_and_an_editable_config_section():
    """The roster's two load-bearing deliveries, pinned per file.

    `model:` is the frontmatter field doing proven work (the tiering table
    exists because of it), so every roster agent must declare one — and the
    `effort:` key ships with its unverified-caveat comment attached, because
    a misspelled or unsupported frontmatter key is silently ignored and a
    caveat that lives only in a doc never reaches the installed file.

    Project-specific content is parameterized the way the hook corpus does
    it: a clearly-marked project-config section the consumer edits after
    install. The marker is the contract — a rewrite that drops it drops the
    whole parameterization story. The verification pair is exempt: it
    predates the roster and deliberately carries neither.
    """
    by_rel = {rel: name for name, rel in install.PLANS['install-agents']}
    for rel in ROSTER:
        body = install.body_of(by_rel[rel])
        head = body.split('---', 2)[1]
        assert '\nmodel: ' in head, f'{rel} declares no model:'
        assert '\neffort: ' in head, f'{rel} declares no effort:'
        assert 'UNVERIFIED' in head, (
            f'{rel} dropped the effort-is-unverified caveat')
        assert 'GENERATED by agentic-sdlc' in body, rel
        assert '## Project config (yours to edit after install)' in body, (
            f'{rel} carries no editable project-config section')
    for rel in AGENTS[:2]:
        head = install.body_of(by_rel[rel]).split('---', 2)[1]
        assert 'model:' not in head, f'{rel} grew a model: it never had'


# --- install-hooks: canonical, and STANDALONE ---------------------------------
def test_the_hooks_carry_no_project_name_and_source_no_library():
    """The bulk of the divergence between the two forked copies was a
    project-name prefix on a shared library and its env var. One neutral name,
    defined where it is used: a hook that `source`s a library a fresh repo
    does not have fails OPEN, so the corpus ships every helper INLINE and the
    shared scope library ships as no file at all."""
    for rel in HOOKS:
        body = install.body_of(Path(rel).name)
        # The STRUCTURAL bans always run: they are facts about the shape of a
        # hook, not about who consumes it.
        for banned in ('_scope.sh', 'source "'):
            assert banned not in body, f'{rel} carries {banned!r}'
        # The project-name ban runs over whatever names are configured; the
        # names are maintainer configuration (tests/support/consumers.py).
        # Word-bounded: a git flag or an English word that merely begins with
        # a configured name is prose, not a project reference.
        lowered = body.lower()
        for name in consumers.consumer_names():
            hit = re.search(rf'\b{re.escape(name)}\b', lowered)
            assert hit is None, f'{rel} carries the consumer name {name!r}'
    # A hook that parses the stdin event carries its parser INLINE — a
    # hook that `source`s a library a fresh repo may not have fails OPEN.
    # DERIVED, not listed: it was `HOOKS[:2]`, which meant "the two that
    # parse a payload" until 0.2.0 moved one of them to the kit that owned
    # the artifact it guarded. A slice cannot say which property it selects
    # for, and a hand-written list here goes stale the same way.
    parsers = [rel for rel in HOOKS
               if 'hook_json_field' in install.body_of(Path(rel).name)]
    assert parsers, 'no installed hook parses its payload — census of zero'
    for rel in parsers:
        assert 'hook_json_field() {' in install.body_of(Path(rel).name), rel


CONFIG_HEADED = ('tools/hooks/cc-stop-gate.sh',
                 'tools/hooks/cc-ledger-subagent.sh',
                 'tools/hooks/cc-ledger-session.sh',
                 'tools/hooks/pre-push',
                 'tools/hooks/prepare-commit-msg',
                 'tools/dev/agent-worktree.sh')


def test_the_corpus_files_carry_an_editable_config_header():
    """Per-project variation is a config header the repo edits AFTER install,
    when the file is its own — never a fork of the source. The header marker
    is the contract; a rewrite that drops it drops the whole parameterization
    story."""
    for rel in CONFIG_HEADED:
        body = install.body_of(Path(rel).name)
        assert 'project config (yours to edit after install' in body, rel
    # The agent-context contract is one marker + one env var, spelled the
    # same in every file that reads it — a hook and the worktree tool
    # disagreeing on the marker name silently de-scopes the hook.
    for rel in ('tools/hooks/cc-stop-gate.sh', 'tools/hooks/pre-push',
                'tools/hooks/prepare-commit-msg',
                'tools/dev/agent-worktree.sh'):
        assert 'SCOPE_MARKER=".agent-scope"' in install.body_of(
            Path(rel).name), rel
    for rel in ('tools/hooks/cc-stop-gate.sh', 'tools/hooks/pre-push',
                'tools/hooks/prepare-commit-msg',
                'tools/hooks/cc-write-confine.sh'):
        assert 'DEVKIT_AGENT_SCOPE' in install.body_of(Path(rel).name), rel


# --- self-hosting -------------------------------------------------------------
def test_this_repo_carries_what_install_ci_produces():
    """The shape ships here first, and stays byte-current.

    A copy edited in place is the fork-by-copy these verbs exist to prevent,
    and it would be invisible — the file still looks like the one that was
    installed. Edit the source under installables/ and re-install.

    PARTIAL, and decided the same way `install-agents` is: verify.yml runs
    `make milestone`, which this repo has, so it MUST be present and current.
    The other three read the version out of a project file at merge — this
    package versions in pyproject.toml, and bumps at CLOSE rather than at
    merge. Installing them here would be three workflows guarding a flow this
    repo does not run — the reasoning that kept `install-hooks` un-self-hosted
    until 0.23.0 gave its corpus a job here (the ledger couriers; the hook
    headers are then this repo's `project config`, edited on purpose). What is
    carried must be current; what is absent is legitimately absent.
    """
    repo_root.cache_clear()
    load_config.cache_clear()
    previous = Path.cwd()
    os.chdir(REPO_ROOT)
    try:
        present = [rel for _, rel in install.PLANS['install-ci']
                   if (REPO_ROOT / rel).is_file()]
        assert WORKFLOW in present, (
            f'{WORKFLOW} is not present in this repo — the one workflow it '
            f'self-hosts, and the floor this test would otherwise pass over')
        code, out = run('install-ci', '--diff')
        assert code == 0, out
        stale = [rel for rel in present if f'{rel} already current' not in out]
        assert not stale, (
            f'not byte-current in this repo: {stale}\n{out}')
    finally:
        os.chdir(previous)
        repo_root.cache_clear()
        load_config.cache_clear()


def test_this_repo_carries_the_roles_it_runs_byte_current():
    """PARTIAL-roster self-hosting, decided with the roster.

    This package runs its own SDLC with the verification pair; the base
    roster (architect, po, developer, reviewer, …) is dispatched by a
    consumer's orchestrator and has nothing to act on in this repo — the same reasoning that keeps
    `install-hooks` un-self-hosted. So the contract is conditional, not
    total: the verification pair MUST be present, and any plan destination
    this repo carries MUST be byte-current with its installable. A local
    `.claude/agents/` file that shadows a roster name with edited content is
    the invisible fork-by-copy; a role this repo does not run is legitimately
    absent.
    """
    present: list[str] = []
    for name, rel in install.PLANS['install-agents']:
        target = REPO_ROOT / rel
        if target.is_file():
            present.append(rel)
            assert (target.read_text(encoding='utf-8')
                    == install.body_of(name)), (
                f'{rel} differs from installables/{name} — edit the source '
                f'under installables/ and re-install with --force')
    # The floor: a repo that stops carrying the pair has stopped self-hosting
    # the verbs it ships, and this test would otherwise pass vacuously.
    for rel in AGENTS[:2]:
        assert rel in present, f'{rel} is not present in this repo'


def test_every_installable_on_disk_is_reachable_through_a_verb():
    """A payload no verb names is a file that ships in the wheel, drifts, and
    is discovered by nobody. Asked of the directory, not of a second list.

    `init` names three of them — the project-owned seeds — and it is a verb
    like the rest, so its table joins the union rather than being carved out.
    """
    from agentic_sdlc.core import walk
    from agentic_sdlc.core.walk import Kind
    from agentic_sdlc.repo import init
    found = walk.children(REPO_ROOT / 'src/agentic_sdlc/repo/installables',
                          Kind.FILE)
    on_disk = {p.name for p in found.kept}
    named = {name for entries in install.PLANS.values()
             for name, _ in entries} | {name for name, _ in init.SEEDS}
    assert on_disk == named, (
        f'unreachable: {sorted(on_disk - named)}; '
        f'missing: {sorted(named - on_disk)}')


# --- the exec bit: the mode is part of the write ------------------------------
# The census (every `.sh` runnable, nothing else) rides on
# `test_the_verb_writes_its_files_and_a_second_run_is_a_no_op`; these two are
# the mode's two edges.
def _mode(target: Path) -> int:
    return target.stat().st_mode & 0o777


def test_the_exec_bit_does_not_widen_who_may_read_the_file():
    """`chmod +x`, not `chmod 755`. The execute bit joins the classes that can
    already read the file — widening a 0600 destination to world-readable is a
    permission decision no install verb was asked to make."""
    with repo() as root:
        target = root / 'tools/dev/gdk_gate.sh'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('stale\n', encoding='utf-8')
        target.chmod(0o600)
        code, out = run('install-gates', '--force')
        assert code == 0, out
        assert _mode(target) == 0o700, oct(_mode(target))


def test_a_byte_current_script_missing_the_bit_is_repaired_not_reported_current():
    """The consumer this fix exists for already ran the old verb: their files
    are byte-identical and 0644. A re-run that reported them `already current`
    would leave every one of them broken forever."""
    with repo() as root:
        code, out = run('install-gates')
        assert code == 0, out
        target = root / 'tools/dev/gdk_gate.sh'
        target.chmod(0o644)

        code, out = run('install-gates')
        assert code == 0, out
        assert os.access(target, os.X_OK), 'the re-run left it unrunnable'
        assert 'wrote tools/dev/gdk_gate.sh' in out, out

        # …and it converges: the run after that has nothing left to do.
        code, out = run('install-gates')
        assert code == 0, out
        assert 'already current' in out and 'wrote ' not in out, out


# --- install-hooks prints the settings.json entries that FIRE the hooks -------
# A git hook runs because `tools/setup-hooks.sh` points core.hooksPath at the
# directory. A Claude Code hook runs because `.claude/settings.json` names it,
# and nothing else does — so an install that wrote eleven files and said
# nothing about registration left six guards on disk and none of them armed.
# The block is PRINTED rather than written: settings.json is hand-maintained,
# carries permissions/env/MCP entries this package knows nothing about, and
# these verbs write a whole file or refuse.
CC_HOOKS = tuple(rel for rel in HOOKS if rel.startswith('tools/hooks/cc-'))
ASYNC_HOOKS = ('tools/hooks/cc-ledger-subagent.sh',
               'tools/hooks/cc-ledger-session.sh')


def test_install_hooks_prints_the_settings_entries_that_fire_every_cc_hook():
    """Every installed Claude Code hook is named in the snippet, and the
    snippet parses as JSON — a block an operator has to repair before pasting
    is a block they will hand-write instead, which is the fork this verb
    exists to prevent."""
    with repo():
        code, out = run('install-hooks')
        assert code == 0, out
        assert '.claude/settings.json' in out, out
        opened = out.index('{\n  "hooks"')
        block = json.loads(out[opened:out.rindex('}') + 1])
        commands = [entry['command']
                    for event in block['hooks'].values()
                    for group in event for entry in group['hooks']]
        for rel in CC_HOOKS:
            assert any(rel in command for command in commands), (
                f'{rel} is installed but no settings entry fires it\n{out}')


def test_the_two_ledger_couriers_are_registered_async_and_unmatched():
    """`async` is the whole reason a Stop hook may parse a transcript at all
    (D4): the orchestrator must not wait for it. And neither courier carries a
    matcher — every dispatch costs something, so a roster of agent types here
    would silently stop measuring the day a repo adds one."""
    with repo():
        code, out = run('install-hooks')
        assert code == 0, out
        block = json.loads(out[out.index('{\n  "hooks"'):out.rindex('}') + 1])
        wired = {}
        for event, groups in block['hooks'].items():
            for group in groups:
                for entry in group['hooks']:
                    for rel in ASYNC_HOOKS:
                        if rel in entry['command']:
                            wired[rel] = (event, group.get('matcher'), entry)
        assert set(wired) == set(ASYNC_HOOKS), wired
        subagent_event, subagent_matcher, subagent = wired[ASYNC_HOOKS[0]]
        session_event, session_matcher, session = wired[ASYNC_HOOKS[1]]
        assert subagent_event == 'SubagentStop', wired
        assert session_event == 'Stop', wired
        assert subagent_matcher is None and session_matcher is None, wired
        assert subagent['async'] is True and session['async'] is True, wired


# --- a collision withholds ITS file, and a header-only one is named as one ----
# The v0.23.0 adoption defect, from both consumers: four hooks differed ONLY
# inside the `project config` header the file invites them to edit, so the two
# hooks that release ADDED — pure additions, nothing in their way — could not be
# installed at all. The way through was `--force` and then re-editing four files
# by hand, or copying two files out of a uv cache. The whole-plan DECISION
# stands; what a collision withholds is that file.
SHELL_OPEN = ("# --- project config (yours to edit after install — the file "
              "is your repo's) --")
SHELL_CLOSE = '# ' + '-' * 77
MD_OPEN = '## Project config (yours to edit after install)'


def header_edited(text: str, line: str = 'MY_PROJECT_SAYS=1') -> str:
    """`text` with `line` inserted INSIDE its project-config block — the edit
    the block exists to invite.

    Finds the OPENING marker on its own and inserts straight after it: a
    fixture built with the production span finder would prove nothing about
    the production span finder.
    """
    lines = text.splitlines(keepends=True)
    for index, one in enumerate(lines):
        if MD_OPEN in one:
            return ''.join(lines[:index + 1] + [f'\n{line}\n'] +
                           lines[index + 1:])
        if 'project config (yours to edit after install' in one:
            return ''.join(lines[:index + 1] + [f'{line}\n'] +
                           lines[index + 1:])
    raise AssertionError('no project-config block to edit')


HEADER_EDITED_HOOKS = ('tools/hooks/cc-stop-gate.sh',
                       'tools/hooks/pre-push',
                       'tools/hooks/prepare-commit-msg')


def a_consumer_mid_adoption(root: Path) -> dict[str, str]:
    """The corpus installed, four headers edited, the two couriers not yet
    there — the state a real adopter of v0.23.0 was in. Returns the edited text
    of each file, to be compared byte for byte afterwards."""
    assert run('install-hooks')[0] == 0
    mine = {}
    for rel in HEADER_EDITED_HOOKS:
        target = root / rel
        mine[rel] = header_edited(target.read_text(encoding='utf-8'))
        target.write_text(mine[rel], encoding='utf-8')
    for rel in ASYNC_HOOKS:
        (root / rel).unlink()
    return mine


def test_a_new_hook_lands_on_a_consumer_whose_headers_are_edited():
    """The bug, whole, asked of ONE run: the couriers land byte-current with
    their installables, the edited headers survive byte for byte, the run
    exits 1 naming what it withheld, and the report says what the disk says.

    The exit code carries the withholding, and only the exit code can: a
    caller that reads it alone must never be told the roster is on disk when
    one of it is the operator's own file. `code == 1` alone is what the
    defect already did, by writing nothing at all — what has to be true
    TOGETHER is that the additions landed AND the run still exits 1.

    The report is the one an operator can act on: `nothing was written` over
    a repo that gained two files is the defect `core.apply` exists to end,
    and a header-only collision is named as one, because the rest of the
    file is byte-current and the repair is to do nothing — not --force and
    four re-edits. Once the collisions are gone the same command is a clean
    0: the non-zero is about the withholding, not about having spoken."""
    with repo() as root:
        mine = a_consumer_mid_adoption(root)
        code, out = refuse('install-hooks')
        assert [rel for rel in ASYNC_HOOKS if (root / rel).is_file()] == list(
            ASYNC_HOOKS), out
        assert code == 1, f'additions landed and the run exited {code}\n{out}'
        for rel in ASYNC_HOOKS:
            assert (root / rel).read_text(encoding='utf-8') == install.body_of(
                Path(rel).name), rel
        for rel, text in mine.items():
            assert (root / rel).read_text(encoding='utf-8') == text, (
                f'{rel} was overwritten by a run that did not say so')
            assert rel in out, f'{rel} was withheld and not named\n{out}'
        for rel in HOOKS:
            assert (root / rel).is_file(), rel
        assert 'nothing was written' not in out, out
        wrote = {line.split('wrote ', 1)[1].strip()
                 for line in out.splitlines() if '] wrote ' in line}
        assert wrote == set(ASYNC_HOOKS), out
        assert out.count(install.HEADER_ONLY_NOTE) == len(
            HEADER_EDITED_HOOKS), out
        assert 'byte-current' in out, out
        assert '--force would replace the header too' in out, out
        for rel in HEADER_EDITED_HOOKS:
            (root / rel).write_text(
                install.body_of(Path(rel).name), encoding='utf-8')
        assert refuse('install-hooks')[0] == 0


def test_a_body_difference_is_not_reported_as_a_header_only_one():
    """The predicate is only allowed to be wrong in one direction. An edit
    OUTSIDE the block is a plain collision, and saying `byte-current` about it
    would send an operator past a real change.

    The one CLI-altitude case for the predicate's False side: the other
    shapes (header AND body edited, the marker itself rewritten, …) are
    `HOSTILE` rows below, at the function altitude, and this case is what
    proves the verb wires the predicate's answer into its report."""
    rel = 'tools/hooks/pre-push'
    with repo() as root:
        assert run('install-hooks')[0] == 0
        target = root / rel
        target.write_text(
            target.read_text(encoding='utf-8') + '\n# my own trailer\n',
            encoding='utf-8')
        code, out = refuse('install-hooks')
        assert code == 1, out
        assert rel in out, out
        assert install.HEADER_ONLY_NOTE not in out, out
        assert 'byte-current' not in out, out


def test_diff_names_a_header_only_difference_before_the_hunks():
    """--diff is where the operator looks first, and where this bug started:
    two additions, five `already current`, and four diffs that said nothing
    about being only the header."""
    with repo() as root:
        mine = a_consumer_mid_adoption(root)
        code, out = run('install-hooks', '--diff')
        assert code == 0, out
        for rel in mine:
            assert f'{rel} differs ONLY inside its project-config header' in out
            assert f'--- a/{rel}' in out, out
        for rel in ASYNC_HOOKS:
            assert f'{rel} does not exist' in out, out
        # Reading is not writing: the couriers are still absent afterwards.
        for rel in ASYNC_HOOKS:
            assert not (root / rel).exists(), rel


def test_force_replaces_a_header_only_collision_whole_header_included():
    """The decision, pinned. The installer does NOT merge the block: a
    preserved consumer header carried onto a newer body is an older contract
    under a newer one, and this corpus reads its header under `set -u` behind
    a fail-open trap."""
    with repo() as root:
        mine = a_consumer_mid_adoption(root)
        code, out = run('install-hooks', '--force')
        assert code == 0, out
        for rel in mine:
            assert (root / rel).read_text(encoding='utf-8') == (
                install.body_of(Path(rel).name)), rel
            assert 'MY_PROJECT_SAYS' not in (
                root / rel).read_text(encoding='utf-8'), rel


def test_a_defect_refuses_the_whole_command_and_writes_no_addition():
    """A collision is the operator's decision about that file; a DEFECT is a
    destination the command cannot write at all, and its repair is the same for
    every entry. Nothing is written, so `nothing was written` is still true —
    and this is the case that keeps proving the plan is decided before the
    first byte."""
    with repo() as root:
        (root / 'tools/hooks').mkdir(parents=True)
        (root / 'tools/hooks/pre-push').mkdir()
        code, out = refuse('install-hooks')
        assert code == 1, out
        assert 'is a directory' in out and 'nothing was written' in out, out
        for rel in HOOKS:
            if rel != 'tools/hooks/pre-push':
                assert not (root / rel).exists(), (
                    f'{rel} was written past a defect')


def test_a_run_with_both_a_collision_and_a_defect_names_both():
    with repo() as root:
        assert run('install-hooks')[0] == 0
        target = root / 'tools/hooks/cc-stop-gate.sh'
        target.write_text(header_edited(target.read_text(encoding='utf-8')),
                          encoding='utf-8')
        doomed = root / 'tools/setup-hooks.sh'
        doomed.unlink()
        doomed.mkdir()
        code, out = refuse('install-hooks')
        assert code == 1, out
        assert 'tools/hooks/cc-stop-gate.sh' in out, out
        assert 'tools/setup-hooks.sh is a directory' in out, out
        assert 'nothing was written' in out, out


def test_collisions_with_no_additions_still_say_nothing_was_written():
    """The all-or-nothing sentence is not retired — it is CHECKED. A run whose
    only entries are current or colliding wrote nothing, and says so."""
    rel = 'tools/hooks/pre-push'
    with repo() as root:
        assert run('install-hooks')[0] == 0
        target = root / rel
        target.write_text(header_edited(target.read_text(encoding='utf-8')),
                          encoding='utf-8')
        code, out = refuse('install-hooks')
        assert code == 1, out
        assert 'nothing was written' in out, out
        assert '] wrote ' not in out, out


def test_every_config_headed_installable_reads_as_header_only_when_edited():
    """The grammar covers every block this package actually ships — shell and
    markdown — rather than the two files a test happened to pick."""
    checked = 0
    for command in ('install-hooks', 'install-agents', 'install-gates'):
        for name, rel in install.PLANS[command]:
            body = install.body_of(name)
            if install.config_block_span(body) is None:
                continue
            checked += 1
            assert install.header_only_difference(header_edited(body), body), (
                f'{rel} carries a block this cannot locate')
            assert not install.header_only_difference(body + 'trailing\n',
                                                      body), rel
    # A floor, not a count: it catches a census that COLLAPSES (a moved
    # PLANS key, a broken `body_of`) without going stale every time the roster
    # changes size. It was 25 when install-gates carried thirteen engine
    # runners; the roster is 18 now and the floor moved with it, deliberately
    # and in the open.
    assert checked >= 15, f'only {checked} config-headed installables scanned'


# --- the predicate, against hostile pairs ------------------------------------
# `header_only_difference` is a claim that the REST of a file is byte-current,
# and an operator who believes it wrongly walks past a real change. Every case
# below is written to make it answer True when it must not.
STOCK = ('#!/usr/bin/env bash\n'
         '# what this hook is\n'
         'set -eu\n'
         '\n'
         f'{SHELL_OPEN}\n'
         '# the branch you protect\n'
         'BRANCH="main"\n'
         f'{SHELL_CLOSE}\n'
         'echo "$BRANCH"\n'
         'exit 0\n')
MD_STOCK = ('---\nname: x\n---\n'
            '\n'
            f'{MD_OPEN}\n'
            '\n```text\nproject: yours\n```\n'
            '\n## How you work\n'
            'the body\n')


def swap(text: str, old: str, new: str) -> str:
    assert old in text, f'{old!r} is not in the fixture'
    return text.replace(old, new)


HOSTILE = {
    'an edit inside the block':
        (swap(STOCK, 'BRANCH="main"', 'BRANCH="main staging"'), True),
    'a line added inside the block':
        (swap(STOCK, 'BRANCH="main"', 'BRANCH="main"\nEXTRA=1'), True),
    'the whole block emptied':
        (swap(STOCK, '# the branch you protect\nBRANCH="main"\n', ''), True),
    'a markdown block edited':
        (swap(MD_STOCK, 'project: yours', 'project: mine'), True),
    'an edit ABOVE the block':
        (swap(STOCK, '# what this hook is', '# what MY hook is'), False),
    'an edit BELOW the block':
        (swap(STOCK, 'echo "$BRANCH"', 'echo "$BRANCH" >&2'), False),
    'a line appended past the end':
        (STOCK + '# mine\n', False),
    'an edit in the header AND the body':
        (swap(swap(STOCK, 'BRANCH="main"', 'BRANCH="x"'), 'exit 0', 'exit 1'),
         False),
    'the opening marker rewritten':
        (swap(STOCK, 'project config (yours to edit after install', 'mine ('),
         False),
    'the closing marker deleted':
        (swap(STOCK, f'{SHELL_CLOSE}\n', ''), False),
    'a second rule line inside the block':
        (swap(STOCK, 'BRANCH="main"', f'{SHELL_CLOSE}\nBRANCH="main"'), False),
    'the block moved below the body':
        (swap(STOCK, f'{SHELL_OPEN}\n# the branch you protect\n'
                     f'BRANCH="main"\n{SHELL_CLOSE}\n', '')
         + f'{SHELL_OPEN}\n# the branch you protect\nBRANCH="main"\n'
           f'{SHELL_CLOSE}\n', False),
    'no block at all on the consumer side':
        ('#!/usr/bin/env bash\nmine, deliberately\n', False),
    'nothing but the block':
        (f'{SHELL_OPEN}\nBRANCH="main"\n{SHELL_CLOSE}\n', False),
    'an empty file':
        ('', False),
    'the trailing newline dropped':
        (STOCK.rstrip('\n'), False),
    'a markdown edit past the block':
        (swap(MD_STOCK, 'the body', 'MY body'), False),
    'the markdown heading rewritten':
        (swap(MD_STOCK, MD_OPEN, '## My config'), False),
}


def test_header_only_difference_answers_every_hostile_pair():
    """One case, every row: the pure predicate costs nothing per row, so a
    parametrize here only multiplied the collected count."""
    wrong = []
    for label, (mine, expected) in HOSTILE.items():
        stock = MD_STOCK if 'markdown' in label else STOCK
        if install.header_only_difference(mine, stock) is not expected:
            wrong.append(f'{label}: expected {expected}')
    assert not wrong, wrong


def test_the_predicate_needs_a_block_on_BOTH_sides():
    """A destination that carries a block and an installable that does not is
    not a header-only difference — there is no header on the side that would
    be written."""
    plain = 'no block here\n'
    assert install.header_only_difference(STOCK, plain) is False
    assert install.header_only_difference(plain, STOCK) is False
    assert install.header_only_difference(plain, plain) is False


def test_the_span_excludes_its_own_markers_and_stops_at_the_first_close():
    """Both ends are the installable's, not the consumer's: an edit that lands
    ON a marker is outside the span by construction."""
    lines = STOCK.splitlines()
    start, end = install.config_block_span(STOCK)
    assert lines[start - 1] == SHELL_OPEN, lines[start - 1]
    assert lines[end] == SHELL_CLOSE, lines[end]
    assert lines[start:end] == ['# the branch you protect', 'BRANCH="main"']
    # An unterminated block runs to the end of the file rather than to a
    # guessed boundary — and the pair test above proves that answers False.
    open_ended = swap(STOCK, f'{SHELL_CLOSE}\n', '')
    assert install.config_block_span(open_ended) == (
        5, len(open_ended.splitlines()))
    assert install.config_block_span('') is None
    assert install.config_block_span('nothing in here\n') is None


# --- the docs are a second list, so they are asserted rather than trusted ------
class TestTheReadmeInstallerTableIsTheRoutedSet:
    """E1 + T3, and the same shape as `test_gate_roster`: a table a human
    maintains beside a dict a machine dispatches from is two lists, and the
    second one lies. It already did — `install-runners` shipped the Godot
    runners, left with them at 0.2.0, and stayed documented here for a release
    afterwards, while `install-gates` (which replaced it) and `install-sdlc`
    had no row at all.
    """

    README = REPO / 'README.md' if 'REPO' in dir() else None

    def _rows(self) -> set[str]:
        import re
        from pathlib import Path
        readme = Path(__file__).resolve().parents[1] / 'README.md'
        text = readme.read_text(encoding='utf-8')
        return {m.group(1) for m in
                re.finditer(r'^\| `(install-[a-z-]+)` \|', text, re.M)}

    def test_every_routed_installer_has_a_row(self):
        missing = sorted(set(install.PLANS) - self._rows())
        assert missing == [], (
            f'{missing} are routed by `install.PLANS` and documented in no '
            f"README row — a consumer cannot discover a verb that isn't there")

    def test_every_row_names_a_routed_installer(self):
        stray = sorted(self._rows() - set(install.PLANS))
        assert stray == [], (
            f'README documents {stray}, which this version does not route. '
            f'A verb that left is worse than one never documented: a reader '
            f'runs it and gets exit 2.')


# --- one wording, five files (0.2.0/every-gate-reports-its-cost story 04) ------
class TestTheNameBothCommandsBlockIsOneWording:
    """Five hand-maintained near-copies drift. This is what keeps them one.

    The rule they carry cost 31 minutes to learn: a dispatch names BOTH the
    narrow command and the wide one, with their measured costs, because an
    agent given one command uses it as its inner loop — nothing told it there
    was another. 154 s against 0.9 s is 170x, and it is the economics this
    whole milestone exists to end.

    **G4 is why this test exists rather than the block alone.** Story 04 filed
    close evidence naming a commit that touched none of its five files, its
    acceptance criterion 1 asked for exactly this assertion, and there was
    none — so a reader of that `## Close` would have taken the criterion as
    delivered. A test comparing the copies is the difference between a rule
    that ships and a rule that was described.
    """

    CARRIERS = ('architect.md', 'po.md', 'developer.md',
                'verification-builder.md', 'test-writer.md')
    OPEN = '<!-- BEGIN name-both-commands -->'
    CLOSE = '<!-- END name-both-commands -->'

    def _block(self, name: str) -> str:
        body = install.body_of(name)
        assert self.OPEN in body and self.CLOSE in body, (
            f'{name} carries no name-both-commands block')
        start = body.index(self.OPEN) + len(self.OPEN)
        return body[start:body.index(self.CLOSE)]

    def test_the_five_carriers_are_byte_identical(self):
        blocks = {name: self._block(name) for name in self.CARRIERS}
        first = blocks[self.CARRIERS[0]]
        drifted = [n for n, b in blocks.items() if b != first]
        assert drifted == [], (
            f'{drifted} carry a different wording from '
            f'{self.CARRIERS[0]} — five near-copies is five chances to say '
            f'something slightly different, and the differences are what get '
            f'the whole block deleted')

    def test_the_agents_whose_work_has_no_inner_loop_do_not_carry_it(self):
        """A rule pasted where it does not apply is the noise that gets the
        whole block deleted. `changelog-writer` and friends sync prose against
        a known diff; there is no narrow command to name."""
        for name in ('changelog-writer.md', 'doc-hygiene.md', 'tech-writer.md',
                     'pm-operator.md'):
            assert self.OPEN not in install.body_of(name), name
