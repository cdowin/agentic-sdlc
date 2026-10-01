"""test_release.py — `release <version>`: five facts, then one write or none.

`release` runs no gate (2.0.0). It asks whether one milestone claims the
version, every feature under it is `done`, the version sites agree, the tree
is clean and HEAD is the milestone's branch. All true: the milestone takes its
`done` state and the `next:` lines print. Any false: exit 1 and nothing is
written. `--force` writes anyway and files ONE `deviation` row naming every
false check. The same command twice is a no-op (rule 3).

Integration tier: `tree-clean` and `on-milestone-branch` are questions only
git answers, so each case builds a real repository.
"""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402
from support.pm import (LEDGER_REL, commit, git, git_tree,  # noqa: E402
                        ledger_rows, write)

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core import frontmatter  # noqa: E402
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo import belts  # noqa: E402
from agentic_sdlc.repo.pm import ledger, vocabulary  # noqa: E402

VERSION = '0.1.0'
BRANCH = 'milestone/0.1'
MFILE = 'pm/roadmap/milestones/0.1.md'


@contextlib.contextmanager
def repo(feature_status: str = 'done', config: str = ''):
    """`git_tree` with a milestone that claims VERSION and names BRANCH, a
    version file that agrees, every story done, committed, on BRANCH."""
    with git_tree(feature_status=feature_status, story_statuses=('done',),
                  config=config) as root:
        write(root / MFILE, {'id': '"0.1"', 'kind': 'milestone', 'name': 'Demo',
                             'status': 'building', 'version': VERSION,
                             'branch': BRANCH})
        (root / 'pyproject.toml').write_text(
            f'[project]\nname = "demo"\nversion = "{VERSION}"\n',
            encoding='utf-8')
        git(root, 'checkout', '-q', '-b', BRANCH)
        commit(root)
        yield root


def release(*argv: str) -> tuple[int, str]:
    repo_root.cache_clear()
    load_config.cache_clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = belts.main(['release', *argv])
    return code, buf.getvalue()


def status(root: Path) -> str:
    return frontmatter.field_of(root / MFILE, 'status')


def deviations(root: Path) -> list[dict]:
    rows = ledger_rows(root) if (root / LEDGER_REL).exists() else []
    return [r for r in rows if r['kind'] == ledger.KIND_DEVIATION]


def done_state() -> str:
    return vocabulary.flow_of(vocabulary.load(), 'milestone').by_category[
        vocabulary.DONE_CATEGORY][0]


def roadmap_bytes(root: Path) -> dict[Path, bytes]:
    return {p: p.read_bytes() for p in (root / 'pm').rglob('*') if p.is_file()}


def test_a_feature_not_done_is_named_and_nothing_is_written():
    """Bites: a release over an open feature, or a write after a false check."""
    with repo(feature_status='building') as root:
        before = roadmap_bytes(root)
        code, out = release(VERSION)
        assert code == 1, out
        assert '[release] error: features-done: 1 of 1 feature(s)' in out, out
        assert '0.1/alpha (building)' in out, out
        assert '[release] ok: tree-clean' in out, out
        assert 'no status written' in out and 'next:' not in out, out
        assert roadmap_bytes(root) == before


def test_all_true_writes_the_done_state_once_and_a_second_run_is_a_no_op():
    """Bites: a release that does not write, or that writes again (rule 3)."""
    with repo() as root:
        code, out = release(VERSION)
        assert code == 0, out
        for check in ('milestone-resolves', 'features-done', 'version-sync',
                      'tree-clean', 'on-milestone-branch'):
            assert f'[release] ok: {check} — ' in out, out
        assert status(root) == done_state()
        assert f'[release] ok — {VERSION} → {done_state()}' in out, out
        assert f'next: push the branch: `git push -u origin {BRANCH}`' in out
        assert f'git tag v{VERSION}' in out
        after = roadmap_bytes(root)
        code, out = release(VERSION)
        assert code == 0, out
        assert 'already' in out and 'nothing written' in out, out
        assert roadmap_bytes(root) == after, 'a second release wrote'


def test_force_writes_and_files_one_row_naming_every_false_check():
    """Bites: a forced write with no account of what it forced."""
    with repo(feature_status='building') as root:
        (root / 'stray.txt').write_text('dirt\n', encoding='utf-8')
        code, out = release(VERSION, '--force')
        assert code == 0, out
        assert status(root) == done_state()
        assert f'[release] forced — {VERSION} → {done_state()} over 2' in out
        rows = deviations(root)
        assert len(rows) == 1, rows
        assert rows[0]['outcome'] == belts.FORCED
        assert rows[0]['step'] == 'features-done, tree-clean'
        assert 'stray.txt' in rows[0]['reason']


def test_version_sites_that_disagree_are_named():
    with repo() as root:
        (root / 'pyproject.toml').write_text(
            '[project]\nname = "demo"\nversion = "0.0.9"\n', encoding='utf-8')
        commit(root)
        code, out = release(VERSION)
        assert code == 1, out
        assert ('[release] error: version-sync: pyproject.toml says 0.0.9 — '
                f'the release is {VERSION}') in out, out
        assert status(root) == 'building'


def test_a_retired_release_key_is_refused_by_name_and_nothing_runs():
    """Bites: `[release] steps` kept by a consumer and silently ignored."""
    with repo(config='[release]\nsteps = ["gate"]\n') as root:
        code, out = release(VERSION)
        assert code == 2, out
        assert '[release] steps is retired' in out and 'runs no gate' in out
        assert '[release] ok:' not in out
        assert status(root) == 'building'
