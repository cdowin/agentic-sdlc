"""test_ci_compare_step.py — the semver-gate's "Compare versions" step, RUN.

Split out of `test_ci_workflows.py` at 0.7.0. That module answers *is this the
shape a workflow has* by reading the YAML with a minimal indentation reader and
spawns nothing; this one answers *what does the `run:` body DO*, which only
bash can say. Two questions, two modules, two tiers — the split is the whole
point, because a module that reaches `subprocess` puts EVERY case in it into
the `shell` tier (`tests/conftest.py::module_spawns`), and 26 pure-parse cases
were paying that toll for these six.

Every claim the gate makes — any-length compare, a non-numeric refusal, a done
milestone's id or a hotfix and NOTHING else — is one row here, and a false PASS
is the row that fails.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.repo import install  # noqa: E402


def body(name: str) -> str:
    return install.body_of(name)


def _compare_step_script() -> str:
    text = body('ci-semver-gate.yml')
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines)
                 if line.strip() == '- name: Compare versions')
    run_at = next(i for i in range(start, len(lines))
                  if lines[i].strip() == 'run: |')
    indent = len(lines[run_at]) - len(lines[run_at].lstrip(' '))
    out = []
    for line in lines[run_at + 1:]:
        if line.strip() and (len(line) - len(line.lstrip(' '))) <= indent:
            break
        out.append(line[indent + 2:] if line.strip() else '')
    return '\n'.join(out) + '\n'


def _milestone(root: Path, mid: str, status: str, quote: str = '"',
               body: str = '', version: str = '') -> None:
    mdir = root / 'pm/roadmap' / f'{mid}-m'
    mdir.mkdir(parents=True)
    declares = f'version: {version}\n' if version else ''
    (mdir / 'milestone.md').write_text(
        f'---\nid: {quote}{mid}{quote}\nname: M\n{declares}status: {status}\n---\n{body}',
        encoding='utf-8')


# --- the field a milestone declares its version IN ----------------------------
# Every fixture above writes a milestone whose id IS a version string, which is
# the layout `pm new milestone` stopped producing at 0.3.0: since
# `ft-a-milestone-declares-its-version` the version is the `version:` FIELD, and
# since 0.6.0's `bg-the-milestone-scaffold-still-mints-the-version` the id is a
# slug minted from the name. Not one milestone in this repo's own tree — not
# even `ms-0.4.0`, whose id carries the digits — has ever had `id == $PR`.
#
# So the gate's success path was DEAD in every layout the tool emits, and the
# rows above could not see it, because they model a shape nothing writes any
# more. A new writer met an old reader; the test fixture was the old reader's
# alibi.
MODERN = ('ms-the-slug', '0.99.0')


def _run_compare(root: Path, script: Path, main: str, pr: str):
    import subprocess
    return subprocess.run(['bash', str(script)], cwd=root, capture_output=True,
                          text=True, env={'PATH': '/usr/bin:/bin', 'PR': pr,
                                          'MAIN': main, 'PM_ROADMAP': 'pm/roadmap'})


def test_a_milestone_declaring_its_version_in_a_field_is_a_release(tmp_path):
    """The layout this package has shipped since 0.3.0, admitted and refused.

    A slug-id milestone at `version: 0.99.0`, `done`, IS the release the gate
    exists to admit — and a `building` one at the same version is the release
    it exists to refuse. Both were invisible before: the loop asked `id` only,
    so a slug id matched nothing, `legit` stayed empty, and a legitimate
    release PR was told it was 'neither the id of a done milestone nor a
    hotfix' — the one message that cannot be acted on, because the operator
    cannot rename a milestone to a version without undoing 0.6.0.
    """
    mid, version = MODERN
    script = tmp_path / 'compare.sh'
    script.write_text(_compare_step_script(), encoding='utf-8')

    closed = tmp_path / 'closed'
    _milestone(closed, mid, 'done', version=version)
    ok = _run_compare(closed, script, '0.98.0', version)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert f'done milestone {mid}' in ok.stdout, ok.stdout

    building = tmp_path / 'building'
    _milestone(building, mid, 'building', version=version)
    refused = _run_compare(building, script, '0.98.0', version)
    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert "not done" in refused.stdout, refused.stdout


def test_the_id_still_declares_the_version_on_a_tree_that_predates_the_field(tmp_path):
    """The fallback, asserted rather than assumed: a pre-0.3.0 milestone whose
    id IS the version still resolves, so reading the new field did not retire
    the old shape out from under a tree that never migrated."""
    script = tmp_path / 'compare.sh'
    script.write_text(_compare_step_script(), encoding='utf-8')
    _milestone(tmp_path, '0.99.0', 'done')
    ok = _run_compare(tmp_path, script, '0.98.0', '0.99.0')
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert 'done milestone 0.99.0' in ok.stdout, ok.stdout


# A `done`/`building` entry is an id that IS the version (the pre-0.3.0 layout),
# or an `(id, version)` pair — the `version:` field every scaffold writes now.
SLUG_28 = ('ms-the-slug', '0.28.4')
INCREMENTED = "incremented hotfix 2 over main's 0.28.4.1, on 0.28.4, the"

COMPARE_ROWS = [
    ('0.90.3',   '0.90.3.1',   (),          ('0.90.3.2',), True,  "appended hotfix 1 on main's 0.90.3"),
    ('0.90.3.1', '0.90.3.2',   ('0.90.3.2',), (),          True,  'done milestone 0.90.3.2'),
    ('0.16',     '0.16.1',     ('0.16.1',),  (),           True,  'done milestone 0.16.1'),
    ('0.90.3.1', '0.90.3.1.1', (),          ('0.90.4',),  True,  "appended hotfix 1 on main's 0.90.3.1"),
    # #27 — the NEXT hotfix. Main is already a hotfix of a done milestone's
    # version, so the PR bumps the final component instead of nesting one deeper.
    ('0.28.4.1', '0.28.4.2',   (SLUG_28,),  (),           True,  f'{INCREMENTED} version of done milestone ms-the-slug'),
    ('0.28.4.1', '0.28.4.2',   ('0.28.4',),  (),           True,  f'{INCREMENTED} id of done milestone 0.28.4'),
    ('0.28.4.2', '0.28.4.5',   (SLUG_28,),  (),           True,  "incremented hotfix 5 over main's 0.28.4.2"),
    ('0.28.4.2', '0.28.4.1',   (SLUG_28,),  (),           False, 'Version must increase'),
    ('0.28.4.1', '0.28.5',     (SLUG_28,),  (),           False, 'the version or id of no done milestone'),
    ('0.28.4.1', '0.28.4.2',   (),          (SLUG_28,),   False, 'the version or id of no done milestone'),
    ('0.28.4.1', '0.28.4.2',   (SLUG_28,),  (('ms-next', '0.28.4.2'),), False, "whose status is 'building', not done"),
    ('0.28.4.1', '0.28.4.2.1', (SLUG_28,),  (),           False, 'the version or id of no done milestone'),
    ('0.28.4.1', '0.28.4.02',  (SLUG_28,),  (),           False, 'the version or id of no done milestone'),
    ('0.90.2',   '0.90.3',     ('0.90.2',),  ('0.90.3',),  False, "whose status is 'building', not done"),
    ('0.90.3',   '0.90.4',     (),          ('0.90.4',),  False, "whose status is 'building', not done"),
    ('0.90.3',   '0.90.3',     (),          (),           False, 'Version must increase'),
    ('0.90.3',   '0.90.2',     ('0.90.2',),  (),           False, 'Version must increase'),
    ('0.90.3',   '0.90.3a',    (),          (),           False, 'Non-numeric version component'),
    ('0.90.3',   '0.90.3.1a',  (),          (),           False, 'Non-numeric version component'),
    ('1.0',      '1.0.0',      ('1.0.0',),   (),           False, 'Version must increase'),
    # The finding that made the first cut of this rule NOT RELEASE-SAFE: a
    # BUILDING milestone whose id is main + one integer read as a hotfix.
    ('0.90.3',   '0.90.3.2',   (),          ('0.90.3.2',), False, "whose status is 'building', not done"),
    ('0.90.3',   '0.90.3.01',  ('0.90.2',),  (),           False, 'the version or id of no done milestone'),
]


def test_the_compare_step_admits_a_done_milestone_or_a_hotfix_and_nothing_else(
        tmp_path):
    """PR #56 on the consumer that motivated this: the 0.90.2 release reached
    main wearing 0.90.3 — the NEXT milestone's bump-at-start had landed before
    the close merged — and the three-field gate waved it through. Row 5 is
    that PR, and it is refused. Every row is one bash run over its own
    scratch roadmap; a row that answers wrongly names itself.

    Issue #27 is the 0.28.x block: `0.28.4.1 -> 0.28.4.2` was refused because
    the only hotfix rule was main plus one APPENDED component, and the consumer
    merged over the red check. The admitted line names the rule that admitted
    it, and a decrement, a skip to an undone version, a parent that is not done
    and a building milestone at the PR's version all still refuse."""
    import subprocess
    script = tmp_path / 'compare.sh'
    script.write_text(_compare_step_script(), encoding='utf-8')
    wrong = []
    for n, (main, pr, done, building, ok, why) in enumerate(COMPARE_ROWS):
        root = tmp_path / f'row{n}'
        for status, entries in (('done', done), ('building', building)):
            for entry in entries:
                mid, version = entry if isinstance(entry, tuple) else (entry, '')
                _milestone(root, mid, status, version=version)
        (root / 'pm/roadmap').mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(['bash', str(script)], cwd=root, capture_output=True,
                              text=True, env={'PATH': '/usr/bin:/bin', 'PR': pr,
                                              'MAIN': main, 'PM_ROADMAP': 'pm/roadmap'})
        text = proc.stdout + proc.stderr
        if (proc.returncode == 0) is not ok or why not in text:
            wrong.append(f'main={main} pr={pr}: exit {proc.returncode}, {text!r}')
    assert not wrong, '\n'.join(wrong)


def test_the_compare_step_reads_only_the_frontmatter_and_either_quote_style(tmp_path):
    """A `status: done` line in a milestone's BODY (a schema example) must not
    vouch for the file, and a single-quoted id is the same id."""
    import subprocess
    _milestone(tmp_path, '0.93', 'planning', body='\nSchema example:\n\nstatus: done\n')
    _milestone(tmp_path, '0.98', 'done', quote="'")
    script = tmp_path / 'compare.sh'
    script.write_text(_compare_step_script(), encoding='utf-8')
    def run(pr):
        return subprocess.run(['bash', str(script)], cwd=tmp_path, capture_output=True,
                              text=True, env={'PATH': '/usr/bin:/bin', 'PR': pr,
                                              'MAIN': '0.90', 'PM_ROADMAP': 'pm/roadmap'})
    refused = run('0.93')
    assert refused.returncode == 1 and "whose status is 'planning'" in refused.stdout, refused.stdout
    admitted = run('0.98')
    assert admitted.returncode == 0 and 'done milestone 0.98' in admitted.stdout, admitted.stdout


def test_the_compare_step_refuses_when_it_scanned_no_milestone(tmp_path):
    """Rule 4: a hotfix-shaped PR over an absent or empty roadmap is not OK —
    the building-milestone refusal only exists if the tree was read."""
    import subprocess
    (tmp_path / 'pm/roadmap').mkdir(parents=True)
    script = tmp_path / 'compare.sh'
    script.write_text(_compare_step_script(), encoding='utf-8')
    for roadmap, why in (('nope', 'is not a directory'),
                         ('pm/roadmap', 'scanned nothing')):
        proc = subprocess.run(['bash', str(script)], cwd=tmp_path, capture_output=True,
                              text=True, env={'PATH': '/usr/bin:/bin', 'PR': '0.8.1',
                                              'MAIN': '0.8', 'PM_ROADMAP': roadmap})
        assert proc.returncode == 1 and why in proc.stdout, (
            roadmap, proc.stdout + proc.stderr)


def test_the_compare_step_ignores_an_unclosed_fence_and_strips_trailing_space(tmp_path):
    import subprocess
    mdir = tmp_path / 'pm/roadmap/0.9-m'; mdir.mkdir(parents=True)
    (mdir / 'milestone.md').write_text('---\nid: "0.9"\nname: x\nfoo\n\nstatus: done\n',
                                       encoding='utf-8')
    _milestone(tmp_path, '0.8', 'done   ', quote='')
    script = tmp_path / 'compare.sh'
    script.write_text(_compare_step_script(), encoding='utf-8')
    def run(pr):
        return subprocess.run(['bash', str(script)], cwd=tmp_path, capture_output=True,
                              text=True, env={'PATH': '/usr/bin:/bin', 'PR': pr,
                                              'MAIN': '0.7', 'PM_ROADMAP': 'pm/roadmap'})
    unclosed = run('0.9')
    assert unclosed.returncode == 1 and 'the version or id of no done milestone' in unclosed.stdout, unclosed.stdout
    padded = run('0.8')
    assert padded.returncode == 0 and 'done milestone 0.8' in padded.stdout, padded.stdout


# --- verify.yml: the toolchain is the project's ------------------------------
# 0.24.0/bugs/ci-verify-installs-no-godot put a game engine, gdlint and
# shellcheck into this workflow behind `if: hashFiles(<that engine's project
# file>) != ''`, plus a step that derived the engine's version from that file.
# It was the right answer to the question being asked — one file, right in a
# game repo and in this one — and the wrong question. Decision D2 of 0.2.0: an
# installable belongs to the kit whose ARTIFACT it acts on, and a conditional
# standing in for an ownership question is how the middle tier stayed invisible.
#
# So the ~120 lines of tests that lived here are gone with the four steps they
# covered, and this comment is the tombstone: the version-derivation refusal
# matrix, the hostile-`config/features` cases and the engine-ordering assertions
# all applied to a step that is now `godot-devkit`'s to ship and to test. What
# survives is the shape any project's workflow must have, above — and the two
# assertions below, which are what is left that is TRUE of every consumer.


VERIFY = 'ci-verify.yml'
HOOKS_GUARD = "hashFiles('tools/setup-hooks.sh') != ''"


def test_the_gate_runs_after_the_checkout_is_armed():
    """`check hooks` asks whether the tree is armed, and a checkout never is.

    `core.hooksPath` lives in .git/config, nothing tracked carries it, and a
    fresh checkout has never had it set — so a gate that asks was red on every
    CI run of a repo that runs one. The arming step is the only thing between
    the checkout and the gate that is true of EVERY consumer, and it is guarded
    on a tracked file (`tools/setup-hooks.sh`) rather than on a language's
    marker.
    """
    text = body(VERIFY)
    arm = text.index('bash tools/setup-hooks.sh')
    gate = text.index('run: make milestone')
    assert arm < gate, 'the gate runs before the checkout is armed'
    assert HOOKS_GUARD in text, (
        'the arming step lost its guard — a repo that ships no corpus has '
        'nothing to arm and must skip it, not fail')


def test_the_workflow_names_no_language_toolchain():
    """The seam a consumer fills, left EMPTY and marked.

    A shipped step that installs one language's toolchain is the defect D2
    names. What ships instead is a commented placeholder saying where to put
    yours and how to guard it; a project adds its step after the write, when
    the file is its own.
    """
    text = body(VERIFY)
    for engine_token in ('setup-godot', 'gdtoolkit', 'gdlint', 'GODOT_PATCH',
                         'config/features'):
        assert engine_token not in text, (
            f'verify.yml still installs {engine_token!r}, which belongs to the '
            f'kit that owns that toolchain')
    assert 'your toolchain goes here' in text.lower(), (
        'the seam is unmarked, so a consumer has nowhere obvious to add the '
        'step this workflow deliberately does not ship')
