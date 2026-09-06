"""`check grain-shape`: the two ways a cap gate lies, a cap that never fires and a
census that reports on nothing, plus the two no-ops a stock-roster gate must say
out loud (no PM tree; a tree with no grain yet)."""
from __future__ import annotations

import contextlib
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT, run_check                        # noqa: E402
from support import pm as pmfx                                  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc import cli as devkit_cli                      # noqa: E402
from agentic_sdlc.repo.checks import grain_shape                # noqa: E402
from agentic_sdlc.repo.pm import model as pm_model              # noqa: E402

STORY = 'pm/roadmap/0.1-demo/features/alpha/stories/s0.md'
FEATURE = 'pm/roadmap/0.1-demo/features/alpha/feature.md'
MODULE = REPO_ROOT / 'src/agentic_sdlc/repo/checks/grain_shape.py'


def gate() -> tuple[int, str]:
    return run_check(grain_shape)


def cli(root: Path, *argv: str) -> tuple[int, str]:
    """The gate through the TOP-LEVEL CLI, which is where exit 2 is decided.

    `run_check` calls `run()` directly and a `ConfigError` would escape it as an
    exception — the exit code contract (0 pass, 1 findings, 2 config) is
    `_run_check`'s, so a config case asked of anything else is not asking about
    the code CI reads. (`support.pm.run_cli` routes the PM tracker's CLI, whose
    unknown-command path also exits 2 — a false green waiting to happen.)
    """
    from agentic_sdlc.core.project import load_config, repo_root
    repo_root.cache_clear()
    load_config.cache_clear()
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            code = devkit_cli.main(['check', 'grain-shape', *argv])
        except SystemExit as exc:  # pragma: no cover - defensive
            code = int(exc.code or 0)
    repo_root.cache_clear()
    load_config.cache_clear()
    return code, buf.getvalue()


def body(n: int) -> str:
    return '\n'.join(f'line {i}' for i in range(n))


def config(root: Path, text: str) -> None:
    """`text` as the tree's devkit.toml, with the flow declaration APPENDED.

    Through `pmfx.write_config` rather than a bare `write_text`: `check
    grain-shape` walks the tree through `pm.model`, so a case overriding
    `[grain_shape]` must not also un-declare `[pm.states.*]` — see
    tests/support/pm.py `with_flow`.
    """
    pmfx.write_config(root, text)


# --- the deliberately-broken probe -------------------------------------------
def test_a_document_over_its_cap_is_a_finding_naming_kind_length_and_cap():
    """THE probe. Without it the gate is a census with an opinion it never
    acts on, which is a permanently-green gate wearing a cap's name.

    And the other half in the same tree: the gate must be SATISFIABLE from
    config, or the ceiling is not an adoption mechanism, it is a wall. A tree
    that cannot meet a default says so in its OWN devkit.toml, in a value a
    reviewer can see and ratchet down.
    """
    with pmfx.tree() as root:
        (root / STORY).write_text(
            (root / STORY).read_text(encoding='utf-8') + body(40),
            encoding='utf-8')
        config(root, '[grain_shape]\ncaps = { story = 5 }\n')
        code, out = gate()
        assert code == 1, out
        assert 'OVER CAP' in out, out
        assert STORY in out, out
        assert 'story cap 5' in out, out
        assert 'body line(s)' in out, out
        assert '[check:grain-shape] FAIL — 1 finding(s)' in out, out

        config(root, '[grain_shape]\ncaps = { story = 500 }\n')
        code, out = gate()
    assert code == 0, out
    assert '[check:grain-shape] PASS' in out, out


def test_a_cap_named_for_one_kind_does_not_uncap_the_others():
    """`number_table` returns only the keys the author DECLARED, so a table
    naming `story` would hand back a dict with no `feature` in it. Merged over
    the defaults, or a repo that tuned one number silently stopped measuring
    five — the shape rule 5 is about, one level down."""
    with pmfx.tree() as root:
        (root / FEATURE).write_text(
            (root / FEATURE).read_text(encoding='utf-8') + body(400),
            encoding='utf-8')
        config(root, '[grain_shape]\ncaps = { story = 5000 }\n')
        code, out = gate()
    assert code == 1, out
    assert FEATURE in out, out
    assert f'feature cap {grain_shape.DEFAULT_CAPS["feature"]}' in out, out


# --- the two ways a census lies ----------------------------------------------
def test_the_slot_names_have_one_source():
    """0.2.0/bugs/the-slot-names-are-spelled-in-six-places. `_kind_of` reads
    a grain's kind from `model.STORIES_DIR` / `model.BUGS_DIR`; a second
    spelling anywhere in the pm tracker or the gates is a kind read from a
    literal in one module and a constant in another. This walks every string
    constant in those modules (the census `tests/test_pm_flow.py` runs for
    state words, pointed at slot words) and names the survivor by file and
    line. No existing case could fail for this: every one reads a tree the
    literals and the constants still agree about."""
    import ast
    from agentic_sdlc.repo.pm import model
    src = Path(grain_shape.__file__).resolve().parents[1]
    slots = (model.STORIES_DIR, model.BUGS_DIR)

    def spells_a_slot(value: str) -> bool:
        # A path piece: the word itself, or a segment ending in `/<slot>/` or
        # opening with `<slot>/` — the shapes `mdir / 'bugs'`,
        # `f'{mid}/bugs/{slug}'` and `'/bugs/' in gid` take. Prose that
        # mentions the directory in passing is not a spelling of the fact.
        return any(value == slot or value.endswith(f'/{slot}/')
                   or value.startswith(f'{slot}/') for slot in slots)

    survivors = []
    for family in ('pm', 'checks'):
        for path in sorted((src / family).glob('*.py')):
            if path.name == 'model.py':
                continue
            tree = ast.parse(path.read_text('utf-8'))
            # A payload KEY (`{'stories': rows}`, `section['bugs']`) is the
            # report's contract with its reader, not a directory name that
            # happens to match; the census is about paths.
            keys = {id(k) for d in ast.walk(tree) if isinstance(d, ast.Dict)
                    for k in d.keys}
            keys |= {id(n.slice) for n in ast.walk(tree)
                     if isinstance(n, ast.Subscript)}
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Constant)
                        and isinstance(node.value, str)) or id(node) in keys:
                    continue
                if spells_a_slot(node.value):
                    survivors.append(f'{path.name}:{node.lineno} {node.value!r}')
    # Docstrings and comments are prose about the tree; a docstring's first
    # statement is a constant too, so the census names only what is not one.
    prose = set()
    for family in ('pm', 'checks'):
        for path in sorted((src / family).glob('*.py')):
            tree = ast.parse(path.read_text('utf-8'))
            for node in ast.walk(tree):
                body = getattr(node, 'body', None)
                if (isinstance(body, list) and body
                        and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    prose.add(f'{path.name}:{body[0].value.lineno}')
    survivors = [s for s in survivors if s.split(' ', 1)[0] not in prose]
    assert survivors == [], '\n'.join(survivors)
    assert grain_shape._kind_of(Path('0.1/features/f/stories/s.md')) == grain_shape.STORY
    assert grain_shape._kind_of(Path('0.1/bugs/topic/b.md')) == grain_shape.BUG


def test_a_repo_with_no_pm_tree_is_a_no_op_that_says_so():
    """Feature risk 2. This gate is in the STOCK `check all` roster, so a FAIL
    here would red every consumer without a PM tree at once — and a silent PASS
    would be the same lie the zero-census case below refuses."""
    with pmfx.tree() as root:
        for path in sorted((root / 'pm/roadmap').rglob('*'), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        (root / 'pm/roadmap').rmdir()
        (root / 'pm').rmdir()
        code, out = gate()
    assert code == 0, out
    assert '[check:grain-shape] PASS' in out, out
    assert 'no pm/roadmap/ in this repo' in out, out


def test_a_pm_tree_with_no_grain_WRITTEN_YET_is_a_no_op_that_says_so():
    """A fresh `pm init` is not a scope that lost its files.

    This test asserted the opposite until 2026-09-05, when the gate joined the
    stock roster and was pointed at a stock `agentic-sdlc init`: that project
    writes `pm/roadmap/ROADMAP.md` and no grain, and this gate FAILED it on its
    first `make check` — the newest possible consumer, reddened on day one,
    which is exactly the risk the feature registered against putting a gate in
    the default set.

    The rule that replaced it is a division of labour, not a softening.
    **`check pm` is the gate with an opinion about a PM tree being there.**
    This one measures documents against caps, and a tree holding no document
    has no answer to give. Two gates over one directory must not both answer
    the same question, or one fact yields two findings.
    """
    with pmfx.tree() as root:
        roadmap = root / 'pm/roadmap'
        for path in sorted(roadmap.rglob('*'), reverse=True):
            path.unlink() if path.is_file() else path.rmdir()
        roadmap.mkdir(parents=True, exist_ok=True)
        code, out = gate()
        assert code == 0, out
        assert 'holds no grain document yet' in out, out
        assert '`check pm`' in out, out

        # And the MEASURED case, in the same tree: what a stock
        # `agentic-sdlc init` actually leaves behind is a `ROADMAP.md` and no
        # grain. That is the tree this gate FAILED on 2026-09-05.
        (roadmap / 'ROADMAP.md').write_text('# Roadmap\n', encoding='utf-8')
        code, out = gate()
    assert code == 0, out


def test_this_gate_HAS_NO_SCOPE_OF_ITS_OWN_TO_LOSE():
    """Why there is no zero-census FAIL here, asserted rather than argued.

    Rule 4 fails a census that LOST files — a scope narrowed by a config value
    nobody re-read. This gate has none: it measures every markdown document
    under `[pm] roadmap_dir`, the directory the tracker itself uses, and its one
    skip reason is `NO_FRONTMATTER`, a classification rather than a loss.

    **Give this gate a scope key and this test fails**, which is the signal that
    the zero-census branch has to come back with it. That is the whole job of
    this test: it is a tripwire on a future edit, not a check on today's.
    """
    source = MODULE.read_text(encoding='utf-8')
    for scope_key in ('exclude_prefixes', 'include_prefixes', 'scope',
                      'roots', 'exclude'):
        assert f"'{scope_key}'" not in source, (
            f'grain_shape now reads a {scope_key!r} scope key, so its census '
            f'CAN lose files — restore the zero-census FAIL for '
            f'SkipReason.EXCLUDED_PATH before this ships')
    assert 'NO_FRONTMATTER' in source or 'no frontmatter' in source


def test_the_census_names_the_cap_every_kind_was_measured_against():
    """Acceptance criterion 1: files scanned, and the ceiling each kind met.
    A verdict that reported only a number would leave a reader unable to tell a
    green tree from one whose caps had been quietly raised."""
    with pmfx.tree() as root:
        code, out = gate()
    assert code == 0, out
    assert 'PM document(s) under pm/roadmap/' in out, out
    for kind, cap in grain_shape.DEFAULT_CAPS.items():
        assert f'{kind} ' in out and f'/{cap}' in out, (kind, out)


# --- the config path: exit 2, never 1 ----------------------------------------
def test_a_bad_value_in_this_gates_section_is_exit_2():
    """Exit 1 is reserved for findings, so CI must never read a devkit.toml
    typo as "prose drift found". Each spelling below is one an author really
    writes, and every one of them would otherwise mean the reverse of itself.
    """
    cases = {
        'caps = "300"': 'a whole table given as a string',
        'caps = { story = "300" }': 'the number quoted',
        'caps = { story = true }': 'a bool — `true` is an int in Python',
        'caps = { story = 0 }': 'a cap no document can be under',
        'caps = { story = -1 }': 'a negative ceiling',
        'caps = { storys = 300 }': 'a kind this package does not ship',
        'caps = {}': 'an empty table, which reads as "no caps"',
    }
    for line, why in cases.items():
        with pmfx.tree() as root:
            config(root, f'[grain_shape]\n{line}\n')
            code, out = cli(root)
        assert code == 2, f'{why}: {line} exited {code}\n{out}'
        assert 'grain_shape' in out, (line, out)


def _outside_roadmap(root: Path) -> Path:
    """A PM tree OUTSIDE the checkout, holding two documents over their caps.

    Over their caps deliberately: a gate that refuses the config never opens
    them, and a gate that does not refuse has findings to print. That is what
    makes the assertion below about READING rather than about a message.
    """
    outside = root.parent / 'outside'
    (outside / '0.1.0' / 'stories').mkdir(parents=True, exist_ok=True)
    pmfx.write(outside / '0.1.0' / 'milestone.md',
               {'id': '"0.1.0"', 'status': 'done'}, body(900))
    pmfx.write(outside / '0.1.0' / 'stories' / 's1.md',
               {'id': '0.1.0/s1', 'status': 'done'}, body(900))
    return outside


def test_a_roadmap_dir_outside_the_checkout_is_refused_at_exit_2():
    """Hard rule 8 and hard rule 6, in the one key that broke both.

    Measured on the unfixed gate, 2026-09-05, against exactly this tree:

      * `roadmap_dir = "<abs>"` reached `path.relative_to(root)` and raised an
        uncaught `ValueError` — a TRACEBACK at exit **1**, which a consumer's
        CI reads as drift found and a human reads as a crash. Neither of those
        is "your devkit.toml is wrong";
      * `roadmap_dir = "../outside"` did not crash. It PASSED THROUGH and
        printed `OVER CAP ../outside/0.1.0/milestone.md — 900 body line(s)`,
        a stock-roster gate reporting findings about a tree that is not this
        checkout.

    So both halves are asserted, and the second assertion is the load-bearing
    one: exit 2 with the outside tree still described would be the same
    violation wearing the right exit code.
    """
    for spelling in ('absolute', 'dot-dot'):
        with pmfx.tree() as root:
            outside = _outside_roadmap(root)
            value = str(outside) if spelling == 'absolute' else '../outside'
            config(root, f'[pm]\nroadmap_dir = "{value}"\n')
            code, out = cli(root)
        assert code == 2, f'{spelling}: exited {code}, not 2\n{out}'
        # Rule 6's other half: a config refusal is a MESSAGE, not a traceback.
        assert 'Traceback' not in out, (spelling, out)
        # It names the key and the value, so the fix is the next thing read.
        assert 'roadmap_dir' in out and value in out, (spelling, out)
        # And nothing out there was measured. `900` is the body length of both
        # documents outside the checkout; it can only appear if one was opened.
        assert 'OVER CAP' not in out and '900' not in out, (spelling, out)


def test_every_path_shaped_spelling_that_leaves_the_checkout_is_refused():
    """The shapes, not just the two that were reported.

    A guard that refused `../x` and took `a/../../x`, or refused `/x` and took
    `~/x`, would be a rule 8 claim with holes in it — and the holes are exactly
    where the next value lands.
    """
    for value in ('/tmp/elsewhere', '/', '~/roadmap', '~', '../outside',
                  'pm/../../outside', 'a/b/../../../c', 'C:/roadmap',
                  '..\\outside', 'file:///tmp/roadmap',
                  'https://example.invalid/roadmap'):
        with pmfx.tree() as root:
            # A TOML LITERAL string: `..\outside` in a basic string is a TOML
            # parse error, and a case that never reached the guard would be a
            # green assertion about nothing.
            config(root, f"[pm]\nroadmap_dir = '{value}'\n")
            code, out = cli(root)
        assert code == 2, f'{value!r} exited {code}, not 2\n{out}'
        assert 'roadmap_dir' in out, (value, out)


def test_a_path_key_that_stays_inside_the_checkout_is_untouched():
    """The other half of a refusal: what it must NOT refuse.

    A `.` segment, a trailing slash and a nested directory all stay inside, and
    every one is a spelling a consumer's devkit.toml may already carry. Rule 5
    says a repo declaring the default behaves identically to one declaring
    nothing — a guard that reddened `pm/roadmap/` would break that on the
    upgrade rather than at the value that is wrong.
    """
    for value in ('pm/roadmap', 'pm/roadmap/', './pm/roadmap', 'pm/./roadmap'):
        with pmfx.tree() as root:
            config(root, f'[pm]\nroadmap_dir = "{value}"\n')
            code, out = cli(root)
        assert code == 0, f'{value!r} exited {code}, not 0\n{out}'


def test_a_repo_with_no_config_behaves_identically_to_one_declaring_defaults():
    """Rule 5, asserted on the BYTES. A default that drifts from its documented
    spelling is a config file that lies about what it changed."""
    declared = '[grain_shape]\ncaps = { ' + ', '.join(
        f'{kind} = {cap}' for kind, cap in
        sorted(grain_shape.DEFAULT_CAPS.items())) + ' }\n'
    with pmfx.tree() as root:
        stock_code, stock_out = gate()
        config(root, declared)
        declared_code, declared_out = gate()
    assert (stock_code, stock_out) == (declared_code, declared_out), (
        f'stock:\n{stock_out}\ndeclared:\n{declared_out}')


# --- what is measured, and what is not ---------------------------------------
def test_frontmatter_is_not_prose_and_is_not_counted():
    """A cap that counted the schema block would make a grain's ceiling depend
    on how many fields its template mints — and `check pm` already owns every
    question about that block."""
    with pmfx.tree() as root:
        fields = {f'k{i}': str(i) for i in range(60)}
        fields['id'] = '0.1/alpha/s0'
        pmfx.write(root / STORY, fields, body(3))
        config(root, '[grain_shape]\ncaps = { story = 10 }\n')
        code, out = gate()
    assert code == 0, out


def test_a_grain_whose_frontmatter_is_damaged_is_measured_WHOLE():
    """No closing fence means no body boundary. Measuring 0 there would print
    PASS over the one document `check pm` is already calling damaged — a gate
    agreeing with nothing while looking green."""
    with pmfx.tree() as root:
        pmfx.write(root / STORY, {'id': '0.1/alpha/s0'}, body(40))
        pmfx.damage(root / STORY, 'no-closing-fence')
        config(root, '[grain_shape]\ncaps = { story = 10 }\n')
        code, out = gate()
    assert code == 1, out
    assert 'OVER CAP' in out and STORY in out, out


def test_a_note_parked_beside_a_grain_is_disclosed_not_measured():
    """A `.md` with no frontmatter is not a grain. Out of scope — and COUNTED
    in the disclosure, because "40 documents" and "40 documents and a README
    nobody looked at" are different facts about a tree."""
    with pmfx.tree() as root:
        (root / 'pm/roadmap/0.1-demo/README.md').write_text(
            '# how bugs are filed\n' + body(400), encoding='utf-8')
        code, out = gate()
    assert code == 0, out
    assert 'note(s) skipped (no frontmatter — not a grain)' in out, out


def test_decisions_md_is_measured_though_it_carries_no_frontmatter():
    """The shared doc this kit MINTS, and the one document here that grows for
    a whole milestone by design. Its template opens no frontmatter block, so a
    cap on it under a grain-only scope could never fire — a knob that cannot
    fire is worse than one that errors, because its author believes it took
    effect."""
    with pmfx.tree() as root:
        (root / 'pm/roadmap/0.1-demo/decisions.md').write_text(
            'Append with `agentic-sdlc pm decide <grain-id>`\n' + body(400),
            encoding='utf-8')
        config(root, '[grain_shape]\ncaps = { decisions = 10 }\n')
        code, out = gate()
    assert code == 1, out
    assert 'decisions.md' in out and 'decisions cap 10' in out, out


def test_a_review_record_over_its_cap_reddens_and_the_census_counts_it():
    """A review record is not a grain, so it is its own walk over `[pm] review_dir`;
    the probe is what keeps the `review` cap from being a knob that never fires."""
    with pmfx.tree() as root:
        record = root / 'docs/reviews/alpha.md'
        record.write_text(record.read_text(encoding='utf-8') + body(400),
                          encoding='utf-8')
        code, out = gate()
        assert code == 1, out
        assert 'OVER CAP' in out and 'docs/reviews/alpha.md' in out, out
        assert f'review cap {grain_shape.DEFAULT_CAPS["review"]}' in out, out
        assert '1 review record(s) under docs/reviews/' in out, out

        config(root, '[grain_shape]\ncaps = { review = 500 }\n')
        code, out = gate()
    assert code == 0, out
    assert '1 review record(s) under docs/reviews/' in out, out
    assert 'review 1/500' in out, out


def test_the_archive_and_dot_prefixed_paths_are_excluded_and_disclosed():
    """Both are deliberate hides, and both leave the count with a line saying
    so — a subtraction nobody can see is how a census comes out smaller than
    the tree with nothing going red."""
    with pmfx.tree() as root:
        archived = root / 'pm/roadmap/zz_archive/0.0-old/milestone.md'
        pmfx.write(archived, {'id': '"0.0"'}, body(400))
        hidden = root / 'pm/roadmap/.hold/milestone.md'
        pmfx.write(hidden, {'id': '"0.0"'}, body(400))
        code, out = gate()
    assert code == 0, out
    assert 'hidden (dot-prefixed' in out, out
    assert 'path(s) excluded from scope' in out, out


# --- the contract surfaces ----------------------------------------------------
def test_it_reads_each_document_once_and_spawns_nothing():
    """Acceptance criterion 1, structurally. The script this replaces spawned
    four subprocesses per file across 683 markdown files and cost 34.8 s — half
    of one consumer's entire gate set. A `subprocess` import here is that cost
    coming back, and it would not show up as a failing assertion anywhere."""
    source = MODULE.read_text(encoding='utf-8')
    assert 'import subprocess' not in source, 'the one-pass gate grew a spawn'
    assert 'subprocess.' not in source, 'the one-pass gate grew a spawn'
    assert source.count('read_raw') == 1, (
        'a second read of the same document — the cache exists so the '
        'frontmatter question and the length question share one open')


HANDOFF = 'pm/roadmap/0.1-demo/handoff.md'


def test_a_shared_doc_that_lost_its_instruction_line_is_a_finding():
    """`SLOT_HEADER`'s comment calls that line "the one channel that reaches a
    dispatched subagent". A doc that lost it is SILENTLY unguided — the writer
    (`templates._header_wanted`) has always known how to spot that, and it only
    ran on `pm new`, so a hand-authored or hand-trimmed doc was never asked.

    This is the probe for that. It is also the case that would have caught the
    0.4.0 handoff, which was authored by hand and opened with its own `#` title.
    """
    with pmfx.tree() as root:
        (root / HANDOFF).write_text('# 0.1 demo — handoff\n\nnotes\n',
                                    encoding='utf-8')
        code, out = gate()
        assert code == 1, out
        assert 'NO HEADER' in out, out
        assert HANDOFF in out, out
        # The finding names the repair AND the literal line, so it is fixable
        # without opening the source.
        assert 'pm new milestone' in out, out
        assert 'Cold-start only' in out, out


def test_a_doc_opening_with_a_RETIRED_header_still_passes():
    """The gate must not out-strict the writer, and rewording an entry in
    `SLOT_HEADER` must not red every doc written under the old words.

    Both halves are one fact: `_header_wanted` treats any KNOWN header as
    present so `_fill_header` cannot stack a second line onto an existing doc.
    If this case fails, a consumer's tree goes red on upgrade day AND `pm new`
    starts growing two headers on the same file.
    """
    retired = sorted(pm_model.RETIRED_SLOT_HEADERS)
    assert retired, 'a retired wording must stay recognised once one exists'
    for header in retired:
        with pmfx.tree() as root:
            (root / HANDOFF).write_text(f'{header}\n\n# 0.1 demo\n',
                                        encoding='utf-8')
            code, out = gate()
        assert code == 0, out
        assert 'NO HEADER' not in out, out


def test_the_writer_and_the_gate_read_ONE_known_header_set():
    """A local copy in either module is a second name for the same fact, and
    the two would drift the first time a header is reworded — the gate reddening
    docs the scaffolder calls correct.
    """
    writer = (REPO_ROOT / 'src/agentic_sdlc/repo/pm/templates/__init__.py'
              ).read_text(encoding='utf-8')
    assert 'model.KNOWN_SLOT_HEADERS' in writer, writer
    text = MODULE.read_text(encoding='utf-8')
    assert 'model.KNOWN_SLOT_HEADERS' in text, text
    assert 'frozenset(model.SLOT_HEADER' not in text, (
        'the gate rebuilt the set locally instead of reading the one source')
