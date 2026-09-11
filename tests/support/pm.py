"""The pm test harness — one tree builder and two runners, shared by the
test_pm_* quartet (verbs / gate / scaffold / guidance).

The load-bearing property across that quartet is that the CLI and the gate
share ONE definition of "reviewed" and of each drift rule. So the harness
builds a tree, the tests drive it through the CLI and assert against the
GATE — if the two ever diverged, the round trips stop closing.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import subprocess
import tempfile
from pathlib import Path

from agentic_sdlc.repo.checks import pm as pm_check
from agentic_sdlc.repo.pm import cli, vocabulary


def _case_sensitive_tmp() -> bool:
    """Can two names differing only by case coexist where tests build trees?

    macOS is case-INSENSITIVE by default, so the two-spellings case cannot be
    STAGED there at all. Reported as a skip rather than asserted away: a test
    that quietly passes because its fixture could not be built is rule 4's sin
    wearing a test's clothes.
    """
    with tempfile.TemporaryDirectory() as tmp:
        lower = Path(tmp) / 'casetest.md'
        lower.write_text('x', encoding='utf-8')
        upper = Path(tmp) / 'CASETEST.md'
        upper.write_text('y', encoding='utf-8')
        return lower.read_text(encoding='utf-8') == 'x'


CASE_SENSITIVE_TMP = _case_sensitive_tmp()


# The three ways a real editor breaks a frontmatter block WITHOUT removing it:
# a Windows editor writes the BOM, a paste lands a blank line above the fence,
# a hand-edit eats the closing one. All three still OPEN a `---` block, so all
# three are grains whose frontmatter is DAMAGED — never notes.
DAMAGE_FORMS = ('bom', 'blank-line', 'no-closing-fence')
STORY_REL = 'pm/roadmap/stories/s0.md'


def damage(path: Path, form: str) -> None:
    raw = path.read_text(encoding='utf-8')
    if form == 'bom':
        raw = '﻿' + raw
    elif form == 'blank-line':
        raw = '\n' + raw
    elif form == 'no-closing-fence':
        lines = raw.split('\n')
        close = next(i for i in range(1, len(lines)) if lines[i] == '---')
        del lines[close]
        raw = '\n'.join(lines)
    else:  # pragma: no cover - a typo in a fixture is not a fixture
        raise AssertionError(f'unknown damage form {form!r}')
    path.write_text(raw, encoding='utf-8')


def write(path: Path, front: dict[str, str], body: str = 'x') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ['---'] + [f'{k}: {v}' for k, v in front.items()] + ['---', '', body, '']
    path.write_text('\n'.join(lines), encoding='utf-8')


# --- the flow a fixture tree DECLARES -----------------------------------------
# `[pm.states.<kind>]` has NO runtime fallback behind it: `vocabulary.flow_of`
# (src/agentic_sdlc/repo/pm/vocabulary.py) exits 2 BY NAME when a tree declared
# nothing, and phase 7 routes every engine question through `vocabulary.holds`.
# From
# that commit on, a fixture that never declared is a tree no `pm` verb and no
# `check pm` run can read — so every tree builder in this suite declares now,
# ahead of the routing change, and that change reviews as a behaviour change
# rather than as four hundred fixture edits.
#
# DERIVED FROM `vocabulary.render_seed()`, never hand-copied. A table typed out
# here would be a second spelling of `vocabulary.DEFAULT_FLOWS`, and the
# copy nobody runs is the one that goes stale — which is exactly why
# `installables/project-devkit.toml` is held to `render_seed()` VERBATIM by
# tests/test_pm_flow.py:559 rather than being allowed its own copy.
FLOW_TOML = vocabulary.render_seed()


def with_flow(config: str = '') -> str:
    """`config` with the flow declaration APPENDED — never replacing it.

    THE APPEND IS THE WHOLE POINT. A fixture that takes a `config=` string and
    hands it straight to `write_text` lets any test supplying one silently drop
    `[pm.states.*]`, and the tree it builds is then refused by `flow_of` for a
    reason having nothing to do with what that test is about. So every config a
    fixture writes comes through here, and a test override ADDS to the
    declaration instead of replacing it.

    Idempotent: a config that already declares `[pm.states.…]` comes back
    untouched, because a second copy of those tables is a TOML duplicate-table
    error rather than a second declaration.
    """
    if '[pm.states.' in config:
        return config
    if config and not config.endswith('\n'):
        config += '\n'
    return config + FLOW_TOML


def declaring(config: str = '', **kinds: dict) -> str:
    """`config` plus a flow whose table for each kind NAMED here is `kinds[kind]`.

    The seed for every kind not named, so a case about the story vocabulary
    declares the story flow and inherits the rest. `kinds` values are
    `{category: (state, ...)}` — the same shape `vocabulary.DEFAULT_FLOWS` holds —
    and `vocabulary.render_seed` is the one renderer, so a case cannot hand-type a
    table the reader would not read.
    """
    flows = {**vocabulary.DEFAULT_FLOWS, **{k: dict(v) for k, v in kinds.items()}}
    if config and not config.endswith('\n'):
        config += '\n'
    return config + vocabulary.render_seed(flows)


def loaded(root: Path) -> vocabulary.PmConfig:
    """`vocabulary.load()` for a tree, caches cleared — the config the verbs read.

    `cfg_for` builds a BARE `PmConfig(root=…)` with no flow, which is right
    for `validate` (it asks no category) and wrong for anything that does.
    """
    from agentic_sdlc.core.project import load_config, repo_root
    repo_root.cache_clear()
    load_config.cache_clear()
    previous = Path.cwd()
    os.chdir(root)
    try:
        return vocabulary.load()
    finally:
        os.chdir(previous)


def write_config(root: Path, config: str = '') -> Path:
    """Write `root/devkit.toml` as `config` PLUS the flow declaration.

    The one config writer for a fixture tree, so that a test overriding `[pm]`
    mid-case cannot drop `[pm.states.*]` by writing the file itself — which is
    what every `(root / 'devkit.toml').write_text(...)` in this suite used to
    do. See `with_flow` for why the append is not optional.
    """
    path = root / 'devkit.toml'
    path.write_text(with_flow(config), encoding='utf-8')
    return path


def _mark(root: Path) -> None:
    """Make `root` findable without spawning anything.

    `core.project.repo_root` walks up for `.git` and no longer shells out to
    `git rev-parse --show-toplevel`, so a tree only has to be MARKED to be
    found. `mkdir` costs microseconds; `git init` costs a process, and a tree
    builder is entered once per TEST across most of this suite.

    **This function must never spawn, and that is load-bearing rather than
    tidy.** `conftest.py` derives the `shell` mark by walking `tests/support`'s
    call graph, so anything `tree` reaches decides the TIER of every module
    that uses it. While the init lived here behind a flag, 1430 tests were
    marked integration for a branch they never took — source cannot see which
    side of an `if` runs, and one helper dragged three hundred cheap cases
    across with it. The two builders are separate functions for that reason.
    """
    (root / '.git').mkdir(exist_ok=True)


@contextlib.contextmanager
def tree(milestone_status='building', feature_status='building',
         story_statuses=('ready',), with_record=True, config=''):
    """A one-milestone/one-feature/N-story repo, cwd'd into.

    `config` is the tree's `devkit.toml` MINUS the flow declaration, which is
    appended for you — see `with_flow`. A case that wants to change the config
    after the tree is standing calls `write_config(root, …)` rather than
    writing the file, for the same reason.

    **This builder never spawns**, and `git_tree` below is the one that does.
    They are two functions rather than one with a flag because `conftest.py`
    derives the `shell` mark from `tests/support`'s CALL GRAPH — source cannot
    see which side of an `if` runs, so a single builder with a `git_repo=`
    branch marked every module that used it as integration, including three
    hundred cases that never took the branch.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        # POOLED (0.4.0), and the IDS ARE UNCHANGED. A kind-prefixed slug is a
        # convention for a human reading a bare id, not something the tool
        # enforces — so every case that names `0.1/alpha/s0` still names it,
        # and what this fixture moved is only where the documents SIT. That is
        # the whole claim the migration makes, and a fixture that changed both
        # at once would prove less about either.
        pools = root / 'pm' / 'roadmap'
        root.mkdir(parents=True, exist_ok=True)
        write_config(root, config)
        write(pools / 'milestones' / '0.1.md',
              {'id': '"0.1"', 'kind': 'milestone', 'name': 'Demo',
               'status': milestone_status})
        feature = {'id': '0.1/alpha', 'kind': 'feature', 'milestone': '"0.1"',
                   'name': 'Alpha', 'status': feature_status, 'reviewed': ''}
        if with_record:
            (root / 'docs' / 'reviews').mkdir(parents=True, exist_ok=True)
            (root / 'docs' / 'reviews' / 'alpha.md').write_text(
                'A real review record with enough content to be substantive.\n',
                encoding='utf-8')
            feature['reviewed'] = 'docs/reviews/alpha.md'
        write(pools / 'features' / 'alpha.md', feature)
        for i, st in enumerate(story_statuses):
            write(pools / 'stories' / f's{i}.md',
                  {'id': f'0.1/alpha/s{i}', 'kind': 'story',
                   'feature': '0.1/alpha', 'milestone': '"0.1"',
                   'name': f'S{i}', 'status': st})
        _mark(root)
        previous = Path.cwd()
        os.chdir(root)
        try:
            yield root
        finally:
            os.chdir(previous)


@contextlib.contextmanager
def git_tree(**kwargs):
    """`tree`, in a REAL repository — for cases that ask git a question.

    What changed, what is staged, what a rev resolves to: those are questions
    only git can answer, and a test asking one is an integration test. It says
    so by reaching for this builder, and `conftest.py`'s derivation reads that
    reach and marks the module.

    **The declaration is the point.** The default is cheap and the exception is
    visible, so a module that quietly grows a git dependency changes tier in
    the census rather than in somebody's wall clock.
    """
    with tree(**kwargs) as root:
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        yield root


def bug(root: Path, slug: str = 'crash', status: str = 'open',
        **extra: str) -> Path:
    """One bug document under `tree()`'s milestone, and its path.

    The canonical frontmatter a scaffolded bug carries, so a test that cares
    about ONE field (`caused_by:`) names that field and nothing else.

    `milestone:` is the ONLY binding (0.6.0/D11). Pass `milestone=''` for a
    POOLED bug — the opt-out `pm remove` writes — which gates nothing and is
    counted.
    """
    path = root / 'pm/roadmap/bugs' / f'{slug}.md'
    front = {'id': f'0.1/bugs/{slug}', 'milestone': '"0.1"', 'name': '',
             'status': status, 'caused_by': ''}
    front.update(extra)
    write(path, front)
    return path


def frontmatter(path: Path) -> list[str]:
    """The lines INSIDE the leading `---` fence, verbatim.

    The bytes, not a parse: field order and an empty field's exact spelling
    (`caused_by:`, no trailing space) are half of what a template promises.
    """
    lines = path.read_text(encoding='utf-8').split('\n')
    assert lines[0] == '---', f'{path} does not open a frontmatter block'
    return lines[1:lines.index('---', 1)]


LEDGER_REL = 'pm/roadmap/ledgers/0.1.jsonl'


def ledger_lines(root: Path, rel: str = LEDGER_REL) -> list[str]:
    """The milestone ledger's raw LINES — the bytes, never a re-serialisation.

    Read as text rather than through a parser on purpose: compactness, key
    order and one-row-per-line are half the row shape, and a parse would
    answer the same for a pretty-printed file that no `readline` reader could
    use. An absent ledger is [] — a milestone nothing has happened in yet.
    """
    path = root / rel
    if not path.is_file():
        return []
    return path.read_text(encoding='utf-8').splitlines()


def ledger_rows(root: Path, rel: str = LEDGER_REL) -> list[dict]:
    """The same lines, parsed, oldest first."""
    return [json.loads(line) for line in ledger_lines(root, rel) if line.strip()]


def cfg_for(root: Path) -> vocabulary.PmConfig:
    """The config a `tree()` READS — flow included — for a direct engine call."""
    return loaded(root)


def run_cli(root: Path, *argv: str, stdout_only: bool = False,
            skipped: tuple[tuple[str, str], ...] = ()) -> tuple[int, str]:
    """Run one `pm` invocation; both streams merged, or stdout alone.

    `stdout_only` is for the cases asserting *a write prints what it wrote and
    nothing else* — a claim about STDOUT, which is what a consumer parses.
    0.4.0 put the conveyor breadcrumb on stderr precisely so that claim stays
    true, and a merged read would have made the two indistinguishable.
    """
    # repo_root()/load_config() are lru_cached on purpose in production, where
    # the cwd never moves mid-run. Tests move it every case.
    from agentic_sdlc.core.project import load_config, repo_root
    repo_root.cache_clear()
    load_config.cache_clear()
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(out if not stdout_only else err):
        try:
            code = cli.main(list(argv), skipped=skipped)
        except SystemExit as exc:  # pragma: no cover - defensive
            code = int(exc.code or 0)
    return code, out.getvalue()


def run_gate(root: Path) -> tuple[int, str]:
    from agentic_sdlc.core.project import load_config, repo_root
    repo_root.cache_clear()
    load_config.cache_clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = pm_check.run()
    return code, buf.getvalue()


# --- ledger fixtures ----------------------------------------------------------
# One home for the LINE builders, because two report tests seeding two
# differently-shaped ledgers must still write the row shape `pm ledger record`
# and the status verbs write — a fixture that drifted from the writer would
# test a file this package never produces. Every builder goes through
# `ledger.dumps`, the serialisation contract itself.
MILESTONE_ID = '0.1'

# D3's snapshot as the hook writes it: every bucket present, empty lists when
# empty. Two key families (decision D7): the frozen five — deprecated, matched
# by the seed's words — and the three category keys the report attributes by.
# A row naming no grain has every list but the milestone's empty.
EMPTY_TREE = {'milestones_building': [MILESTONE_ID], 'features_building': [],
              'features_review': [], 'stories_wip': [], 'stories_review': [],
              'milestones_in_progress': [MILESTONE_ID],
              'features_in_progress': [], 'stories_in_progress': []}

# The OLD shape — what every row written before 0.2.0's category keys holds.
# `snapshot_legacy(...)` builds one for a case about the reader's boundary.
LEGACY_TREE = {'milestones_building': [MILESTONE_ID], 'features_building': [],
               'features_review': [], 'stories_wip': [], 'stories_review': []}


def snapshot_legacy(**over: list) -> dict:
    snap = dict(LEGACY_TREE)
    snap.update(over)
    return snap


def snapshot(**over: list) -> dict:
    """A CURRENT-shape snapshot. A frozen key given alone is mirrored into its
    category key, so a case that says `stories_wip=[s]` builds the row the
    writer would build for a `building` story — both families agreeing."""
    snap = dict(EMPTY_TREE)
    mirror = {'stories_wip': 'stories_in_progress',
              'stories_review': 'stories_in_progress',
              'features_building': 'features_in_progress',
              'features_review': 'features_in_progress',
              'milestones_building': 'milestones_in_progress'}
    for key, ids in over.items():
        if key in mirror and mirror[key] not in over:
            snap[mirror[key]] = sorted(set(snap[mirror[key]]) | set(ids))
    snap.update(over)
    return snap


def status_line(ts: str, grain: str, frm: str, to: str) -> str:
    from agentic_sdlc.repo.pm import ledger
    return ledger.dumps(ledger.status_row(grain, frm, to, ts=ts))


def decision_line(ts: str, grain: str, entry: str, title: str = 'why') -> str:
    from agentic_sdlc.repo.pm import ledger
    return ledger.dumps(ledger.decision_row(grain, entry, title, ts=ts))


def dispatch_line(ts: str, **fields: object) -> str:
    from agentic_sdlc.repo.pm import ledger
    fields.setdefault('tree', snapshot())
    return ledger.dumps(ledger.usage_row(ledger.KIND_DISPATCH, ts=ts,
                                         **fields))


def session_line(ts: str, **fields: object) -> str:
    from agentic_sdlc.repo.pm import ledger
    return ledger.dumps(ledger.usage_row(ledger.KIND_SESSION, ts=ts, **fields))


def put_ledger(root: Path, *lines: str, rel: str = LEDGER_REL) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(line + '\n' for line in lines), encoding='utf-8')


SECTION_SEPARATOR = ' — '


def section_of(out: str, title: str) -> str:
    """One `pm ledger report` section, heading included, from the whole report.

    The report is five sections and each one is a separate contract, so a case
    that pins section 4's table must fail when section 4 changes and NOT when
    section 2 grows a column. The slice runs from the section's own heading to
    the next one — `<prefix> <milestone> — <name> — <census>`, the three-part
    shape only a section heading has. Section 1's SUMMARY line carries one
    separator, not two, so it belongs to the section it closes rather than
    opening a new one.
    """
    from agentic_sdlc.repo.pm import report
    lines = out.rstrip('\n').split('\n')
    heads = [i for i, line in enumerate(lines)
             if line.startswith(report.HEADING_PREFIX)
             and line.count(SECTION_SEPARATOR) >= 2]
    start = next(i for i in heads if f'— {title} —' in lines[i])
    end = next((i for i in heads if i > start), len(lines))
    return '\n'.join(lines[start:end]).rstrip('\n')


# --- git fixtures -------------------------------------------------------------
# `tree()` already `git init`s, because `check pm`'s flow rules read the branch.
# These three add the rest of what a `--from <rev>` case needs: a commit, a tag,
# and a way to assert that a read verb left the tree exactly as it found it.
#
# Identity and signing are supplied per INVOCATION rather than written into the
# scratch repo's config. A test that inherited the developer's `user.email`, a
# global `commit.gpgsign`, or a `gpg.program` that prompts would pass on one
# machine and hang or fail on the next, for a reason having nothing to do with
# the verb under test.
GIT_IDENTITY = ('-c', 'user.name=pm tests', '-c', 'user.email=pm@tests.invalid',
                '-c', 'commit.gpgsign=false', '-c', 'tag.gpgsign=false')


def git(root: Path, *args: str) -> str:
    """One git command in a scratch repo. A failure is an ASSERTION, not a
    return code: a fixture that half-built itself and carried on would test a
    tree nobody described, which is the one failure mode a fixture cannot
    report on its own."""
    done = subprocess.run(['git', *GIT_IDENTITY, *args], cwd=root,
                          capture_output=True, text=True)
    assert done.returncode == 0, (
        f'git {" ".join(args)} failed in {root}:\n{done.stderr}{done.stdout}')
    return done.stdout


def commit(root: Path, message: str = 'seed') -> str:
    """Stage everything and commit it; return the commit's full hash."""
    git(root, 'add', '-A')
    git(root, 'commit', '-q', '--allow-empty', '-m', message)
    return git(root, 'rev-parse', 'HEAD').strip()


def porcelain(root: Path) -> str:
    """`git status --porcelain` — '' for a tree a read verb did not touch."""
    return git(root, 'status', '--porcelain')
