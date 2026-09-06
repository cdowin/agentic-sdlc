"""sdlc_doc.py — the protocol document, RENDERED from the lists that run.

`agentic-sdlc install-sdlc` writes `docs/sdlc-protocol.md`. Every check line
in it comes from `[<operation>] steps` and the registry those names resolve
against, every "then:" line from `steps.AFTER`, and the write from the
project's own `[pm.states.<kind>] done` — never from a table of prose kept
here. Change the config, re-run the verb, and the document changes with it.
A hand-written document DESCRIBING the checks recreates the drift this
package measured three times in one milestone.

Two rules this module is written to:

1. **It holds no per-check text.** The sentences live in `steps.STEP_DOC`,
   beside the `check()` that asks them; the after-lists in `steps.AFTER`; the
   not-a-check guidance in `steps.GUIDANCE`.
2. **It writes a WHOLE file it owns.** It never splices into `SDLC.md`
   (rule 3); `SDLC.md` LINKS here.

The output is a function of CONFIG ALONE: nothing here reads the clock, the
environment or the working tree, so two repos with the same config render
byte-identical documents.
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
    """One markdown table cell. A `|` inside would open a column that is not
    there; a check NAME can never carry one (the grammar is `[a-z][a-z0-9-]*`)
    so this only guards the prose halves."""
    return text.replace('|', '\\|').replace('\n', ' ')


def _write_line(operation: str) -> str:
    """What the belt writes when every check is true. The WORD is not
    rendered — it is `[pm.states.<kind>] done`'s first entry, read by the
    belt at run time and printed by `pm vocabulary` — so this document stays
    a function of the check lists alone: `init` renders it before `pm init`
    has written the flow, and a project that renames a state does not leave
    a stale document behind."""
    kind = driver.WRITES[operation]
    if not kind:
        return ('**Then:** nothing. `adopt` writes nothing; it is checks '
                'only, and `--force` is refused.')
    return (f'**Then, all true:** the {kind}\'s status → the first state of '
            f'`[pm.states.{kind}] done` (`pm vocabulary` prints it), through '
            f'`pm {kind} <state> <id>`, which mints the ledger\'s `status` '
            f'row. Any check false → `error:` lines, exit 1, nothing written. '
            f'`--force` writes anyway and the ledger\'s `deviation` row '
            f'names the false checks.')


def _table(operation: str) -> list[str]:
    """The ordered check list for one operation, as rows, or why there is
    none — a SENTENCE, never an empty section that reads as complete."""
    known = driver.registry_for(operation)
    # A `ConfigError` PROPAGATES: exit 2 from the verb before a byte is
    # rendered, never a document with a note where a list should be.
    names = steps.steps_for(operation, known)
    if not names:
        return [f'> `[{operation}] steps` is not configured in this repo, and '
                f'this package ships no default list for `{operation}`. '
                f'Nothing runs it.']
    commands = steps.commands_for(operation, names, known)
    out = ['| # | check | runs | what must be true |',
           '|---|---|---|---|']
    for index, name in enumerate(names, start=1):
        command = commands.get(name, '')
        shipped = steps.SHIPPED_ACTION.get(name, '')
        if command:
            shown = f'`{_cell(command)}`'
        elif shipped:
            shown = f'`{_cell(shipped)}` *(shipped)*'
        else:
            shown = '— *(reads the tree)*'
        doc = steps.STEP_DOC.get(
            name, '*(this check ships no sentence)*')
        out.append(f'| {index} | `{name}` | {shown} | {_cell(doc)} |')
    out.append('')
    out.append(_write_line(operation))
    after = steps.after_lines(operation, commands, version='<version>',
                              branch='<branch>', mainline='<mainline>')
    if after:
        out.append('')
        out.append('**Yours, after the write** (printed as `next:` lines):')
        out.append('')
        out.extend(f'- {line}' for line in after)
    return out


def _guidance() -> list[str]:
    out = ['## Not checks, and why',
           '',
           'A check earns its place by having something to READ in the tree. '
           'What follows is real protocol with nothing to read, so the '
           'machine states it and does not pretend to enforce it.',
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
        body.append(f'## `{operation}` — the checks')
        body.append('')
        body.extend(_table(operation))
        body.append('')
    out = template.replace(STEPS_MARKER, '\n'.join(body).rstrip('\n'))
    out = out.replace(GUIDANCE_MARKER, '\n'.join(_guidance()))
    return out
