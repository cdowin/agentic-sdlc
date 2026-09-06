"""The `install-*` verbs: write a file into a repo, once, from one source.

`install-ci` (the three workflows), `install-agents` (the contract and the base roster
as agent definitions), `install-hooks` (the guard corpus and the script that arms it),
`install-gates` (`gdk_gate.sh` and `Makefile.devkit`), `install-sdlc` (the protocol,
rendered from the step lists). A destination that exists and differs is refused by
name, with `--force` and moving it aside as the remedies; an entry with nothing in the
way is still written, and the run exits 1 because a replacement was withheld. A
difference confined to the `project config` header is reported as one. No manifest,
no merge, no sync: after the write the file is the repo's.
"""
from __future__ import annotations

import difflib
import re
import sys
from importlib import resources
from pathlib import Path

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
       agentic-sdlc install-hooks   [--force] [--diff]
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
                `check`). The run prints the .claude/settings.json entries that
                fire them.
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
file, header included. --diff prints what would change and writes nothing."""

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
                     'a guard cannot quietly change a verdict. Then paste the '
                     'settings block below into '
                     '.claude/settings.json — installing a Claude Code hook '
                     'is not registering it, and an unregistered hook is a '
                     'file nothing ever runs.',
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
    'install-sdlc': 'docs/sdlc-protocol.md is GENERATED — it is the one '
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

# Printed, never written: `.claude/settings.json` is hand-maintained and there is no merge.
# The couriers are async because they parse a transcript; the guards must block in time.
_HOOK_SETTINGS = '''{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {"type": "command", "command": "bash tools/hooks/cc-commit-pathspec.sh"}
        ]
      },
      {
        "matcher": "Write|Edit|MultiEdit|NotebookEdit",
        "hooks": [
          {"type": "command", "command": "bash tools/hooks/cc-write-confine.sh"}
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {"type": "command", "command": "bash tools/hooks/cc-stop-gate.sh"},
          {"type": "command", "command": "bash tools/hooks/cc-ledger-session.sh", "async": true}
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          {"type": "command", "command": "bash tools/hooks/cc-ledger-subagent.sh", "async": true}
        ]
      }
    ]
  }
}'''

_SETTINGS_BLOCK = {'install-hooks': _HOOK_SETTINGS}


HEADER_ONLY_NOTE = '   (project-config header only)'


def collision_refusal(collisions: list[str],
                      wrote: list[str] | None = None,
                      header_only: tuple[str, ...] | list[str] = (),
                      ) -> tuple[str, str]:
    """(what collided, what that means), plural-correct; shared with `pm install-skills`.

    `wrote` is what the same run landed; `header_only` names the collisions
    confined to the editable block, whose repair is to do nothing.
    """
    flagged = set(header_only)
    if len(collisions) == 1:
        rel = collisions[0]
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


def read_destination(target: Path) -> tuple[str | None, str]:
    """(the file's text, or None when it cannot be decoded and so is a collision; a read defect)."""
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


def print_diff(rel: str, target: Path, body: str) -> None:
    """What an install would change, as a unified diff. Writes nothing."""
    if not target.is_file():
        print(f'[install] {rel} does not exist — the whole file is an addition')
        existing = ''
    else:
        text, defect = read_destination(target)
        if text is None:
            print(f'[install] {rel} {defect or "is not text this can diff"} '
                  f'— --force would replace it whole')
            return
        if text == body:
            print(f'[install] {rel} already current')
            return
        if header_only_difference(text, body):
            print(f'[install] {rel} differs ONLY inside its project-config '
                  f'header — the rest of the file is byte-current')
        existing = text
    sys.stdout.writelines(difflib.unified_diff(
        existing.splitlines(keepends=True), body.splitlines(keepends=True),
        fromfile=f'a/{rel}', tofile=f'b/{rel}'))


def _defect_refusal(command: str, defects: list[str], wrote: list[str]) -> str:
    listed = '\n'.join(f'    {d}' for d in defects)
    what = ('nothing was written' if not wrote else
            'ALREADY WRITTEN before this was reached: ' + ', '.join(wrote))
    return (f'agentic-sdlc {command}: {len(defects)} destination(s) cannot be '
            f'written:\n{listed}\n'
            f'agentic-sdlc {command}: {what}. Fix the path(s) and re-run — the '
            f'command is idempotent.')


def main(command: str, argv: list[str], next_step: bool = True) -> int:
    """One install verb; `next_step=False` is for `init`, which does what the paragraph asks."""
    force = False
    diff = False
    for arg in argv:
        if arg == '--force':
            force = True
        elif arg == '--diff':
            diff = True
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
        return 0

    # Decide the whole plan first; touch nothing until it holds.
    plan: list[tuple[str, Path, str, str]] = []   # (kind, target, rel, body)
    collisions: list[str] = []
    header_only: list[str] = []
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
                if existing is not None and header_only_difference(existing,
                                                                   body):
                    header_only.append(rel)
                continue
        plan.append((kind, target, rel, body))

    # A defect refuses the whole command: it is not a decision the operator made.
    if defects:
        if collisions:
            head, tail = collision_refusal(collisions,
                                           header_only=header_only)
            print(f'agentic-sdlc {command}: {head}\n'
                  f'agentic-sdlc {command}: {tail}', file=sys.stderr)
        print(_defect_refusal(command, defects, []), file=sys.stderr)
        return 1

    writes = apply.Plan()
    for kind, target, rel, body in plan:
        if kind != 'current':
            writes.overwrite(target, body, newline=None, label=rel,
                             executable=rel.endswith(EXECUTABLE_SUFFIX))
    # A failure here means the filesystem changed under the plan; `landed` says how far it got.
    result = writes.apply(decide=False)
    written = [step.label for step in result.landed]
    landed = set(written)
    for kind, target, rel, body in plan:
        if kind == 'current':
            print(f'[install] {rel} already current')
        elif rel in landed:
            print(f'[install] wrote {rel}')
        else:
            break
    if result.failed is not None:
        print(_defect_refusal(command,
                              [f'{result.failed.label} could not be written '
                               f'({result.error})'], written),
              file=sys.stderr)
        return 1
    # Before the next-step paragraph, so the pasteable settings block stays last on stdout.
    if collisions:
        head, tail = collision_refusal(collisions, wrote=written,
                                       header_only=header_only)
        print(f'agentic-sdlc {command}: {head}\n'
              f'agentic-sdlc {command}: {tail}', file=sys.stderr)
    if written and next_step:
        print(f'[install] {_NEXT_STEP[command]}')
        settings = _SETTINGS_BLOCK.get(command)
        if settings:
            # Unprefixed, so the block can be pasted whole.
            print(f'\n.claude/settings.json — the entries that FIRE these '
                  f'hooks (merge into yours):\n\n{settings}\n')
    # A withheld replacement is non-zero even when additions landed.
    return 1 if collisions else 0
