"""test_conveyor_steps.py — the release checks, each a read of a real tree.

Every check here is a question about a scratch git repo, and every answer is
asserted against the bytes the check left behind (none) as much as against
the sentence it returned. Under D12 no check writes: `version-sync` READS the
version sites and names the release commit as the caller's, the changelog is
read and never retitled, and the gate is a configured command whose exit code
is the whole answer.
"""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import with_flow  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.config import ConfigError  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo import emit  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, lessons, steps  # noqa: E402
from agentic_sdlc.repo.pm import ledger, vocabulary  # noqa: E402

VERSION = '9.9.9'
ROADMAP_DIR = 'pm/roadmap'
MDIR = f'{ROADMAP_DIR}/{VERSION}-scratch'
MILESTONE = f'''---
id: "{VERSION}"
name: A scratch milestone
status: building
branch: milestone/{VERSION}
---

# A scratch milestone
'''


@contextlib.contextmanager
def tree(files: dict[str, str] | None = None, config: str = ''):
    """A scratch repo with a milestone directory, committed, entered.
    `config` is the devkit.toml MINUS the flow declaration (`with_flow`)."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        (root / MDIR).mkdir(parents=True)
        (root / MDIR / 'milestone.md').write_text(MILESTONE, encoding='utf-8')
        (root / 'devkit.toml').write_text(with_flow(config), encoding='utf-8')
        for rel, body in (files or {}).items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        subprocess.run(['git', 'init', '-q', '-b', f'milestone/{VERSION}'],
                       cwd=root, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
        subprocess.run(['git', '-c', 'user.email=t@example.invalid',
                        '-c', 'user.name=t', 'commit', '-qm', 'scratch'],
                       cwd=root, check=True)
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


def ctx(root: Path) -> driver.Context:
    return driver.Context(root=root, operation='release', version=VERSION)


def check(name: str, root: Path) -> driver.Answer:
    return steps.RELEASE_STEPS[name].check(ctx(root))


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob('*'))
            if p.is_file() and '.git' not in p.parts}


# --- the census ---------------------------------------------------------------
def test_the_release_registry_is_exactly_the_shipped_list_and_every_check_has_a_sentence():
    """Bites: a name in the list nothing runs, a check nothing lists, or a
    check the rendered protocol cannot describe."""
    assert set(steps.RELEASE_STEPS) == set(steps.DEFAULT_RELEASE_STEPS)
    assert steps.DEFAULT_RELEASE_STEPS == (
        'tree-clean', 'on-milestone-branch', 'changelog-unreleased-nonempty',
        'features-done', 'findings-resolved', 'version-sync', 'gate')
    for operation, names in steps.DEFAULT_STEPS.items():
        for name in names:
            assert name in steps.STEP_DOC, (operation, name)
    for name in ('milestone-done', 'changelog-retitle', 'push-branch', 'tag',
                 'readme-pins', 'pr-open', 'ci-green', 'prove-artifact'):
        assert name not in steps.RELEASE_STEPS, f'{name} survived D12'


# Inputs no belt reads since 0.6.0: the file, its section, the bug fields.
RETIRED_INPUTS = (('CHANGELOG.md', 'Unreleased')
                  + tuple(sorted(vocabulary.RETIRED_FIELDS)))


def test_every_registry_sentence_names_what_its_check_reads_and_nothing_retired():
    """Bites: a check re-pointed at a new input keeping its old sentence.
    `changelog-unreleased-nonempty` has graded each closed grain's
    `changelog:` field since 0.6.0, and `install-sdlc` went on rendering it as
    counting bullets under `## Unreleased` (#33). The step id stays — an id is
    contract — so only the sentence can tell a consumer what runs."""
    from agentic_sdlc.repo.pm import changelog as clog
    for name, sentence in steps.STEP_DOC.items():
        for retired in RETIRED_INPUTS:
            assert retired not in sentence, (name, retired, sentence)
    # What each release check reads, spelled as its sentence must name it.
    reads = {
        'tree-clean': '`git status --porcelain`',
        'on-milestone-branch': '`branch:`',
        'changelog-unreleased-nonempty': f'`{clog.FIELD}:`',
        'features-done': '`pm ready-for milestone',
        'findings-resolved': '`pm ready-for tag',
    }
    for name, token in reads.items():
        assert token in steps.STEP_DOC[name], (name, token,
                                              steps.STEP_DOC[name])


# --- tree-clean ---------------------------------------------------------------
def test_tree_clean_names_every_modified_path_and_the_first_is_not_short_by_one():
    """Bites: `git status --porcelain` is COLUMNAR and a blanket strip ate
    column 0 of the first line — `SDLC.md` reported as `DLC.md`. Two files,
    compared exactly, because `'DLC.md' in 'SDLC.md'`."""
    with tree({'SDLC.md': 'one\n', 'zzz.md': 'one\n'}) as root:
        assert check('tree-clean', root).is_true
        for name in ('SDLC.md', 'zzz.md'):
            (root / name).write_text('two\n', encoding='utf-8')
        answer = check('tree-clean', root)
        assert not answer.is_true
        listed = answer.detail.split(': ', 1)[1].split(', ')
        assert listed == ['SDLC.md', 'zzz.md'], listed


def test_tree_clean_and_committed_answer_the_same_tree_the_same_way():
    """Bites: the two cleanliness checks drifting apart again.

    `committed` (story belt) excluded the roadmap directory and `tree-clean`
    (release) did not, so the same tree satisfied one belt and could never
    satisfy the other — and a belt writes in that directory BY DESIGN, so the
    release side was unrecoverable rather than merely strict. Both are asked of
    one tree here, dirty inside the directory and dirty outside it.
    """
    with tree({'src/a.py': 'one\n'}) as root:
        both = (steps.RELEASE_STEPS['tree-clean'],
                steps.STORY_STEPS['committed'])
        (root / MDIR / 'ledger.jsonl').write_text('{"kind": "lesson"}\n',
                                                  encoding='utf-8')
        for shipped in both:
            answer = shipped.check(ctx(root))
            assert answer.is_true, (
                f'{shipped.name} refused a tree whose ONLY modified path is '
                f'inside {ROADMAP_DIR}/ — the belt wrote it: {answer.detail}')
            assert ROADMAP_DIR in answer.detail, (
                f'{shipped.name} skipped a path and did not say so '
                f'(rule 11): {answer.detail}')
        (root / 'src/a.py').write_text('two\n', encoding='utf-8')
        for shipped in both:
            answer = shipped.check(ctx(root))
            assert not answer.is_true and 'src/a.py' in answer.detail
            assert answer.detail.startswith('1 ') and \
                MDIR not in answer.detail, (
                f'{shipped.name} counted or named the roadmap path it does '
                f'not read: {answer.detail}')


# --- a lesson is never a gate -------------------------------------------------
# `test_conveyor_lessons.py` owns the lesson surfaces and runs in the unit tier
# over scripted checks. The claim BELOW cannot be made there: the surfacer
# writes to the filesystem, so the only check that can catch it reads the
# filesystem, and reading it means git — the shell tier, which is here.
LESSON_AT = '2026-09-07T00:00:00Z'
LESSON_SOURCE = 'docs/reviews/scratch.md'
LESSON_TEXT = 'the belt writes in the roadmap directory by design'


def lesson_row(grain: str) -> dict:
    """One `lesson` row, minted from the READER's own field list so a renamed
    column goes red here rather than surfacing nothing."""
    values = {'grain': grain, 'rule': '', 'source': LESSON_SOURCE,
              'text': LESSON_TEXT, 'ts': LESSON_AT}
    return {'kind': lessons.KIND,
            **{name: values[name] for name in lessons.FIELDS}}


def commit(root: Path) -> None:
    """Everything on disk, committed — so `tree-clean` starts true and every
    later modification is the BELT's."""
    subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
    subprocess.run(['git', '-c', 'user.email=t@example.invalid',
                    '-c', 'user.name=t', 'commit', '-q', '--allow-empty',
                    '-m', 'recorded'], cwd=root, check=True)


def release_over_tree_clean(root: Path) -> tuple[int, list[str], list[str]]:
    """`release` through the VERB over the real `tree-clean` and nothing else:
    (exit code, stdout lines, the states the write seam was handed)."""
    writes: list[str] = []

    def write(_ctx: driver.Context, state: str,
              skipped: tuple = ()) -> tuple[bool, str]:
        writes.append(state)
        return True, f'wrote {state}'

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = driver.main(['release', VERSION], root=root,
                           registry={'tree-clean':
                                     steps.RELEASE_STEPS['tree-clean']},
                           steps=('tree-clean',), write=write)
    return code, out.getvalue().splitlines(), writes


def test_a_recorded_lesson_changes_no_verdict_no_exit_code_and_no_write():
    """**A lesson is never a gate**, asked of a check that READS the filesystem
    the surfacer just wrote to.

    Bites the shape a scripted-check case cannot see: `Surfacer.at_entry` runs
    before the first check and `emit.emit` appends `lesson.enter` to the
    milestone's git-TRACKED ledger, so a `tree-clean` that counted the roadmap
    directory turned `release` from exit 0 to exit 1 — and it never cleared,
    because committing the row only made room for the next one. Two trees built
    identically, one carrying a lesson against the milestone, both committed
    clean before the belt runs.

    `[emit]` is DECLARED here because declaring it is what turns emission on
    (0.5.0/D1): without the section nothing is written to the ledger, the
    surfacer's write never happens, and this case would pass while probing
    nothing — which is why the emission count is asserted before the verdicts.
    """
    runs = []
    for recorded in (False, True):
        with tree(config=f'[{emit.SECTION}]\n') as root:
            mledger = ledger.ledger_for(vocabulary.load(), VERSION)
            if recorded:
                ledger.append_to(mledger, lesson_row(VERSION))
            commit(root)
            runs.append(release_over_tree_clean(root))
            said = (mledger.read_text(encoding='utf-8')
                    if mledger.is_file() else '')
            emitted = said.count(f'"{lessons.KIND}.')
            assert emitted == (1 if recorded else 0), (
                f'the surfacer emitted {emitted} event(s) into the tracked '
                f'ledger; if the emission moved, this case no longer probes '
                f'what it says it does')
    (bare_code, bare_lines, bare_writes) = runs[0]
    (code, lines, writes) = runs[1]

    surfaced = [line for line in lines if f'] {lessons.WORD}' in line]
    assert surfaced == [f'[release] {lessons.WORD}: {lessons.SCOPE_GRAIN} '
                        f'{VERSION} — {LESSON_TEXT} '
                        f'(source: {LESSON_SOURCE})'], (
        f'nothing surfaced, so the case proves nothing: {lines}')
    assert (code, writes) == (bare_code, bare_writes) == (0, ['done']), (
        f'a recorded lesson changed the belt: bare {bare_code}/{bare_writes} '
        f'vs {code}/{writes}')
    assert [line for line in lines if f'] {lessons.WORD}' not in line] == \
        bare_lines, 'a lesson reshaped a line that is not its own (rule 6)'


# --- on-milestone-branch ------------------------------------------------------
def test_on_milestone_branch_reads_the_stamp_and_will_not_assume_without_one():
    """Bites: a release cut from whatever branch was checked out, or a
    missing `branch:` stamp read as 'the current one must be right'."""
    with tree() as root:
        assert check('on-milestone-branch', root).is_true
        subprocess.run(['git', 'switch', '-q', '-c', 'elsewhere'], cwd=root,
                       check=True)
        wrong = check('on-milestone-branch', root)
        assert wrong.truth is driver.Truth.FALSE
        assert 'elsewhere' in wrong.detail and f'milestone/{VERSION}' in wrong.detail
        stamped = root / MDIR / 'milestone.md'
        stamped.write_text(MILESTONE.replace(f'branch: milestone/{VERSION}\n', ''),
                           encoding='utf-8')
        assert check('on-milestone-branch', root).truth is \
            driver.Truth.UNVERIFIABLE


# --- the changelog ------------------------------------------------------------
# 0.6.0: the step grades GRAINS, not a file. It counted bullets in
# `CHANGELOG.md` — one bullet passed a release of forty grains, and nothing
# bound a bullet to the work it described. The file is retired; the parameter
# table below moved from file bodies to tree states for that reason.
# The grains this step grades, written into the scratch tree's pools.
FEATURE_DOC = f'''---
id: f-alpha
kind: feature
milestone: "{VERSION}"
name: Alpha
status: done
reviewed:
changelog:
---

# Alpha
'''


def _with_changelog(root: Path, entry: str) -> None:
    """One closed feature under the scratch milestone, `changelog:` set.

    THE NESTED SLOT (`<milestone>/features/<slug>/feature.md`), because this
    fixture builds a nested tree — writing into `pm/roadmap/features/` creates
    a POOL and flips the layout, after which the milestone itself stops
    resolving. Written as bytes: `pm set` would spawn.
    """
    from agentic_sdlc.repo.pm import changelog as clog
    path = root / MDIR / 'features' / 'alpha' / 'feature.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    body = FEATURE_DOC
    if entry:
        body = body.replace(f'{clog.FIELD}:', f'{clog.FIELD}: {entry}')
    path.write_text(body, encoding='utf-8')


@pytest.mark.parametrize('entry,truth,why', [
    # The closed feature is silent — NAMED, with the two ways to answer.
    ('', driver.Truth.FALSE, 'answered neither'),
    # `none` is an ANSWER. That is the whole point of the word.
    ('none', driver.Truth.TRUE, '1 declined'),
    # And a sentence.
    ('a change', driver.Truth.TRUE, '1 entry/ies'),
])
def test_the_changelog_step_grades_grains_and_writes_nothing(entry, truth,
                                                             why):
    """Bites: a release over a closed grain nobody wrote a line for, and the
    `none` that must satisfy it. The step is a READER — it writes nothing."""
    with tree({}) as root:
        _with_changelog(root, entry)
        before = snapshot(root)
        answer = check('changelog-unreleased-nonempty', root)
        assert answer.truth is truth, answer
        assert why in answer.detail, answer.detail
        assert snapshot(root) == before


# --- version-sync -------------------------------------------------------------
PYPROJECT = '[project]\nname = "x"\nversion = "0.0.1"\n'


def test_version_sync_names_every_site_and_bumps_nothing():
    """Bites: the bump this check used to PERFORM. It reads both sites, names
    the one that is wrong with the value it holds, and leaves both bytes
    alone; with every site right it is true."""
    config = ('[release.version_files]\n'
              '"pyproject.toml" = \'^version = "(.*)"$\'\n'
              '"pkg/__init__.py" = "^__version__ = \'(.*)\'$"\n')
    files = {'pyproject.toml': PYPROJECT,
             'pkg/__init__.py': f"__version__ = '{VERSION}'\n"}
    with tree(files, config=config) as root:
        before = snapshot(root)
        answer = check('version-sync', root)
        assert answer.truth is driver.Truth.FALSE
        assert 'pyproject.toml says 0.0.1' in answer.detail, answer.detail
        assert snapshot(root) == before, 'version-sync wrote a version site'
        (root / 'pyproject.toml').write_text(
            PYPROJECT.replace('0.0.1', VERSION), encoding='utf-8')
        assert check('version-sync', root).is_true
    with tree(config=config) as root:
        assert check('version-sync', root).truth is driver.Truth.UNVERIFIABLE


# --- the pm predicates, asked of the verb --------------------------------------
def test_findings_resolved_and_features_done_ask_pm_ready_for():
    """Bites: a second reader of 'is every finding dispositioned'. The
    milestone has one feature pointing at a record with an open finding:
    `ready-for tag` says so by name; with no feature at all `ready-for
    milestone` reports the empty census rather than passing."""
    record = ('```\nverdict: SHIP-WITH-FIXES\n'
              '| id | severity | disposition |\n| W1 | MAJOR | open |\n```\n')
    feature = (f'---\nid: {VERSION}/alpha\nmilestone: "{VERSION}"\n'
               f'name: Alpha\nstatus: done\nreviewed: docs/reviews/alpha.md\n'
               f'phase: 1\n---\n\n# Alpha\n')
    with tree({f'{MDIR}/features/alpha/feature.md': feature,
               'docs/reviews/alpha.md': record}) as root:
        answer = check('findings-resolved', root)
        assert answer.truth is driver.Truth.FALSE, answer
        assert 'W1' in answer.detail or 'open' in answer.detail, answer.detail
    with tree() as root:
        answer = check('features-done', root)
        assert not answer.is_true, answer


# --- the gate: a configured command -------------------------------------------
def test_the_gate_fills_version_passes_the_shells_braces_through_and_names_the_code():
    """Bites: `{version}` handed to the shell unfilled (M4 — this repo's own
    command carried it for a milestone), the shell's own braces mangled, or
    a failing gate whose exit code is not on the line."""
    filled = '[release.commands]\ngate = "test {version} = 9.9.9 && echo v{version}"\n'
    with tree(config=filled) as root:
        answer = check('gate', root)
        assert answer.is_true, answer.detail
        assert '{version}' not in answer.detail and 'v9.9.9' in answer.detail
    theirs = ('[release.commands]\n'
              "gate = \"echo ${HOME} {} | awk '{print $1}' >/dev/null\"\n")
    with tree(config=theirs) as root:
        answer = check('gate', root)
        assert answer.is_true, answer.detail
        assert "{print $1}" in answer.detail and '${HOME}' in answer.detail
    with tree(config='[release.commands]\ngate = "exit 3"\n') as root:
        answer = check('gate', root)
        assert answer.truth is driver.Truth.FALSE
        assert 'exited 3' in answer.detail, answer.detail


def test_a_gates_output_is_bounded_and_a_timeout_is_false_not_a_hang():
    noisy = "awk 'BEGIN{for(i=0;i<200000;i++)printf \"x\"}'\nexit 1\n"
    with tree({'noisy.sh': noisy},
              config='[release.commands]\ngate = "sh noisy.sh"\n') as root:
        answer = check('gate', root)
        assert answer.truth is driver.Truth.FALSE
        assert len(answer.detail) < 1000, len(answer.detail)
    config = ('[release]\ncommand_timeout = 1\n\n'
              '[release.commands]\ngate = "sleep 30"\n')
    with tree(config=config) as root:
        answer = check('gate', root)
        assert answer.truth is driver.Truth.FALSE
        assert 'did not finish' in answer.detail, answer.detail


def test_a_callee_that_exits_2_is_UNVERIFIABLE_and_never_a_finding(monkeypatch):
    """D11. Bites: a callee's config error read as a plain no, and the belt
    then deciding over a question that was never asked."""
    monkeypatch.setattr(
        steps, '_own_cli',
        lambda c, *argv: (2, '[verify] feature must be a string, got 42',
                          argv))
    context = driver.Context(root=Path('.'), operation='story', version='x')
    answer = steps._own_verdict(context, 'verify', '--story', 'x')
    assert answer.truth is driver.Truth.UNVERIFIABLE, answer
    assert 'nothing was decided' in answer.detail and 'got 42' in answer.detail


# --- config -------------------------------------------------------------------
def test_no_devkit_toml_and_the_stock_list_declared_are_the_same_bytes():
    """Rule 5, the equivalence test."""
    declared = ('[release]\nsteps = [\n'
                + ''.join(f'  "{n}",\n' for n in steps.DEFAULT_RELEASE_STEPS)
                + ']\n')
    with tree():
        absent = driver.step_names('release')
    with tree(config=declared):
        explicit = driver.step_names('release')
    assert absent == explicit == steps.DEFAULT_RELEASE_STEPS


@pytest.mark.parametrize('config,expected', [
    ('[release]\nsteps = "tree-clean"\n', 'list of strings'),
    ('[release]\nsteps = []\n', 'remove the key'),
    ('[release]\nsteps = ["tree-clan"]\n', 'no check is registered'),
    ('[release]\nsteps = ["tree-clean", 3]\n', 'must be a string'),
    ('[release]\nsteps = ["gate;rm -rf /"]\n', 'not a step name'),
    ('[release]\nsteps = ["' + 'g' * 4096 + '"]\n', 'the limit is'),
    ('[release]\ncommands = "make x"\n', 'table of step'),
    ('[release.commands]\ngate = 3\n', 'one command string'),
    ('[release.commands]\ngate = "   "\n', 'is empty'),
    ('[release.commands]\ngate = "echo {verison}"\n', 'placeholder'),
    ('[release.commands]\n"version-sync" = "x"\n', 'reads the tree'),
    ('[release]\nsteps = ["tree-clean"]\n\n[release.commands]\ngate = "x"\n',
     'never runs'),
    ('[release.commands]\nnot-a-step = "x"\n', 'names no registered check'),
    ('[release]\ncommand_timeout = "soon"\n', 'positive integer'),
    # 0.6.0: the key named the FILE the changelog step counted bullets in. A
    # consumer still declaring it would keep a path nothing reads.
    ('[release]\nchangelog = "NOTES.md"\n', 'retired in 0.6.0'),
    ('release = "x"\n', ''),
])
def test_the_config_refusal_matrix_is_exit_2_and_runs_no_check(config, expected):
    """Bites: a typo narrowing the release list in silence — the check that
    vanishes is the one that mattered."""
    with tree(config=config):
        with pytest.raises(ConfigError) as err:
            driver.step_names('release')
        assert expected in str(err.value), str(err.value)


def test_duplicates_collapse_in_declaration_order_and_are_reported(capsys):
    config = '[release]\nsteps = ["gate", "tree-clean", "gate"]\n'
    with tree(config=config):
        assert driver.step_names('release') == ('gate', 'tree-clean')
    assert 'more than once' in capsys.readouterr().out


def test_an_after_belt_command_is_accepted_and_lands_on_the_next_line():
    """Bites: this repo's own `[release.commands] prove-artifact` — a key that
    names no check since D12 — refused at exit 2, or accepted and lost. It is
    the caller's command, and the after-list carries it filled in."""
    config = ('[release.commands]\n'
              'prove-artifact = "uvx --from x@v{version} x --version"\n')
    with tree(config=config):
        names = driver.step_names('release')
        commands = steps.commands_for('release', names)
        assert 'prove-artifact' in commands
        lines = steps.after_lines('release', commands, version=VERSION,
                                  branch='b', mainline='m')
        assert any(f'x@v{VERSION} x --version' in line for line in lines), lines
        assert not any('{' in line for line in lines), lines
