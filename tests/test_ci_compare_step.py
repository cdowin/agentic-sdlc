"""test_ci_compare_step.py — the semver-gate's "Compare versions" step, RUN.

Split out of `test_ci_workflows.py` at 0.7.0. That module answers *is this the
shape a workflow has* by reading the YAML with a minimal indentation reader and
spawns nothing; this one answers *what does the `run:` body DO*, which only
bash can say. Two questions, two modules, two tiers — the split is the whole
point, because a module that reaches `subprocess` puts EVERY case in it into
the `shell` tier (`tests/conftest.py::module_spawns`), and 26 pure-parse cases
were paying that toll.

Every claim the gate makes — any-length compare, a non-numeric refusal, a
greater version and NOTHING else — is one row here, and a false PASS is the
row that fails.
"""
from __future__ import annotations

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


# --- the one question: does the version increase? ----------------------------
# Issue #116: a release is not tied to a milestone. The gate used to admit a PR
# only when its version was a `done` milestone's or a hotfix of main's, so a
# plain patch (1.6.1) with no milestone was refused. Now it compares numbers and
# reads no PM tree: every row runs in a scratch dir that HAS no `pm/roadmap`.
COMPARE_ROWS = [
    ('2.3.0',    '2.3.1',      True,  'Version bump OK: 2.3.0 -> 2.3.1'),
    ('2.3.0',    '2.4.0',      True,  'Version bump OK: 2.3.0 -> 2.4.0'),
    ('2.3.0',    '2.3.0.1',    True,  'Version bump OK: 2.3.0 -> 2.3.0.1'),
    ('2.3.0',    '3.0',        True,  'Version bump OK: 2.3.0 -> 3.0'),
    ('0.28.4.1', '0.28.5',     True,  'Version bump OK: 0.28.4.1 -> 0.28.5'),
    ('0.28.4.1', '0.28.4.2',   True,  'Version bump OK: 0.28.4.1 -> 0.28.4.2'),
    ('',         '1.0.0',      True,  'first versioned merge'),
    ('2.3.0',    '2.3.0',      False, 'Main is 2.3.0, PR is 2.3.0'),
    ('2.3.0',    '2.2.9',      False, 'Main is 2.3.0, PR is 2.2.9'),
    ('2.3.0.1',  '2.3.0',      False, 'Main is 2.3.0.1, PR is 2.3.0'),
    ('1.0',      '1.0.0',      False, 'Main is 1.0, PR is 1.0.0'),
    ('0.90.3',   '0.90.3a',    False, 'Non-numeric version component'),
    ('0.90.3',   '0.90.3.1a',  False, 'Non-numeric version component'),
]


def test_the_compare_step_passes_a_greater_version_and_reads_no_pm_tree(tmp_path):
    """Every row is one bash run in a dir with no `pm/roadmap`; a row that
    answers wrongly names itself. A patch, a minor, an appended component and
    an incremented one all pass; equal, lower and non-numeric fail and name
    both versions."""
    import subprocess
    assert 'PM_ROADMAP' not in body('ci-semver-gate.yml')
    script = tmp_path / 'compare.sh'
    script.write_text(_compare_step_script(), encoding='utf-8')
    wrong = []
    for main, pr, ok, why in COMPARE_ROWS:
        proc = subprocess.run(['bash', str(script)], cwd=tmp_path, capture_output=True,
                              text=True, env={'PATH': '/usr/bin:/bin', 'PR': pr,
                                              'MAIN': main})
        text = proc.stdout + proc.stderr
        if (proc.returncode == 0) is not ok or why not in text:
            wrong.append(f'main={main} pr={pr}: exit {proc.returncode}, {text!r}')
    assert not wrong, '\n'.join(wrong)


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
