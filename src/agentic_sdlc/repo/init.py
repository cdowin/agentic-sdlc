"""`agentic-sdlc init`: a repo wired for this toolkit, in one command.

Composes the install verbs in order plus the seeds nobody else writes (devkit.toml,
Makefile, CLAUDE.md, .gitignore). Installed files are devkit-owned and `--force`
overwrites them; the seeds and the PM tree are project-owned from the first write and
`--force` never touches them. Each verb lands or refuses whole; init runs every one
and reports each refusal rather than stopping at the first.
"""
from __future__ import annotations

import sys
from pathlib import Path

from agentic_sdlc import __version__
from agentic_sdlc.core import apply, spawn
from agentic_sdlc.core.project import repo_root
from agentic_sdlc.repo import install

VERSION_PLACEHOLDER = '{version}'

# (installable, destination): the project-owned seeds, written once and never forced.
SEED_CONFIG = ('project-devkit.toml', 'devkit.toml')
SEED_MAKEFILE = ('project-Makefile', 'Makefile')
SEED_CLAUDE = ('project-CLAUDE.md', 'CLAUDE.md')
SEEDS = (SEED_CONFIG, SEED_MAKEFILE, SEED_CLAUDE)

GIT_DIR = '.git'

GITIGNORE = '.gitignore'
GITIGNORE_HEADER = '# agentic-sdlc run artifacts (agentic-sdlc init)'
# Every run artifact this package writes; a test pins each to the constant that owns it,
# because an unignored artifact falsifies `tree-clean`.
IGNORED = (
    '.gate-reports/',       # GDK_GATE_REPORT_DIR      (gdk_gate.sh)
    '.agent-scope',         # SCOPE_MARKER             (agent-worktree.sh)
    '.claude/worktrees/',   # WORKTREE_PARENT          (agent-worktree.sh)
)

SETUP_HOOKS = 'tools/setup-hooks.sh'

# The order is init's contribution; a dict's insertion order is not a contract.
VERBS = ('install-gates', 'install-hooks', 'install-agents', 'install-sdlc',
         'install-ci')

USAGE = """usage: agentic-sdlc init [--force] [--diff]

Stand a repo up on this toolkit. Writes, in order:

  devkit.toml        every [section] the gates read, commented at its default
  pm/roadmap/        the PM tree, plus the execution rule and the operations
                     skill (`pm init`)
  Makefile           two lines — the DEVKIT_VERSION pin, and the include
  Makefile.devkit    the standard target set, plus the gate library it
  + tools/dev/       sources                          (`install-gates`)
  tools/hooks/       the guard corpus, then `bash tools/setup-hooks.sh` to arm
                     it                               (`install-hooks`)
  .claude/agents/    the review/build contract + the base roster
                                                      (`install-agents`)
  docs/              the SDLC protocol, rendered from your step lists
                                                      (`install-sdlc`)
  .github/workflows/ verify, semver-gate, auto-tag      (`install-ci`)
  .gitignore         the run-artifact directories, appended if absent
  CLAUDE.md          a skeleton naming the standard targets + installed rules

The one file it does NOT write is `.claude/settings.json`: registering the
hooks with a harness is the step this package offers and never takes by
default. The run prints the block and names the file it belongs in.

Run it again any time: it fills what is missing and reports the rest.
--diff  prints what a run would change, per file, and writes nothing.
--force overwrites the DEVKIT-owned files (the installables). devkit.toml,
        Makefile, CLAUDE.md and the PM tree are the project's from the first
        write, and --force does not touch them.

Refuses, before writing anything: a root that is not a git repository."""


def seed_body(name: str) -> str:
    """One seed's text, with the pin substituted."""
    return install.body_of(name).replace(VERSION_PLACEHOLDER, f'v{__version__}')


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
    body = seed_body(name)
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
        else:
            _say(f'{rel} is yours — left alone (it differs from the template; '
                 f'`agentic-sdlc init --diff` shows how)')
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
    return skills.cmd_install_skills(cfg, [])


def _pm_config():
    from agentic_sdlc.repo.pm import vocabulary
    return vocabulary.load()


def _diff(root: Path) -> int:
    """What a run would change, per file, in run order, writing nothing."""
    from agentic_sdlc.repo.pm import skills
    install.print_diff(SEED_CONFIG[1], root / SEED_CONFIG[1],
                       seed_body(SEED_CONFIG[0]))
    skills.cmd_install_skills(_pm_config(), ['--diff'])
    install.print_diff(SEED_MAKEFILE[1], root / SEED_MAKEFILE[1],
                       seed_body(SEED_MAKEFILE[0]))
    for command in VERBS:
        install.main(command, ['--diff'], next_step=False)
    missing = _gitignore_missing(root)
    print(f'[install] {GITIGNORE} '
          + (f'is missing {" ".join(missing)}' if missing
             else 'already ignores the run artifacts'))
    install.print_diff(SEED_CLAUDE[1], root / SEED_CLAUDE[1],
                       seed_body(SEED_CLAUDE[0]))
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
             f'Makefile, CLAUDE.md or the PM tree).')
        return worst
    if worst != 0:
        _say('finished with the problem(s) named above; everything else was '
             'written. The command is idempotent — fix those and re-run.')
        return worst
    _say(f'agentic-sdlc v{__version__} — this project is wired. Next:')
    print()
    print('  1. `git add -A` — FIRST. Every gate here reads `git ls-files`, '
          'so until')
    print('     these files are tracked they are invisible to the tools that '
          'just wrote')
    print('     them, and `check shell` correctly reports it scanned nothing.')
    print('  2. `make help` — the standard target set, plus any of your own.')
    print('  3. Edit CLAUDE.md and devkit.toml. They are yours now: the '
          'skeleton says where')
    print('     your own facts go, and every gate roster and scope lives in '
          'devkit.toml.')
    print('  4. Every file under .claude/agents/ and tools/ opens with a '
          'project-config')
    print('     section carrying stock values — edit them to your spellings.')
    print('  5. .github/workflows/: semver-gate.yml and auto-tag.yml name '
          'their branches')
    print('     literally (an `on:` filter takes no variable) and read your '
          'version through')
    print('     VERSION_FILE/VERSION_PATTERN at the head of each file. '
          'auto-tag.yml dispatches')
    print('     RELEASE_WORKFLOW — leave that alone if you have no release '
          'pipeline; the')
    print('     step is a no-op then.')
    print('  6. Your language kit installs Makefile.tiers, which is where '
          '`make precommit`')
    print('     and `make milestone` get their tiers. Without one they are '
          '`check` alone,')
    print('     and they say so.')
    print('  7. `agentic-sdlc pm new milestone first-light "First Milestone" '
          '--version 0.1`')
    print('     (it mints the id `ms-first-light` — the kind prefix and your '
          'slug — and')
    print('     stamps `version: 0.1`), then `agentic-sdlc check pm`.')
    print(f'  8. The hooks are on disk and NOT registered: a harness runs them '
          f'because')
    print(f'     {install.AGENT_SETTINGS} names them, and nothing else does. '
          f'The block is')
    print(f'     below — `agentic-sdlc install-hooks {install.SETTINGS_FLAG}` '
          f'lands it in this')
    print('     tree, or paste it into whatever settings file your harness '
          'reads.')
    # Last on stdout, so the block stays pasteable whole. Registering the
    # hooks with a harness is the one step `init` cannot take, and naming
    # neither file nor fragment left a consumer with nothing to take it.
    install.settings_step(root, False)
    return 0
