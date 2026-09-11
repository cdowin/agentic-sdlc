"""test_init_verb.py — `agentic-sdlc init` on a fresh repo.

The verb is a COMPOSITION, so the contract under test is what a composition
can get wrong:

  * the file set is EXACTLY the documented one — spelled literally below, so
    this file reads as the roster, and cross-checked against the tables the
    verbs actually carry so the literal cannot rot;
  * a second run writes NOTHING — proven by hashing every file before and
    after, not by reading the report, which is the thing that would lie;
  * `--diff` names drift on BOTH ownerships (a devkit-owned installable and a
    project-owned seed) and writes nothing;
  * `--force` respects the ownership split: it overwrites the installed files
    and does not touch devkit.toml / Makefile / CLAUDE.md / the PM tree;
  * THERE IS ONE REFUSAL, and it is decided BEFORE the first byte: a directory
    that is not a git repo is left as it was found. The second refusal 0.1.0
    carried is held as its INVERSE rather than deleted — see
    `test_a_git_repo_with_no_engine_project_file_is_initialized_whole`.

The fixture keeps a `project.godot` and an icon because a fresh repo with two
files of its own is the realistic shape, not because `init` reads either one —
the case named above says so. Nothing here boots anything. `init` runs OUT OF
PROCESS, because it resolves the repo root and the config through module-level
caches that a same-process run would leave pointing at a deleted temp directory.
"""
from __future__ import annotations

import ast
import contextlib
import hashlib
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import __version__  # noqa: E402
from agentic_sdlc.repo import dispatch, init, install  # noqa: E402
from agentic_sdlc.repo.pm import model  # noqa: E402
from agentic_sdlc.repo.verify import rules as verify_rules  # noqa: E402

PROJECT_GODOT = ('config_version=5\n\n[application]\n\n'
                 'config/name="Fresh"\nconfig/version="0.1.0"\n')
ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"/>\n'

# THE ROSTER. Spelled out so this file states the contract; cross-checked
# against the verbs' own tables below so it cannot become a second list that
# quietly disagrees with what ships.
#
# IT SHRANK FROM 49 TO 34 IN 0.2.0 under decision D2 — an installable belongs to
# the kit whose ARTIFACT it acts on — and the number is recorded here because a
# roster that only ever gets shorter is how a census stops being one. Nothing on
# this list is optional, and `test_the_roster_above_is_what_the_verbs_actually_carry`
# is what stops the number moving again without a line moving here.
WRITES = (
    'devkit.toml',
    '.claude/rules/pm-execution.md',
    '.claude/skills/pm-operations/SKILL.md',
    # A skill rather than a rule: nothing path-triggers on "write me a
    # handoff", and a skill description is the only surface that matches
    # the words somebody types (0.4.0 decisions.md D6).
    '.claude/skills/handoff/SKILL.md',
    'Makefile',
    'Makefile.devkit',
    'tools/dev/gdk_gate.sh',
    'tools/hooks/cc-commit-pathspec.sh',
    'tools/hooks/cc-stop-gate.sh',
    'tools/hooks/cc-write-confine.sh',
    'tools/hooks/cc-ledger-subagent.sh',
    'tools/hooks/cc-ledger-session.sh',
    'tools/hooks/pre-push',
    'tools/hooks/prepare-commit-msg',
    'tools/dev/agent-worktree.sh',
    'tools/setup-hooks.sh',
    '.claude/agents/verification-reviewer.md',
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
    '.claude/agents/pm-operator.md',
    '.github/workflows/verify.yml',
    '.github/workflows/semver-gate.yml',
    '.github/workflows/auto-tag.yml',
    '.gitignore',
    'CLAUDE.md',
    'docs/sdlc-protocol.md',
)
# Rule 4: the roster above must not be able to collapse and still pass. 34 is
# what ships today; the floor is what a composition of four install verbs plus
# four owned writes cannot go under without a verb having silently stopped
# firing, and it is asserted rather than trusted.
ROSTER_FLOOR = 20
assert len(WRITES) == len(set(WRITES)) >= ROSTER_FLOOR, WRITES

# What the fixture starts with — everything else present afterwards is init's.
PRE_EXISTING = ('project.godot', 'icon.svg')


@contextlib.contextmanager
def fresh_project(git: bool = True, files: dict[str, str] | None = None):
    """An empty Godot 4 project: a project.godot, an icon, and a git repo."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'game'
        root.mkdir()
        (root / 'project.godot').write_text(PROJECT_GODOT, encoding='utf-8')
        (root / 'icon.svg').write_text(ICON, encoding='utf-8')
        for rel, body in (files or {}).items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        if git:
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        yield root


def devkit(root: Path, *argv: str) -> subprocess.CompletedProcess:
    """The CLI, out of process, from SOURCE — never a cached wheel."""
    return subprocess.run(
        [sys.executable, '-m', 'agentic_sdlc.cli', *argv],
        cwd=root, capture_output=True, text=True,
        env={**os.environ, 'PYTHONPATH': str(REPO_ROOT / 'src')})


def census(root: Path) -> dict[str, str]:
    """Every file in the tree, git metadata excluded, as path -> content hash."""
    found: dict[str, str] = {}
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith('.git/'):
            continue
        found[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


# --- the one step init cannot take ---------------------------------------------
def test_init_names_the_settings_file_the_hooks_are_registered_in():
    """`init` installs the hooks and cannot ARM them with a harness.

    Through 0.5.0 it called `install.main(..., next_step=False)`, which skips
    the settings step entirely — so the brand-new consumer this composition
    exists for got no destination, no block and no flag, while the seven-step
    Next list named `.claude/settings.json`, `--write-settings`, the block and
    `GDK_LEDGER_ROOT` zero times. That is strictly less than the hand-paste
    the step replaced.
    """
    with fresh_project() as root:
        done = devkit(root, 'init')
        assert done.returncode == 0, done.stdout + done.stderr
        out = done.stdout
        # `.resolve()`: the emitted path is the one `repo_root()` found,
        # symlinks and all, which is the canonical spelling of the tree.
        here = root.resolve()
        assert str(here / install.AGENT_SETTINGS) in out, out
        assert install.SETTINGS_FLAG in out, out
        assert f'GDK_LEDGER_ROOT={here}' in out, out
        # The BLOCK, parseable and last on stdout, so it can be pasted whole.
        block = json.loads(out[out.index('{\n  "hooks"'):out.rindex('}') + 1])
        assert set(block['hooks']) >= {'Stop', 'SubagentStop'}, block
        # And `init` still writes nothing there: the offer is the whole act.
        assert not (root / install.AGENT_SETTINGS).exists(), out


# --- the file set -------------------------------------------------------------
def test_init_writes_exactly_the_documented_file_set():
    with fresh_project() as root:
        done = devkit(root, 'init')
        assert done.returncode == 0, done.stdout + done.stderr
        present = set(census(root))
    assert present == set(WRITES) | set(PRE_EXISTING), (
        f'unexpected: {sorted(present - set(WRITES) - set(PRE_EXISTING))}; '
        f'missing: {sorted(set(WRITES) - present)}')


def test_the_roster_above_is_what_the_verbs_actually_carry():
    """The literal roster cross-checked against the tables that ship, so an
    installable added to a plan without a line up there fails HERE rather than
    silently widening what `init` writes."""
    from_tables = {rel for entries in install.PLANS.values()
                   for _, rel in entries}
    from_tables |= {rel for _, rel in init.SEEDS}
    # No `install.PLANS` entry: .gitignore is init's own write and the guidance
    # files come from `skills.py`'s own plan. Named here for exactly that
    # reason. 0.3.0: ROADMAP.md left this list with the file; `init` still
    # stands up `pm/roadmap/` itself, a DIRECTORY, which writes no file here.
    owned = {'.gitignore',
             '.claude/rules/pm-execution.md',
             '.claude/skills/pm-operations/SKILL.md',
             '.claude/skills/handoff/SKILL.md'}
    assert set(WRITES) == from_tables | owned, (
        f'roster drift: {sorted(set(WRITES) ^ (from_tables | owned))}')


def test_the_makefile_pins_this_version_and_includes_the_standard_set():
    with fresh_project() as root:
        assert devkit(root, 'init').returncode == 0
        body = (root / 'Makefile').read_text(encoding='utf-8')
    assert f'DEVKIT_VERSION := v{__version__}' in body, body
    assert 'include Makefile.devkit' in body, body
    assert init.VERSION_PLACEHOLDER not in body, 'the pin was never substituted'


# Every [section] the seed devkit.toml offers, asserted as an EQUALITY rather
# than as a floor, which is the direction that got stronger: a section ADDED to
# the template without a line here now fails too, where the old `in` loop would
# have let one arrive unmentioned.
CONFIG_SECTIONS = ('checks', 'gates', 'doc', 'shell', 'grain_shape', 'repo_hygiene',
                   'pm', 'emit', 'verify', 'dispatch')


# The two sections with NO default behind them, each with the reader that
# refuses when it is absent. Hard rule 5's workflow half, as an assertion
# rather than as prose: the byte-identical guarantee is GATES-ONLY, and these
# are what it is not about.
DECLARATIONS = {
    '[pm.states.*]': lambda: model.missing_flow_defect({}),
    '[verify]': lambda: _refusal(verify_rules.read, {}),
    # 0.6.0: the preamble a dispatched agent gets. Its `contracts` are the
    # project's own authored files and the tool cannot invent them (rule 8),
    # so there is nothing to stand behind the key.
    '[dispatch]': lambda: _refusal(dispatch.settings, {}),
}


def _refusal(reader, section) -> str:
    """Why this reader refuses an absent section, or '' if it does not."""
    try:
        reader(section)
    except model.ConfigError as err:
        return str(err)
    return ''


def test_the_config_template_carries_every_section_the_gates_read():
    """Commented out, at the stock default — a repo with no devkit.toml must
    behave byte-identically to one declaring the defaults, so the GATE half of
    the template is a menu rather than an opinion.

    **THE GUARANTEE IS GATES-ONLY, and that is what this case asserts.** Every
    gate key has a real default and the commented line IS that default
    (`tests/test_config_seed.py` compares the two, key by key). The FILE is not
    optional, though, and the two sections below are why: nothing sits behind
    `[pm.states.*]` or `[verify]`, so their readers REFUSE BY NAME instead of
    falling back, and a tree without the first has no working `pm` at all.
    `[pm.states.*]` is therefore the one section written LIVE — every live line
    has to belong to it, asserted as an equality against `render_seed()`, which
    is also what `test_pm_flow.py` pins the template's bytes to. `[verify]`
    stays commented because its argument is make targets this seed cannot know,
    and it says so where it sits.
    """
    body = init.seed_body(init.SEED_CONFIG[0])
    offered = re.findall(r'^# \[([a-z_]+)\]$', body, re.MULTILINE)
    assert offered, 'the template offers no section at all'
    assert sorted(offered) == sorted(CONFIG_SECTIONS), (
        f'template drift: {sorted(set(offered) ^ set(CONFIG_SECTIONS))}')
    live = [ln for ln in body.splitlines()
            if ln.strip() and not ln.lstrip().startswith('#')]
    seeded = [ln for ln in model.render_seed().splitlines() if ln.strip()]
    assert live == seeded, (
        f'the template declares something outside the flow: '
        f'{[ln for ln in live if ln not in seeded]}')
    for name, refuses in DECLARATIONS.items():
        assert refuses(), (
            f'{name} now has a default behind it — then it is a GATE key, the '
            f'byte-identical guarantee covers it, and it belongs commented at '
            f'that value like every other knob in the seed')


# Each `IGNORED` entry, pinned to the constant in the file that WRITES it.
# `(shipped shell file, variable)` for a shell default — not readable from
# Python, but greppable — and `None` for the one whose writer is Python and can
# simply be imported.
IGNORE_OWNERS = {
    '.gate-reports/': ('gdk_gate.sh', 'GDK_GATE_REPORT_DIR'),
    '.agent-scope': ('agent-worktree.sh', 'SCOPE_MARKER'),
    '.claude/worktrees/': ('agent-worktree.sh', 'WORKTREE_PARENT'),
}


def test_the_gitignore_entries_are_their_writers_own_defaults():
    """A shell default is not readable from Python, so it is PINNED here: each
    ignored path must be the default of the shipped file that writes it. A
    rename on either side fails this rather than silently committing a
    consumer's run artifacts.

    THREE ENTRIES (R3,
    `docs/reviews/2026-09-05-the-release-is-a-conveyor.md`). It was
    `.gate-reports/` alone while three other paths this package's own files
    write were left tracked, and `.agentic-sdlc/` is the one that bit: the
    conveyor's run state dirtied the tree the conveyor's own `tree-clean` step
    measures. The floor this census stands on is that it is not EMPTY — an
    `IGNORED` that emptied out would have every consumer committing its run
    artifacts while this test passed over nothing, so emptiness is a failure
    here before the equality below is even asked.
    """
    assert init.IGNORED, 'init.IGNORED is empty — this test would prove nothing'
    assert set(init.IGNORED) == set(IGNORE_OWNERS)
    for entry, owner in IGNORE_OWNERS.items():
        if owner is None:
            continue
        shipped, variable = owner
        body = install.body_of(shipped)
        # Both spellings the shipped scripts use: a `${VAR:-default}` fallback
        # and a plain assignment. Either one is the file DECLARING that path.
        assert (f'{variable}="${{{variable}:-{entry.rstrip("/")}}}"' in body
                or f'{variable}="{entry.rstrip("/")}"' in body), (
            f'{shipped} no longer defaults {variable} to {entry}')


def test_every_run_artifact_this_package_writes_is_ignored():
    """R3's second half: the SWEEP, not just the one entry that was found.

    Gitignoring is what keeps `tree-clean` answerable (under D12 a belt keeps
    no run state, so the directory it once wrote is gone from this sweep), so
    a path this package's own files write and `init` does not ignore is a
    `tree-clean` this package falsifies in every consumer. Asked of the
    installables' own constants rather than restated, so a renamed marker fails
    here instead of quietly re-opening the hole.
    """
    writes: set[str] = set()
    body = install.body_of('agent-worktree.sh')
    for variable in ('SCOPE_MARKER', 'WORKTREE_PARENT'):
        found = re.search(rf'^{variable}="([^"]+)"', body, re.MULTILINE)
        assert found, f'agent-worktree.sh declares no {variable}'
        writes.add(found.group(1))
    ignored = {entry.rstrip('/') for entry in init.IGNORED}
    missing = sorted(path for path in writes if path.rstrip('/') not in ignored)
    assert missing == [], (
        f'{missing} are written by files this package installs and are in no '
        f'init.IGNORED entry — every one of them dirties the tree that '
        f'`tree-clean` measures')


# --- idempotence --------------------------------------------------------------
def test_a_second_run_writes_nothing():
    with fresh_project() as root:
        assert devkit(root, 'init').returncode == 0
        before = census(root)
        done = devkit(root, 'init')
        after = census(root)
    assert done.returncode == 0, done.stdout + done.stderr
    changed = [rel for rel in before if before[rel] != after.get(rel)]
    assert not changed, f'a second run rewrote: {changed}'
    assert set(after) == set(before), (
        f'a second run added: {sorted(set(after) - set(before))}')
    # The LINE SHAPE, not the word. `'wrote' not in stdout` was a false
    # positive the moment init's own next-steps prose used the word — the third
    # substring assertion in this milestone to catch prose instead of the thing
    # it was aimed at ('DLC.md' is in 'SDLC.md' too). The two assertions above
    # already prove no byte moved; this one exists to catch a verb that WRITES
    # and reports itself as current, so it must match what the writer prints.
    wrote = [line for line in done.stdout.splitlines()
             if line.startswith(('[install] wrote ', '[init] wrote ',
                                 '[pm] wrote '))]
    assert wrote == [], done.stdout


def test_a_second_run_does_not_duplicate_the_gitignore_entries():
    with fresh_project(files={'.gitignore': '*.tmp\n'}) as root:
        assert devkit(root, 'init').returncode == 0
        assert devkit(root, 'init').returncode == 0
        body = (root / '.gitignore').read_text(encoding='utf-8')
    assert body.startswith('*.tmp\n'), 'the project\'s own entries were lost'
    for entry in init.IGNORED:
        assert body.count(entry) == 1, f'{entry} appears twice:\n{body}'


# --- --diff -------------------------------------------------------------------
# The devkit-owned file the ownership cases below drift. A hook, so the refusal
# case can still name the verb that owns it.
DEVKIT_OWNED = 'tools/hooks/cc-stop-gate.sh'


def test_diff_names_drift_on_both_ownerships_and_writes_nothing():
    with fresh_project() as root:
        assert devkit(root, 'init').returncode == 0
        (root / DEVKIT_OWNED).write_text(
            '#!/usr/bin/env bash\necho mine\n', encoding='utf-8')
        (root / 'CLAUDE.md').write_text('# mine\n', encoding='utf-8')
        before = census(root)
        done = devkit(root, 'init', '--diff')
        after = census(root)
    assert done.returncode == 0, done.stdout + done.stderr
    assert before == after, '--diff wrote something'
    assert f'a/{DEVKIT_OWNED}' in done.stdout, done.stdout
    assert 'a/CLAUDE.md' in done.stdout, done.stdout
    # Everything else is reported current, so the drift is what stands out.
    assert done.stdout.count('already current') >= len(WRITES) - 4, done.stdout


def test_diff_names_a_missing_gitignore_entry():
    with fresh_project() as root:
        assert devkit(root, 'init').returncode == 0
        (root / '.gitignore').write_text('*.tmp\n', encoding='utf-8')
        done = devkit(root, 'init', '--diff')
    assert done.returncode == 0, done.stdout + done.stderr
    assert '.gitignore is missing .gate-reports/' in done.stdout, done.stdout


# --- ownership ----------------------------------------------------------------
def test_a_differing_project_owned_file_is_reported_not_refused():
    """devkit.toml, Makefile and CLAUDE.md are the project's from the first
    write. Divergence is what they are FOR, so it is not a collision. The one
    thing init still does to a devkit.toml it did not write is APPEND the
    flow, because that is the section nothing falls back on — every byte the
    project wrote stays, in front of it."""
    with fresh_project() as root:
        assert devkit(root, 'init').returncode == 0
        mine = '# mine\n'
        for rel in ('devkit.toml', 'Makefile', 'CLAUDE.md'):
            (root / rel).write_text(mine, encoding='utf-8')
        done = devkit(root, 'init')
        kept = [(root / rel).read_text(encoding='utf-8')
                for rel in ('devkit.toml', 'Makefile', 'CLAUDE.md')]
    assert done.returncode == 0, done.stdout + done.stderr
    assert kept[1:] == [mine] * 2, 'a project-owned file was overwritten'
    assert kept[0].startswith(mine), 'devkit.toml lost the project\'s bytes'
    assert model.render_seed() in kept[0], kept[0]
    assert done.stdout.count('is yours — left alone') == 3, done.stdout
    assert 'appended the flow to devkit.toml' in done.stdout, done.stdout


def test_init_appends_the_flow_to_a_config_it_did_not_write_byte_preserving():
    """F2/F3 of docs/reviews/2026-09-05-the-project-declares-its-flow.md,
    measured the way the review measured them: a hand-written CRLF
    devkit.toml with `[checks]` and `[pm]` and NO `[pm.states.*]`.

    No existing case could fail for this. Every other case here initialises
    a tree that has no devkit.toml, so the template is written whole and the
    append path never runs; the one case that pre-writes the file (above)
    read it back as text, which is where a CRLF-to-LF rewrite hides. This one
    holds the BYTES: the original is a prefix of the result, the appended
    block uses the file's own CRLF, the second run changes nothing, and a
    verb that asks `flow_of` — the refusal that names `pm init` — now works.
    """
    theirs = ('[checks]\r\nall = ["doc"]\r\n\r\n[pm]\r\n'
              'review_dir = "docs/reviews"\r\n')
    with fresh_project(files={'devkit.toml': theirs}) as root:
        path = root / 'devkit.toml'
        path.write_bytes(theirs.encode())          # write_text would translate
        done = devkit(root, 'init')
        assert done.returncode == 0, done.stdout + done.stderr
        first = path.read_bytes()
        assert first.startswith(theirs.encode()), first
        appended = first[len(theirs):].decode()
        assert '\n' not in appended.replace('\r\n', ''), (
            'the appended block does not use the file\'s CRLF')
        assert appended.replace('\r\n', '\n').endswith(model.render_seed())
        again = devkit(root, 'init')
        assert again.returncode == 0, again.stdout + again.stderr
        assert path.read_bytes() == first, 'a second run rewrote devkit.toml'
        assert 'already declares [pm.states.*]' in again.stdout, again.stdout
        # ...and the tree the refusal was about now answers.
        vocab = devkit(root, 'pm', 'vocabulary', '--json')
        assert vocab.returncode == 0, vocab.stderr
        assert '"flow_declared": true' in vocab.stdout


def test_force_overwrites_the_installed_files_and_not_the_projects_own():
    with fresh_project() as root:
        assert devkit(root, 'init').returncode == 0
        stock = (root / DEVKIT_OWNED).read_text(encoding='utf-8')
        (root / DEVKIT_OWNED).write_text('# mine\n', encoding='utf-8')
        (root / 'CLAUDE.md').write_text('# mine\n', encoding='utf-8')
        done = devkit(root, 'init', '--force')
        restored = (root / DEVKIT_OWNED).read_text(encoding='utf-8')
        claude = (root / 'CLAUDE.md').read_text(encoding='utf-8')
    assert done.returncode == 0, done.stdout + done.stderr
    assert restored == stock, '--force did not restore the devkit-owned file'
    assert claude == '# mine\n', '--force overwrote a project-owned file'


def test_a_differing_installed_file_refuses_and_names_force():
    with fresh_project() as root:
        assert devkit(root, 'init').returncode == 0
        (root / DEVKIT_OWNED).write_text('# mine\n', encoding='utf-8')
        done = devkit(root, 'init')
        kept = (root / DEVKIT_OWNED).read_text(encoding='utf-8')
    assert done.returncode == 1, done.stdout + done.stderr
    assert kept == '# mine\n', 'the refusal wrote anyway'
    assert '--force' in done.stderr + done.stdout
    assert 'REFUSED by install-hooks' in done.stdout, done.stdout


# --- the refusal matrix, and the refusal that was REMOVED ---------------------
def test_a_git_repo_with_no_engine_project_file_is_initialized_whole():
    """THE REMOVAL, HELD. This exact tree — `git init` and nothing else — was
    refused at exit 2 through 0.1.0 for holding no `project.godot`, and this
    case asserted the refusal. 0.2.0 took the engine half out and the refusal
    went with it: an engine-less kit whose `init` declined every engine-less
    repo was the sharpest thing left in the package.

    So the case is INVERTED rather than deleted. A removal that is merely
    absent from a suite is a removal nothing holds, and the way this one comes
    back is a preflight quietly regaining an opinion — which would read as an
    exit code nobody asserted. What is asked is the whole result, not the exit
    code: the roster lands entire in a repo with no engine file anywhere in
    it, and no output mentions one.
    """
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        done = devkit(root, 'init')
        present = set(census(root))
    assert done.returncode == 0, done.stdout + done.stderr
    assert 'project.godot' not in done.stdout + done.stderr, (
        f'init has an opinion about an engine project file again:\n'
        f'{done.stdout}{done.stderr}')
    assert present == set(WRITES), (
        f'missing: {sorted(set(WRITES) - present)}; '
        f'unexpected: {sorted(present - set(WRITES))}')


def test_a_directory_that_is_not_a_git_repo_is_refused_whole():
    """The ONE refusal left, and it still fires before the first byte: the
    tree comes back holding exactly what it held going in."""
    with fresh_project(git=False) as root:
        done = devkit(root, 'init')
        left = set(census(root))
    assert done.returncode == 2, done.stdout + done.stderr
    assert 'not a git repository' in done.stderr
    assert left == set(PRE_EXISTING), f'a refused init wrote: {sorted(left)}'


def test_the_preflight_carries_exactly_one_refusal():
    """The other half of the inversion, asked of the code rather than of a run.
    `_preflight` is the whole before-the-first-byte gate, and the case above
    proves the engine one is gone by OBSERVING one tree; this proves there is
    no third refusal waiting for a tree neither case builds."""
    reasons = [node for node in ast.walk(ast.parse(
        inspect.getsource(init._preflight)))
        if isinstance(node, ast.Return) and not (
            isinstance(node.value, ast.Constant) and node.value.value == '')]
    assert len(reasons) == 1, (
        f'`init` grew a refusal: _preflight has {len(reasons)} of them, and '
        f'the suite asserts one — the git-repo check')


def test_an_unknown_flag_is_a_usage_error_that_writes_nothing():
    """Five spellings, one project: a usage error writes nothing, so the
    tree is as fresh for the second flag as for the first."""
    with fresh_project() as root:
        for flag in ('--forse', '-f', 'install', '--diff=1', ''):
            done = devkit(root, 'init', flag)
            left = set(census(root))
            assert done.returncode == 2, (flag, done.stdout + done.stderr)
            assert 'unknown flag' in done.stderr, flag
            assert left == set(PRE_EXISTING), (
                f'{flag!r}: a usage error wrote: {sorted(left)}')


def test_help_prints_the_written_set_and_writes_nothing():
    with fresh_project() as root:
        done = devkit(root, 'init', '--help')
        left = set(census(root))
    assert done.returncode == 0, done.stdout + done.stderr
    assert 'usage: agentic-sdlc init' in done.stdout
    assert left == set(PRE_EXISTING)


def test_a_seed_destination_that_is_a_directory_is_a_refusal_not_a_traceback():
    with fresh_project() as root:
        (root / 'CLAUDE.md').mkdir()
        done = devkit(root, 'init')
    assert done.returncode == 1, done.stdout + done.stderr
    assert 'CLAUDE.md is a directory' in done.stderr, done.stderr
    assert 'Traceback' not in done.stderr


# --- what init does BEYOND writing --------------------------------------------
def test_the_hooks_are_armed_not_merely_installed():
    """`core.hooksPath` silently skips a non-executable hook, so an install
    without the arming run is a guard that is not there."""
    with fresh_project() as root:
        done = devkit(root, 'init')
        configured = subprocess.run(
            ['git', 'config', '--get', 'core.hooksPath'], cwd=root,
            capture_output=True, text=True).stdout.strip()
        modes = {p.name: os.access(p, os.X_OK)
                 for p in (root / 'tools/hooks').iterdir()}
    assert done.returncode == 0, done.stdout + done.stderr
    assert configured == 'tools/hooks', configured
    assert all(modes.values()), f'not executable: {sorted(k for k, v in modes.items() if not v)}'


def test_the_installed_claude_md_passes_the_doc_gate_it_arrives_beside():
    """Install day must be green. The skeleton names the standard targets, and
    every one of them lives in the INCLUDED Makefile — which is why `check doc`
    resolves a repo's include chain rather than only its root Makefile."""
    with fresh_project() as root:
        assert devkit(root, 'init').returncode == 0
        subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
        done = devkit(root, 'check', 'doc')
    assert done.returncode == 0, (
        f'the skeleton reddens the gate on install day:\n'
        f'{done.stdout}{done.stderr}')


def test_the_doc_gate_widened_to_the_include_chain_and_no_further():
    """The other half of the fix above: `check doc` now resolves the targets an
    included Makefile defines — and STILL fails a target neither file defines.
    A widening that turned the gate into a false PASS would be the cardinal
    sin, so both directions are asserted in one tree."""
    with fresh_project() as root:
        assert devkit(root, 'init').returncode == 0
        # A tier the project's kit hangs off the include's `-include
        # $(GDK_TIERS_MK)` seam — a variable path, resolved from the
        # include's own `?=` default rather than skipped. Every `make unit`
        # in every consumer's CLAUDE.md read as dead until it was.
        (root / 'Makefile.tiers').write_text(
            'GDK_PRECOMMIT_TIERS := kit-unit\n.PHONY: kit-unit\n'
            'kit-unit:\n\t@echo unit\n', encoding='utf-8')
        (root / 'CLAUDE.md').write_text(
            '# Doc\n\nThe gate is `make check`, `make precommit` and '
            '`make kit-unit`.\n', encoding='utf-8')
        subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
        green = devkit(root, 'check', 'doc')
        (root / 'CLAUDE.md').write_text(
            '# Doc\n\nThe gate is `make check` and `make wombat`.\n',
            encoding='utf-8')
        red = devkit(root, 'check', 'doc')
    assert green.returncode == 0, green.stdout + green.stderr
    assert red.returncode == 1, red.stdout
    assert 'unknown make target: `make wombat`' in red.stdout, red.stdout
    assert 'make check' not in red.stdout.split('wombat')[0].split('\n')[-1]
