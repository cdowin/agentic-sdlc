"""Property fuzz: mangled input against the CLI's universal negatives.

A docstring's universal negative ("this cannot write a sibling grain") is the
one claim an existential test never attacks, and every blocker this harness was
built for had that shape. So a seeded mangler composes hostile ids and paths —
traversal, empty and dot segments, backslashes, globs, absolute paths, URL-ish
schemes, whitespace, newlines, quotes, unicode confusables, over-long strings —
and drives them through the REAL CLI against a scratch tree, asserting the
property the docstrings claim:

  GRAIN CONTAINMENT (pm) — for every id fed to status verbs / set / get /
  move / decide: either the command refuses (exit 1/2, whole scratch tree
  byte-identical, proven by snapshot), or every file it touched realpaths
  INSIDE pm/roadmap/<milestone>/ in the slot the verb's grain kind owns. Never
  an exception escaping `cli.main` (the real CLI's traceback), and never a
  write to a file the command did not name.

TEETH, proven rather than assumed. `DEVKIT_FUZZ_TARGET_SRC=<dir>` points the
harness at another checkout's `src/`, which is how the corpus was run against
the resolver it was written for. The committed floor under that one-time run is
`test_the_corpus_separates_the_pre_fix_resolver`, which keeps a transcription
of the rejected resolver in-tree and proves the corpus still reaches it.
"""
from __future__ import annotations

import contextlib
import functools
import io
import os
import random
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support  # noqa: E402,F401 — imported for the side effect it owns: the
# support package is what puts src/ on sys.path, and this module imports the
# package below.

# Teeth-proof overlay: point the harness at another src tree (see docstring).
# Purging agentic_sdlc from sys.modules makes the overlay win even when another
# collected test file imported the package first — run this file alone when
# the variable is set.
_TARGET_SRC = os.environ.get('DEVKIT_FUZZ_TARGET_SRC')
if _TARGET_SRC:
    sys.path.insert(0, str(Path(_TARGET_SRC).resolve()))
    for _name in [m for m in list(sys.modules)
                  if m.split('.')[0] == 'agentic_sdlc']:
        del sys.modules[_name]

from agentic_sdlc import cli  # noqa: E402
from agentic_sdlc.repo.pm.ledger import LEDGER_FILE_NAME  # noqa: E402

# BELOW the overlay purge on purpose: `support.pm` derives `FLOW_TOML` from
# `vocabulary.render_seed()` at import, so importing it above would seed the scratch
# tree from THIS checkout's seed while the fuzz drove the overlaid one.
from support.pm import FLOW_TOML  # noqa: E402

pytestmark = pytest.mark.fuzz

# The seed is part of the gate. Changing it changes which hostile inputs are
# covered, so it moves only with a recorded reason.
SEED = 20260830
PM_CASES = 320


# --- the mangler --------------------------------------------------------------
# Composed, not enumerated: hostile SEGMENTS spliced into valid ids, joined by
# hostile SEPARATORS, wrapped in hostile PREFIXES. Every input class the module
# docstring names has members here, and `_classes_of` is the census that proves
# the generator still emits all of them.
_HOSTILE_SEGMENTS = (
    '..', '..', '.', '', '...', '.md', '.git',
    'a\\b', '..\\..', 'C:\\roadmap',
    '*', '?', 's[0-9]', 'st*ries', '!bang',
    ' ', ' alpha', 'crash ', '\ttab', 'two words',
    'аlpha', 'ѕ0', '０.１', 'x\u200by', 'bugs\u2024crash',
    'x' * 300,
    "it's", 'say "hi"', '`tick`', '$HOME', '-', '--force',
)
_WRAP_SCHEMES = ('res://', 'file://', 'user://', 'http://evil/', 'uid://')
_SEPS = ('/', '/', '/', '/', '//', '/./', '\\', '\u2044')


def _mangle(rng: random.Random, bases: tuple[str, ...]) -> str:
    roll = rng.random()
    if roll < 0.15:
        return rng.choice(bases)  # exactly valid — keeps the accept path live
    if roll < 0.60:  # splice hostility into a valid id
        segs = rng.choice(bases).split('/')
        for _ in range(rng.randrange(1, 3)):
            pick = rng.choice(_HOSTILE_SEGMENTS)
            if rng.random() < 0.5:
                segs[rng.randrange(len(segs))] = pick
            else:
                segs.insert(rng.randrange(len(segs) + 1), pick)
    else:  # built from whole cloth
        pool = tuple(s for b in bases for s in b.split('/')) + _HOSTILE_SEGMENTS
        segs = [rng.choice(pool) for _ in range(rng.randrange(1, 6))]
    out = ''
    for i, seg in enumerate(segs):
        out += (rng.choice(_SEPS) if i else '') + seg
    wrap = rng.random()
    if wrap < 0.08:
        out = '/' + out
    elif wrap < 0.16:
        out = rng.choice(_WRAP_SCHEMES) + out
    elif wrap < 0.20:
        out = ' ' + out + ' '
    elif wrap < 0.24:
        out += '\n' + rng.choice(('x', '---', 'status: pwned'))
    elif wrap < 0.27:
        out += 'x' * 400
    return out


def _classes_of(text: str) -> set[str]:
    """Which hostile input classes a generated string exercises."""
    segs = re.split(r'[/\\]', text)
    hit = set()
    if any(s in ('.', '..', '...') for s in segs):
        hit.add('dot-segment')
    if '' in segs[1:]:
        hit.add('empty-segment')
    if '\\' in text:
        hit.add('backslash')
    if set('*?[]!') & set(text):
        hit.add('glob')
    if text.startswith('/'):
        hit.add('absolute')
    if '://' in text:
        hit.add('scheme')
    if ' ' in text or '\t' in text:
        hit.add('whitespace')
    if '\n' in text or '\r' in text:
        hit.add('newline')
    if any(q in text for q in ('"', "'", '`')):
        hit.add('quote')
    if any(ord(c) > 127 for c in text):
        hit.add('confusable')
    if len(text) > 255:
        hit.add('overlong')
    if text.startswith('-'):
        hit.add('dash')
    return hit


# --- running the real CLI -----------------------------------------------------
def _run(argv: tuple[str, ...]) -> tuple[int | None, str, BaseException | None]:
    """cli.main in-process. An exception escaping it IS the real CLI's
    traceback — returned, never asserted here, so the property owns the claim."""
    from agentic_sdlc.core.project import load_config, repo_root
    repo_root.cache_clear()
    load_config.cache_clear()
    buf = io.StringIO()
    code, escaped = None, None
    try:
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            code = cli.main(list(argv))
    except SystemExit as bail:  # argparse's spelling of a usage error
        code = bail.code if isinstance(bail.code, int) else 2
    except Exception as err:  # noqa: BLE001 — the property judges it
        escaped = err
    finally:
        repo_root.cache_clear()
        load_config.cache_clear()
    return code, buf.getvalue(), escaped


# --- byte-snapshots of the whole scratch tree ---------------------------------
def _snap(root: Path) -> dict[str, bytes | None]:
    """Every file's bytes and every directory under `root`, .git excluded
    (nothing here runs git after setup). Keyed relative, dirs suffixed '/'."""
    out: dict[str, bytes | None] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != '.git']
        rel = Path(dirpath).relative_to(root)
        for d in dirnames:
            out[f'{rel / d}/'] = None
        for f in filenames:
            out[str(rel / f)] = (Path(dirpath) / f).read_bytes()
    return out


def _delta(before: dict, after: dict) -> list[str]:
    keys = set(before) | set(after)
    return sorted(k for k in keys if before.get(k, ...) != after.get(k, ...))


def _restore(root: Path, before: dict) -> None:
    current = _snap(root)
    for rel in current:
        if rel in before:
            continue
        target = root / rel
        if not rel.endswith('/'):
            target.unlink()
    for rel, data in before.items():
        target = root / rel
        if rel.endswith('/'):
            target.mkdir(parents=True, exist_ok=True)
        elif current.get(rel, ...) != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    # prune created-and-now-empty directories, deepest first
    for rel in sorted((k for k in current if k.endswith('/')),
                      key=len, reverse=True):
        if rel not in before:
            with contextlib.suppress(OSError):
                (root / rel).rmdir()
    assert _snap(root) == before, 'restore failed — the scratch tree drifted'


@contextlib.contextmanager
def _scratch(build) -> tuple[Path, Path]:
    """(outer, repo): repo is `outer/repo`, snapshots cover ALL of `outer`, so
    a `repo/../…` traversal write lands inside the evidence."""
    with tempfile.TemporaryDirectory() as tmp:
        outer = Path(tmp)
        root = outer / 'repo'
        build(outer, root)
        subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
        subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
        previous = Path.cwd()
        os.chdir(root)
        try:
            yield outer, root
        finally:
            os.chdir(previous)


# --- property (a): grain containment ------------------------------------------
_PM_BASES = ('0.1', '0.1/alpha', '0.1/beta', '0.1/alpha/s0', '0.1/alpha/s1',
             '0.1/beta/b0', '0.1/bugs/crash', '0.1/bugs/sub/nested')

# The fixed refusal matrix under the fuzz: canonical hostile shapes, including
# the v0.16.0 blocker id verbatim, run against every verb regardless of what
# the seeded stream generates.
_KILLERS = (
    '0.1/bugs/../features/alpha/feature',
    '0.1/bugs/sub/../../features/alpha/feature',
    '0.1/bugs/',
    '0.1/bugs/../../../outside',
    '0.1/../0.1/alpha/s0',
    '../repo/pm/roadmap/features/alpha',
    '/etc/hosts',
    '0.1/alpha/../../0.1/bugs/crash',
)

# `move` is GONE (0.4.0): re-parenting is `pm set <id> feature <fid>`, which
# `set` already drives. `rename` takes the slot — it writes across every
# document holding a ref, so it is the verb with the most to contain.
_PM_VERBS = ('story', 'bug', 'feature', 'milestone', 'set', 'get', 'rename',
             'decide')


def _grain_front(path: Path, front: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ['---'] + [f'{k}: {v}' for k, v in front.items()] + ['---', '', 'x', '']
    path.write_text('\n'.join(lines), encoding='utf-8')


def _build_pm(outer: Path, root: Path) -> None:
    (outer / 'outside.md').write_text('---\nstatus: decoy\n---\n', encoding='utf-8')
    m = root / 'pm' / 'roadmap' / '0.1-demo'
    # THE FLOW IS PART OF THE TREE, not decoration. `[pm.states.*]` has no
    # runtime fallback (`vocabulary.flow_of`), so every `pm` verb the fuzz
    # drives would exit 2 on the DECLARATION rather than on the hostile id it
    # was handed — and a refusal matrix that refuses for the wrong reason is a
    # green suite proving nothing (hard rule 4).
    root.mkdir(parents=True, exist_ok=True)
    (root / 'devkit.toml').write_text(FLOW_TOML, encoding='utf-8')
    _grain_front(m / 'milestone.md',
                 {'id': '"0.1"', 'name': 'Demo', 'status': 'building'})
    for slug in ('alpha', 'beta'):
        _grain_front(m / 'features' / slug / 'feature.md',
                     {'id': f'0.1/{slug}', 'milestone': '"0.1"', 'name': slug,
                      'status': 'building', 'reviewed': ''})
    for fid, sslug in (('alpha', 's0'), ('alpha', 's1'), ('beta', 'b0')):
        _grain_front(m / 'features' / fid / 'stories' / f'{sslug}.md',
                     {'id': f'0.1/{fid}/{sslug}', 'feature': f'0.1/{fid}',
                      'milestone': '"0.1"', 'name': sslug, 'status': 'ready'})
    _grain_front(m / 'bugs' / 'crash.md',
                 {'id': '0.1/bugs/crash', 'milestone': '"0.1"', 'status': 'open'})
    _grain_front(m / 'bugs' / 'sub' / 'nested.md',
                 {'id': '0.1/bugs/sub/nested', 'milestone': '"0.1"',
                  'status': 'open'})


def _pm_argv(rng: random.Random, verb: str,
             gid: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """(argv, the caller-supplied grain ids inside it)."""
    if verb == 'story':
        return ('pm', 'story', 'building', gid), (gid,)
    if verb == 'bug':
        return ('pm', 'bug', 'fixed', gid), (gid,)
    if verb == 'feature':
        return ('pm', 'feature', 'planning', gid), (gid,)
    if verb == 'milestone':
        return ('pm', 'milestone', 'ready', gid), (gid,)
    if verb == 'set':
        # `owner`, not `status`: `set` refuses the status key by name
        # before resolving the grain (a status is a move), and a verb that
        # never writes is a verb the containment property never exercises.
        return ('pm', 'set', gid, 'owner', 'wombat'), (gid,)
    if verb == 'get':
        return ('pm', 'get', gid, 'status'), (gid,)
    if verb == 'decide':
        return ('pm', 'decide', gid, 'fuzz', 'entry'), (gid,)
    # Both argument positions, because a rename reads one id and WRITES the
    # other into every document that held it.
    if rng.random() < 0.5:
        return ('pm', 'rename', gid, 'ft-fuzzed'), (gid, 'ft-fuzzed')
    return ('pm', 'rename', '0.1/alpha', gid), ('0.1/alpha', gid)


def _grain_shaped(path: Path) -> bool:
    return (path.name in ('feature.md', 'milestone.md')
            or 'stories' in path.parts or 'bugs' in path.parts)


_KIND_OK = {
    'story': lambda p: 'stories' in p.parts,
    'bug': lambda p: 'bugs' in p.parts,
    'feature': lambda p: p.name == 'feature.md',
    'milestone': lambda p: p.name == 'milestone.md',
    'set': _grain_shaped,
    'rename': _grain_shaped,
    'decide': lambda p: p.name == 'decisions.md',
}


def _literal_segments(gid: str) -> bool:
    return all(s not in ('', '.', '..')
               for s in gid.replace('\\', '/').split('/'))


def _judge_pm(verb: str, argv: tuple[str, ...], ids: tuple[str, ...],
              code, out: str, escaped, delta: list[str],
              outer: Path, roadmap: Path) -> str | None:
    where = f'{argv!r} -> code={code} delta={delta} out={out[:160]!r}'
    if escaped is not None:
        return f'TRACEBACK {type(escaped).__name__}: {escaped!r} on {where}'
    if code not in (0, 1, 2):
        return f'EXIT CODE outside the contract on {where}'
    if code != 0 and delta:
        return f'REFUSAL WROTE on {where}'
    if code == 0 and verb == 'get' and delta:
        return f'READ VERB WROTE on {where}'
    if code == 0:
        for rel in delta:
            resolved = (outer / rel.rstrip('/')).resolve()
            if not resolved.is_relative_to(roadmap):
                return f'ESCAPED pm/roadmap/: {rel} on {where}'
            if resolved.name == LEDGER_FILE_NAME:
                # Every WRITING verb appends a row (D6/D8), so the question
                # for the ledger is not which verb wrote it but WHERE: it is
                # legal in a milestone directory and nowhere else in the tree.
                if resolved.parent.parent != roadmap:
                    return f'LEDGER OUTSIDE A MILESTONE DIR: {rel} on {where}'
                continue
            if not _KIND_OK[verb](Path(rel)):
                return f'WRONG GRAIN KIND: {rel} on {where}'
        if delta:
            for gid in ids:
                if not _literal_segments(gid):
                    return f'NON-LITERAL ID ACCEPTED: {gid!r} on {where}'
    return None


@functools.lru_cache(maxsize=1)
def _pm_results() -> tuple[tuple[str, ...], dict]:
    rng = random.Random(SEED)
    violations: list[str] = []
    census: Counter = Counter()
    cases = [(verb, gid) for gid in _KILLERS for verb in _PM_VERBS]
    cases += [(rng.choice(_PM_VERBS), _mangle(rng, _PM_BASES))
              for _ in range(PM_CASES)]
    with _scratch(_build_pm) as (outer, root):
        roadmap = (root / 'pm' / 'roadmap').resolve()
        base = _snap(outer)
        for verb, gid in cases:
            argv, ids = _pm_argv(rng, verb, gid)
            code, out, escaped = _run(argv)
            delta = _delta(base, _snap(outer))
            verdict = _judge_pm(verb, argv, ids, code, out, escaped, delta,
                                outer, roadmap)
            if verdict:
                violations.append(verdict)
            census['refused'] += 1 if code in (1, 2) else 0
            census['accepted-write'] += 1 if code == 0 and delta else 0
            census['ok-no-write'] += 1 if code == 0 and not delta else 0
            for cls in _classes_of(gid):
                census[f'class:{cls}'] += 1
            if delta:
                _restore(outer, base)
    return tuple(violations), dict(census)


def test_grain_containment_under_mangled_ids():
    violations, _ = _pm_results()
    assert not violations, (
        f'{len(violations)} containment violations (seed {SEED}):\n\n'
        + '\n\n'.join(violations[:8]))


# --- the teeth ----------------------------------------------------------------
# Every hostile class the module docstring advertises. Named here rather than
# inline so the census and the prose cannot drift: a class dropped from the
# generator has to be dropped from this tuple, in the open.
HOSTILE_CLASSES = ('dot-segment', 'empty-segment', 'backslash', 'glob',
                   'absolute', 'scheme', 'whitespace', 'newline', 'quote',
                   'confusable', 'overlong', 'dash')


def test_the_corpus_actually_exercises_every_hostile_class_and_both_verdicts():
    """A fuzz whose corpus is all one answer proves nothing.

    Two censuses, asserted rather than trusted: the generator must still emit
    every hostile input class it advertises, and the run must contain both
    refusals AND accepted writes — a corpus the CLI always refuses would let
    the containment clauses rot unexercised.
    """
    _, pm = _pm_results()
    for cls in HOSTILE_CLASSES:
        assert pm.get(f'class:{cls}', 0) >= 8, (cls, pm)
    assert pm['refused'] >= 150, pm
    assert pm['accepted-write'] >= 5, pm


def test_the_census_names_every_class_the_mangler_can_emit():
    """The other direction, and the one a shrinking census needs: a class the
    generator produces but the roster above forgot would go unasserted for
    ever. `_classes_of` is the closed vocabulary, so the two must agree
    exactly."""
    import inspect
    emitted = {line.split("add('")[1].split("')")[0]
               for line in inspect.getsource(_classes_of).splitlines()
               if '.add(' in line}
    assert emitted == set(HOSTILE_CLASSES), (
        f'the classifier emits {sorted(emitted)} and the census asserts '
        f'{sorted(HOSTILE_CLASSES)} — one of them was narrowed alone')


def _pre_fix_bug_resolver(mdir: Path, gid: str) -> Path | None:
    """The v0.16.0 resolver, kept on purpose — transcribed from
    `git show 76e28fb~1:src/agentic_sdlc/repo/pm/cli.py` `_grain_file`:
    partition on '/bugs/', join the slug half, no segment guard. This is the
    code the release review rejected; the corpus must still reach it."""
    _, _, rest = gid.partition('/bugs/')
    bf = mdir / 'bugs' / f'{rest}.md'
    try:
        return bf if bf.is_file() else None
    except OSError:
        return None


def test_the_corpus_separates_the_pre_fix_resolver():
    """The harness proven to have teeth, not just to be green.

    Path-level: the generated stream (not just the fixed matrix) must keep
    producing bug ids whose slug half resolves OUTSIDE bugs/. Live-fire: at
    least one corpus id must make the pre-fix resolver hand back an EXISTING
    sibling grain file — the exact cross-grain write of the v0.16.0 blocker.
    """
    rng = random.Random(SEED)
    generated = [_mangle(rng, _PM_BASES) for _ in range(PM_CASES)]
    bug_ids = [g for g in generated if '/bugs/' in g]
    assert len(bug_ids) >= 20, len(bug_ids)
    escapes = 0
    for gid in bug_ids:
        rest = gid.partition('/bugs/')[2]
        resolved = os.path.normpath(os.path.join('bugs', rest + '.md'))
        if not resolved.startswith('bugs' + os.sep):
            escapes += 1
    assert escapes >= 5, (
        f'only {escapes} of {len(bug_ids)} generated bug ids escape the '
        f'bugs/ slot at the path level — the fuzz has lost its teeth')
    with _scratch(_build_pm) as (_, root):
        mdir = root / 'pm' / 'roadmap' / '0.1-demo'
        live = [gid for gid in list(_KILLERS) + bug_ids
                if (hit := _pre_fix_bug_resolver(mdir, gid)) is not None
                and not hit.resolve().is_relative_to((mdir / 'bugs').resolve())]
        assert live, ('no corpus id makes the pre-fix resolver return an '
                      'existing sibling grain — the blocker shape is gone')


def test_decide_refuses_dot_segment_traversal_without_writing():
    """Replaced the known-finding pin (0.17.0 decide-dot-segment-traversal).

    At the pinned HEAD, `pm decide '0.1/..'` wrote the MILESTONE's
    decisions.md through `features/..` and `pm decide '0.1/.'` minted
    `features/decisions.md` — a slot the schema does not have — both at
    exit 0. The resolver now refuses the segment before the join.
    """
    with _scratch(_build_pm) as (outer, root):
        mdir = root / 'pm' / 'roadmap' / '0.1-demo'
        base = _snap(outer)
        for gid in ('0.1/..', '0.1/.', '0.1/..\\..'):
            code, out, escaped = _run(('pm', 'decide', gid, 'pin', 'probe'))
            assert escaped is None, (gid, escaped)
            assert code == 2, (gid, code, out)
        # Deeper spellings refuse on their own (story/bug) precondition —
        # what matters is refusal WITHOUT a write, either exit code.
        code, out, escaped = _run(('pm', 'decide', '0.1//', 'pin', 'probe'))
        assert escaped is None and code in (1, 2), (code, out)
        assert not (mdir / 'decisions.md').is_file()
        assert not (mdir / 'features' / 'decisions.md').is_file()
        assert _delta(base, _snap(outer)) == []


def test_absolute_milestone_id_is_refused_not_a_glob_crash():
    """Replaced the known-finding pin (0.17.0 absolute-milestone-id-crash).

    At the pinned HEAD an absolute milestone id reached `Path.glob` as a
    non-relative pattern and escaped as NotImplementedError — a traceback
    where exit 2 belongs. The resolver now refuses before the glob.
    """
    with _scratch(_build_pm) as (outer, _):
        base = _snap(outer)
        for mid in ('/etc/hosts', '/', '\\\\host\\share', 'a/b', '..'):
            code, out, escaped = _run(('pm', 'milestone', 'ready', mid))
            assert escaped is None, (mid, escaped)
            assert code == 2, (mid, code, out)
        assert _delta(base, _snap(outer)) == []

