"""The forward-reconcile record (#92) — one census, rendered by `dispatch`.

A milestone declaring `reconcile: forward` keeps `<stem>-reconcile.md` beside
it; `check pm` WARNs while it is absent, and `dispatch --reconcile` renders its
census. A milestone without the field is unchanged. Every case builds a pooled
tree and spawns nothing.
"""
from __future__ import annotations

import contextlib
import io
from pathlib import Path

import pytest

from support.pm import loaded, run_cli, tree, write, write_config

from agentic_sdlc.cli import stock_roster
from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.core.project import load_config, repo_root
from agentic_sdlc.repo import dispatch
from agentic_sdlc.repo.checks import pm as pm_check
from agentic_sdlc.repo.pm import inventory, reconcile, vocabulary

POOLS = 'pm/roadmap'
RECORD = f'{POOLS}/milestones/0.1-reconcile.md'
NEXT_LOG = f'{POOLS}/milestones/0.2-decisions.md'
ROW = '| exit codes | 1 on usage | 2 on usage | README.md |\n'
UPDATED = '- ft-next\n'
DECISION = '# decisions\n\n## D1 — 2026-09-29 — the plan follows 0.1\n'


def _milestone(root: Path, **extra: str) -> None:
    front = {'id': '"0.1"', 'kind': 'milestone', 'name': 'Demo',
             'status': 'building', 'version': '"0.1.0"',
             'branch': 'milestone/0.1'}
    front.update(extra)
    write(root / POOLS / 'milestones/0.1.md', front)


@contextlib.contextmanager
def forward_tree(**extra: str):
    """`support.pm.tree`, its feature `done` with a record, a milestone 0.2
    after it in `order:`, and 0.2 owning the feature `ft-next`."""
    with tree(feature_status='done', story_statuses=('done',)) as root:
        _milestone(root, **extra)
        write(root / POOLS / 'milestones/0.2.md',
              {'id': '"0.2"', 'kind': 'milestone', 'name': 'Next',
               'status': 'planning'})
        write(root / POOLS / 'features/next.md',
              {'id': 'ft-next', 'kind': 'feature', 'milestone': '"0.2"',
               'name': 'Next', 'status': 'planning'})
        (root / POOLS / 'releases.md').write_text(
            '---\nid: roadmap\nkind: roadmap\norder:\n  - "0.1"\n  - "0.2"\n'
            '---\n', encoding='utf-8')
        yield root


def _record(root: Path, contracts: str, updated: str) -> None:
    (root / RECORD).write_text(
        f'{vocabulary.SLOT_HEADER[vocabulary.RECONCILE_FILE_NAME]}\n\n'
        f'## Contracts\n\n| contract | said | does | file |\n|---|---|---|---|\n'
        f'{contracts}\n## Forward grains updated\n\n{updated}\n'
        f'## Needs you\n', encoding='utf-8')


def _census(root: Path) -> reconcile.Census:
    cfg = loaded(root)
    return reconcile.census(cfg, inventory.grain(cfg, '0.1', 'milestone'))


def _declared(root: Path) -> bool:
    cfg = loaded(root)
    return reconcile.declared(cfg, inventory.grain(cfg, '0.1', 'milestone'))


def _gate(root: Path) -> tuple[int, str]:
    repo_root.cache_clear()
    load_config.cache_clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = pm_check.run()
    return code, buf.getvalue()


# (case, contracts rows, forward list, decision in 0.2?, the defect named)
CENSUS = [
    ('missing', None, '', False, 'new reconcile 0.1'),
    ('empty table', '', '', False, 'none changed'),
    ('unresolved id', ROW, '- ft-nowhere\n', False, "'ft-nowhere'"),
    ('no decision', ROW, UPDATED, False, 'no heading naming 0.1'),
    ('not forward', ROW, '- ft-here\n', False, 'is not after 0.1'),
    ('complete', ROW, UPDATED, True, ''),
    ('none changed', 'none changed\n', '', False, ''),
    # A `<!--` in a fence opens no comment, so it eats nothing up to a later
    # `-->` (C3).
    ('fenced comment', '```\n<!-- an example\n```\n' + ROW,
     '<!-- a note -->\n' + UPDATED, True, ''),
]


@pytest.mark.parametrize('case,rows,updated,decided,defect', CENSUS,
                         ids=[c[0] for c in CENSUS])
def test_the_census_names_each_defect(case, rows, updated, decided, defect):
    """Bites: a census passing a record with no row, an id that resolves to
    nothing, or a forward milestone with no decision naming this one."""
    with forward_tree(reconcile='forward') as root:
        if 'ft-here' in updated:   # a grain of this milestone, not one ahead
            write(root / POOLS / 'features/here.md',
                  {'id': 'ft-here', 'kind': 'feature', 'milestone': '"0.1"',
                   'name': 'Here', 'status': 'planning'})
        if rows is not None:
            _record(root, rows, updated)
        if decided:
            (root / NEXT_LOG).write_text(DECISION, encoding='utf-8')
        defects = _census(root).defects
        if defect:
            assert any(defect in why for why in defects), defects
        else:
            assert not defects, defects


def test_a_milestone_without_the_field_is_unchanged():
    """Bites: the opt-in leaking into every milestone — `check pm` must say
    nothing new."""
    with forward_tree() as root:
        assert not _declared(root)
        _, out = _gate(root)
        assert 'reconcile' not in out, out


def test_a_value_other_than_forward_is_exit_2_by_name():
    with forward_tree(reconcile='sideways') as root:
        with pytest.raises(ConfigError, match="reconcile: 'sideways'"):
            _declared(root)
        code, out = _gate(root)
        assert code == 2 and "'sideways'" in out, out


def test_check_pm_warns_until_new_reconcile_mints_the_record_once():
    """Bites: an opted-in milestone with no record and no line saying so
    (rule 11), or a second `pm new reconcile` over the author's bytes."""
    with forward_tree(reconcile='forward') as root:
        _, out = _gate(root)
        assert 'no reconcile.md' in out and 'pm new reconcile 0.1' in out, out
        code, out = run_cli(root, 'new', 'reconcile', '0.1')
        assert code == 0, out
        body = (root / RECORD).read_text(encoding='utf-8')
        assert body.startswith(
            vocabulary.SLOT_HEADER[vocabulary.RECONCILE_FILE_NAME]), body
        for section in reconcile.SECTIONS:
            assert f'## {section}\n' in body, section
        assert '{id}' not in body and '{name}' not in body
        _, out = _gate(root)
        assert 'no reconcile.md' not in out, out
        # The minted template is not a complete record.
        assert any('none changed' in why for why in _census(root).defects)
        (root / RECORD).write_text(body + 'mine\n', encoding='utf-8')
        code, out = run_cli(root, 'new', 'reconcile', '0.1')
        assert code == 0 and 'no-op' in out, out
        assert (root / RECORD).read_text(encoding='utf-8') == body + 'mine\n'


def test_dispatch_reconcile_renders_the_range_and_the_milestones_ahead():
    with forward_tree(reconcile='forward') as root:
        write_config(root, '[dispatch]\nproject = "p"\ncontracts = ["R.md"]\n')
        (root / 'R.md').write_text('# r', encoding='utf-8')
        repo_root.cache_clear()
        load_config.cache_clear()
        out = dispatch.render(reconcile='0.1', stock_gates=stock_roster())
        assert 'main..milestone/0.1' in out, out
        assert '    0.2  planning' in out, out
        assert RECORD in out and 'new reconcile 0.1' in out, out
        with pytest.raises(ConfigError, match='no milestone'):
            dispatch.render(reconcile='ft-next', stock_gates=stock_roster())
