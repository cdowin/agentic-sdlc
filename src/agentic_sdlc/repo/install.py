"""install.py — write a file into a repo, once, from one source.

Four verbs, one relationship, and it is deliberately the whole relationship:

    install-ci      the three workflows a project runs on a push: verify.yml
                    (checkout, uv, `make milestone`), semver-gate.yml and
                    auto-tag.yml. Each was forked in both consumers, drifting
                    on a project name and on which fix each fork got. They
                    carry no gate of their own and no way to parameterize one:
                    a project that wants something else edits the file, which
                    is now its file. Release / website / social workflows are
                    the project's and are not written.
    install-agents  the review and build contract PLUS the base agent roster
                    (architect, po, developer, reviewers, simplifier, the
                    writers, pm-operator), as AGENT DEFINITIONS under
                    .claude/agents/. Deliberately not `.claude/rules/*`: it is
                    measured that a rules file never reaches a subagent's spawn
                    context while its definition does, so a contract written as
                    a rule is a contract that arrives nowhere. The roster is
                    generalized from the two consumers; per-file variation is a
                    marked `Project config` section the repo edits after
                    install, the same relationship the hook corpus has.
    install-hooks   the agent-workflow guard corpus: the Claude Code hooks
                    (commit-pathspec, stop gate, write confinement), the git
                    hooks (pre-push, prepare-commit-msg), the worktree tool
                    that writes the scope marker the guards read, and the
                    script that arms them.
                    Forked between two repos (~1,000 lines duplicated per repo,
                    drifting on a project-name prefix and on which fixes each
                    fork got); canonical here. Every installed file is
                    STANDALONE — no sourcing of a library the repo may lack —
                    and per-project variation is a small config header the
                    repo edits after install, when the file is its own.
    install-gates   the gate FRAMEWORK: `gdk_gate.sh`, the shell library that
                    gives every gate one verdict line and a transcript on disk,
                    plus `Makefile.devkit` — the standard target set that calls
                    it (`check`, `precommit`, `milestone`) and the `-include`
                    seam a LANGUAGE KIT hangs its own tiers on. Not folded into
                    install-hooks: a hooks-only consumer would carry a make
                    include it never runs, and the library is sourced by make
                    targets rather than fired by Claude Code. Every function is
                    `gdk_*` — the per-project `<project>_*` forks this replaces
                    are what drifted, so a consumer keeping its own prefix is a
                    second name for the same fact and is not supported.

                    It was `install-runners` through 0.1.0, and it carried the
                    engine runners with it. Decision D2 of 0.2.0: an installable
                    belongs to the kit whose ARTIFACT it acts on, so the runners
                    left and the framework kept the verb — renamed, because a
                    verb called `install-runners` that installs no runner is
                    the kind of name that has to be explained every time.

The verb writes the file. Once. If the destination is already there and is not
byte-for-byte what would be written, the command REFUSES, names the path, and
names both remedies — move it aside, or `--force`. `--diff` shows what a run
would change and writes nothing. There is no manifest, no content hash, no
drift tracking, no merge and no ongoing sync: after the file is written it
belongs to the repo that asked for it, and the next install has to be told, by
an operator, that clobbering it is the intent.

Every refusal is decided for EVERY entry in the plan before the first byte is
written — the same rule the PM scaffolder states as "every refusal the grain
can raise is decided before the first rename runs". A refusal raised mid-loop
leaves a half-installed repo behind and still says nothing was written;
`nothing was written` has to be a claim about the whole command, not about the
entry the refusal happened to land on.

A COLLISION withholds ITS file, not the roster. Both consumers adopting v0.23.0
had four hooks differing only inside the `project config` header the file
invites them to edit, so the two hooks that release ADDED — pure additions,
nothing in their way — could not be installed at all; the way through was
`--force` and then re-editing four files by hand. An entry with no destination
in the way is written, every collision is named, and the run still exits 1,
because a replacement was withheld and a caller that reads only the exit code
must not be told everything landed. A DEFECT still refuses the whole command
(see `main`): it is not a decision the operator made about that file.

A difference confined to the `project config` block is REPORTED as one — the
rest of that file is byte-current, so there is nothing in it to take and the
run needs no `--force` at all. The installer does not MERGE the block: `--force`
replaces the whole file, header included. Preserving a consumer's header under
a new body would write a file whose header is one version and whose body is
another, and this package's own history says what that costs. A guard hook
whose header gained two keys across two releases was measured with the OLD
header grafted onto the current body: four keys the body reads go unset, `set
-u` kills the hook on an unbound variable before it decides anything, and it
exits 1 — where only exit 2 is a BLOCK. The thing it guards goes through a
guard that is on disk, looks installed, and stops nothing. **A hook that fails
open is not a hook**, and a merge is how you get one without noticing.

The three refusal helpers below are shared with `pm install-skills`, the fourth
install verb this package ships. They live here rather than in a verb because
the wording is the contract: the collision sentence was written twice once, one
copy got the plural wrong, and the two refusals disagreed about the same
situation for a release.
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
        # The set both consumers actually run on a push, in the order they
        # fire: the full gate on every PR and mainline push, then the three
        # that guard the merge and the tag. Release, website and social
        # workflows are the PROJECT's — this verb does not write them and does
        # not know they exist.
        ('ci-verify.yml', '.github/workflows/verify.yml'),
        ('ci-semver-gate.yml', '.github/workflows/semver-gate.yml'),
        ('ci-auto-tag.yml', '.github/workflows/auto-tag.yml'),
    ),
    'install-agents': (
        # The verification pair first — the contract predates the roster and
        # is the pair devkit itself self-hosts. Then the base roster: the
        # generalized consumer agents, each with model/effort frontmatter
        # (the tiering table in SDLC.md) and a project-config
        # section the consumer edits after install, hook-corpus style.
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
        # The two ledger couriers. They GUARD nothing — they copy the stop
        # event's transcript path and ids into `pm ledger record` and exit 0 —
        # but they are hooks, they are standalone, and they carry the same
        # editable header, so they ship on the verb that already writes
        # tools/hooks/ and the script that already arms it by glob.
        ('cc-ledger-subagent.sh', 'tools/hooks/cc-ledger-subagent.sh'),
        ('cc-ledger-session.sh', 'tools/hooks/cc-ledger-session.sh'),
        ('pre-push', 'tools/hooks/pre-push'),
        ('prepare-commit-msg', 'tools/hooks/prepare-commit-msg'),
        ('agent-worktree.sh', 'tools/dev/agent-worktree.sh'),
        ('setup-hooks.sh', 'tools/setup-hooks.sh'),
    ),
    'install-gates': (
        # The library first, then the include that sources it. Two files and
        # neither is usable alone: `Makefile.devkit`'s `gdk_gate` define sources
        # `$(GDK_DEV_DIR)/gdk_gate.sh` on every gate recipe, and the library
        # publishes verdicts nothing would call without the targets. One verb,
        # one working `make`.
        #
        # What is NOT here is the point of the verb. Through 0.1.0 this plan
        # also carried twelve engine runners, and `Makefile.devkit` named their
        # targets in `precommit` and `milestone` — the gate framework and one
        # language's roster in one file, which is what blocked the split of this
        # package in two. The framework now composes from `GDK_PRECOMMIT_TIERS`
        # and `GDK_MILESTONE_TIERS`, set by a `Makefile.tiers` a LANGUAGE kit
        # installs. A project that builds nothing gets a working `check`,
        # `precommit` and `milestone` from this verb alone.
        ('gdk_gate.sh', 'tools/dev/gdk_gate.sh'),
        ('Makefile.devkit', 'Makefile.devkit'),
    ),
    'install-sdlc': (
        # The one plan entry whose body is RENDERED rather than copied. The
        # source name is the template the renderer fills; `resolve_body` is
        # the seam, and `body_of` stays exactly what its docstring says it is.
        ('sdlc-template.md', 'docs/sdlc-protocol.md'),
    ),
}

# Destinations whose body is PRODUCED rather than read verbatim. Keyed by
# DESTINATION, not by source, because the thing being produced is the file the
# consumer ends up with.
#
# `body_of` is verbatim by contract — "no substitution and no template" — and
# every static verb depends on that being literally true. So the resolver is a
# separate function and `body_of` is not weakened: a generated body names a
# PRODUCER here, and a static one never reaches this table at all.
#
# The producer is imported lazily. `conveyor.sdlc_doc` reads devkit.toml and
# imports the step registry; binding it at module import would make every
# install verb pay for the one that needs it, and would put a config read on
# the import path of a module that must be importable in a repo with no config.
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
install-sdlc    docs/sdlc-protocol.md — YOUR release protocol, rendered from
                `[release] steps` (and `[adopt] steps`) in your devkit.toml
                and from the registry that walks them. It is the document for
                the list `agentic-sdlc release` actually runs, so it cannot
                drift from it: change the config, re-run this verb. The only
                install verb whose body is GENERATED rather than copied.
A destination that already exists and differs is REFUSED — that file, not the
roster: the entries with nothing in their way are written, every collision is
named, and the run exits 1 because a replacement was withheld. A difference
confined to the `project config` header is reported as one, and the rest of
that file is byte-current, so it needs no --force. --force overwrites the whole
file, header included. --diff prints what would change and writes nothing."""

# A `.sh` installable is WRITTEN EXECUTABLE. Every one of them is a script a
# caller runs — a make recipe, a hook dispatcher, another runner's fan-out —
# and a script that is not executable is a file that looks installed and is
# not. `integration.sh` exec'd `scenario.sh` directly and got exit 126 from
# every scenario on every `init`'d project, under a FAILURES block that printed
# nothing, because `Permission denied` matched no summary pattern.
#
# The mode is part of the WRITE, in `core.apply`, which owns every mutation
# this package makes. It is not a post-pass: a chmod outside the plan is the
# decide-as-you-go shape that module exists to remove.
#
# The extension-less git hooks (`pre-push`, `prepare-commit-msg`) are still
# armed by `tools/setup-hooks.sh`, because arming one is also pointing
# `core.hooksPath` at the directory — one act, one owner, and it ships in the
# same install.
EXECUTABLE_SUFFIX = '.sh'


def _is_executable(target: Path) -> bool:
    """Whether `target` already carries an execute bit for anyone."""
    try:
        return bool(target.stat().st_mode & 0o111)
    except OSError:
        return False


# Installing tools/hooks/* is not arming them: core.hooksPath silently skips a
# non-executable hook, and pointing git at the directory is the other half of
# the same act. The script that does both is in the same install.
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
                    'installed file you do not edit. Its ordered lists come '
                    'from `[release] steps` in devkit.toml and from the step '
                    'registry that walks them, so the way to change the '
                    'protocol is to change the config (or a step) and re-run '
                    'this verb with --force. Link to it from your own SDLC '
                    'document rather than restating the steps there: a second '
                    'copy of an ordered list is the drift this verb exists to '
                    'end. Then run `agentic-sdlc release <version>` — it '
                    'stops at the first step whose postcondition is not true '
                    'and says what would make it true. Steps that need a tool '
                    'this package will never ship (a GitHub client, your '
                    'artifact proof) are yours to name in '
                    '`[release.commands]`; with none they refuse to advance '
                    'rather than pass.',
}

# The `.claude/settings.json` entries that FIRE the Claude Code half of the
# corpus. `tools/setup-hooks.sh` arms the GIT hooks — `core.hooksPath` plus the
# exec bit — and there is no equivalent for a Claude Code hook: it runs because
# a settings file names it, and nothing else. So an install that wrote the
# files and said nothing else left every guard on disk and none of them armed.
#
# PRINTED, not written. `.claude/settings.json` is a hand-maintained file with
# permissions, env and MCP entries this package knows nothing about, and the
# install verbs write a whole file or refuse — there is no merge here and there
# is deliberately not going to be one. Copying a block is the operator's edit
# to their own file.
#
# The two ledger couriers are `"async": true` because they are the only entries
# here that do WORK rather than decide: the verb parses a transcript that can
# be tens of megabytes (D4), and an orchestrator that waits for that on every
# stop pays the cost the async flag exists to remove. The four guards are
# synchronous on purpose — a PreToolUse block that arrived after the tool ran
# would be narration, and cc-stop-gate's exit 2 IS the gate.
#
# `SubagentStop` takes a matcher (on `agent_type`) and `Stop` takes none;
# cc-ledger-subagent.sh is registered with NO matcher, because every dispatch
# costs something and a roster written here would silently stop measuring the
# day a repo adds an agent.
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

# Only `install-hooks` has a registration step; the other three verbs' files
# are found by a path (a workflow directory, an agents directory, a make
# include) rather than by a settings entry.
_SETTINGS_BLOCK = {'install-hooks': _HOOK_SETTINGS}


# The per-entry annotation for a collision confined to the editable block.
# Short, because it hangs off a path in a list; the sentence that says what it
# MEANS is printed once, below the list.
HEADER_ONLY_NOTE = '   (project-config header only)'


def collision_refusal(collisions: list[str],
                      wrote: list[str] | None = None,
                      header_only: tuple[str, ...] | list[str] = (),
                      ) -> tuple[str, str]:
    """(what collided, what that means) — plural-correct, for any install verb.

    Two sentences rather than one string because the callers frame them
    differently: this module prefixes each line with `agentic-sdlc <command>:`,
    while the pm CLI raises them as one `Refused`.

    `wrote` is what the SAME run landed, and it changes the second sentence
    only. `nothing was written` is a claim about the disk, so it has to be
    checked rather than asserted: an install verb writes the entries with
    nothing in their way even when a neighbour collides. A caller that passes
    nothing gets the all-or-nothing sentence, which is what `pm install-skills`
    still is.

    `header_only` names the subset whose difference is confined to the editable
    `project config` block. That is a different message, not a softer one: the
    rest of those files is byte-current, so the repair is to do NOTHING rather
    than to force and re-edit — and the sentence says out loud that `--force`
    would take the header too, because it would.
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

# The wording this verb's refusals have always used, mapped from the closed
# `Obstruction` vocabulary `core.apply` decides in. A dict, not a sentence
# built at the call site: the check lives in one place and the phrasing lives
# in one place, and neither has to know the other's business.
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
    """'' when `target` can be written, else what stands in the way — decided
    WITHOUT writing a byte.

    The all-or-nothing property used to cover collisions only, so every other
    way a write can fail arrived as a traceback, and two of them arrived AFTER
    the first file had already been written: a destination that is a directory,
    a destination that is read-only, a parent path that is a file. A stack trace
    is not a refusal — it names no repair, and its "nothing was written" is a
    claim nobody made.

    This function used to BE those checks. It is now a caller: `core.apply`
    decides, in the same closed vocabulary every other writer in this package
    is decided in, and this maps the reason to the sentence four install verbs
    already print. A second copy of "can this be written" is a second chance to
    answer it differently.

    SYMLINKS ARE FOLLOWED here, said out loud rather than left to a default: an
    install destination is an ordinary repo file, and a project that symlinks
    `.claude/agents/` somewhere deliberate is exercising a choice this tool has
    no business overriding. The scaffolder declares the opposite, because a
    symlinked grain slot points OUT of the grain it was asked to fill.

    Not a substitute for handling the write's own OSError: a permission can
    change between this call and the write, and TOCTOU is exactly the case that
    must still not traceback. This is what turns the common cases into a
    sentence naming the path.
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
    """(the file's text, or None when it is not ours to compare; a defect).

    A destination this cannot DECODE cannot be compared with an installable,
    which is text — so it is treated as a collision rather than as an error,
    and `--force` overwrites it the same way it overwrites any other differing
    file. An unreadable one (permissions, a race) is a defect: a collision
    check that silently skipped it would clobber whatever is there.
    """
    try:
        return target.read_text(encoding='utf-8'), ''
    except UnicodeDecodeError:
        return None, ''
    except OSError as err:
        return None, f'cannot be read ({err.strerror or err})'


# The editable `project config` block, in the two spellings the installables
# use: a shell file opens it with a rule comment and closes with another, a
# markdown one opens it with a heading and closes at the next heading. Both
# ends are markers the source ships and the consumer keeps — an edit that
# takes one out is an edit this cannot locate, and it says so by declining to
# classify rather than by guessing where the block ended.
_BLOCK_GRAMMARS = (
    ('--- project config (yours to edit after install',
     re.compile(r'^#\s*-{5,}\s*$')),
    ('## Project config (yours to edit after install)',
     re.compile(r'^## ')),
)


def config_block_span(text: str) -> tuple[int, int] | None:
    """The half-open LINE range of `text`'s editable project-config block, or
    None when it carries none this can locate.

    The first opening marker wins and the first closing marker after it ends
    the block; an opened block with no closing marker runs to the end of the
    file. The marker lines themselves are OUTSIDE the span — a consumer who
    edited one has changed something the installable owns, and that has to
    read as a plain difference.

    Locating LESS than is there is the safe direction and the only direction
    this is allowed to be wrong in: the one caller asks whether a difference
    is confined to the span, so a span that is too small can only answer "no".
    """
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
    """True when the two texts differ ONLY inside the project-config block —
    the header the installable invites the consumer to edit.

    Decided by DELETING both blocks and comparing what is left, byte for byte,
    rather than by aligning the two files: an alignment is free to pair a line
    inside one block with an identical line outside the other, and a predicate
    whose True means "the rest of your file is byte-current" must not be able
    to reach that answer through a coincidence. Everything outside the two
    blocks is identical here, or this is False.

    False whenever either side carries no block this can locate. A consumer who
    moved or rewrote the markers gets the plain collision — the honest answer
    about a file whose shape this can no longer read.
    """
    mine = config_block_span(existing)
    theirs = config_block_span(body)
    if mine is None or theirs is None:
        return False
    return _outside_block(existing, mine) == _outside_block(body, theirs)


def _outside_block(text: str, span: tuple[int, int]) -> list[str]:
    # keepends, so a difference that is only a trailing newline is still a
    # difference: `splitlines()` renders 'x' and 'x\n' as the same one line.
    lines = text.splitlines(keepends=True)
    return lines[:span[0]] + lines[span[1]:]


def body_of(name: str) -> str:
    """One installable, verbatim. There is no substitution and no template."""
    return resources.files(PACKAGE).joinpath(name).read_text(encoding='utf-8')


def resolve_body(name: str, rel: str) -> str:
    """What this plan entry WRITES: `body_of(name)`, or the producer's output.

    The seam, and deliberately a separate function from `body_of`. A resolver
    folded into `body_of` would make "verbatim, no substitution, no template"
    false of the four static verbs that depend on it being true — and the day
    it is false somewhere is the day nobody can tell which files a `--diff` is
    honest about.
    """
    producer = BODIES.get(rel)
    if producer is None:
        return body_of(name)
    module_name, function = producer.split(':')
    from importlib import import_module
    return getattr(import_module(module_name), function)()


def print_diff(rel: str, target: Path, body: str) -> None:
    """What an install WOULD change, as a unified diff. Writes nothing."""
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
            # Said BEFORE the hunks, because it is the answer: the hunks below
            # are the operator's own header and the rest of the file is
            # byte-current, so this file has nothing in it to take.
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
    """One install verb. `next_step=False` silences the closing paragraph.

    `init` composes all four of these and then DOES most of what those
    paragraphs ask for — writes the two-line Makefile, gitignores the run
    artifacts, runs setup-hooks.sh. Printed there, they would send an operator
    to wire what the same command just wired, and a report whose instructions
    are already stale is a report nobody finishes reading. Init prints its own,
    covering the residue that still applies.
    """
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
        # A generated body reads the project's own config, and a bad value
        # there is exit 2 — a typo is not a finding. Raised BEFORE the plan is
        # decided, so nothing was written.
        print(f'agentic-sdlc {command}: {err}', file=sys.stderr)
        return 2

    # --diff reads and prints. It is never combined with a write, so it is
    # answered before the plan is decided rather than inside it.
    if diff:
        for target, rel, body in entries:
            print_diff(rel, target, body)
        return 0

    # Decide the WHOLE plan first — resolve every destination, collect every
    # collision — and touch nothing until it holds.
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
                # Right bytes, missing execute bit. Not `current`: the file a
                # consumer installed before this package wrote the mode is
                # exactly the broken one, and reporting it current would leave
                # it broken forever. Rewritten (same bytes) so the ONE writer
                # sets the mode, and idempotent — the next run finds it right.
                pass
            elif not force:
                collisions.append(rel)
                # `existing` is None for a destination this cannot decode, and
                # a file with no text has no block to confine anything to.
                if existing is not None and header_only_difference(existing,
                                                                   body):
                    header_only.append(rel)
                continue
        plan.append((kind, target, rel, body))

    # A DEFECT refuses the whole command, the additions with it. It is not a
    # decision the operator made about that file the way a collision is — it is
    # a destination the command cannot write at all, its repair is the same for
    # every entry (fix the path, re-run), and nothing has been written yet, so
    # `nothing was written` is still true at the moment it is printed. The
    # collisions are named first when a run has both, because that is the
    # refusal a human is most likely to hit and the one --force answers.
    if defects:
        if collisions:
            head, tail = collision_refusal(collisions,
                                           header_only=header_only)
            print(f'agentic-sdlc {command}: {head}\n'
                  f'agentic-sdlc {command}: {tail}', file=sys.stderr)
        print(_defect_refusal(command, defects, []), file=sys.stderr)
        return 1

    # ONE plan, decided above and applied here. `install-agents` half-installed
    # twice because the loop that wrote also decided: the third file's problem
    # arrived with the first two already on disk. `core.apply` returns what
    # LANDED, so the refusal below names it instead of guessing.
    writes = apply.Plan()
    for kind, target, rel, body in plan:
        if kind != 'current':
            writes.overwrite(target, body, newline=None, label=rel,
                             executable=rel.endswith(EXECUTABLE_SUFFIX))
    # Everything answerable was answered above, so a failure here means the
    # filesystem changed under the plan. It is still a refusal that names what
    # it did — never a traceback, and never a silent "nothing was written" over
    # a directory that already has one.
    result = writes.apply(decide=False)
    written = [step.label for step in result.landed]
    landed = set(written)
    # Reported in PLAN order, and STOPPING where the plan stopped: a line
    # printed past the failure would describe a file that was never reached.
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
    # After the writes, and named against what actually landed: a collision
    # withholds ITS file, so the sentence about the disk has to be built from
    # the disk. Before the next-step paragraph, so the pasteable settings block
    # stays the last thing on stdout.
    if collisions:
        head, tail = collision_refusal(collisions, wrote=written,
                                       header_only=header_only)
        print(f'agentic-sdlc {command}: {head}\n'
              f'agentic-sdlc {command}: {tail}', file=sys.stderr)
    if written and next_step:
        print(f'[install] {_NEXT_STEP[command]}')
        settings = _SETTINGS_BLOCK.get(command)
        if settings:
            # Raw, unprefixed, so the block can be selected and pasted whole.
            # A `[install] ` on every line would make the operator strip it,
            # and a JSON file is the one place a stray prefix is not a cosmetic
            # problem.
            print(f'\n.claude/settings.json — the entries that FIRE these '
                  f'hooks (merge into yours):\n\n{settings}\n')
    # A withheld replacement is a non-zero exit even when additions landed: a
    # caller that reads the code alone must never be told the roster is on disk
    # when one of it is the operator's own file.
    return 1 if collisions else 0
