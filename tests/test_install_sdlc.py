"""test_install_sdlc.py — the protocol document, and the drift it ends.

`install-sdlc` is the one `PLANS` entry whose body is RENDERED. It inherits
every sentence `tests/test_install.py` asserts of the other verbs (it is
parametrized over `VERBS` there); what is left here is what is new:

1. **the document is a function of CONFIG ALONE** — same config, same bytes;
   a different `[release] steps`, a different document;
2. **every configured check appears and nothing else does** — a check silently
   missing from the doc is the same class of defect as a gate silently leaving
   a roster;
3. **story 04 criterion 5** — the rendered protocol carries every check, the
   state each belt writes, and each belt's after-list.

Plus the seam the audit named: `body_of` is verbatim BY CONTRACT.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo import install  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, sdlc_doc, steps  # noqa: E402
from agentic_sdlc.repo.pm import vocabulary  # noqa: E402


DEST = 'docs/sdlc-protocol.md'
VERB = 'install-sdlc'


@contextlib.contextmanager
def repo(files: dict[str, str] | None = None):
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / 'repo'
        root.mkdir()
        for rel, body in (files or {}).items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(body, encoding='utf-8')
        (root / '.git').mkdir(exist_ok=True)  # a MARKER, not a repo: `repo_root` walks for it
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


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = install.main(VERB, list(argv))
    return code, buf.getvalue()


def listed(text: str) -> list[str]:
    """The check names the rendered document actually carries, in order."""
    return re.findall(r'^\| \d+ \| `([a-z0-9-]+)` \|', text, re.M)


SHORT = '[release]\nsteps = ["tree-clean", "findings-resolved", "gate"]\n'


# --- the two claims -----------------------------------------------------------
def test_the_document_is_a_function_of_config_alone():
    """Bites: a render that reads the clock or the tree, so two repos with one
    config disagree — or one that ignores the config."""
    with repo() as root:
        assert run()[0] == 0
        stock = (root / DEST).read_text(encoding='utf-8')
    with repo() as root:
        assert run()[0] == 0
        again = (root / DEST).read_text(encoding='utf-8')
    with repo({'devkit.toml': SHORT}) as root:
        assert run()[0] == 0
        different = (root / DEST).read_text(encoding='utf-8')
    assert stock == again, 'two repos with the same config rendered differently'
    assert stock != different, 'the config did not reach the document'


def heading_of(operation: str) -> str:
    return f'## `{operation}` — the checks'


def section(text: str, operation: str) -> str:
    """ONE operation's part of the document, scoped to its own heading."""
    after = text.split(heading_of(operation))[1]
    for other in driver.OPERATIONS:
        after = after.split(heading_of(other))[0]
    return after


def test_every_configured_check_appears_in_order_and_nothing_else_does():
    """Bites: a protocol document shorter (or longer) than the list that
    runs — the drift this verb exists to end."""
    with repo({'devkit.toml': SHORT}) as root:
        assert run()[0] == 0
        assert listed(section(
            (root / DEST).read_text(encoding='utf-8'), 'release')) == [
            'tree-clean', 'findings-resolved', 'gate']
    with repo() as root:
        assert run()[0] == 0
        assert listed(section(
            (root / DEST).read_text(encoding='utf-8'), 'release')) == list(
            steps.DEFAULT_RELEASE_STEPS)


def test_the_renderer_holds_no_per_check_text_of_its_own():
    """Bites: a second home for a check's sentence, one indirection along."""
    source = (REPO_ROOT
              / 'src/agentic_sdlc/repo/conveyor/sdlc_doc.py').read_text(
                  encoding='utf-8')
    body = source.split('"""', 2)[-1]
    for names in steps.DEFAULT_STEPS.values():
        for name in names:
            assert f"'{name}'" not in body and f'"{name}"' not in body, name


# --- story 04, criterion 5 ----------------------------------------------------
def test_the_rendered_protocol_carries_every_check_the_write_and_the_after_list():
    """Bites: a belt whose checks, write or after-list the document does not
    say — the caller reading a protocol the machine does not run. The write
    is named by its KEY (`[pm.states.<kind>] done`), never by the word: the
    document is a function of the check lists alone, so `init` can render it
    before `pm init` has written the flow."""
    text = sdlc_doc.render()
    for operation in driver.OPERATIONS:
        assert heading_of(operation) in text, operation
        body = section(text, operation)
        assert 'not configured' not in body, (operation, body[:400])
        assert listed(body) == list(steps.DEFAULT_STEPS[operation]), operation
        for name in steps.DEFAULT_STEPS[operation]:
            assert steps.STEP_DOC[name].split('.')[0][:40] in body, name
        kind = driver.WRITES[operation]
        if kind:
            assert f'[pm.states.{kind}] done' in body, (operation, body[-900:])
            assert f'`pm {kind} <state> <id>`' in body, operation
        else:
            assert 'writes nothing' in body, body[-400:]
        commands = steps.commands_for(operation)
        for line in steps.after_lines(operation, commands, version='<version>',
                                      branch='<branch>', mainline='<mainline>'):
            assert f'- {line}' in body, (operation, line)


# Inputs no belt reads since 0.6.0: the file, its section, the bug fields.
RETIRED_INPUTS = (('CHANGELOG.md', 'Unreleased')
                  + tuple(sorted(vocabulary.RETIRED_FIELDS)))


def _reads() -> dict[str, tuple[str, ...]]:
    """{check: what its sentence must name}, for EVERY shipped check.

    Where the code publishes the input — the command a check runs when none is
    configured, the field the changelog reader grades — the token is asked of
    it. The rest is typed, and each names the input or the "never" the check's
    own docstring states: a sentence that drops it is a different check."""
    from agentic_sdlc.repo.pm import changelog as clog
    typed = {
        'telemetry-live': ('`.claude/settings.json`',
                           '`.claude/settings.local.json`'),
        'tree-clean': ('`git status --porcelain`', 'roadmap directory'),
        'on-milestone-branch': ('`branch:`',),
        'changelog-unreleased-nonempty': (f'`{clog.FIELD}:`',
                                          '`done` category'),
        # Review M4: a feature done with a blank `reviewed:` blocks, and so
        # does a bug at `fixed`; "no open bug" undersold both.
        'features-done': ('`reviewed:`', 'every bug', '`done` category'),
        'findings-resolved': ('`open`',),
        'version-sync': ('version site', 'never bumped'),
        'gate': ('gate command',),
        'pin-bumped': ('`DEVKIT_VERSION`',),
        'installables-current': ('`[<op>] ours`', '`install-* --diff`'),
        'config-updated': ('devkit.toml',),
        'hooks-self-test': (),
        'runner-targets-resolve': (),
        'checks-pass': (),
        'pm-validates': (),
        'story-exists': ('exactly one document',),
        'story-verified': ('`[verify] story`',),
        'committed': ('roadmap directory', 'never commits'),
        'evidence-written': ('`done:', 'never written'),
        'stories-done': ('`done` category',),
        'review-recorded': ('`reviewed:`', 'verdict block'),
        'findings-landed': ('`disposition: open`',),
        'feature-verified': (),
    }
    for name, action in steps.SHIPPED_ACTION.items():
        # `agentic-sdlc pm ready-for feature <id>` -> `pm ready-for feature`:
        # the words before the first placeholder or assignment.
        words = []
        for word in action.split():
            if word.startswith('<') or '=' in word:
                break
            words.append(word)
        if words[0] == 'agentic-sdlc':
            words = words[1:]
        typed[name] = (*typed.get(name, ()), ' '.join(words))
    return typed


def _misreads(name: str, sentence: str | None) -> list[str]:
    """What is wrong with `sentence` as `name`'s description, or `[]`."""
    reads = _reads()
    if sentence is None:
        return [f'{name} has no STEP_DOC sentence']
    if name not in reads:
        return [f'{name} has no entry in _reads() — name what it reads']
    if not reads[name]:
        return [f'{name} holds its sentence to nothing']
    return ([f'names retired input {retired!r}' for retired in RETIRED_INPUTS
             if retired in sentence]
            + [f'omits {token!r}' for token in reads[name]
               if token not in sentence])


# Sentences each check has shipped with, or nearly, that were FALSE: the grader
# above must refuse every one. The first is #33 itself; the next two are the
# review's probe, which the five-check table this replaced passed; the last is
# `features-done` before review M4.
PLANTED = (
    ('changelog-unreleased-nonempty',
     'the changelog\'s `## Unreleased` section holds at least one bullet.'),
    ('version-sync',
     'every configured version site is BUMPED to the release version and '
     'committed.'),
    ('stories-done', 'the feature file lists its stories and each is ticked.'),
    ('features-done',
     '`pm ready-for milestone <milestone>` exits 0 — every feature is in the '
     '`done` category and no open bug names the milestone.'),
)
SHIPPED_CHECKS = sorted(set(steps.STEP_DOC).union(
    *(registry for registry in steps.REGISTRIES.values())))


@pytest.mark.parametrize(
    'name, sentence, true',
    [(name, steps.STEP_DOC.get(name), True) for name in SHIPPED_CHECKS]
    + [(name, sentence, False) for name, sentence in PLANTED],
    ids=[*SHIPPED_CHECKS, *(f'planted-{name}' for name, _ in PLANTED)])
def test_every_registry_sentence_names_what_its_check_reads_and_nothing_retired(
        name, sentence, true):
    """Bites: a check re-pointed at a new input keeping its old sentence.
    `changelog-unreleased-nonempty` has graded each closed grain's
    `changelog:` field since 0.6.0, and `install-sdlc` went on rendering it as
    counting bullets under `## Unreleased` (#33). The step id stays — an id is
    contract — so only the sentence can tell a consumer what runs. Every
    shipped check is a row, so a new one with no entry in `_reads()` fails by
    name; the PLANTED rows prove the grader refuses what did ship false.

    Here, not in test_conveyor_steps.py: that module spawns, so a case in it
    runs only in the `shell` tier, and this one reads a dict."""
    wrong = _misreads(name, sentence)
    if true:
        assert not wrong, (name, wrong, sentence)
    else:
        assert wrong, f'{name}: the grader passed a sentence that is false'


def test_a_configured_command_is_shown_and_an_unconfigured_one_is_not():
    config = SHORT + '\n[release.commands]\ngate = "make check"\n'
    with repo({'devkit.toml': config}) as root:
        run()
        text = (root / DEST).read_text(encoding='utf-8')
        assert '`make check`' in text
        assert 'make milestone' not in text


# --- the seam -----------------------------------------------------------------
def test_body_of_is_still_verbatim_and_the_resolver_is_the_seam():
    """`body_of`'s docstring claims no substitution and no template, and four
    verbs depend on that being literally true."""
    template = install.body_of('sdlc-template.md')
    assert sdlc_doc.STEPS_MARKER in template, (
        'body_of substituted into the template — the contract is verbatim')
    with repo():
        rendered = install.resolve_body('sdlc-template.md', DEST)
    assert sdlc_doc.STEPS_MARKER not in rendered
    assert install.resolve_body('gdk_gate.sh', 'tools/dev/gdk_gate.sh') == \
        install.body_of('gdk_gate.sh')


def test_every_plans_key_has_a_next_step_and_a_usage_line():
    for verb in install.PLANS:
        assert verb in install._NEXT_STEP, f'{verb} has no next-step note'
        assert verb in install.USAGE, f'{verb} is not in USAGE'


def test_a_bad_release_section_is_exit_2_and_writes_nothing():
    with repo({'devkit.toml': '[release]\nsteps = "tree-clean"\n'}) as root:
        code, out = run()
        assert code == 2, out
        assert not (root / DEST).exists()


def test_a_check_name_cannot_smuggle_markdown_through_the_config():
    for bad in ('gate|x', '# gate', '`gate`', '- gate'):
        with repo({'devkit.toml':
                   f'[release]\nsteps = ["{bad}"]\n'}) as root:
            code, out = run()
            assert code == 2, (bad, out)
            assert not (root / DEST).exists(), bad


# --- self-hosting -------------------------------------------------------------
# The sentences the OLD machines were described with. D8 removed the halting
# ones, D12 removed the walking ones: a belt does not walk, stop, resume,
# perform or keep a scoreboard. Byte-current with the renderer proves nothing
# on its own — the renderer and the tree agreed once, and both were wrong.
HALTED = ('stops at the first', 'stopped on a step', 'refuse to advance',
          'refuses to advance', '--skip', 'resolved and deleted',
          'scoreboard', 'no step halts', 'walks every step', 'resumable',
          'do()')


def test_this_repos_own_protocol_document_is_byte_current_and_describes_d12():
    """The same bar `tests/test_install.py` holds the installed agent
    definitions to: a generated document that has gone stale, or one that is
    byte-current with a renderer describing a machine that no longer exists."""
    target = REPO_ROOT / DEST
    assert target.is_file(), (
        f'{DEST} is not in this repo — run `agentic-sdlc install-sdlc`')
    rendered = target.read_text(encoding='utf-8')
    assert rendered == sdlc_doc.render(), (
        f'{DEST} differs from the renderer — re-run '
        f'`agentic-sdlc install-sdlc --force`')
    surfaces = {
        DEST: rendered,
        'install-sdlc closing message': install._NEXT_STEP[VERB],
        'SDLC.md': (REPO_ROOT / 'SDLC.md').read_text(encoding='utf-8'),
        'cli --help': __import__('agentic_sdlc.cli', fromlist=['x']).__doc__,
    }
    for name, text in surfaces.items():
        for phrase in HALTED:
            assert phrase not in text, f'{name} still says {phrase!r}'
    assert 'one write' in rendered and '--force' in rendered


def test_the_release_skill_points_at_the_document_and_restates_no_check():
    """`.claude/skills/release/SKILL.md` is *run this verb, then do these*. A
    second copy of the check list is exactly the drift measured here."""
    text = (REPO_ROOT / '.claude/skills/release/SKILL.md').read_text(
        encoding='utf-8')
    assert DEST in text, 'the skill does not point at the generated document'
    assert 'agentic-sdlc release' in text
    for phrase in HALTED:
        assert phrase not in text, f'the release skill still says {phrase!r}'
    restated = [n for n in steps.DEFAULT_RELEASE_STEPS
                if f'`{n}`' in text and n != 'version-sync']
    assert restated == [], restated


def test_the_standard_flags_answer_for_the_new_verb():
    """`--diff` reads and leaves the file; `--force` then replaces it."""
    with repo() as root:
        (root / 'docs').mkdir()
        (root / DEST).write_text('mine\n', encoding='utf-8')
        code, out = run('--diff')
        assert code == 0, out
        assert (root / DEST).read_text(encoding='utf-8') == 'mine\n'
        assert f'--- a/{DEST}' in out
        code, out = run('--force')
        assert code == 0, out
        assert (root / DEST).read_text(encoding='utf-8') != 'mine\n'


# --- the emitted schema is rendered, not written (0.5.0) ---------------------
def test_the_protocol_renders_the_event_schema_from_the_minters_own_keys():
    """A hand-written event table beside a rendered check table is the second
    scoreboard this package deletes everywhere else — so the payload cells come
    off `ledger.EVENT_KEYS`, which `tests/test_pm_ledger.py` binds to the three
    functions that mint the rows. Bites: a tap added, a key added, or a key
    renamed, with the document still describing last release's stream."""
    from agentic_sdlc.repo import emit
    from agentic_sdlc.repo.pm import ledger

    text = sdlc_doc.render()
    body = text.split('## The events a belt emits')[1].split('\n## ')[0]
    assert sdlc_doc.EVENTS_MARKER not in text, 'the marker was not replaced'
    for kind, keys in ledger.EVENT_KEYS.items():
        row = [ln for ln in body.splitlines() if f'| `{kind}` |' in ln]
        assert len(row) == 1, body
        assert row[0].startswith(f'| `{kind.rsplit(".", 1)[-1]}` |'), row[0]
        for key in keys:
            assert f'`{key}`' in row[0], (kind, key)
    for word in driver.VERDICT_WORDS.values():
        assert f'`{word}`' in body, word
    assert f'`{steps.READS_THE_TREE}`' in body
    # The absence IS the signal, and the document says so rather than leaving
    # a reader to wonder which event tells them a belt stopped.
    assert 'no fourth kind' in body and 'rung.leave' in body
    assert len(emit.TAPS) == len(ledger.EVENT_KEYS)
