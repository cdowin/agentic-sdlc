"""`agentic-sdlc init`: a repo wired for this toolkit, in one command.

Composes the install verbs in order plus the seeds nobody else writes (devkit.toml,
Makefile, pyproject.toml, CLAUDE.md, .gitignore). Installed files are devkit-owned and `--force`
overwrites them; the seeds and the PM tree are project-owned from the first write and
`--force` never touches them. Each verb lands or refuses whole; init runs every one
and reports each refusal rather than stopping at the first.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from agentic_sdlc import __version__
from agentic_sdlc.core import apply, spawn
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.repo import install, vehicle

VERSION_PLACEHOLDER = '{version}'
PROJECT_PLACEHOLDER = '{project}'

# (installable, destination): the project-owned seeds, written once and never forced.
SEED_CONFIG = ('project-devkit.toml', 'devkit.toml')
SEED_MAKEFILE = ('project-Makefile', 'Makefile')
SEED_CLAUDE = ('project-CLAUDE.md', 'CLAUDE.md')
# Tooling only, and only where there is none: an existing pyproject.toml is the
# project's, and init names the `uv add` line for it instead (rule 3).
SEED_PYPROJECT = ('project-pyproject.toml', 'pyproject.toml')
SEEDS = (SEED_CONFIG, SEED_MAKEFILE, SEED_PYPROJECT, SEED_CLAUDE)

GIT_DIR = '.git'

GITIGNORE = '.gitignore'
GITIGNORE_HEADER = '# agentic-sdlc run artifacts (agentic-sdlc init)'
# Every run artifact this package writes; a test pins each to the constant that owns it,
# because an unignored artifact falsifies `tree-clean`.
IGNORED = (
    '.gate-reports/',       # GDK_GATE_REPORT_DIR      (gdk_gate.sh)
    '.agent-scope',         # SCOPE_MARKER             (agent-worktree.sh)
    '.claude/worktrees/',   # WORKTREE_PARENT          (agent-worktree.sh)
    '.venv/',               # GDK_VENV                 (Makefile.devkit)
)

SETUP_HOOKS = 'tools/setup-hooks.sh'

# The order is init's contribution; a dict's insertion order is not a contract.
VERBS = ('install-gates', 'install-hooks', 'install-agents', 'install-ci')

USAGE = """usage: agentic-sdlc init [--force] [--diff]

Stand a repo up on this toolkit. Writes, in order:

  devkit.toml        every [section] the gates read, commented at its default
  pm/roadmap/        the PM tree, plus the execution rule and the operations
                     skill (`pm init`)
  Makefile           one line — the include
  pyproject.toml     tooling only, pinning agentic-sdlc for uv.lock — written
                     when there is none; an existing one is left alone and
                     init prints the `uv add` line that pins the kit in it
  Makefile.devkit    the standard target set, plus the gate library it
  + tools/dev/       sources                          (`install-gates`)
  tools/hooks/       the guard corpus, then `bash tools/setup-hooks.sh` to arm
                     it                               (`install-hooks`)
  .claude/agents/    the review/build contract + the base roster
                                                      (`install-agents`)
  .github/workflows/ verify, semver-gate, auto-tag      (`install-ci`)
  .gitignore         the run-artifact directories, appended if absent
  CLAUDE.md          a skeleton naming the standard targets + installed rules

The one file it does NOT write is `.claude/settings.json`: registering the
hooks with a harness is the step this package offers and never takes by
default. The run prints the block and names the file it belongs in.

It ends with the loop a story takes, from `pm new` to `release`, spelled in
the states devkit.toml declares, and names `adopt` as the check of the setup.

Run it again any time: it fills what is missing and reports the rest.
--diff  prints what a run would change, per file, and writes nothing.
--force overwrites the DEVKIT-owned files (the installables). devkit.toml,
        Makefile, pyproject.toml, CLAUDE.md and the PM tree are the project's
        from the first write, and --force does not touch them.

Refuses, before writing anything: a root that is not a git repository."""


def project_name(root: Path) -> str:
    """The root directory's name as a PEP 508 name, for the pyproject seed."""
    return re.sub(r'[^a-z0-9]+', '-', root.name.lower()).strip('-') or 'project'


def seed_body(name: str, root: Path | None = None) -> str:
    """One seed's text, with the pin and the project's name substituted."""
    return (install.body_of(name)
            .replace(VERSION_PLACEHOLDER, __version__)
            .replace(PROJECT_PLACEHOLDER,
                     project_name(root) if root else 'project'))


def _pyproject_note(root: Path) -> str:
    """What an existing pyproject.toml gets instead of a write."""
    rel = SEED_PYPROJECT[1]
    locked = vehicle.locked_version(root)
    if locked is not None:
        return (f'{rel} is yours — left alone; {vehicle.LOCK_FILE} pins '
                f'{vehicle.PROGRAM} {locked}')
    return (f'{rel} is yours — left alone, and {vehicle.LOCK_FILE} names no '
            f'{vehicle.PROGRAM}, so `make` refuses until you run '
            f'`{vehicle.add_line()}` and add `{vehicle.EXPLICIT}` to the '
            f'`[[tool.uv.index]]` table it writes')


def _say(message: str) -> None:
    print(f'[init] {message}')


def _preflight(root: Path) -> str:
    """'' when this root can be initialized, else why it cannot."""
    if not (root / GIT_DIR).exists():
        return (f'{root} is not a git repository — every gate resolves its '
                f'scope through `git ls-files` (a 0-file census reddens each '
                f'of them), and {SETUP_HOOKS} has no git to point at the '
                f'installed hooks. Run `git init` first, then re-run here.')
    return ''


def _write_seed(root: Path, name: str, rel: str) -> int:
    """Write one project-owned seed; a differing seed is reported, not a collision."""
    target = root / rel
    body = seed_body(name, root)
    defect = install.destination_defect(target)
    if defect:
        print(f'agentic-sdlc init: {rel} {defect} — nothing was written to it',
              file=sys.stderr)
        return 1
    if target.is_file():
        existing, unreadable = install.read_destination(target)
        if unreadable:
            print(f'agentic-sdlc init: {rel} {unreadable}', file=sys.stderr)
            return 1
        if existing == body:
            _say(f'{rel} already current')
        elif (name, rel) == SEED_PYPROJECT:
            _say(_pyproject_note(root))
        else:
            # Pinned, not the vehicle: `init` writes `Makefile.devkit` (D2).
            _say(f'{rel} is yours — left alone (it differs from the template; '
                 f'`{vehicle.pinned("init", "--diff")}` shows how)')
        return 0
    result = apply.Plan().overwrite(target, body, newline=None,
                                    label=rel).apply(decide=False)
    if result.failed is not None:
        print(f'agentic-sdlc init: {rel} could not be written '
              f'({result.error})', file=sys.stderr)
        return 1
    _say(f'wrote {rel}')
    return 0


def _gitignore_missing(root: Path) -> list[str]:
    """The run-artifact entries `.gitignore` does not already carry."""
    target = root / GITIGNORE
    if not target.is_file():
        return list(IGNORED)
    text, _ = install.read_destination(target)
    if text is None:
        return list(IGNORED)
    present = {line.strip().lstrip('/').rstrip('/')
               for line in text.splitlines()}
    return [entry for entry in IGNORED if entry.rstrip('/') not in present]


def _write_gitignore(root: Path) -> int:
    """Append the missing entries: the one merge here, because every project has opinions in this file."""
    missing = _gitignore_missing(root)
    if not missing:
        _say(f'{GITIGNORE} already ignores the run artifacts')
        return 0
    target = root / GITIGNORE
    defect = install.destination_defect(target)
    if defect:
        print(f'agentic-sdlc init: {GITIGNORE} {defect}', file=sys.stderr)
        return 1
    existing = ''
    if target.is_file():
        text, unreadable = install.read_destination(target)
        if unreadable:
            print(f'agentic-sdlc init: {GITIGNORE} {unreadable}',
                  file=sys.stderr)
            return 1
        existing = text or ''
        if existing and not existing.endswith('\n'):
            existing += '\n'
        existing += '\n'
    block = GITIGNORE_HEADER + '\n' + ''.join(f'{entry}\n' for entry in missing)
    result = apply.Plan().overwrite(target, existing + block, newline=None,
                                    label=GITIGNORE).apply(decide=False)
    if result.failed is not None:
        print(f'agentic-sdlc init: {GITIGNORE} could not be written '
              f'({result.error})', file=sys.stderr)
        return 1
    _say(f'{"appended to" if existing else "wrote"} {GITIGNORE}: '
         f'{" ".join(missing)}')
    return 0


def _arm_hooks(root: Path) -> int:
    """Run the installed `setup-hooks.sh`; installing a hook is not arming it."""
    script = root / SETUP_HOOKS
    if not script.is_file():
        _say(f'{SETUP_HOOKS} is not present — the hooks were NOT armed')
        return 1
    done = spawn.run(['bash', str(script)], cwd=root,
                     capture_output=True, text=True)
    for line in done.stdout.splitlines():
        if line.strip():
            _say(line.strip())
    if done.returncode != 0:
        print(f'agentic-sdlc init: {SETUP_HOOKS} exited {done.returncode} — '
              f'the hooks are installed but NOT armed; run `bash '
              f'{SETUP_HOOKS}` yourself and read what it says\n'
              f'{done.stderr.strip()}', file=sys.stderr)
        return 1
    return 0


def _stand_up_pm_tree(cfg) -> int:
    """`pm init` minus its next-steps; a pre-existing devkit.toml gets the flow appended."""
    from agentic_sdlc.repo.pm import skills
    _say(skills.install_flow(cfg))
    for made in skills.stand_up_tree(cfg):
        _say(f'created {made}')
    # The gates this verb installs file rows into the local ledger, and the
    # hook it arms runs them on every commit: unignored, that commit leaves
    # its own tree dirty (#48).
    code = 0
    try:
        _say(skills.install_local_ignore(cfg))
    except skills.Refused as err:
        print(f'agentic-sdlc init: {err}', file=sys.stderr)
        code = 1
    return max(code, skills.cmd_install_skills(cfg, []))


def _pm_config():
    from agentic_sdlc.repo.pm import vocabulary
    return vocabulary.load()


def loop_lines(flow, spot: str) -> list[str]:
    """The loop a story takes, each step the command a consumer types.

    `flow` is the story's declared flow: the move is its first `in_progress`
    state and the close its first `done` state — the one `integrate` writes.
    `spot` is the `[verify] spot` rung, '' when undeclared. Nothing here
    spells a state word (rule 9); a category the tree leaves empty is named.
    """
    from agentic_sdlc.repo.pm import vocabulary
    kind = vocabulary.GRAIN_STORY
    sid = vehicle.Slot(f'<{kind}-id>')

    def first(category: str) -> str:
        return (flow.by_category.get(category) or ('',))[0]

    moving, closing = first(vocabulary.IN_PROGRESS), first(
        vocabulary.DONE_CATEGORY)
    new = vehicle.command('pm', 'new', kind, vehicle.Slot('<feature-id>'),
                          vehicle.Slot('<slug>'), vehicle.Slot('<name...>'))
    move = (f'`{vehicle.command("pm", kind, moving, sid)}` moves it into work.'
            if moving else
            f'[pm.states.{kind}] declares no {vocabulary.IN_PROGRESS} state, '
            f'so a {kind} has no move into work.')
    rung = (f'`{spot}`' if spot else
            'which this devkit.toml does not declare yet')
    close = (f'and writes `{closing}`.' if closing else
             f'and has no state to write: [pm.states.{kind}] declares no '
             f'{vocabulary.DONE_CATEGORY} state.')
    return [
        f'[init] The loop, in the states devkit.toml declares for a {kind}:',
        f'  1. `{new}` creates it.',
        f'  2. {move}',
        f'  3. `{vehicle.command("dispatch", "--grain", sid)}` prints the '
        f'builder\'s brief.',
        f'  4. `{vehicle.command("verify", "--spot")}` is the builder\'s check '
        f'after each edit:',
        f'     [verify] spot, {rung}.',
        f'  5. `{vehicle.command("integrate", vehicle.Slot("<slug>..."))}` '
        f'merges the lanes, proves them once,',
        f'     {close}',
        f'  6. `{vehicle.command("release", vehicle.Slot("<version>"))}` '
        f'closes the milestone.',
        f'  Check the whole setup with '
        f'`{vehicle.command("adopt", vehicle.Slot("<version>"))}`.',
    ]


def _print_loop() -> int:
    """The loop, read from the devkit.toml this run wrote or kept."""
    from agentic_sdlc.core.config import (ConfigError, config_section,
                                          section_declared)
    from agentic_sdlc.repo.pm import vocabulary
    from agentic_sdlc.repo.verify import rules
    try:
        # `reload`: this run may have appended the flow after the first read.
        flow = vocabulary.flow_of(vocabulary.reload(), vocabulary.GRAIN_STORY)
        spot = (rules.read(config_section(rules.SECTION)).rung(rules.SPOT)
                if section_declared(rules.SECTION) else '')
    except ConfigError as err:
        print(f'agentic-sdlc init: the loop is not printed — {err}',
              file=sys.stderr)
        return 2
    for line in loop_lines(flow, spot or ''):
        print(line)
    return 0


def _diff(root: Path) -> int:
    """What a run would change, per file, in run order, writing nothing."""
    from agentic_sdlc.repo.pm import skills
    install.print_diff(SEED_CONFIG[1], root / SEED_CONFIG[1],
                       seed_body(SEED_CONFIG[0], root))
    skills.cmd_install_skills(_pm_config(), ['--diff'])
    install.print_diff(SEED_MAKEFILE[1], root / SEED_MAKEFILE[1],
                       seed_body(SEED_MAKEFILE[0], root))
    if (root / SEED_PYPROJECT[1]).exists():
        print(f'[install] {_pyproject_note(root)}')
    else:
        install.print_diff(SEED_PYPROJECT[1], root / SEED_PYPROJECT[1],
                           seed_body(SEED_PYPROJECT[0], root))
    for command in VERBS:
        install.main(command, ['--diff'], next_step=False)
    missing = _gitignore_missing(root)
    print(f'[install] {GITIGNORE} '
          + (f'is missing {" ".join(missing)}' if missing
             else 'already ignores the run artifacts'))
    text, _ = (install.read_destination(root / GITIGNORE)
               if (root / GITIGNORE).is_file() else ('', ''))
    # Every line `install_local_ignore` appends, one report each.
    for local in skills.local_ignore_lines(_pm_config().roadmap_dir):
        print(f'[install] {GITIGNORE} '
              + ('already ignores' if skills.ignores_local(text or '', local)
                 else 'is missing') + f' {local}')
    install.print_diff(SEED_CLAUDE[1], root / SEED_CLAUDE[1],
                       seed_body(SEED_CLAUDE[0], root))
    return 0


def main(argv: list[str]) -> int:
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
            print(f'agentic-sdlc init: unknown flag {arg!r}', file=sys.stderr)
            print(USAGE, file=sys.stderr)
            return 2

    root = repo_root()
    blocked = _preflight(root)
    if blocked:
        print(f'agentic-sdlc init: {blocked}', file=sys.stderr)
        print('agentic-sdlc init: nothing was written.', file=sys.stderr)
        return 2

    if diff:
        return _diff(root)

    passthrough = ['--force'] if force else []
    refused: list[str] = []
    worst = 0

    worst = max(worst, _write_seed(root, *SEED_CONFIG))
    worst = max(worst, _stand_up_pm_tree(_pm_config()))
    worst = max(worst, _write_seed(root, *SEED_MAKEFILE))
    worst = max(worst, _write_seed(root, *SEED_PYPROJECT))
    for command in VERBS:
        code = install.main(command, list(passthrough), next_step=False)
        if code != 0:
            refused.append(command)
        worst = max(worst, code)
        if command == 'install-hooks':
            worst = max(worst, _arm_hooks(root))
    worst = max(worst, _write_gitignore(root))
    worst = max(worst, _write_seed(root, *SEED_CLAUDE))

    print()
    if refused:
        _say(f'REFUSED by {", ".join(refused)} — each names the file(s) it '
             f'would not overwrite. Move yours aside, or re-run with --force '
             f'(which touches the installed files only, never devkit.toml, '
             f'Makefile, pyproject.toml, CLAUDE.md or the PM tree).')
        return worst
    if worst != 0:
        _say('finished with the problem(s) named above; everything else was '
             'written. The command is idempotent — fix those and re-run.')
        return worst
    _say(f'agentic-sdlc v{__version__} — this project is wired. Next:')
    print()
    print('  1. `uv sync` — writes uv.lock and installs the kit it pins into '
          '.venv. `make`')
    print('     runs .venv/bin/agentic-sdlc and refuses while uv.lock does '
          'not name it.')
    print('  2. `git add -A` — before any gate. Every gate here reads `git '
          'ls-files`, so')
    print('     until these files are tracked they are invisible to the tools '
          'that just')
    print('     wrote them, and `check shell` correctly reports it scanned '
          'nothing.')
    print('     Commit uv.lock with them: it is the pin.')
    print('  3. `make help` — the standard target set, plus any of your own.')
    print('  4. Edit CLAUDE.md and devkit.toml. They are yours now: the '
          'skeleton says where')
    print('     your own facts go, and every gate roster and scope lives in '
          'devkit.toml.')
    print('  5. Every file under .claude/agents/ and tools/ opens with a '
          'project-config')
    print('     section carrying stock values — edit them to your spellings.')
    print('  6. .github/workflows/: semver-gate.yml and auto-tag.yml name '
          'their branches')
    print('     literally (an `on:` filter takes no variable) and read your '
          'version through')
    print('     VERSION_FILE/VERSION_PATTERN at the head of each file. '
          'auto-tag.yml dispatches')
    print('     RELEASE_WORKFLOW — leave that alone if you have no release '
          'pipeline; the')
    print('     step is a no-op then.')
    print('  7. Your language kit installs Makefile.tiers, which is where '
          '`make precommit`')
    print('     and `make milestone` get their tiers. Without one they are '
          '`check` alone,')
    print('     and they say so.')
    # Through the vehicle: `init` has just written the `Makefile.devkit` it
    # lives in. `pm init` prints the same line.
    from agentic_sdlc.repo.pm.skills import FIRST_MILESTONE
    print(f'  8. `{FIRST_MILESTONE[0]}`')
    print('     (it mints the id `ms-first-light` — the kind prefix and your '
          'slug — and')
    print(f'     stamps `version: 0.1`), then '
          f'`{vehicle.command("check", "pm")}`.')
    print('  9. The hooks are on disk and NOT registered: a harness runs them '
          'because')
    print(f'     {install.AGENT_SETTINGS} names them, and nothing else does. '
          f'The block is')
    print(f'     below — '
          f'`{vehicle.command("install-hooks", install.SETTINGS_FLAG)}` '
          f'lands it in this')
    print('     tree, or paste it into whatever settings file your harness '
          'reads.')
    # Unprefixed between blank lines, so the block stays pasteable whole.
    # Registering the hooks with a harness is the one step `init` cannot
    # take, and naming neither file nor fragment left a consumer with
    # nothing to take it.
    install.settings_step(root, False)
    # Last: what a consumer does next, every day, once the tree stands.
    return _print_loop()
