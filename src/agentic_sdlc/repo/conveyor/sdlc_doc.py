"""sdlc_doc.py — the protocol document, RENDERED from the list that runs.

`agentic-sdlc install-sdlc` writes `docs/sdlc-protocol.md`. Every ordered line
in it comes from `[<operation>] steps` and from the step registry those names
resolve against — never from a table of prose kept here. Change the config,
re-run the verb, and the document changes with it.

That is not a documentation chore. It is `the-release-is-a-conveyor` risk 2:
*a hand-written doc DESCRIBING the steps recreates the drift immediately*. The
drift is measured, not hypothetical — `SDLC.md` § *Close protocol* and
`.claude/skills/release/SKILL.md` disagreed with each other and with the code,
in this repo, in the milestone that built this module.

## Two rules this module is written to

1. **It holds no per-step text.** The postcondition sentences live in
   `steps.STEP_DOC`, beside the `check()` that enforces them, and the
   not-a-step guidance lives in `steps.GUIDANCE`. A second copy here would be
   the second home again, one indirection further along.
2. **It writes a WHOLE file it owns.** It never splices a section into
   `SDLC.md`: that would be a write verb editing lines it was not asked to
   edit, inside a file an author owns (rule 3). `SDLC.md` LINKS here instead,
   and keeps the doctrine that is not a step list.

The output is a function of CONFIG ALONE. Nothing here reads the clock, the
environment or the working tree, so two repos with the same config render
byte-identical documents and a second run of the verb is `already current`.
"""
from __future__ import annotations

from importlib import resources

from agentic_sdlc.repo.conveyor import driver, steps

PACKAGE = 'agentic_sdlc.repo.installables'
TEMPLATE = 'sdlc-template.md'

STEPS_MARKER = '<!-- STEPS -->'
GUIDANCE_MARKER = '<!-- GUIDANCE -->'

# The operations a rendered document covers, in the order it covers them.
OPERATIONS = driver.OPERATIONS


def _cell(text: str) -> str:
    """One markdown table cell. A `|` inside a cell would open a column that is
    not there — and a step NAME can never carry one (the name grammar is
    `[a-z][a-z0-9-]*`), so this only ever guards the prose halves."""
    return text.replace('|', '\\|').replace('\n', ' ')


def _table(operation: str) -> list[str]:
    """The ordered list for one operation, as rows, or why there is none.

    An operation with no configured list gets a SENTENCE saying so — never an
    empty section, which reads as a protocol that is complete and has no steps.
    """
    known = driver.registry_for(operation)
    # A `ConfigError` PROPAGATES. It is exit 2 from the verb, before a byte is
    # rendered — never a document with a note where a list should be, which
    # would install a protocol whose broken half looks like a rendered one.
    names = steps.steps_for(operation, known)
    if not names:
        return [f'> `[{operation}] steps` is not configured in this repo, and '
                f'this package ships no default list for `{operation}`. '
                f'Nothing walks it.']
    commands = steps.commands_for(operation, names, known)
    out = ['| # | step | kind | command | what makes it true |',
           '|---|---|---|---|---|']
    for index, name in enumerate(names, start=1):
        step = known[name]
        command = commands.get(name, '')
        shown = f'`{_cell(command)}`' if command else (
            '— *(operator)*' if step.kind is not driver.StepKind.AUTOMATIC
            else '—')
        doc = steps.STEP_DOC.get(
            name, '*(this step ships no postcondition sentence)*')
        out.append(f'| {index} | `{name}` | {step.kind.name} | {shown} | '
                   f'{_cell(doc)} |')
    return out


def _guidance() -> list[str]:
    out = ['## Not steps, and why',
           '',
           'A step earns its place by having a CHECKABLE POSTCONDITION. What '
           'follows is real protocol with none, so the machine states it and '
           'does not pretend to enforce it.',
           '']
    for title, body in steps.GUIDANCE:
        out.append(f'**{title}.** {body}')
        out.append('')
    return out[:-1]


def render() -> str:
    """The whole document, from the template plus the configured lists."""
    template = resources.files(PACKAGE).joinpath(TEMPLATE).read_text(
        encoding='utf-8')
    body: list[str] = []
    for operation in OPERATIONS:
        body.append(f'## `{operation}` — the ordered list')
        body.append('')
        body.extend(_table(operation))
        body.append('')
    out = template.replace(STEPS_MARKER, '\n'.join(body).rstrip('\n'))
    out = out.replace(GUIDANCE_MARKER, '\n'.join(_guidance()))
    return out
