"""sdlc_doc.py — `docs/sdlc-protocol.md`, rendered from the lists that run.

Every check line comes from `[<operation>] steps` and `steps.STEP_DOC`, every
"then:" line from `steps.AFTER`; nothing here holds per-check text or reads the
clock or the tree, so two repos with one config render byte-identical files.
"""
from __future__ import annotations

from importlib import resources

from agentic_sdlc.repo.conveyor import driver, steps
from agentic_sdlc.repo.pm import ledger

PACKAGE = 'agentic_sdlc.repo.installables'
TEMPLATE = 'sdlc-template.md'

STEPS_MARKER = '<!-- STEPS -->'
EVENTS_MARKER = '<!-- EVENTS -->'
GUIDANCE_MARKER = '<!-- GUIDANCE -->'

# The operations a rendered document covers, in the order it covers them.
OPERATIONS = driver.OPERATIONS


def _cell(text: str) -> str:
    """One markdown table cell; a `|` inside would open a column that is not
    there."""
    return text.replace('|', '\\|').replace('\n', ' ')


def _write_line(operation: str) -> str:
    """What the belt writes when every check is true. The state word is not
    rendered, so the document stays a function of the check lists alone."""
    kind = driver.WRITES[operation]
    if not kind:
        return ('**Then:** nothing. `adopt` writes nothing; it is checks '
                'only, and `--force` is refused.')
    return (f'**Then, all true:** the {kind}\'s status → the first state of '
            f'`[pm.states.{kind}] done` (`pm vocabulary` prints it), through '
            f'`pm {kind} <state> <id>`, which mints the ledger\'s `status` '
            f'row. Any check false → `error:` lines, exit 1, no status written. '
            f'`--force` writes anyway and the ledger\'s `deviation` row '
            f'names the false checks.')


def _table(operation: str) -> list[str]:
    """The ordered check list for one operation as rows, or a sentence saying
    why there is none."""
    known = driver.registry_for(operation)
    # A `ConfigError` propagates: exit 2 before a byte is rendered.
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


def _events() -> list[str]:
    """The emitted schema, off `ledger.EVENT_KEYS` — the same tuples the three
    minters build their rows from. Rendered rather than written here for the
    reason the check tables are: a hand-written table beside a rendered one is
    the second scoreboard this package deletes everywhere else."""
    out = ['| tap | kind | the row it writes |', '|---|---|---|']
    for kind, keys in ledger.EVENT_KEYS.items():
        cells = ', '.join(f'`{key}`' for key in keys)
        out.append(f'| `{kind.rsplit(".", 1)[-1]}` | `{kind}` | {cells} |')
    words = ', '.join(f'`{word}`' for word in driver.VERDICT_WORDS.values())
    out.append('')
    out.append(f'`verdict` is one of {words}. `ran` is the command in the '
               f'operation\'s table above, or the literal '
               f'`{steps.READS_THE_TREE}`. Every field is derived: the ids '
               f'from the invocation, the categories from `[pm.states.*]`, '
               f'the names from the registry that ran them.')
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
    out = out.replace(EVENTS_MARKER, '\n'.join(_events()))
    out = out.replace(GUIDANCE_MARKER, '\n'.join(_guidance()))
    return out
