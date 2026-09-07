"""The `install-*` verbs: write a file into a repo, once, from one source.

`install-ci` (the three workflows), `install-agents` (the contract and the base roster
as agent definitions), `install-hooks` (the guard corpus and the script that arms it),
`install-gates` (`gdk_gate.sh` and `Makefile.devkit`), `install-sdlc` (the protocol,
rendered from the step lists). A destination that exists and differs is refused by
name, with `--force` and moving it aside as the remedies; an entry with nothing in the
way is still written, and the run exits 1 because a replacement was withheld. A
difference confined to the `project config` header is reported as one. No manifest,
no merge, no sync: after the write the file is the repo's.

Two things the report owes a consumer, and both are about SILENCE: every destination
gets ONE `[install]` line whatever its disposition, because `grep '^\\[install\\]'` is
how a run is summarised; and a run names what this verb has STOPPED shipping over the
span between the version this repo pins and this one, because a make target that left
in a bump is otherwise learnt from a broken build and a retired flag from nothing at
all.
"""
from __future__ import annotations

import difflib
import json
import re
import shlex
import sys
from importlib import resources
from pathlib import Path
from typing import NamedTuple

from agentic_sdlc import __version__
from agentic_sdlc.core import apply
from agentic_sdlc.core.config import ConfigError
from agentic_sdlc.core.project import repo_root

PACKAGE = 'agentic_sdlc.repo.installables'

# (source name under installables/, destination relative to the repo root).
PLANS: dict[str, tuple[tuple[str, str], ...]] = {
    'install-ci': (
        ('ci-verify.yml', '.github/workflows/verify.yml'),
        ('ci-semver-gate.yml', '.github/workflows/semver-gate.yml'),
        ('ci-auto-tag.yml', '.github/workflows/auto-tag.yml'),
    ),
    'install-agents': (
        ('verification-reviewer.md', '.claude/agents/verification-reviewer.md'),
        ('verification-builder.md', '.claude/agents/verification-builder.md'),
        ('architect.md', '.claude/agents/architect.md'),
        ('po.md', '.claude/agents/po.md'),
        ('developer.md', '.claude/agents/developer.md'),
        ('reviewer.md', '.claude/agents/reviewer.md'),
        ('milestone-reviewer.md', '.claude/agents/milestone-reviewer.md'),
        ('simplifier.md', '.claude/agents/simplifier.md'),
        ('test-writer.md', '.claude/agents/test-writer.md'),
        ('tech-writer.md', '.claude/agents/tech-writer.md'),
        ('changelog-writer.md', '.claude/agents/changelog-writer.md'),
        ('doc-hygiene.md', '.claude/agents/doc-hygiene.md'),
        ('pm-operator.md', '.claude/agents/pm-operator.md'),
    ),
    'install-hooks': (
        ('cc-commit-pathspec.sh', 'tools/hooks/cc-commit-pathspec.sh'),
        ('cc-stop-gate.sh', 'tools/hooks/cc-stop-gate.sh'),
        ('cc-write-confine.sh', 'tools/hooks/cc-write-confine.sh'),
        # The two ledger couriers guard nothing but carry the same header and arming.
        ('cc-ledger-subagent.sh', 'tools/hooks/cc-ledger-subagent.sh'),
        ('cc-ledger-session.sh', 'tools/hooks/cc-ledger-session.sh'),
        ('pre-push', 'tools/hooks/pre-push'),
        ('prepare-commit-msg', 'tools/hooks/prepare-commit-msg'),
        ('agent-worktree.sh', 'tools/dev/agent-worktree.sh'),
        ('setup-hooks.sh', 'tools/setup-hooks.sh'),
    ),
    'install-gates': (
        # The library, then the include that sources it; neither is usable alone.
        ('gdk_gate.sh', 'tools/dev/gdk_gate.sh'),
        ('Makefile.devkit', 'Makefile.devkit'),
    ),
    'install-sdlc': (
        # The one entry whose body is rendered rather than copied.
        ('sdlc-template.md', 'docs/sdlc-protocol.md'),
    ),
}

# Destinations whose body is produced, keyed by destination; the producer is
# imported lazily so no install verb pays for a config read it does not need.
BODIES: dict[str, str] = {'docs/sdlc-protocol.md':
                          'agentic_sdlc.repo.conveyor.sdlc_doc:render'}

USAGE = """usage: agentic-sdlc install-ci      [--force] [--diff]
       agentic-sdlc install-agents  [--force] [--diff]
       agentic-sdlc install-hooks   [--force] [--diff] [--write-settings]
       agentic-sdlc install-gates   [--force] [--diff]
       agentic-sdlc install-sdlc    [--force] [--diff]

install-ci      three workflows under .github/workflows/: verify.yml
                (checkout, uv, `make milestone`, which it ASSUMES is your full
                gate), semver-gate.yml (a merge to main must bump your version
                file) and auto-tag.yml (tag the mainline, then dispatch
                RELEASE_WORKFLOW if you have one). A project without one of
                those assumptions edits the file, which after the write is its
                own. A toolchain step your gate needs and the runner lacks goes
                in verify.yml after the write — it is yours.
install-agents  the review/build contract plus the base agent roster, as
                AGENT DEFINITIONS under .claude/agents/ — the one place a
                subagent actually reads. Each roster file carries a
                `Project config` section — yours to edit after install.
install-hooks   the agent-workflow guard corpus, under tools/: the Claude Code
                hooks (cc-commit-pathspec, cc-stop-gate, cc-write-confine)
                plus the two ledger couriers
                (cc-ledger-subagent on SubagentStop, cc-ledger-session on
                Stop, each handing the stop event's transcript path to
                `pm ledger record` and exiting 0 whatever it says), the git
                hooks (pre-push, prepare-commit-msg),
                tools/dev/agent-worktree.sh and tools/setup-hooks.sh, which
                arms them. Each carries a small `project config` header — yours
                to edit after install. The two couriers ship their own corpora:
                wire `bash tools/hooks/<hook>.sh --self-test` into your static
                gate (a `hooks-self-test`-shaped target inside your own
                `check`). The run names .claude/settings.json and prints
                the entries that FIRE them, with ABSOLUTE script paths, so the
                same block works in whatever settings file your harness reads
                — including one above this repo, where a relative path fires
                nothing. --write-settings writes that file when nothing is in
                the way; without it the block is printed and the file is left
                alone. A settings file that already exists is never merged
                into and never replaced, --force included: it carries
                permissions, env and MCP entries this package knows nothing
                about.
install-gates   tools/dev/gdk_gate.sh — the shell library your gate targets
                source (one verdict line per gate naming
                .gate-reports/<gate>.log, VERBOSE=1 streams the transcript, and
                a bounded-run contract so a hung gate is a verdict rather than
                a wait) — plus Makefile.devkit at the repo root, the standard
                target set your own two-line Makefile `include`s: `check`
                (this package's gates, then your `[gates] extra`), `precommit`
                and `milestone`.
                `precommit` and `milestone` compose from GDK_PRECOMMIT_TIERS
                and GDK_MILESTONE_TIERS, which a LANGUAGE kit sets in a
                Makefile.tiers this include `-include`s. With no such file a
                project gets `check` alone, and says so. Both files carry
                --help and --self-test.
install-sdlc    docs/sdlc-protocol.md — YOUR protocol, rendered from the
                `[story]` / `[feature]` / `[release]` / `[adopt]` check lists
                in your devkit.toml, the registry that runs them, and the
                `[pm.states.<kind>] done` state each belt writes. It is the
                document for the checks the belts actually run, so it cannot
                drift from them: change the config, re-run this verb. The only
                install verb whose body is GENERATED rather than copied.
A destination that already exists and differs is REFUSED — that file, not the
roster: the entries with nothing in their way are written, every collision is
named, and the run exits 1 because a replacement was withheld. A difference
confined to the `project config` header is reported as one, and the rest of
that file is byte-current, so it needs no --force. --force overwrites the whole
file, header included. --diff prints what would change and writes nothing.
EVERY destination gets one `[install]` line whatever its disposition — added,
modified, header-only, already current, withheld — so a run summarised with
`grep '^[install]'` cannot omit a file. Each run also names what this verb has
STOPPED shipping (make targets, retired verb flags) between the DEVKIT_VERSION
your Makefile pins and the version running; no readable pin reports the whole
record rather than none of it."""

# A `.sh` installable is written executable, as part of the write in `core.apply`.
EXECUTABLE_SUFFIX = '.sh'


def _is_executable(target: Path) -> bool:
    """Whether `target` already carries an execute bit for anyone."""
    try:
        return bool(target.stat().st_mode & 0o111)
    except OSError:
        return False


_NEXT_STEP = {
    'install-hooks': 'run `bash tools/setup-hooks.sh` to point git at them and '
                     'set the exec bit — an unexecutable hook is skipped in '
                     'silence. Then review each file\'s `project config` '
                     'header (gate commands, protected branches, trailer): '
                     'the files are yours now, and the stock values assume '
                     'the standard consumer Makefile. Then wire `bash '
                     'tools/hooks/cc-ledger-subagent.sh --self-test` and its '
                     'session twin into your static gate (a '
                     '`hooks-self-test`-shaped target inside your own `check`) '
                     '— each replays its own block/allow corpus, so an edit to '
                     'a guard cannot quietly change a verdict. Then land the '
                     'settings block below — re-run with --write-settings, '
                     'which writes .claude/settings.json when nothing is in '
                     'the way, or paste it into the settings file your '
                     'harness reads. Installing a Claude Code hook is not '
                     'registering it, and an unregistered hook is a file '
                     'nothing ever runs. THESE ENTRIES ARE NOT YET IN FORCE '
                     'until one of those two happens, and until then the '
                     'couriers are on disk and nothing fires them — '
                     '`agentic-sdlc adopt` and `check pm` U2 both report that. '
                     'Next, the couriers take the TREE from GDK_LEDGER_ROOT '
                     'when the session cwd is not inside it: a session rooted '
                     'at a parent directory derives no repo and files no row, '
                     'and no gate here can see that from outside. '
                     'Last, the ledger couriers read GDK_LEDGER_GRAIN from '
                     'THEIR OWN ENVIRONMENT and pass it as `--grain`, which is '
                     'what puts a session\'s tokens on a story\'s line rather '
                     'than in `rows naming no grain`. Nothing exports it for '
                     'you: whoever starts a session or dispatches an agent '
                     'exports the grain it was told to work on. Unset is '
                     'normal and passes no flag — the verb then resolves the '
                     'grain from the tree, or omits the key.',
    'install-agents': 'the verification pair carries the review and build '
                      'contract; the rest are the base roster. Each roster '
                      'file opens with a `Project config` section — edit its '
                      'stock values (gate commands, pm tree, doc layout) to '
                      'your spellings: the files are yours now. `model:` in '
                      'the frontmatter is doing proven work; `effort:` is '
                      'carried unverified. The SDLC these agents run is '
                      'SDLC.md at the agentic-sdlc repo root.',
    'install-ci': 'verify.yml runs `make milestone` — confirm that target '
                  'exists and is your full gate, and add whatever toolchain '
                  'your gate needs and the runner lacks. semver-gate.yml and '
                  'auto-tag.yml read your version out of the file `[pm] '
                  'version_file` names; rename the branches in the `on:` '
                  'filters if yours differ (a filter takes no variable). Set '
                  'RELEASE_WORKFLOW in auto-tag.yml if your release pipeline '
                  'is not release.yml, and leave it alone if you have none — '
                  'the step is a documented no-op then.',
    'install-gates': 'make your Makefile two lines — `DEVKIT_VERSION := '
                     '<tag>` and then `include Makefile.devkit` — plus your '
                     'own targets; your own gates join `check` through '
                     '`[gates] extra` in devkit.toml, never a fork of the '
                     'include. A language kit\'s own installer writes '
                     'Makefile.tiers beside it and sets GDK_PRECOMMIT_TIERS / '
                     'GDK_MILESTONE_TIERS; without one, `precommit` and '
                     '`milestone` are `check` and say so. Then gitignore '
                     '.gate-reports/. Both files are written EXECUTABLE where '
                     'that applies, so a target may call the library either '
                     'way — the stock recipes source it. Then edit the '
                     '`project config` header: the files are yours now.',
    # No paragraph here may OPEN with a destination path: `[install] <path> …`
    # is a destination's own header line, and prose wearing that shape is prose
    # a summary counts as a file. `test_install.py` holds this.
    'install-sdlc': 'this one is GENERATED — docs/sdlc-protocol.md is the one '
                    'installed file you do not edit. Its check lists come '
                    'from `[<operation>] steps` in devkit.toml and from the '
                    'registry that runs them, so the way to change the '
                    'protocol is to change the config (or a check) and re-run '
                    'this verb with --force. Link to it from your own SDLC '
                    'document rather than restating the checks there: a '
                    'second copy of an ordered list is the drift this verb '
                    'exists to end. Then run `agentic-sdlc release <version>` '
                    '— every check runs and prints, all true → the milestone '
                    'is written `done` and the `next:` lines say what is yours '
                    '(retitle, push, PR, tag, prove), any false → nothing is '
                    'written and each false check is named; `--force` writes '
                    'anyway and the ledger row names them.',
}

# The wiring, as data: (event, matcher, hook, whether it is async). The couriers
# are async because they parse a transcript; the guards must block in time.
_WIRING: tuple[tuple[str, str | None, str, bool], ...] = (
    ('PreToolUse', 'Bash', 'tools/hooks/cc-commit-pathspec.sh', False),
    ('PreToolUse', 'Write|Edit|MultiEdit|NotebookEdit',
     'tools/hooks/cc-write-confine.sh', False),
    ('Stop', None, 'tools/hooks/cc-stop-gate.sh', False),
    ('Stop', None, 'tools/hooks/cc-ledger-session.sh', True),
    ('SubagentStop', None, 'tools/hooks/cc-ledger-subagent.sh', True),
)

# The one destination this package OFFERS to write and never merges into.
AGENT_SETTINGS = '.claude/settings.json'
SETTINGS_FLAG = '--write-settings'
SETTINGS_COMMANDS = ('install-hooks',)
SETTINGS_INDENT = 2


def hook_settings(root: Path) -> str:
    """The settings body that FIRES the installed hooks, with ABSOLUTE script paths.

    A relative path resolves only when the harness's cwd IS `root`, so a
    session rooted anywhere else fires nothing and says nothing. An absolute
    one is the same block wherever the settings file carrying it lives.

    QUOTED, because the harness hands this string to a shell: absolutising the
    path is what introduced the class, since a relative `tools/hooks/…` has no
    space to break on and `/Users/me/my repo/tools/…` does. An unquoted one
    still reads as an absolute existing file to anything that splits on the
    first space, so it fails where nothing is looking.
    """
    events: dict[str, list[dict]] = {}
    groups: dict[tuple[str, str | None], dict] = {}
    for event, matcher, rel, is_async in _WIRING:
        script = shlex.quote(str(root / rel))
        entry: dict = {'type': 'command', 'command': f'bash {script}'}
        if is_async:
            entry['async'] = True
        group = groups.get((event, matcher))
        if group is None:
            group = {'hooks': []} if matcher is None else {'matcher': matcher,
                                                           'hooks': []}
            groups[(event, matcher)] = group
            events.setdefault(event, []).append(group)
        group['hooks'].append(entry)
    return json.dumps({'hooks': events}, indent=SETTINGS_INDENT)


SETTINGS_NAMES = (
    '{path} — the entries that FIRE these hooks. The script paths are '
    'ABSOLUTE, so this block works in whatever settings file your harness '
    'actually reads, including one above this repo. Export '
    'GDK_LEDGER_ROOT={root} in that session when its cwd is not inside this '
    'tree, or the couriers derive no tree and file nothing. An absolute path '
    'names one machine, so a SHARED checkout puts the block in '
    '{local} and gitignores it — every surface here reads that file too:')
# The per-user override a harness writes for itself, and the one place a
# public repo can carry absolute wiring. Read back by `check pm` U2/U4 and by
# `adopt`'s `telemetry-live`, off `checks.pm.AGENT_SETTINGS_LOCAL`.
AGENT_SETTINGS_LOCAL = '.claude/settings.local.json'
SETTINGS_OFFER = ('{rel} was NOT written — pass {flag} and this verb writes it '
                  'when nothing is in the way')
# ONE line, like every other disposition: `grep '^[install]'` is how a run
# is summarised, and it is the only place the concrete export survives when
# the offer is taken (the pasteable block is not printed after a write).
SETTINGS_WROTE = (
    'wrote {rel} — in force for a session rooted here. A session rooted '
    'anywhere else reads its own settings file, and needs this same block '
    'plus `export GDK_LEDGER_ROOT={root}` — this package cannot observe '
    'which file a harness loads')
SETTINGS_CURRENT = '{rel} already carries exactly this block'
SETTINGS_WITHHELD = (
    '{rel} exists and is yours — it carries permissions, env and MCP entries '
    'this package knows nothing about, so nothing here merges into it and '
    '--force does not replace it; paste the block above')
SETTINGS_DEFECT = '{rel} {defect} — nothing was written'


def settings_step(root: Path, write: bool) -> bool:
    """Name the settings file, say what became of it, print what to paste.

    True when a write was ASKED FOR and withheld, which is exit 1 like any
    other withheld replacement.

    PUBLIC, because `init` calls it too: a brand-new consumer that never
    reaches this step gets neither the fragment nor the destination, which is
    strictly less than the hand-paste this verb exists to replace.
    """
    target = root / AGENT_SETTINGS
    body = hook_settings(root) + '\n'
    line, withheld, paste = _settings_write(root, target, body, write)
    _say(line)
    if paste:
        # Last on stdout and unprefixed, so the block can be pasted whole.
        print(f'\n{SETTINGS_NAMES.format(path=target, root=root, local=AGENT_SETTINGS_LOCAL)}'
              f'\n\n{body}')
    return withheld


def _settings_write(root: Path, target: Path, body: str,
                    write: bool) -> tuple[str, bool, bool]:
    """(the report line, was a write withheld, is there still a paste to do).

    Without the flag nothing is touched: a package that silently edits a
    harness config is worse than one that does not. With it, a file with
    nothing in the way is written whole — and one that EXISTS is refused by
    path, `--force` included, because it carries permissions, env and MCP
    entries this package knows nothing about and there is no merge.
    """
    if not write:
        return (SETTINGS_OFFER.format(rel=AGENT_SETTINGS, flag=SETTINGS_FLAG),
                False, True)
    defect = destination_defect(target)
    if defect:
        return SETTINGS_DEFECT.format(rel=AGENT_SETTINGS,
                                      defect=defect), True, True
    if target.is_file():
        existing, _unreadable = read_destination(target)
        if existing == body:
            return SETTINGS_CURRENT.format(rel=AGENT_SETTINGS), False, False
        return SETTINGS_WITHHELD.format(rel=AGENT_SETTINGS), True, True
    result = apply.Plan().overwrite(target, body, newline=None,
                                    label=AGENT_SETTINGS).apply(decide=False)
    if result.failed is not None:
        return SETTINGS_DEFECT.format(
            rel=AGENT_SETTINGS,
            defect=f'could not be written ({result.error})'), True, True
    return SETTINGS_WROTE.format(rel=AGENT_SETTINGS, root=root), False, False


HEADER_ONLY_NOTE = '   (project-config header only)'


def collision_refusal(collisions: list[str],
                      wrote: list[str] | None = None,
                      header_only: tuple[str, ...] | list[str] = (),
                      undecodable: tuple[str, ...] | list[str] = (),
                      ) -> tuple[str, str]:
    """(what collided, what that means), plural-correct; shared with `pm install-skills`.

    `wrote` is what the same run landed; `header_only` names the collisions
    confined to the editable block, whose repair is to do nothing.
    """
    flagged = set(header_only)
    # Review I5: a file that cannot be decoded did not "differ" — it could not
    # be compared. `--force` still replaces it, which is why it is a collision
    # and not a defect, but the reader is told which of the two this is.
    note = ('' if not undecodable else
            '\n    ' + ', '.join(sorted(undecodable))
            + f' {UNDECODABLE_NOTE}')
    if len(collisions) == 1:
        rel = collisions[0]
        if rel in set(undecodable):
            return (f'{rel} {UNDECODABLE_NOTE}',
                    'Nothing was written. `--force` replaces it whole; there '
                    'is no diff to read first.')
        if rel in flagged:
            head = (f'{rel} exists and differs ONLY inside its project-config '
                    f'header — the rest of the file is byte-current, so there '
                    f'is nothing in it to take; leave it as yours, or pass '
                    f'--force to replace the whole file, header included')
        else:
            head = (f'{rel} exists and differs from what this would '
                    f'write — move your version aside, or pass --force')
    else:
        listed = '\n'.join(
            f'    {rel}' + (HEADER_ONLY_NOTE if rel in flagged else '')
            for rel in collisions)
        head = (f'{len(collisions)} destinations exist and differ from what '
                f'this would write — move your versions aside, or pass '
                f'--force:\n{listed}')
        if flagged:
            head += (f'\n{len(flagged)} of them differ only inside the '
                     f'project-config header the file invites you to edit: '
                     f'the rest of each is byte-current, so there is nothing '
                     f'in them to take, and --force would replace the header '
                     f'too')
    if wrote:
        landed = f'{len(wrote)} file(s) with nothing in the way'
        landed += ' was written' if len(wrote) == 1 else ' were written'
        held = 'it was' if len(collisions) == 1 else 'those above were'
        return head, (f'{landed}; {held} withheld and no existing file was '
                      f'overwritten. --diff shows what would change.')
    return head, ('nothing was written; every colliding destination is listed '
                  'above, not just the first. --diff shows what would change.')

# The wording this verb has always used, mapped from `core.apply`'s closed vocabulary.
_DEFECT_TEXT = {
    apply.Obstruction.IS_A_DIRECTORY: 'is a directory',
    apply.Obstruction.NOT_A_REGULAR_FILE: 'is not a regular file',
    apply.Obstruction.NOT_WRITABLE: 'is not writable',
}
_PARENT_TEXT = {
    apply.Obstruction.PARENT_IS_A_FILE: 'is not a directory',
    apply.Obstruction.PARENT_NOT_WRITABLE: 'is not writable',
}


def destination_defect(target: Path) -> str:
    """'' when `target` can be written, else what stands in the way, decided without a write.

    Symlinks are followed: an install destination is an ordinary repo file.
    """
    blocked = apply.Plan().overwrite(
        target, '', symlink=apply.Symlink.FOLLOW).decide()
    if not blocked:
        return ''
    first = blocked[0]
    if first.reason in _DEFECT_TEXT:
        return _DEFECT_TEXT[first.reason]
    return f'cannot be created: {first.path} {_PARENT_TEXT[first.reason]}'


UNDECODABLE_NOTE = 'is not UTF-8 text, so it cannot be compared'


def read_destination(target: Path) -> tuple[str | None, str]:
    """(the file's text, or None when it cannot be decoded; a read DEFECT, or '').

    An undecodable file comes back as `(None, '')` on purpose: it is a
    COLLISION, not a defect — `--force` can replace it and that is useful — and
    the caller tells the two apart by `text is None` with no defect. What it is
    NOT is a file that "differs", and the refusal now says which (review I5).
    """
    try:
        return target.read_text(encoding='utf-8'), ''
    except UnicodeDecodeError:
        return None, ''
    except OSError as err:
        return None, f'cannot be read ({err.strerror or err})'


# The editable block's two spellings: a shell rule comment pair, a markdown heading pair.
_BLOCK_GRAMMARS = (
    ('--- project config (yours to edit after install',
     re.compile(r'^#\s*-{5,}\s*$')),
    ('## Project config (yours to edit after install)',
     re.compile(r'^## ')),
)


def config_block_span(text: str) -> tuple[int, int] | None:
    """The half-open line range of the editable project-config block, markers excluded,
    or None; locating less than is there is the only safe direction."""
    lines = text.splitlines()
    for opening, closing in _BLOCK_GRAMMARS:
        for start, line in enumerate(lines):
            if opening not in line:
                continue
            for end in range(start + 1, len(lines)):
                if closing.match(lines[end]):
                    return start + 1, end
            return start + 1, len(lines)
    return None


def header_only_difference(existing: str, body: str) -> bool:
    """True when the two texts differ only inside the project-config block, decided by
    deleting both blocks and comparing the rest byte for byte."""
    mine = config_block_span(existing)
    theirs = config_block_span(body)
    if mine is None or theirs is None:
        return False
    return _outside_block(existing, mine) == _outside_block(body, theirs)


def _outside_block(text: str, span: tuple[int, int]) -> list[str]:
    # keepends, so a trailing-newline difference is still a difference.
    lines = text.splitlines(keepends=True)
    return lines[:span[0]] + lines[span[1]:]


def body_of(name: str) -> str:
    """One installable, verbatim. There is no substitution and no template."""
    return resources.files(PACKAGE).joinpath(name).read_text(encoding='utf-8')


def resolve_body(name: str, rel: str) -> str:
    """What this plan entry writes: `body_of(name)`, or the producer's output."""
    producer = BODIES.get(rel)
    if producer is None:
        return body_of(name)
    module_name, function = producer.split(':')
    from importlib import import_module
    return getattr(import_module(module_name), function)()


# --- one line per destination, whatever its disposition -----------------------
# A consumer summarises a run with `grep '^\[install\]'`. Through 0.2.0 a MODIFIED
# file printed a bare unified diff and no header at all, so that summary named the
# additions and silently omitted the file that actually changed — over a 1,211-line
# diff, the most consequential one. The dispositions below are a CLOSED set, and
# every entry of a plan gets exactly one of them, in `--diff` and in a real run.
REPORT_PREFIX = '[install]'
WOULD_ADD = '{rel} does not exist — the whole file is an addition'
IS_CURRENT = '{rel} already current'
HEADER_ONLY_DIFFERS = ('{rel} differs ONLY inside its project-config header — '
                       'the rest of the file is byte-current')
BODY_DIFFERS = '{rel} exists and differs from what this would write'
UNDECODABLE = '{rel} {defect} — --force would replace it whole'
WROTE = 'wrote {rel}'
WITHHELD = ('{rel} withheld — it exists and differs from what this would '
            'write, and no --force was given')
WRITE_FAILED = '{rel} could not be written — the refusal names why'
NOT_REACHED = '{rel} not reached — an earlier write failed'


def _say(line: str) -> None:
    """One report line, under the prefix consumers grep for."""
    print(f'{REPORT_PREFIX} {line}')


def print_diff(rel: str, target: Path, body: str) -> None:
    """What an install would change, as a unified diff under ONE header line.

    Every disposition gets a header, the modified file included; writes nothing.
    """
    if not target.is_file():
        # `is_file()` is false for a DIRECTORY and for an unwritable parent
        # too, and calling either "an addition" at exit 0 disagrees with the
        # real run, which refuses at exit 1 (review I4). `--diff` is what a
        # consumer reads BEFORE the run, so it is the surface where the
        # disagreement costs the most.
        defect = destination_defect(target)
        if defect:
            _say(f'{rel} {defect} — a real run REFUSES this; no diff')
            return
        _say(WOULD_ADD.format(rel=rel))
        existing = ''
    else:
        text, defect = read_destination(target)
        if text is None:
            _say(UNDECODABLE.format(
                rel=rel, defect=defect or 'is not text this can diff'))
            return
        if text == body:
            _say(IS_CURRENT.format(rel=rel))
            return
        _say((HEADER_ONLY_DIFFERS if header_only_difference(text, body)
              else BODY_DIFFERS).format(rel=rel))
        existing = text
    sys.stdout.writelines(difflib.unified_diff(
        existing.splitlines(keepends=True), body.splitlines(keepends=True),
        fromfile=f'a/{rel}', tofile=f'b/{rel}'))


# --- what a verb STOPPED shipping ---------------------------------------------
# Neither half of this is derivable. A make target dropped by a SPLIT is in no
# installable this package still ships, and a retired FLAG lived in the consumer's
# prose — a sentence naming it survives a bump intact and green, because no gate
# reads a sentence. So it is DECLARED: one row per (version, verb), and a release
# that withdraws something appends one row. The shape, for the release that needs
# it:
#
#     Retirement('0.4.0', 'install-gates', targets=('some-target',),
#                flags=('pm feature done --cascade',))
#
# The table is EMPTY because nothing this package ships was withdrawn between
# 0.2.0 and 0.3.0 — install-gates' targets (`check`, `precommit`, `milestone`) and
# every verb flag are all still here. Inventing a row to exercise the mechanism
# would put a false sentence in a consumer's terminal; the mechanism is proven in
# `tests/test_install.py` against a fixture table instead.


class Retirement(NamedTuple):
    """What one version stopped shipping, for one install verb."""

    version: str
    command: str
    targets: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()


RETIREMENTS: tuple[Retirement, ...] = ()

# Where a consumer's `DEVKIT_VERSION` pin lives — READ, never written, and never
# created. `[adopt] pin_file` can move it, but an install verb runs in trees with
# no devkit.toml at all, so this reads the stock path and treats every other
# answer as unknown, which WIDENS the span rather than narrowing it.
PIN_FILE = 'Makefile'
_VERSION = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)')

NO_LONGER_SHIPPED = (
    'no longer shipped: {what} — withdrawn {span}. A make target your Makefile '
    'or `[gates] extra` still names fails with `No rule to make target`, so '
    'drop or replace each one')
RETIRED_FLAGS = (
    'retired verb flags: {what} — withdrawn {span}. A flag lives in your prose, '
    'and no gate can read a sentence about one: grep your rules and agent '
    'briefs for each')
NOTHING_WITHDRAWN = (
    '{command} has withdrawn no make target and no verb flag {span}')


def _version_key(version: str) -> tuple[int, int, int] | None:
    """(major, minor, patch), or None when the string is not one — and an
    unreadable version widens the span rather than narrowing it."""
    found = _VERSION.match(version.strip().strip('"\''))
    return (int(found[1]), int(found[2]), int(found[3])) if found else None


def installed_stamp(root: Path) -> str | None:
    """The version `root` pins, or None when there is no readable pin.

    The pin is the only version marker a consumer repo carries: the installables
    are written verbatim and carry no stamp of their own. Read through the one
    pin grammar (`conveyor.steps.PIN_LINE`), never a second copy of it.
    """
    from agentic_sdlc.repo.conveyor.steps import PIN_LINE

    try:
        text = (root / PIN_FILE).read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    for line in text.split('\n'):
        found = PIN_LINE.match(line)
        if found:
            return found.group(1).strip('"\'')
    return None


def retired_since(command: str, stamp: str | None,
                  rows: tuple[Retirement, ...] | None = None,
                  current: str | None = None) -> tuple[Retirement, ...]:
    """`command`'s rows over the span between `stamp` and `current`.

    This version's OWN row is always in the span — a run of this installer says
    what this installer stopped shipping, whatever the pin says — and an older
    stamp, or one that cannot be read at all, only widens it. Narrowing is the
    direction that costs a consumer a broken build.
    """
    rows = RETIREMENTS if rows is None else rows
    ceiling = _version_key(current or __version__)
    floor = _version_key(stamp) if stamp else None
    kept = []
    for row in rows:
        if row.command != command:
            continue
        key = _version_key(row.version)
        if key is None or ceiling is None or key == ceiling:
            kept.append(row)
        elif key < ceiling and (floor is None or key > floor):
            kept.append(row)
    return tuple(kept)


def _span_phrase(stamp: str | None) -> str:
    at = f'v{__version__}'
    if stamp is None:
        return (f'at or before {at} — this repo pins no readable '
                f'DEVKIT_VERSION, so the whole record is reported')
    return f'between {stamp if stamp.startswith("v") else "v" + stamp} and {at}'


def retirement_report(command: str, stamp: str | None,
                      rows: tuple[Retirement, ...] | None = None,
                      current: str | None = None) -> list[str]:
    """The lines a run prints about what `command` stopped shipping.

    Never empty: a span that withdrew nothing SAYS so, because a report that
    found nothing and a report that never ran read identically in a transcript.
    """
    found = retired_since(command, stamp, rows, current)
    span = _span_phrase(stamp)
    targets = [t for row in found for t in row.targets]
    flags = [f for row in found for f in row.flags]
    lines = []
    if targets:
        lines.append(NO_LONGER_SHIPPED.format(what=', '.join(targets),
                                              span=span))
    if flags:
        lines.append(RETIRED_FLAGS.format(what=', '.join(flags), span=span))
    return lines or [NOTHING_WITHDRAWN.format(command=command, span=span)]


def _defect_refusal(command: str, defects: list[str], wrote: list[str]) -> str:
    listed = '\n'.join(f'    {d}' for d in defects)
    what = ('nothing was written' if not wrote else
            'ALREADY WRITTEN before this was reached: ' + ', '.join(wrote))
    return (f'agentic-sdlc {command}: {len(defects)} destination(s) cannot be '
            f'written:\n{listed}\n'
            f'agentic-sdlc {command}: {what}. Fix the path(s) and re-run — the '
            f'command is idempotent.')


def _report_retirements(command: str, root: Path) -> None:
    """What `command` stopped shipping over the span this repo is crossing.

    Skipped under `next_step=False`, which is `init`: a tree being wired for the
    first time has no span, and there is nothing it could have lost.
    """
    for line in retirement_report(command, installed_stamp(root)):
        _say(line)


def main(command: str, argv: list[str], next_step: bool = True) -> int:
    """One install verb; `next_step=False` is for `init`, which does what the paragraph asks."""
    force = False
    diff = False
    write_settings = False
    for arg in argv:
        if arg == '--force':
            force = True
        elif arg == '--diff':
            diff = True
        elif arg == SETTINGS_FLAG and command in SETTINGS_COMMANDS:
            write_settings = True
        elif arg in ('-h', '--help', 'help'):
            print(USAGE)
            return 0
        else:
            print(f'agentic-sdlc {command}: unknown flag {arg!r}',
                  file=sys.stderr)
            print(USAGE, file=sys.stderr)
            return 2

    root = repo_root()
    try:
        entries = [(root / rel, rel, resolve_body(name, rel))
                   for name, rel in PLANS[command]]
    except ConfigError as err:
        # A generated body reads the project's config; a bad value is exit 2, before any write.
        print(f'agentic-sdlc {command}: {err}', file=sys.stderr)
        return 2

    if diff:
        for target, rel, body in entries:
            print_diff(rel, target, body)
        if next_step:
            _report_retirements(command, root)
        if write_settings:
            # Named rather than ignored: --diff writes nothing, this included.
            _say(f'{SETTINGS_FLAG} writes nothing under --diff')
        return 0

    # Decide the whole plan first; touch nothing until it holds. A WITHHELD entry
    # keeps its row and its place, so the report below names every entry the run
    # reached, in plan order, rather than dropping the ones it did not write. (A
    # defect refuses the whole command below, before any of that is printed.)
    plan: list[tuple[str, Path, str, str]] = []   # (kind, target, rel, body)
    collisions: list[str] = []
    header_only: list[str] = []
    undecodable: list[str] = []
    defects: list[str] = []
    for target, rel, body in entries:
        kind = 'write'
        defect = destination_defect(target)
        if defect:
            defects.append(f'{rel} {defect}')
            continue
        if target.is_file():
            existing, unreadable = read_destination(target)
            if unreadable:
                defects.append(f'{rel} {unreadable}')
                continue
            if existing == body and not (rel.endswith(EXECUTABLE_SUFFIX)
                                         and not _is_executable(target)):
                kind = 'current'
            elif existing == body:
                # Right bytes, missing execute bit: rewritten so the one writer sets the mode.
                pass
            elif not force:
                collisions.append(rel)
                if existing is None:
                    # Review I5: not a file that "differs" — one that cannot be
                    # compared at all, which is a different thing to be told.
                    undecodable.append(rel)
                elif header_only_difference(existing, body):
                    header_only.append(rel)
                plan.append(('withheld', target, rel, body))
                continue
        plan.append((kind, target, rel, body))

    # A defect refuses the whole command: it is not a decision the operator made.
    if defects:
        # ...but it still HEADS every file this verb owns, because the report's
        # completeness is the criterion (review I1). Refusing with zero
        # `[install]` lines makes `grep -c '^\[install\]'` answer 0 for a verb
        # that owns six files, which is the exact silence this feature exists to
        # end — and it is worst on the path where a human most needs the list.
        blocked = {d.split(' ', 1)[0] for d in defects}
        for target, rel, body in entries:
            if rel in blocked:
                _say(f'{rel} CANNOT be written — the refusal on stderr says why')
            elif rel in collisions:
                _say(f'{rel} exists and differs; nothing was written because '
                     f'another destination is unusable')
            else:
                _say(f'{rel} was reachable; nothing was written because '
                     f'another destination is unusable')
        if collisions:
            head, tail = collision_refusal(collisions,
                                           header_only=header_only,
                                           undecodable=undecodable)
            print(f'agentic-sdlc {command}: {head}\n'
                  f'agentic-sdlc {command}: {tail}', file=sys.stderr)
        print(_defect_refusal(command, defects, []), file=sys.stderr)
        return 1

    writes = apply.Plan()
    for kind, target, rel, body in plan:
        if kind == 'write':
            writes.overwrite(target, body, newline=None, label=rel,
                             executable=rel.endswith(EXECUTABLE_SUFFIX))
    # A failure here means the filesystem changed under the plan; `landed` says how far it got.
    result = writes.apply(decide=False)
    written = [step.label for step in result.landed]
    landed = set(written)
    failed = None if result.failed is None else result.failed.label
    for kind, target, rel, body in plan:
        if kind == 'current':
            _say(IS_CURRENT.format(rel=rel))
        elif kind == 'withheld':
            _say(WITHHELD.format(rel=rel))
        elif rel in landed:
            _say(WROTE.format(rel=rel))
        elif rel == failed:
            _say(WRITE_FAILED.format(rel=rel))
        else:
            # Named, not dropped: the entries a mid-plan failure never reached
            # are the ones an operator has to re-run for.
            _say(NOT_REACHED.format(rel=rel))
    if result.failed is not None:
        print(_defect_refusal(command,
                              [f'{result.failed.label} could not be written '
                               f'({result.error})'], written),
              file=sys.stderr)
        return 1
    # Before the next-step paragraph, so the pasteable settings block stays last on stdout.
    if collisions:
        head, tail = collision_refusal(collisions, wrote=written,
                                       header_only=header_only,
                                       undecodable=undecodable)
        print(f'agentic-sdlc {command}: {head}\n'
              f'agentic-sdlc {command}: {tail}', file=sys.stderr)
    if next_step:
        _report_retirements(command, root)
    if written and next_step:
        print(f'[install] {_NEXT_STEP[command]}')
    # Whatever the plan did: a re-run on a current tree is how an operator
    # reaches --write-settings, and the wiring is the step no gate observes.
    settings_withheld = False
    if next_step and command in SETTINGS_COMMANDS:
        settings_withheld = settings_step(root, write_settings)
    # A withheld replacement is non-zero even when additions landed.
    return 1 if collisions or settings_withheld else 0
