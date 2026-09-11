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
already proven there. A claim about what a write did to the disk is asserted
here; a claim about the installables' PROSE is not, with ONE exception at the
foot of this module — an installable that NAMES something this package retired
is a false instruction to an operator, and until
`bg-the-shipped-rules-name-retired-behaviour` nothing in the repo graded these
files at all.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shlex
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
from agentic_sdlc.repo.checks import pm as pm_check  # noqa: E402


@contextlib.contextmanager
def repo(files: dict[str, str] | None = None, name: str = 'repo'):
    """An empty repo, cwd'd into. `.git` is a MARKER directory: `repo_root`
    walks up for it and never asks git, so `git init` here was a process
    per case that bought nothing (tests/support/pm.py `_mark`).

    `name` is the directory the checkout sits in, because a path this package
    interpolates into a shell command is only as safe as the worst checkout
    path — see `SPACED_ROOT`.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / name
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


def streams(command: str, *argv: str) -> tuple[int, str, str]:
    """Exit code, stdout and stderr APART — for the claims about which stream a
    fact reached. A refusal on stderr is not a report on stdout, and the summary
    an operator builds reads one of them."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = install.main(command, list(argv))
    return code, out.getvalue(), err.getvalue()


def headers(out: str) -> list[str]:
    """The summary a consumer actually builds: `grep '^\\[install\\]'`."""
    return [line for line in out.splitlines()
            if line.startswith(install.REPORT_PREFIX)]


def dispositions(out: str, command: str) -> dict[str, list[str]]:
    """That summary, keyed by destination — the run's PROSE (the next-step
    paragraph, the retirement report) dropped, because it is not a file's line.

    A header line is `[install] <rel> …` or `[install] wrote <rel>`, anchored:
    two shapes, so a destination can be counted rather than searched for.
    """
    lines = headers(out)
    return {rel: [line for line in lines
                  if line.startswith(f'{install.REPORT_PREFIX} {rel} ')
                  or line == f'{install.REPORT_PREFIX} wrote {rel}']
            for rel in DESTINATIONS[command]}


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
# verdict line, and the include that calls it. A language kit installs its own
# runners and a `Makefile.tiers` that hangs them off this include's `-include`
# seam (decision D2) — one verb carrying both is what blocked splitting this
# package in two.
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
        # One header line per destination, on the run that WROTE them: the
        # next-step paragraph names paths too, and a summary that counts those
        # is a summary that can also miss one (0.3.0).
        one_each(out, command)
        code, out = run(command)
        assert code == 0, out
        assert out.count('already current') == len(DESTINATIONS[command]), out
        one_each(out, command)
        assert {rel: (root / rel).read_text(encoding='utf-8')
                for rel in DESTINATIONS[command]} == bodies
        code, out = run(command, '--diff')
        assert code == 0
        assert out.count('already current') == len(DESTINATIONS[command]), out
        one_each(out, command)
        assert '@@' not in out, out


def one_each(out: str, command: str) -> None:
    """Every destination of `command` named by exactly one header line."""
    for rel, lines in dispositions(out, command).items():
        assert len(lines) == 1, (
            f'{command}: {rel} has {len(lines)} header line(s), not one — a '
            f'summary built from these omits it or double-counts it\n{out}')


@pytest.mark.parametrize('command', VERBS)
def test_no_run_prose_opens_with_a_destination_path(command):
    """`[install] <path> …` is a destination's own line, and the shape is what
    makes the summary countable. A next-step paragraph that OPENS with a path
    wears that shape, and `install-sdlc`'s did — one file, two header lines."""
    for rel in DESTINATIONS[command]:
        assert not install._NEXT_STEP[command].startswith(rel), (
            f'{command}: the next-step paragraph opens with {rel}, so it reads '
            f'as that file\'s header line')


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
# "follow-up" — never prose that merely mentions the flag. The release notes are
# `changelog:` on each grain and `_grain_notes()` reads them, so the rule follows
# its subject rather than the file that used to hold it; a released record is
# never rewritten to satisfy a rule written after it.
INSTRUCTION_SITES = ('.claude/skills/release/SKILL.md',)
INSTRUCTION_MARKER = 'follow-up'
# The cost, in any of the words somebody would reach for. A closed list, so
# what the gate accepts is reviewable rather than guessed at.
NAMES_THE_COST = ('per-file', 'per file', 'PER FILE', 'whole-set', 'whole set',
                  'all four')
# Claims that are FALSE of a whole-set --force, in the spellings this package
# has actually used. Closed, and each one earns its place by having shipped.
COST_FREE_CLAIMS = ('re-applying nothing', 're-applies nothing',
                    'nothing to re-apply')


def _grain_notes() -> list[tuple[str, str]]:
    """[(where, sentence)] — every live `changelog:` in this repo's own tree.

    The release notes moved onto the grains at 0.6.0, so the rule scans the
    field. Read off the documents rather than through the CLI: this module is
    in the `not shell` tier and must boot nothing.
    """
    out = []
    for kind in ('milestones', 'features', 'stories', 'bugs'):
        for path in sorted((REPO_ROOT / 'pm/roadmap' / kind).glob('*.md')):
            for line in path.read_text(encoding='utf-8').split('\n'):
                if line.startswith('---') and out:
                    break
                if line.startswith('changelog:'):
                    text = line.split(':', 1)[1].strip()
                    if text:
                        out.append((f'{kind}/{path.name}', text))
                    break
    return out


def test_no_shipped_instruction_offers_force_without_naming_what_it_costs():
    """A release note is read once, acted on, and not re-read. So the sentence
    that sends a consumer to `--force` has to carry the one fact that decides
    whether they should: the verb writes a SET, and a file they edited on
    purpose is in it."""
    whole_set = {verb for verb, entries in install.PLANS.items()
                 if len(entries) > 1}
    assert whole_set, 'no verb writes a set — this rule has no subject'
    checked = 0
    sites = [(rel, (REPO_ROOT / rel).read_text(encoding='utf-8'))
             for rel in INSTRUCTION_SITES]
    sites += [(where, note) for where, note in _grain_notes()]
    for rel, body in sites:
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
                     f'{INSTRUCTION_SITES} or any grain\'s `changelog:` — '
                     'the rule scanned nothing')


@pytest.mark.parametrize('command', VERBS)
def test_diff_prints_a_unified_diff_and_writes_nothing(command):
    """…and a MODIFIED file gets a header line of its own.

    The 0.2.0 defect, from an adoption: `--diff` headed an ADDITION and printed
    a bare hunk for a change, so `grep '^[install]'` over a 1,211-line diff
    reported one file and silently omitted the most consequential one. It was
    found by counting lines and hunting `+++` markers. Every disposition gets a
    header now, so the summary is complete by construction.
    """
    first = DESTINATIONS[command][0]
    mine = 'my own version, deliberately\n'
    with repo({first: mine}) as root:
        code, out = run(command, '--diff')
        assert code == 0, out
        # A real unified diff of the DIFFERING file …
        assert f'--- a/{first}' in out and f'+++ b/{first}' in out, out
        assert '-my own version, deliberately' in out, out
        # … under a header line, so the grep-summary names it …
        assert dispositions(out, command)[first] == [
            f'{install.REPORT_PREFIX} {install.BODY_DIFFERS.format(rel=first)}'
        ], out
        # … and every other destination is named exactly once too.
        one_each(out, command)
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


# --- what a verb STOPPED shipping ---------------------------------------------
# The other half of the same silence. A split dropped seven make targets between
# two pins; one was named in that consumer's `[gates] extra`, so `make check`
# broke with `No rule to make target`, and the other six surfaced only because
# that repo ran a doc check that validates make targets — a gate in the CONSUMER
# doing the installer's job. A retired FLAG has not even that: it lives in prose
# ("the way stories close"), and the sentence survives the bump green.
#
# Nothing this package ships was withdrawn between 0.2.0 and 0.3.0, so
# `install.RETIREMENTS` is empty and a row invented to exercise it would print a
# false sentence in a consumer's terminal. The table below is the FIXTURE the
# mechanism is proven against; it is not this package's history.
THIS = install.__version__
OLD_TARGET = 'a-target-withdrawn-long-ago'
GONE_TARGET = 'a-target-a-split-dropped'
GONE_FLAG = 'some-verb --a-flag-that-left'
GONE_FILE = '.claude/agents/a-role-that-was-withdrawn.md'
FIXTURE = (
    install.Retirement('0.0.2', 'install-gates', targets=(OLD_TARGET,)),
    install.Retirement(THIS, 'install-gates',
                       targets=(GONE_TARGET,), flags=(GONE_FLAG,)),
    install.Retirement(THIS, 'install-hooks', targets=('another-verbs-loss',)),
    install.Retirement(THIS, 'install-agents', files=(GONE_FILE,)),
)


def reported(command: str, stamp: str | None) -> set[str]:
    """Every target, flag and file the report would name, as one set."""
    found = install.retired_since(command, stamp, rows=FIXTURE)
    return {name for row in found
            for name in row.targets + row.flags + row.files}


@pytest.mark.parametrize('stamp,expected', [
    # An unbumped pin: the whole span between where they are and where this is.
    ('v0.0.1', {OLD_TARGET, GONE_TARGET, GONE_FLAG}),
    # Already bumped — the ONE case the defect was reported from. The pin said
    # the new version and the run said nothing, so `(stamp, current]` read empty
    # and the consumer learnt the removals from a broken build. This version's
    # own row is in the span whatever the pin says.
    (f'v{THIS}', {GONE_TARGET, GONE_FLAG}),
    # No pin this can read: report the whole record rather than none of it.
    (None, {OLD_TARGET, GONE_TARGET, GONE_FLAG}),
    # A pin AHEAD of the package running: still never narrower than this version.
    ('v9.9.9', {GONE_TARGET, GONE_FLAG}),
])
def test_the_span_between_the_pin_and_this_version_is_what_is_reported(
        stamp, expected):
    assert reported('install-gates', stamp) == expected


def test_the_report_is_per_verb_and_says_so_when_nothing_was_withdrawn():
    """A verb reports its OWN losses — another verb's row in the same table is
    not its news — and a span that withdrew nothing prints a line saying so,
    because a report that found nothing and a report that never ran read
    identically in a transcript (hard rule 4)."""
    assert reported('install-hooks', None) == {'another-verbs-loss'}
    lines = install.retirement_report('install-ci', None, rows=FIXTURE)
    assert len(lines) == 1, lines
    assert 'install-ci' in lines[0] and 'no longer shipped' not in lines[0]
    assert 'withdrawn no make target, verb flag or file' in lines[0]
    # And a verb the SHIPPED table has no row for is honest the same way.
    assert install.retirement_report('install-gates', None) == [
        install.NOTHING_WITHDRAWN.format(
            command='install-gates',
            span=install._span_phrase(None))]


def test_a_withdrawn_FILE_is_named_because_an_install_never_deletes():
    """The quiet retirement, and 0.6.0 is the first real one.

    An install verb writes a SET and never deletes, so a file this package
    stops shipping simply STAYS in a consumer's tree — correct-looking, and
    pointed at nothing. A withdrawn make target announces itself the next time
    `make` runs; a withdrawn agent definition announces itself never, until
    somebody dispatches it.
    """
    lines = install.retirement_report('install-agents', None, rows=FIXTURE)
    assert len(lines) == 1, lines
    assert GONE_FILE in lines[0]
    assert 'no longer written' in lines[0]
    # The reason a consumer needs, in the line: nothing deleted it for them.
    assert 'never deletes' in lines[0]


def test_the_shipped_table_names_the_changelog_writer_at_0_6_0():
    """The row is real, not a fixture. `ft-the-changelog-is-a-field-and-a-verb`
    deleted `CHANGELOG.md`; the agent whose whole role was maintaining it went
    with it, and a bumping consumer keeps the orphan unless told."""
    rows = [r for r in install.RETIREMENTS if r.version == '0.6.0']
    assert rows, 'the 0.6.0 retirement row is gone'
    files = [f for r in rows for f in r.files]
    assert '.claude/agents/changelog-writer.md' in files, files
    # It reports at 0.6.0 and is silent before it.
    after = install.retirement_report('install-agents', None, current='0.6.0')
    assert any('changelog-writer' in line for line in after), after
    before = install.retirement_report('install-agents', None, current='0.5.0')
    assert not any('changelog-writer' in line for line in before), before


# A version this cannot read is not a version this may narrow on: every one of
# these has to widen the span to the whole record. Traversal, empty, whitespace,
# an over-long string and a bare word are the shapes the matrix asks of any
# grammar here; the pin is a file's contents, so all of them are reachable.
MALFORMED = ('', '   ', 'v', '0.2', 'latest', 'not-a-version', '../0.1.0',
             'v' + '9' * 400, '0.2.0.0.0.0'[::-1], '\n')


@pytest.mark.parametrize('stamp', MALFORMED)
def test_a_version_this_cannot_read_widens_the_span_never_narrows_it(stamp):
    """Both ends of the comparison. A stamp that will not parse reports the
    whole record, and a ROW whose version will not parse is reported whatever
    the stamp says — the cardinal sin here is the quiet omission, not the
    extra line."""
    assert reported('install-gates', stamp) == {OLD_TARGET, GONE_TARGET,
                                                GONE_FLAG}
    unreadable = (install.Retirement('who-knows', 'install-gates',
                                     targets=('cannot-be-placed',)),)
    assert install.retired_since('install-gates', 'v9.9.9',
                                 rows=unreadable) == unreadable


def test_every_declared_retirement_names_a_routed_verb_and_a_readable_version():
    """The gate on the table itself, so the row a future release appends is
    checked the day it lands. The shipped table is empty today, so the fixture
    rides with it: a check that scanned zero rows would prove nothing."""
    checked = 0
    for row in install.RETIREMENTS + FIXTURE:
        assert row.command in install.PLANS, (
            f'{row.version} names {row.command}, which no verb routes')
        assert install._version_key(row.version) is not None, (
            f'{row.command} row {row.version!r} is not a version')
        assert row.targets or row.flags or row.files, (
            f'{row.command} {row.version} withdrew nothing — a row with '
            f'nothing to say is a row that should not exist')
        checked += 1
    assert checked >= len(FIXTURE)


def test_a_run_and_a_diff_both_carry_the_report_and_init_does_not(monkeypatch):
    """The verb's altitude: the report reaches the terminal on a real run and
    on `--diff`, the pin is READ and never written, and the tree `init` is
    wiring for the first time is spared a span it cannot have.

    The pin is read through `conveyor.steps.PIN_LINE`, the one grammar for that
    line (SDLC §5): the `?=` spelling below is one a hand-rolled `:=` regex
    would miss, and missing it would report OLD_TARGET here rather than the
    narrowed span the pin asks for.
    """
    monkeypatch.setattr(install, 'RETIREMENTS', FIXTURE)
    pin = f'DEVKIT_VERSION ?= v{THIS}\ninclude Makefile.devkit\n'
    with repo({'Makefile': pin}) as root:
        for argv in ((), ('--diff',)):
            code, out, err = streams('install-gates', *argv)
            assert code == 0, out + err
            said = [line for line in headers(out)
                    if 'no longer shipped' in line or 'retired verb' in line]
            assert len(said) == 2, out
            assert GONE_TARGET in said[0] and GONE_FLAG in said[1], out
            assert 'No rule to make target' in said[0], out
            assert OLD_TARGET not in out, (
                'the pin was not read: the span widened past what it names')
        assert (root / 'Makefile').read_text(encoding='utf-8') == pin
        # `init`'s call — a fresh tree has no span, and nothing it could lose.
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            install.main('install-gates', ['--force'], next_step=False)
        assert 'no longer shipped' not in buffer.getvalue(), buffer.getvalue()


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
    `test_a_new_hook_lands_on_a_consumer_whose_headers_are_edited`.

    The withheld file gets its header line on STDOUT with the rest (0.3.0): the
    refusal on stderr is a second stream, and a summary of the report proper
    had one file missing from it — the one the operator has to decide about."""
    command = 'install-agents'
    rels = DESTINATIONS[command]
    mine = 'my own version, deliberately\n'
    with repo({rels[-1]: mine}) as root:
        code, out, err = streams(command)
        assert code == 1, out + err
        for earlier in rels[:-1]:
            assert (root / earlier).is_file(), (
                f'{earlier} was withheld by a collision on {rels[-1]}')
            assert f'wrote {earlier}' in out, out
        assert (root / rels[-1]).read_text(encoding='utf-8') == mine
        assert dispositions(out, command)[rels[-1]] == [
            f'{install.REPORT_PREFIX} '
            f'{install.WITHHELD.format(rel=rels[-1])}'], out
        one_each(out, command)
        assert f'wrote {rels[-1]}' not in out, out
        assert 'nothing was written' not in out + err, out + err


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


def _registered_wiring(root: Path) -> tuple[set, list[str]]:
    """((event, matcher, script rel, async) …, the COMMITTED commands).

    Both settings files, because the block `install-hooks` emits carries
    ABSOLUTE paths and a public repo must not commit a machine path — so the
    honest home for it is `.claude/settings.local.json`, which the harness
    writes itself and this repo gitignores. Reading only the committed file
    would call a correctly-wired checkout unwired.
    """
    wiring, committed = set(), []
    for rel in (install.AGENT_SETTINGS, SETTINGS_LOCAL):
        path = root / rel
        if not path.is_file():
            continue
        block = json.loads(path.read_text(encoding='utf-8'))
        for event, groups in (block.get('hooks') or {}).items():
            for group in groups:
                for entry in group.get('hooks', []):
                    command = entry.get('command', '')
                    parts = shlex.split(command)
                    if len(parts) != 2 or parts[0] != 'bash':
                        continue
                    if rel == install.AGENT_SETTINGS:
                        committed.append(command)
                    script = parts[1]
                    for _name, target in install.PLANS['install-hooks']:
                        if script == target or script.endswith(f'/{target}'):
                            wiring.add((event, group.get('matcher'), target,
                                        bool(entry.get('async'))))
    return wiring, committed


def test_this_repo_registers_the_wiring_install_hooks_emits():
    """The self-hosting gate CLAUDE.md makes of `.claude/settings.json`.

    **This is the tree whose nine dispatches recorded zero rows** (issue #13),
    and nothing graded its wiring: the `install-ci` and `install-agents`
    self-hosting cases have no `install-hooks` twin, and `--diff` writes and
    compares nothing here (`--write-settings writes nothing under --diff`). A
    hook this verb starts emitting and this repo never registers is a guard on
    disk that never fires, discovered by nobody.

    Asked of the wiring, not of the bytes: the paths this verb emits are
    ABSOLUTE and machine-specific, so byte-parity with what a run prints is
    the one thing this repo must NOT have.
    """
    wiring, _committed = _registered_wiring(REPO_ROOT)
    missing = sorted(set(install._WIRING) - wiring)
    assert not missing, (
        f'this repo registers no hook for {missing} — `agentic-sdlc '
        f'install-hooks {install.SETTINGS_FLAG}` writes '
        f'{install.AGENT_SETTINGS} when nothing is in the way, and prints the '
        f'block when something is; paste it into {SETTINGS_LOCAL}')


def test_this_repo_commits_no_machine_path_in_its_hook_wiring():
    """The other half, and the reason the first is asked of both files.

    `install-hooks` emits `bash /Users/<someone>/<their tree>/tools/hooks/…`.
    That is correct for the operator who ran it and wrong for everyone who
    clones this public repo — a committed absolute path names one machine's
    filesystem, and rule 8's spirit is that a shipped file knows nothing about
    who is reading it. The absolute block belongs in the gitignored per-user
    override, with `GDK_LEDGER_ROOT` exported by any session rooted elsewhere;
    what stays committed resolves for a session rooted here.
    """
    _wiring, committed = _registered_wiring(REPO_ROOT)
    absolute = [command for command in committed
                if Path(shlex.split(command)[1]).is_absolute()]
    assert not absolute, (
        f'{install.AGENT_SETTINGS} is committed and carries a machine path: '
        f'{absolute}. Move the absolute block to {SETTINGS_LOCAL} (gitignored) '
        f'and export GDK_LEDGER_ROOT for a session rooted outside this tree')


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
        commands = _commands(_block(out))
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
        block = _block(out)
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


# --- the wiring is one act, and it is PORTABLE (0.5.0, issue #13) -------------
# This milestone's own build recorded zero rows across nine dispatches. The
# block carried RELATIVE script paths, which resolve only when the harness's cwd
# IS the repo root, and the run named no file to put them in — a fragment with
# no destination, pasted by hand, wrong invisibly, with every surface reporting
# success. So: absolute paths, the destination named, and the write OFFERED.


def _block(out: str) -> dict:
    """The pasteable block, parsed — an operator who has to repair it first
    hand-writes their own instead, which is the fork this verb prevents."""
    return json.loads(out[out.index('{\n  "hooks"'):out.rindex('}') + 1])


def _commands(block: dict) -> list[str]:
    return [entry['command'] for event in block['hooks'].values()
            for group in event for entry in group['hooks']]


# A checkout path with a space in it: `~/my repo`, `~/Google Drive/…`, and
# every macOS home under `Application Support`. The relative form the block
# used to carry had no space to break on, so absolutising the path INTRODUCED
# the class — and the run still exits 0 and reports a write.
SPACED_ROOT = 'my repo'
# The harness's own per-user override: it writes this file itself, and a
# repo gitignores it. An ABSOLUTE block cannot be committed to a public
# tree, so this is where a self-hosting checkout puts the one it was
# printed. Spelled off `checks.pm`, never a second copy of the name.
SETTINGS_LOCAL = pm_check.AGENT_SETTINGS_LOCAL


def _script_of(command: str) -> str:
    """The script a SHELL would run, not the text after the first space.

    `command.split(' ', 1)[1]` under a spaced root yields the whole remainder,
    which is still absolute and still an existing file — so the assertion the
    guard makes stays true on a command `sh -c` cannot run.
    """
    parts = shlex.split(command)
    assert parts[0] == 'bash' and len(parts) == 2, command
    return parts[1]


def test_every_emitted_command_is_an_absolute_path_to_an_installed_file():
    """`bash tools/hooks/cc-ledger-subagent.sh` fires nothing from a session
    rooted at a parent directory, and says nothing when it does not."""
    with repo() as root:
        code, out = run('install-hooks')
        assert code == 0, out
        commands = _commands(_block(out))
        assert commands, out
        for command in commands:
            script = Path(_script_of(command))
            assert script.is_absolute(), f'{command} is relative\n{out}'
            assert script.is_file(), f'{command} names no installed file'
            # `.resolve()`: the emitted path is the one `repo_root()` found,
            # symlinks and all, which is the canonical spelling of the tree.
            assert script.is_relative_to(root.resolve()), command


def test_a_checkout_path_with_a_space_emits_a_command_a_shell_can_run():
    """The emitted command is handed to a shell, so it is QUOTED.

    Probed end to end before the fix: under `.../my repo`, `--write-settings`
    exited 0, wrote the file and reported it, and every one of the five
    commands ran as `bash /private/.../my` — five hooks, none of them firing,
    nothing red anywhere. This asserts what a shell would do with the string
    rather than what a `split(' ', 1)` sees.
    """
    with repo(name=SPACED_ROOT) as root:
        assert ' ' in str(root), root
        code, out = run('install-hooks', install.SETTINGS_FLAG)
        assert code == 0, out
        written = json.loads(
            (root / install.AGENT_SETTINGS).read_text(encoding='utf-8'))
        for command in _commands(written):
            script = Path(_script_of(command))
            assert script.is_file(), f'{command} names no installed file'
            assert script.is_relative_to(root.resolve()), command
        # The block a `sh -c` would run, split by the shell's own rules: one
        # word for `bash`, one for the path, whatever the path holds.
        assert all(len(shlex.split(command)) == 2
                   for command in _commands(written)), written


def test_the_write_reports_what_it_did_and_not_what_it_cannot_observe():
    """Rule 4 at the one surface this milestone exists to make honest.

    `these hooks are in force now` asserts an outcome this package cannot see:
    whether a harness LOADS this file depends on the session's project root,
    which is issue #13's whole story and is spelled in this same run's own
    block. The write is a fact; being in force is an inference — and the
    concrete `GDK_LEDGER_ROOT` export, which lives only in the pasteable block
    that a successful write does NOT print, rides on this line instead.
    """
    with repo() as root:
        code, out = run('install-hooks', install.SETTINGS_FLAG)
        assert code == 0, out
        wrote = [line for line in headers(out)
                 if install.AGENT_SETTINGS in line and 'wrote' in line]
        assert len(wrote) == 1, out
        assert 'in force now' not in out, out
        assert f'GDK_LEDGER_ROOT={root.resolve()}' in wrote[0], wrote


def test_the_run_names_the_file_the_wiring_belongs_in_and_offers_to_write_it():
    """A fragment with no destination is the step no gate observes. The name
    is the ABSOLUTE path, and the offer names the flag that lands it."""
    with repo() as root:
        code, out = run('install-hooks')
        assert code == 0, out
        assert str(root / install.AGENT_SETTINGS) in out, out
        assert install.SETTINGS_FLAG in out, out
        # The per-user override, named through the READER's constant: the verb
        # that prints it and the rules that read it back must not drift into
        # two spellings of one file name.
        assert SETTINGS_LOCAL in out, out
        assert not (root / install.AGENT_SETTINGS).exists(), (
            'the default run wrote a harness config nobody asked it to')


def test_write_settings_lands_the_file_and_the_second_run_is_a_no_op():
    """The offer, taken. What lands is what was printed, and the run after it
    has nothing to do — an installer's write is idempotent."""
    with repo() as root:
        code, out = run('install-hooks', install.SETTINGS_FLAG)
        assert code == 0, out
        target = root / install.AGENT_SETTINGS
        assert target.is_file(), out
        written = json.loads(target.read_text(encoding='utf-8'))
        assert written == json.loads(install.hook_settings(root.resolve()))
        for rel in CC_HOOKS:
            assert any(rel in command for command in _commands(written)), rel
        code, again = run('install-hooks', install.SETTINGS_FLAG)
        assert code == 0, again
        assert 'already carries exactly this block' in again, again


def test_a_settings_file_that_exists_is_never_merged_into_or_replaced():
    """The one destination `--force` does not take. It carries permissions,
    env and MCP entries this package knows nothing about, so overwriting it
    would be rule 4's second sin wearing an installer's clothes."""
    mine = '{"permissions": {"allow": ["Bash"]}}\n'
    with repo() as root:
        assert run('install-hooks')[0] == 0
        target = root / install.AGENT_SETTINGS
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(mine, encoding='utf-8')
        for argv in ((install.SETTINGS_FLAG,),
                     ('--force', install.SETTINGS_FLAG)):
            code, out = refuse('install-hooks', *argv)
            assert code == 1, out
            assert install.AGENT_SETTINGS in out, out
            assert target.read_text(encoding='utf-8') == mine, argv
        # And the block is still printed, because pasting is now the way in.
        assert _commands(_block(out)), out


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
    # changes size. It moves with the roster, deliberately and in the open.
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
        whole block deleted. `tech-writer` and friends sync prose against
        a known diff; there is no narrow command to name."""
        for name in ('doc-hygiene.md', 'tech-writer.md',
                     'pm-operator.md'):
            assert self.OPEN not in install.body_of(name), name


def test_install_hooks_says_the_settings_are_not_yet_in_force_and_who_sets_the_grain():
    """0.4.0. Two rule-11 holes in one paragraph, both found in review.

    The block is PRINTED and never written (`.claude/settings.json` is the
    consumer's and has no merge), and a printed block reads as informational —
    which is how step 1 gets skipped and a consumer runs for a milestone with
    the couriers on disk and nothing firing them. And `GDK_LEDGER_GRAIN` is the
    one `GDK_LEDGER_*` a courier cannot take off the payload: nothing in this
    package exports it, so the paragraph has to say who does.
    """
    from agentic_sdlc.repo import install
    said = install._NEXT_STEP['install-hooks']
    assert 'NOT YET IN FORCE' in said
    assert 'adopt' in said and 'U2' in said
    assert 'GDK_LEDGER_GRAIN' in said
    assert 'Nothing exports it for you' in said
# --- the report is complete on the FAILING run too (review I1/I4/I5) ----------
def _heads(out: str) -> list[str]:
    return [ln for ln in out.split('\n') if ln.startswith('[install]')]


def test_a_defect_still_heads_every_file_the_verb_owns():
    """Review I1. `grep -c '^[install]'` answered 0 for a verb that owns two
    files, on the path where a human most needs the list. The criterion is
    "whatever its disposition", and a refusal is a disposition."""
    with repo() as root:
        (root / 'Makefile.devkit').mkdir()          # a DIRECTORY where a file goes
        code, out = run('install-gates')
        assert code == 1, out
        heads = _heads(out)
        assert len(heads) == 2, out
        assert any('Makefile.devkit CANNOT be written' in h for h in heads), out
        assert any('gdk_gate.sh was reachable' in h for h in heads), out


def test_diff_refuses_a_directory_rather_than_calling_it_an_addition():
    """Review I4: `--diff` said "does not exist — the whole file is an addition"
    at exit 0 while a real run refused at exit 1. `--diff` is what a consumer
    reads BEFORE the run, so the disagreement costs the most there."""
    with repo() as root:
        (root / 'Makefile.devkit').mkdir()
        code, out = run('install-gates', '--diff')
        assert code == 0, out
        assert 'is a directory' in out, out
        assert 'a real run REFUSES this' in out, out
        assert 'the whole file is an addition' not in out.split('gdk_gate')[0], out


def test_an_undecodable_destination_says_so_rather_than_differs():
    # Review I5: the decode branch handed back an EMPTY defect string, so
    # `if unreadable:` was dead for it and the file was reported as one that
    # "differs" — which it does not, because it cannot be compared at all.
    with repo() as root:
        (root / 'Makefile.devkit').write_bytes(b'\x00\xff\xfe')
        # A COLLISION, not a defect: `--force` can still replace it, which is
        # useful. What changed is that the refusal says which of the two it is.
        text, defect = install.read_destination(root / 'Makefile.devkit')
        assert text is None and defect == ''
        code, out = refuse('install-gates')
        assert code == 1, out
        assert install.UNDECODABLE_NOTE in out, out
        # ...and specifically NOT the word the old path used for it.
        assert 'Makefile.devkit exists and differs' not in out, out


def test_the_sixth_installer_heads_its_files_under_the_same_prefix():
    """Review I2: `pm install-skills` is the sixth installer in CLAUDE.md's
    self-hosting list, and it prefixed `[pm]`, so the documented
    `grep '^[install]'` summary returned 0 for both of its files."""
    from agentic_sdlc.repo.pm import cli as pm_cli, skills
    with repo() as root:
        (root / 'devkit.toml').write_text(_flow(), encoding='utf-8')
        load_config.cache_clear()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            pm_cli.main(['install-skills'])
        heads = _heads(buf.getvalue())
        # Asked of the PLAN, not counted: 0.4.0 added the handoff skill as a
        # third entry, and a hand-written `== 2` made that a red build for a
        # roster change the criterion has no opinion about.
        assert len(heads) == len(skills.GUIDANCE_PLAN), buf.getvalue()
        for _name, rel in skills.GUIDANCE_PLAN:
            assert any(rel in h for h in heads), buf.getvalue()


def _flow() -> str:
    from support.pm import with_flow
    return with_flow('')


# --- the shipped instructions name nothing this package retired ---------------
# `bg-the-shipped-rules-name-retired-behaviour`: two files `pm install-skills`
# writes into every consumer, and that auto-load into every session, told an
# operator to do things this package deleted — maintain `ROADMAP.md` (retired in
# 0.3.0), trust `pm validate` to hold an id to its path (V2/V3, retired in
# 0.4.0). They are neither code nor a doc in `[doc] scope`, so nothing graded
# them, and an agent that trusts an installed rule over the tool's own output is
# behaving correctly. The defect is ours.
#
# The names come from the code's OWN retirement registries, so a verb, key or
# check retired tomorrow joins this sweep with no edit here — the two cannot
# drift apart. What this CANNOT catch is a false claim that names nothing
# retired ("`pm new` scaffolds to the schema", the sibling half of that bug):
# grading a sentence against behaviour is a different mechanism.
RETIRED_ELSEWHERE = {
    # Retired outside a registry the code can be asked for.
    'ROADMAP.md': 'retired in 0.3.0 — `pm roadmap` + releases.md `order`',
    '<!-- pm:execution -->': 'retired in 0.4.0 with V6 — `order:` on the parent',
    '[[verify.narrow]]': 'retired — the story rung is a make target',
    'CHANGELOG.md': 'retired in 0.6.0 — `changelog:` on the grain, '
                    '`agentic-sdlc changelog` renders',
}
# A migration NOTE is the legitimate way to name a retired thing, and the seed
# devkit.toml is full of them. So the allowance is exactly that: the line has to
# say the word.
MIGRATION_NOTE = 'retire'
# Everything a consumer receives verbatim: `install-*`'s payloads, the guidance
# `pm install-skills` writes, and the grain templates `pm templates` copies out.
INSTALLED_SOURCES = ('src/agentic_sdlc/repo/installables',
                     'src/agentic_sdlc/repo/pm/guidance',
                     'src/agentic_sdlc/repo/pm/templates')
NOT_SHIPPED = ('__init__.py',)


def _retired_names() -> dict[str, str]:
    """{the spelling that would appear in prose: what it is}, off the code."""
    from agentic_sdlc.repo.pm import cli as pm_cli, vocabulary
    from agentic_sdlc.repo.verify import rules
    names = {f'pm {verb}': 'a retired pm verb'
             for verb in pm_cli.RETIRED_COMMANDS}
    names.update({key: 'a retired [pm] config key'
                  for key in vocabulary.RETIRED_KEYS})
    names.update({check: 'a retired check id'
                  for check in vocabulary.RETIRED_CHECKS})
    names.update({f'[{section}]': 'a retired config section'
                  for section in vocabulary.RETIRED_SECTIONS})
    names.update({f'[verify] {key}': 'a retired [verify] key'
                  for key in rules.RETIRED})
    names.update(RETIRED_ELSEWHERE)
    return names


def _boundaried(name: str) -> re.Pattern:
    """`pm move` must not match `pm moved`; `[[verify.narrow]]` has no word
    edge to guard, so the guard is added per side."""
    left = r'(?<![\w-])' if name[0].isalnum() or name[0] == '_' else ''
    right = r'(?![\w-])' if name[-1].isalnum() or name[-1] == '_' else ''
    return re.compile(left + re.escape(name) + right)


def test_no_installable_names_a_retired_thing_except_as_a_migration_note():
    names = _retired_names()
    assert names, 'the retirement registries are empty — this scanned nothing'
    patterns = {name: _boundaried(name) for name in names}
    scanned = 0
    found: list[str] = []
    for source in INSTALLED_SOURCES:
        directory = REPO_ROOT / source
        assert directory.is_dir(), f'{source} is not a directory'
        for path in sorted(directory.rglob('*')):
            if (not path.is_file() or path.suffix == '.pyc'
                    or path.name in NOT_SHIPPED):
                continue
            scanned += 1
            body = path.read_text(encoding='utf-8', errors='replace')
            for number, line in enumerate(body.splitlines(), 1):
                if MIGRATION_NOTE in line.lower():
                    continue
                for name, pattern in patterns.items():
                    if pattern.search(line):
                        found.append(
                            f'{source}/{path.name}:{number} names {name!r} '
                            f'({names[name]}) as if it were live: '
                            f'{line.strip()[:90]}')
    assert scanned, f'no installable was read from {INSTALLED_SOURCES}'
    assert not found, (
        f'{len(found)} shipped instruction(s) name something this package '
        f'retired; say "retired" on the line to keep it as a migration note:\n'
        + '\n'.join(f'    {row}' for row in found))


# --- every definition names the verbs its ROLE reaches for --------------------
# `ft-a-surface-reaches-its-reader-or-it-is-decoration` sweep 1. Across the 12
# shipped definitions `ready-for` appeared 0 times, `pm ledger` 0 and
# `lesson record` 0 — a dispatched `developer` was never told the entry rung
# exists, so six briefs this milestone hand-pasted a roster the package already
# ships. That is rule 11's own test failed by this package's own surface.
#
# The section is a POINTER: the invocation, and in a few words what it ANSWERS.
# Never what the verb does or how it behaves — that is
# `ft-prose-that-restates-a-verb-is-rendered-or-gone`'s rule, and five sentences
# drifted in one day the last time this package restated.
#
# The sibling above proves no definition names something RETIRED. This one is
# the other half, and it is the load-bearing one: every verb a definition NAMES
# resolves against the live CLI, asked of the code rather than of a list typed
# here, so a citation goes RED the day its verb leaves.
ROLE_VERBS_OPEN = '<!-- BEGIN role-verbs -->'
ROLE_VERBS_CLOSE = '<!-- END role-verbs -->'
# A citation is BACKTICKED, so the answer beside it is never parsed as argv.
# `[^`\n]` because a code span does not span lines here.
CITATION = re.compile(r'`(agentic-sdlc [^`\n]+)`')


def _verb_rosters() -> dict[tuple[str, ...], tuple[str, ...]]:
    """{the token path resolved so far: what this package routes after it}.

    Every value is asked of the shipped code. `routed_verbs()` is imported
    rather than copied — it reads `cli.main()`'s branches by AST, so it cannot
    miss a verb, and a second copy here would go stale the way the definitions
    did. Cross-module import is this suite's established shape
    (test_cli_surface itself imports from test_check_budget).
    """
    from test_cli_surface import routed_verbs
    from agentic_sdlc import cli as root_cli
    from agentic_sdlc.repo.conveyor import driver, lessons
    from agentic_sdlc.repo.pm import cli as pm_cli, ready_for
    from agentic_sdlc.repo.verify.main import MODES
    return {(): tuple(sorted(routed_verbs())),
            ('pm',): pm_cli.commands(),
            ('pm', 'ready-for'): tuple(ready_for.KINDS),
            # Review S4: `pm ledger report` is a shipped citation whose last
            # token was graded as an argument, because this stopped one
            # position short of a real sub-roster.
            ('pm', 'ledger'): pm_cli.ledger_commands(),
            ('check',): tuple(root_cli.KNOWN_GATES),
            ('close',): tuple(driver.CLOSE_OPERATIONS),
            ('lesson',): (lessons.RECORD, lessons.SHOW),
            ('verify',): tuple(f'--{mode}' for mode in MODES)}


def _unrouted(citation: str,
              rosters: dict[tuple[str, ...], tuple[str, ...]]) -> str:
    """The prefix of `citation` this package does not route, or `''`.

    It walks only as deep as a ROSTER exists for. A token past the last one is
    an argument — an id, a path, a state word this project declared in its own
    `devkit.toml` — and grading it here would be inventing a claim rather than
    reading one.
    """
    path: tuple[str, ...] = ()
    for token in citation.split()[1:]:
        roster = rosters.get(path)
        if roster is None:
            return ''
        if token.startswith('-') and not any(o.startswith('-') for o in roster):
            # A flag where the roster holds verbs: `pm --help`. This package
            # publishes no roster of flags at that position, so it stops.
            return ''
        if token not in roster:
            return ' '.join((*path, token))
        path = (*path, token)
    return ''


def _role_verb_citations() -> dict[str, list[tuple[int, str]]]:
    """{installable: [(line number in its SOURCE, citation)]} for the whole
    file — not just the block. A retired citation in a config paragraph is the
    same false instruction as one in the roster."""
    found = {}
    for name, _rel in install.PLANS['install-agents']:
        body = install.body_of(name)
        found[name] = [(number, citation)
                       for number, line in enumerate(body.splitlines(), 1)
                       for citation in CITATION.findall(line)]
    return found


def test_every_agent_definition_names_the_verbs_its_role_reaches_for():
    """(a) of the ship criterion: a definition with no verbs in it leaves every
    dispatch to hand-paste them, which is the measurement that opened sweep 1.
    An EMPTY section counts as none — a heading is not a pointer."""
    plans = install.PLANS['install-agents']
    assert len(plans) == len(AGENTS), 'the agent roster moved without this test'
    bare: list[str] = []
    for name, _rel in plans:
        body = install.body_of(name)
        if ROLE_VERBS_OPEN not in body or ROLE_VERBS_CLOSE not in body:
            bare.append(f'{name} carries no {ROLE_VERBS_OPEN} section')
            continue
        start = body.index(ROLE_VERBS_OPEN) + len(ROLE_VERBS_OPEN)
        block = body[start:body.index(ROLE_VERBS_CLOSE)]
        if not CITATION.findall(block):
            bare.append(f'{name} has the section and names no verb in it')
    assert not bare, (
        f'{len(bare)} shipped definition(s) name none of their role\'s verbs, '
        f'so a dispatch into that role has to hand-paste them:\n'
        + '\n'.join(f'    {row}' for row in bare))


def test_every_verb_an_agent_definition_names_resolves_against_the_cli():
    """(b), and the half that can go red on its own. Asked of the router, the
    gate roster, the verify modes and the pm table — never of a list here."""
    rosters = _verb_rosters()
    assert len(rosters[()]) > 5, 'the router census collapsed — this graded nothing'
    assert len(rosters[('pm',)]) > 5, 'the pm table collapsed'
    cited = _role_verb_citations()
    assert sum(len(rows) for rows in cited.values()), 'no citation was scanned'
    unrouted: list[str] = []
    for name, rows in cited.items():
        for number, citation in rows:
            bad = _unrouted(citation, rosters)
            if bad:
                unrouted.append(
                    f'{INSTALLED_SOURCES[0]}/{name}:{number} cites '
                    f'`{citation}` — this package routes no '
                    f'`agentic-sdlc {bad}`')
    assert not unrouted, (
        f'{len(unrouted)} shipped definition(s) cite a verb this package does '
        f'not route; a definition naming a retired verb is a false instruction '
        f'to an operator who cannot check it:\n'
        + '\n'.join(f'    {row}' for row in unrouted))
