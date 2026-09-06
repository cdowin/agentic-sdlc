"""test_install_sdlc.py — the protocol document, and the drift it ends.

`install-sdlc` is the fifth `PLANS` entry and the only one whose body is
RENDERED. So it inherits every sentence `tests/test_install.py` already asserts
of the other four (it is parametrized over `VERBS` there), and what is left for
this module is the two claims that are new:

1. **the document is a function of CONFIG ALONE** — same config, same bytes;
   different `[release] steps`, different document;
2. **every configured step appears and nothing else does** — a step silently
   missing from the doc is the same class of defect as a gate silently leaving
   a roster.

Plus the seam the audit named: `body_of` is verbatim BY CONTRACT, and a
generated body must not have weakened it.
"""
from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from support import REPO_ROOT  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / 'src'))
from agentic_sdlc.core.project import load_config, repo_root  # noqa: E402
from agentic_sdlc.repo import install  # noqa: E402
from agentic_sdlc.repo.conveyor import driver, sdlc_doc, steps  # noqa: E402

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
    """The step names the rendered document actually carries, in order."""
    return re.findall(r'^\| \d+ \| `([a-z0-9-]+)` \|', text, re.M)


SHORT = '[release]\nsteps = ["tree-clean", "review-landed", "gate"]\n'


# --- the two new claims -------------------------------------------------------
def test_the_document_is_a_function_of_config_alone():
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
    return f'## `{operation}` — the ordered list'


def section(text: str, operation: str) -> str:
    """ONE operation's table. The document carries one per operation — four of
    them since the inner belts landed — so a claim about a list is scoped to
    its own section and never to "everything below this heading", which is how
    the adopt assertion came to read the story list too."""
    after = text.split(heading_of(operation))[1]
    for other in driver.OPERATIONS:
        after = after.split(heading_of(other))[0]
    return after


def release_section(text: str) -> str:
    return section(text, 'release')


def test_every_configured_step_appears_in_order_and_nothing_else_does():
    with repo({'devkit.toml': SHORT}) as root:
        assert run()[0] == 0
        assert listed(release_section(
            (root / DEST).read_text(encoding='utf-8'))) == [
            'tree-clean', 'review-landed', 'gate']
    with repo() as root:
        assert run()[0] == 0
        assert listed(release_section(
            (root / DEST).read_text(encoding='utf-8'))) == list(
            steps.DEFAULT_RELEASE_STEPS)


def test_each_rendered_step_carries_its_kind_and_its_postcondition():
    with repo() as root:
        run()
        text = (root / DEST).read_text(encoding='utf-8')
        for name, step in steps.RELEASE_STEPS.items():
            row = next(line for line in text.split('\n')
                       if line.startswith(f'| ') and f'| `{name}` |' in line)
            assert step.kind.name in row, row
            # The postcondition, taken from the registry rather than restated.
            assert steps.STEP_DOC[name].split('.')[0][:40] in row, row


def test_the_renderer_holds_no_per_step_text_of_its_own():
    """Criterion 4: the sentences live beside the `check()` that enforces
    them. A second table of prose here would be the second home, one
    indirection further along."""
    source = (REPO_ROOT
              / 'src/agentic_sdlc/repo/conveyor/sdlc_doc.py').read_text(
                  encoding='utf-8')
    body = source.split('"""', 2)[-1]
    for name in steps.DEFAULT_RELEASE_STEPS:
        assert f"'{name}'" not in body and f'"{name}"' not in body, name


def test_every_operation_renders_its_whole_list_beside_the_others():
    """`the-inner-levels-are-belts-too` ship criterion 5, which subsumes
    `adopt-is-a-conveyor`'s criterion 4: ALL FOUR lists in one document, from
    the same source, so the generated protocol is the whole SDLC and not just
    its outer half. The renderer is `sdlc_doc.py`'s; what is asserted here is
    that every step of every list arrives with its kind. One render, every
    operation — it is one document."""
    with repo() as root:
        run()
        text = (root / DEST).read_text(encoding='utf-8')
        for operation in driver.OPERATIONS:
            assert heading_of(operation) in text, (operation, text[:400])
            body = section(text, operation)
            assert 'not configured' not in body, (operation, body[:400])
            for name, step in steps.REGISTRIES[operation].items():
                row = next(line for line in body.split('\n')
                           if line.startswith('| ') and f'| `{name}` |' in line)
                assert step.kind.name in row, row
            assert listed(body) == list(steps.DEFAULT_STEPS[operation]), operation


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
    """The unguarded reads the audit named: a fifth verb with no `_NEXT_STEP`
    row is a KeyError on the SUCCESS path, and a verb missing from `USAGE` is
    a verb nobody can discover."""
    for verb in install.PLANS:
        assert verb in install._NEXT_STEP, f'{verb} has no next-step note'
        assert verb in install.USAGE, f'{verb} is not in USAGE'


def test_a_bad_release_section_is_exit_2_and_writes_nothing():
    with repo({'devkit.toml': '[release]\nsteps = "tree-clean"\n'}) as root:
        code, out = run()
        assert code == 2, out
        assert not (root / DEST).exists()


def test_a_step_name_cannot_smuggle_markdown_through_the_config():
    """The name grammar refuses it upstream; this proves the renderer cannot
    be made to emit a broken table through the config anyway."""
    for bad in ('gate|x', '# gate', '`gate`', '- gate'):
        with repo({'devkit.toml':
                   f'[release]\nsteps = ["{bad}"]\n'}) as root:
            code, out = run()
            assert code == 2, (bad, out)
            assert not (root / DEST).exists(), bad


# --- self-hosting -------------------------------------------------------------
def test_this_repos_own_protocol_document_is_byte_current():
    """The same bar `tests/test_install.py` holds the installed agent
    definitions to. A generated document that has gone stale is the drift this
    verb exists to end, arriving through the back door."""
    target = REPO_ROOT / DEST
    assert target.is_file(), (
        f'{DEST} is not in this repo — run `agentic-sdlc install-sdlc`')
    assert target.read_text(encoding='utf-8') == sdlc_doc.render(), (
        f'{DEST} differs from the renderer — re-run '
        f'`agentic-sdlc install-sdlc --force`')


def test_the_shrunk_release_skill_points_at_the_document_and_lists_no_steps():
    """`.claude/skills/release/SKILL.md` shrinks to *run this verb*. A second
    copy of the ordered list is exactly the drift measured in this repo, this
    milestone."""
    text = (REPO_ROOT / '.claude/skills/release/SKILL.md').read_text(
        encoding='utf-8')
    assert DEST in text, 'the skill does not point at the generated document'
    assert 'agentic-sdlc release' in text
    named = [n for n in steps.DEFAULT_RELEASE_STEPS if f'`{n}`' in text]
    # The three the operator must answer are named as JUDGEMENTS the machine
    # hands back; the ordered list is not restated.
    assert set(named) <= set(steps.NO_DEFAULT_COMMAND), named


def test_the_standard_flags_answer_for_the_new_verb():
    """`--diff` reads and leaves the file; `--force` then replaces it — one
    tree, in that order, because the second flag's precondition is the
    first flag's postcondition."""
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
