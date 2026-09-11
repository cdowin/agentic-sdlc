"""test_boundaries.py — the two primitives, enforced by AST rather than by memory.

A day of review found ~25 defects in this package that were three bugs in
eighteen places. Two of the three are shapes, not incidents:

  * something silently leaves a census (~6x), and
  * a write is not all-or-nothing (~6x).

Every fix before this file was an INSTANCE — one filter taught to report
itself, one writer given a pre-pass — so the next feature reintroduced the
shape somewhere new. Fixing grain detection literally created a new narrowing
via dotted names, because the fix was a filter and nothing made filters
disclose.

`core/walk.py` and `core/apply.py` make each shape impossible to express. THIS
FILE makes them impossible to route around. Both tests are exact module
ALLOWLISTS, not patterns: a new gate that enumerates directly, or a new verb
that writes directly, breaks the build and is named by `file:line`.

Deliberately AST, not grep: `subprocess.run(['git', 'mv', ...])` is not a
`Path.rename`, a string `'rglob'` in a docstring is not a call, and a grep
cannot tell those apart. An AST walk decides from the syntax, with no inference
and nothing to tune.

**Every guard here declares `CORPUS` and `catches()`, and a new one must.**
`tests/test_guard_corpus.py` replays each corpus and names any AST-shaped guard
that declares none: the classifiers below all assert an EMPTY offender list,
and a reader that stopped reading returns one too.
"""
from __future__ import annotations

import ast
import re
import tomllib
import unittest
from collections.abc import Iterable
from pathlib import Path

# The derivation that puts the `shell` mark on a spawning module. Imported
# rather than re-implemented: primitive 5 below holds `repo/emit.py` to the
# SAME no-subprocess question the tier definition is built on, and two
# spellings of one question is how they drift apart. Since primitive 11 that
# question is necessary and NOT sufficient — one module in `src/` imports
# `subprocess`, so it answers False everywhere else whatever the file does —
# and primitive 5 asks it beside the reach to the seam, never instead of it.
from conftest import module_spawns
from support import REPO_ROOT

SRC = REPO_ROOT / 'src' / 'agentic_sdlc'
# Both allowlists assert an EMPTY offender list, so both pass perfectly on a
# census of zero files — which is what a moved/renamed SRC produces. Rule 4 says
# a gate scanning nothing must say so, and these are gates. The floor is well
# under the real count (48 at the time of writing) and well over zero: it is
# there to catch a broken root, not to track the module count.
MIN_SOURCES = 20

# --- primitive 1: one walk ----------------------------------------------------
# The exact module that owns filesystem ENUMERATION. Not a package, not a
# prefix — one file.
WALK_MODULE = 'core/walk.py'
# Attribute calls that ENUMERATE. `Path.walk` is 3.12+, banned here so the two
# spellings of `os.walk` cannot split the ownership between interpreters.
ENUMERATORS = ('glob', 'rglob', 'iterdir', 'walk', 'scandir', 'listdir')
# --- primitive 2: one apply ---------------------------------------------------
APPLY_MODULE = 'core/apply.py'
# Path methods that mutate and CANNOT be anything else at the syntax level.
# `.replace()` is absent on purpose: `str.replace` is the same syntax, and no
# amount of staring at an AST distinguishes them by name. It is caught by ARITY
# instead — see `_replace_is_a_path_replace`.
PATH_MUTATORS = ('write_text', 'write_bytes', 'unlink', 'rmdir', 'mkdir',
                 'rename', 'touch', 'symlink_to', 'hardlink_to', 'chmod')
# Module-qualified mutators. The receiver is right there in the syntax, so
# these need no disambiguation at all.
MODULE_MUTATORS = {
    'os': ('rename', 'replace', 'remove', 'unlink', 'rmdir', 'mkdir',
           'makedirs', 'removedirs', 'symlink', 'link', 'truncate', 'chmod'),
    'shutil': ('rmtree', 'copy', 'copy2', 'copyfile', 'copytree', 'move'),
}
# Modes that make `open()` a mutation. A read-mode `open()` is not a write and
# stays anybody's to call.
WRITE_MODES = ('w', 'a', 'x', '+')
# Where the mode SITS, per spelling. The builtin carries the path first, so its
# mode is the second argument; the bound method already has the path in the
# receiver, so its mode is the FIRST. Reading `args[1]` for both was this gate's
# blind spot: every `p.open('w')` in `src/` classified as a read and passed.
BUILTIN_OPEN_MODE_ARG = 1
METHOD_OPEN_MODE_ARG = 0
# `mode=` outranks the positional slot in either spelling, because that is what
# Python itself does; an absent mode is a read, because that is the default.
OPEN_MODE_KEYWORD = 'mode'
DEFAULT_OPEN_MODE = 'r'
# The ONE sanctioned writer outside APPLY_MODULE, pinned by PATH **and** MODE
# rather than by a blanket allowlist. `ledger.append_row` opens its file in
# append mode deliberately (0.22.0/ledger decision D1): a read-modify-write
# drops rows when two appenders collide and rewrites the bytes `merge=union`
# depends on nobody rewriting. Append is a different primitive, not a variant of
# overwrite — so a `'w'` in THIS file is still a finding, and an `'a'` in any
# other module is too.
APPEND_ONLY_MODULE = 'repo/pm/ledger.py'
APPEND_MODES = ('a', 'ab')
# --- primitive 11: one spawn --------------------------------------------------
# The third of the family above, and the one hard rule 2 had no home for.
# `apply.py` owns the mutation and `walk.py` owns the enumeration; sixteen call
# sites across nine modules each imported `subprocess` for themselves, so "this
# package boots nothing" was a claim about nine files and a reviewer's memory.
#
# The NUMBER is assignment order, like primitive 9's: 11 beside 1 and 2 is a
# label, not a reading order.
SPAWN_SEAM = 'core/spawn.py'
# The library that owns process start-up, and the constructors that reach it.
# Spelled the way `tests/conftest.py` derives the `shell` mark —
# `subprocess.<attr>` — so the tier definition, primitive 8 below and this
# allowlist police one chokepoint. Declared here and read in both places, for
# the reason OS_SPAWNERS is.
#
# `SPAWNERS` is also what makes the owner an owner: the companion case asserts
# the seam still makes one of these calls, so the allowlist cannot be satisfied
# by a module that stopped spawning — and asserts it makes it ATTRIBUTE-style
# off the module, because `tests/conftest.py` enforces the unit tier by
# rebinding `subprocess.Popen`, and a `from subprocess import Popen` here would
# hold its own reference and unarm that guard for the whole suite.
SPAWN_MODULE = 'subprocess'
SPAWNERS = ('run', 'Popen', 'call', 'check_output', 'check_call')
# The `os.<name>` spellings that start a process WITHOUT importing
# `subprocess`, and therefore without the `shell` derivation, the runtime tier
# guard or the allowlist above seeing anything at all. Declared here because
# primitive 11 bans them across `src/` and primitive 5 bans them on the emit
# path: ONE roster, two readers, so neither can be widened behind the other.
OS_SPAWNERS = ('system', 'popen', 'execv', 'execve', 'execvp', 'execvpe',
               'execl', 'execle', 'execlp', 'execlpe', 'spawnv', 'spawnve',
               'spawnl', 'spawnle', 'spawnlp', 'spawnlpe', 'posix_spawn',
               'posix_spawnp', 'fork', 'forkpty', 'startfile')
# The name every caller imports the owner under, and the dotted module behind
# it. A module reaching EITHER is reaching a process, which is what primitive 5
# has to ask now that `import subprocess` answers False everywhere but one file.
SPAWN_OWNER = 'spawn'
SPAWN_DOTTED = 'agentic_sdlc.core.spawn'
# --- primitive 9: one frontmatter ---------------------------------------------
# The third of the family above, and it sits here rather than at the end of the
# file because it is the same shape: ONE module, an exact allowlist, an empty
# offender list. The NUMBER is assignment order — the banners below were
# numbered as they were added and 6 is already used twice — so 9 beside 1 and 2
# is a label, not a reading order.
#
# `repo/pm/model.py` held 385 lines of frontmatter I/O in the middle of the PM
# invariants (the file is `vocabulary.py` + `inventory.py` now): the fence scan, the per-process document cache, the field readers
# and the three byte-exact writers. Nothing said they belonged together, so a
# caller that wanted the bytes back reached past them and opened the file —
# `conveyor/steps._read` was a second `read_raw`, character for character.
#
# Rule 3 is what a second reader breaks: `newline=''` disables universal-newline
# translation both ways, `_split` is `str.split('\n')` and NOT `splitlines()`
# (which also breaks on U+2028, U+2029, form feed and lone CR), and `_eol`
# carries the CR half of a CRLF. Every one of those is invisible until a CRLF
# grain round-trips through a writer that skipped one.
FRONTMATTER_MODULE = 'core/frontmatter.py'
# The name every caller imports the owner under, so `frontmatter.read_raw` is
# reaching the owner and a module-level `read_raw` is a second one.
FRONTMATTER_OWNER = 'frontmatter'
# The mechanics that must have exactly one home. A module can only spell one of
# these by BINDING it — `def`, `class`, an assignment or an import — so binding
# is the whole question, and a re-export (`from ...frontmatter import read_raw`)
# is a binding like any other. Class-body `def`s are NOT bindings here:
# `report.Source` declares `read_raw` as one of a fourteen-read source seam and
# `DiskSource` delegates it to the owner, which is the shape this rule wants.
FRONTMATTER_INTERNALS = ('_split', '_fence_bounds', '_eol', 'read_raw',
                         'write_raw', 'parse_document', '_remember',
                         '_DOCUMENTS')
# The other half, because a hand-rolled reader need not reuse a name. A READ
# `open()` carrying `newline=` is the byte-exact read and cannot be anything
# else; the write side is primitive 2's, so `apply.py`'s `'w'` and the ledger's
# `'a'` need no exemption here and this roster stays empty.
OPEN_NEWLINE_KEYWORD = 'newline'
# --- primitive 10: the engine asks by ID, not by path -------------------------
# Primitive 9 put frontmatter I/O in one module. This one is about who may
# ADDRESS it: 102 call sites outside the grain layer handed `field_of` a `Path`
# to ask what a grain SAYS, which is "a grain is a file on disk" hard-coded 102
# times. `inventory.grain(cfg, gid)` resolves an id to a `Grain` and
# `Grain.field` asks it; a module that knows an id goes through those and names no file.
#
# What a second backend would cost is the argument: at 102 `Path` call sites it
# is not expensive, it is impossible — and the reachability is worth having
# WITHOUT one, because the reads now say which question they are asking.
GRAIN_LAYER_MODULE = 'repo/pm/inventory.py'
# The name every caller imports the grain layer under, so `inventory.doc_grain`
# is reaching it and a bare `doc_grain(` is the layer's own spelling.
GRAIN_LAYER_OWNER = 'inventory'
# The storage reads that take a PATH and answer *what does this document say*.
# `field_in` is absent on purpose: its first argument is LINES, so it cannot
# hand storage a path.
STORAGE_FIELD_READS = ('field_of', 'list_field_of', 'document',
                       'sequence_defect')
# The rest of what the census below finds in the storage module, each with the
# reason it may still be handed a path. `read_raw` asks *what are this file's
# bytes*, which is a question about a FILE that a template, a version file and
# a shared doc all legitimately ask; the three setters are WRITES, and who may
# write by path is primitive 2's question rather than this one's.
STORAGE_BY_PATH_OK = {
    'read_raw': "a FILE's bytes — not a question about what a grain says",
    'set_field': 'the write side — primitive 2 owns who may write',
    'set_fields': 'the write side — primitive 2 owns who may write',
    'set_list_field': 'the write side — primitive 2 owns who may write',
}
# The ONE file-to-grain adapter, graded here too — otherwise every
# `frontmatter.field_of(p, k)` could become `inventory.doc_grain(p).field(k)`,
# the gate would go green and nothing would have changed. A module that really
# holds a file is a ROSTER entry with a reason, not a `doc_grain` call.
GRAIN_ADAPTER = 'doc_grain'
# ...AND THE ADAPTER'S SIBLINGS, which is M1 of `ft-the-module-says-what-it-
# does`'s review: grading `doc_grain` alone left `read_grain` — `doc_grain`
# plus a `None` filter, three lines below it in the same file — answering the
# identical question ungraded, so the substitution the banner above forbids
# worked one name over and eight live sites were doing it. The tuple is not
# maintained by hand: `test_every_by_path_read_an_owner_exposes_is_named`
# derives the census from the layer's own source and fails on a name that is in
# neither this tuple nor the excusal below.
GRAIN_LAYER_PATH_READS = (GRAIN_ADAPTER, 'read_grain', 'empty_section')
# The grain layer's own file-questions, the `read_raw` case one layer up: a
# SHARED DOC declares no `id:` at all, so there is nothing to ask it by and
# `templates` asking a doc it just minted for its header is not addressable any
# other way. The two predicates answer *is this file a grain document* about a
# path a walk just produced, which is the same question one step earlier.
GRAIN_LAYER_BY_PATH_OK = {
    'header_of': "a shared doc's first line — a shared doc declares no id",
    '_is_grain_doc': 'does this FILE open a frontmatter fence',
    '_is_shared_doc': 'is this FILE a grain\'s shared doc, by name and fence',
}
# The dotted module behind each owner name. The classifier matches the RECEIVER
# (`frontmatter.field_of`, `inventory.doc_grain`), so an import bound under any
# other name is invisible to it — F2 of the same review. These are what
# `_renamed_owner_sites` holds the import side to, so the convention is a test
# rather than a habit.
FRONTMATTER_DOTTED = 'agentic_sdlc.core.frontmatter'
GRAIN_LAYER_DOTTED = 'agentic_sdlc.repo.pm.inventory'
# Modules that may still address a storage read BY PATH, each with the reason
# it holds a file rather than an id. SHRINKS ONLY — `ROSTER_OPENED_AT` below
# fails the build on a fourth entry, because the convenient fourth entry is
# this gate's whole failure mode. `core/frontmatter.py` is not here: it IS the
# storage module, which primitive 9 already pins to one file.
PATH_ADDRESSED_ROSTER = {
    # The grain layer itself: `doc_grain` is the file-to-grain adapter, the
    # pool walks hand back documents, and `Grain.field` is the one read every
    # other module goes through. If a second backend ever arrives, this is the
    # module that learns about it.
    GRAIN_LAYER_MODULE: 'the grain layer — it owns the seam',
    # `report.Source`'s two implementations. `GitSource` reads git BLOBS at a
    # rev: the handle it passes has no `stat`, is not a file, and is in no
    # index, so an id-addressed read routed through `grain_index` would
    # silently answer about the working tree instead. `pm ledger report --from
    # <rev>` is that read, and it only fails in the `shell` tier.
    'repo/pm/report.py': 'the rev-addressed source seam — a blob is not a file',
    # `_repair_verb` resolves the grain BESIDE a shared doc by taking the
    # slot suffix off its filename. There is no id to ask with: the shared doc
    # declares none, and which grain it sits beside is a fact about the two
    # names. The rest of the module measures file BODIES.
    'repo/checks/grain_shape.py': 'the grain beside a shared doc, found by name',
}
# The opening size, pinned so the roster cannot grow. Criterion 3 of
# `st-the-engine-asks-by-id-not-by-path`: an entry added to make this green is
# the defect, so adding one breaks the build and has to be argued for here.
ROSTER_OPENED_AT = 3
# THE CENSUS THE TWO TUPLES ABOVE ARE CHECKED AGAINST, per owner module:
# (module, the reads at the bottom of it, the graded names, the excused ones).
# A hand-kept list of names is exactly how this gate shipped grading five of
# eight — so the names are DERIVED from the owner's own source and the tuples
# above only say what was DECIDED about each. `read_raw`/`document` are where
# every question about a document bottoms out in the storage module; the four
# storage reads are where every question about a document bottoms out in the
# grain layer, which is one layer up and asks nothing else.
DOCUMENT_READ_CENSUS = (
    (FRONTMATTER_MODULE, {'read_raw': 0, 'document': 0},
     STORAGE_FIELD_READS, STORAGE_BY_PATH_OK),
    (GRAIN_LAYER_MODULE, {name: 0 for name in STORAGE_FIELD_READS},
     GRAIN_LAYER_PATH_READS, GRAIN_LAYER_BY_PATH_OK),
)
# `unquote` is idempotent on every value whose stripped form is not itself
# quote-wrapped, and NOT a no-op on the rest: `unquote('""x""')` is `'x'` where
# one strip gives `'"x"'`. Every reader below unquotes as it parses, so an
# `unquote` around one of them strips TWICE — and `pm get` never did, so two
# verbs disagreed about the same field. 68 such sites were deleted; this is
# what stops the 69th.
UNQUOTE = 'unquote'
ALREADY_UNQUOTED = ('field_of', 'list_field_of', 'field_in', 'field',
                    'list_field')


def _sources() -> list[tuple[str, Path]]:
    """(module-relative posix path, file) for every shipped module.

    Enumerated through `core.walk`, because a test that hand-rolled its own
    `rglob` to police `rglob` would be the joke that writes itself.
    """
    from agentic_sdlc.core import walk as walkmod
    from agentic_sdlc.core.walk import Kind
    found = walkmod.descendants(SRC, Kind.FILE, suffix='.py')
    out = [(p.relative_to(SRC).as_posix(), p) for p in found.kept]
    # The census floor, at the one place every caller goes through, so no
    # allowlist can be satisfied by having scanned nothing.
    assert len(out) >= MIN_SOURCES, (
        f'{len(out)} shipped module(s) under {SRC} — expected at least '
        f'{MIN_SOURCES}. The allowlists below assert an EMPTY offender list, '
        f'so a census this small passes them while checking nothing.')
    return out


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding='utf-8'), filename=str(path))


def _is_an_open_call(node: ast.Call) -> bool:
    """True for both spellings of `open` — the builtin and the bound method."""
    func = node.func
    return ((isinstance(func, ast.Attribute) and func.attr == 'open')
            or (isinstance(func, ast.Name) and func.id == 'open'))


def _open_mode(node: ast.Call) -> str | None:
    """The literal mode of this `open(...)`, or None when it is not a literal.

    The positional slot depends on the SPELLING: `open(path, 'w')` puts the mode
    where `p.open('w')` puts nothing at all. `mode=` wins over the positional in
    either form, and an absent mode is `DEFAULT_OPEN_MODE` — `open(p)` reads.
    """
    index = (METHOD_OPEN_MODE_ARG if isinstance(node.func, ast.Attribute)
             else BUILTIN_OPEN_MODE_ARG)
    mode: ast.expr | None = node.args[index] if len(node.args) > index else None
    for kw in node.keywords:
        if kw.arg == OPEN_MODE_KEYWORD:
            mode = kw.value
    if mode is None:
        return DEFAULT_OPEN_MODE
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return mode.value
    return None


def _is_write_open(node: ast.Call) -> bool:
    """True when this `open(...)` call names a WRITE mode.

    The mode is a literal in every call in this package. A non-literal mode is
    treated as a write: an unreadable mode is exactly the case a guard must not
    wave through.
    """
    mode = _open_mode(node)
    if mode is None:
        return True
    return any(ch in mode for ch in WRITE_MODES)


def _is_sanctioned_append(rel: str, node: ast.Call) -> bool:
    """True for the one append `APPEND_ONLY_MODULE` is allowed to make.

    By path AND by mode: a `'w'` in that same file is not sanctioned, and an
    `'a'` anywhere else is not either. A non-literal mode (None) matches no
    entry in `APPEND_MODES`, so an unreadable mode cannot buy the exception.
    """
    return rel == APPEND_ONLY_MODULE and _open_mode(node) in APPEND_MODES


def _is_unsanctioned_write_open(rel: str, node: ast.Call) -> bool:
    """A write-mode `open(...)` that is not the ledger's sanctioned append."""
    return _is_write_open(node) and not _is_sanctioned_append(rel, node)


def _calls(tree: ast.Module):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node


def _enumeration_sites(rel: str, tree: ast.Module) -> list[str]:
    out = []
    for node in _calls(tree):
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr in ENUMERATORS:
            # `ast.walk` / `os.walk` / `path.walk` — the receiver decides
            # whether `walk` is an enumeration or this package's own module.
            if func.attr == 'walk' and isinstance(func.value, ast.Name) \
                    and func.value.id in ('ast', 'walk'):
                continue
            out.append(f'{rel}:{node.lineno}: {func.attr}()')
        elif isinstance(func, ast.Name) and func.id in ('scandir', 'listdir'):
            out.append(f'{rel}:{node.lineno}: {func.id}()')
    return out


def _replace_is_a_path_replace(node: ast.Call) -> bool:
    """True when this `.replace(...)` is `Path.replace`, decided by ARITY.

    `str.replace` needs at least TWO arguments — `s.replace(old)` is a
    TypeError, so it cannot appear in code that runs. `Path.replace(target)`
    takes exactly one. That is a syntactic fact, not a guess about types, and it
    is the only honest way to tell the two apart from an AST.
    """
    return len(node.args) == 1 and not node.keywords


def _mutation_sites(rel: str, tree: ast.Module) -> list[str]:
    out = []
    for node in _calls(tree):
        func = node.func
        if isinstance(func, ast.Name):
            if func.id == 'open' and _is_unsanctioned_write_open(rel, node):
                out.append(f'{rel}:{node.lineno}: open(..., write mode)')
            continue
        if not isinstance(func, ast.Attribute):
            continue
        receiver = func.value.id if isinstance(func.value, ast.Name) else None
        if receiver in MODULE_MUTATORS and func.attr in MODULE_MUTATORS[receiver]:
            out.append(f'{rel}:{node.lineno}: {receiver}.{func.attr}()')
        elif func.attr in PATH_MUTATORS:
            out.append(f'{rel}:{node.lineno}: {func.attr}()')
        elif func.attr == 'replace' and _replace_is_a_path_replace(node):
            out.append(f'{rel}:{node.lineno}: replace() (one arg — Path.replace)')
        elif func.attr == 'open' and _is_unsanctioned_write_open(rel, node):
            out.append(f'{rel}:{node.lineno}: .open(..., write mode)')
    return out


def _module_level_bindings(tree: ast.Module):
    """(name, lineno) for every name this module binds at MODULE level.

    Module level only, and that is the narrowing the source seam asks for: a
    `def read_raw` inside a `class` body is a method on `report.Source`, which
    declares fourteen reads and delegates them, while one at column 0 is a
    second module-level function of that name.

    An `import` yields BOTH halves — the name imported and the name it was
    bound under. `from ...frontmatter import write_raw as put` binds `put`, so
    a reader that only looked at the binding waved the re-export through, and
    the corpus said so before this file was trusted.
    """
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield node.name, node.lineno
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    yield target.id, node.lineno
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            yield node.target.id, node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                yield alias.name, node.lineno
                if alias.asname:
                    yield alias.asname, node.lineno
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield (alias.asname or alias.name).split('.')[0], node.lineno


def _is_raw_frontmatter_read(node: ast.Call) -> bool:
    """True for a READ `open(...)` that disables newline translation.

    The mode decides, through `_open_mode` rather than a second reading of it:
    a WRITE with `newline=` is `core/apply.py`'s and the ledger's, and both are
    primitive 2's business. A read that asks for the bytes as they are on disk
    has exactly one home.
    """
    if not _is_an_open_call(node):
        return False
    if _is_write_open(node):
        return False
    return any(kw.arg == OPEN_NEWLINE_KEYWORD for kw in node.keywords)


def _frontmatter_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every second spelling of the frontmatter mechanics in one module."""
    out = []
    for name, lineno in _module_level_bindings(tree):
        if name in FRONTMATTER_INTERNALS:
            out.append(f'{rel}:{lineno}: binds {name} at module level')
    for node in _calls(tree):
        if _is_raw_frontmatter_read(node):
            out.append(f'{rel}:{node.lineno}: open(..., newline=…) in read mode')
    return out


def _called_name(node: ast.Call) -> tuple[str, str]:
    """(receiver, attribute) of this call — ('', name) for a bare one.

    Both spellings, because the owner of a name calls it bare and everybody
    else calls it through the module: `doc_grain(path)` inside the grain layer
    and `inventory.doc_grain(path)` outside it are the same call.
    """
    func = node.func
    if isinstance(func, ast.Attribute):
        receiver = func.value.id if isinstance(func.value, ast.Name) else ''
        return receiver, func.attr
    if isinstance(func, ast.Name):
        return '', func.id
    return '', ''


def _spawn_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every way this module could start a process without the seam.

    Three routes, because `import subprocess` alone is not the whole question:
    the import in any spelling, an attribute off the `subprocess` name (which is
    what a `sys.modules` lookup or a rebind would leave behind), and the
    `os.<name>` spawners, which import nothing and so are invisible to every
    reader built on that import.

    `ast.walk` and not `tree.body`: a deferred `import subprocess` inside a
    function is still an import, and "we only do it lazily" is exactly how a
    second spawner would arrive.
    """
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(f'{rel}:{node.lineno}: import {alias.name}'
                       for alias in node.names
                       if alias.name.split('.')[0] == SPAWN_MODULE)
        elif (isinstance(node, ast.ImportFrom)
                and (node.module or '').split('.')[0] == SPAWN_MODULE):
            out.extend(f'{rel}:{node.lineno}: from {node.module} '
                       f'import {alias.name}' for alias in node.names)
        elif (isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == SPAWN_MODULE):
            out.append(f'{rel}:{node.lineno}: {SPAWN_MODULE}.{node.attr}')
    out.extend(f'{rel}:{node.lineno}: os.{node.func.attr}()'
               for node in _calls(tree)
               if isinstance(node.func, ast.Attribute)
               and isinstance(node.func.value, ast.Name)
               and node.func.value.id == 'os'
               and node.func.attr in OS_SPAWNERS)
    return sorted(set(out))


def _seam_reach_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every way this module reaches `core/spawn.py` — the import, or a call.

    The question primitive 5 has to ask once the seam exists. "Does this module
    import `subprocess`" was the right question while nine modules did; with
    exactly one owner it answers False for every other file in the package, and
    an emit path calling `spawn.run(...)` forty times passes it.
    """
    out: list[str] = []
    bound: set[str] = set()
    for name, source, lineno in _import_bindings(rel, tree):
        if source == SPAWN_DOTTED or source.startswith(SPAWN_DOTTED + '.'):
            bound.add(name)
            out.append(f'{rel}:{lineno}: imports {source}')
    out.extend(f'{rel}:{node.lineno}: '
               f'{".".join(part for part in _called_name(node) if part)}()'
               for node in _calls(tree)
               if (isinstance(node.func, ast.Attribute)
                   and isinstance(node.func.value, ast.Name)
                   and node.func.value.id in bound | {SPAWN_OWNER})
               or (isinstance(node.func, ast.Name) and node.func.id in bound))
    return sorted(set(out))


def _path_addressed_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every read in one module that ASKS A PATH what a grain says.

    Decided by the NAME of the function called, not by guessing which argument
    is path-shaped: every name here takes the document as a parameter of the
    CALLER's, so reaching one at all IS handing storage a path — whether it
    arrives first (`field_of(p, k)`) or second (`read_grain(cfg, p, kind)`). A
    `Grain.field(key)` call carries no path to hand over and is invisible here.
    """
    out = []
    for node in _calls(tree):
        receiver, name = _called_name(node)
        if name in STORAGE_FIELD_READS and receiver in ('', FRONTMATTER_OWNER):
            out.append(f'{rel}:{node.lineno}: {name}(<path>, …) — ask '
                       f'`grain(cfg, gid).{name.replace("_of", "")}` instead')
        elif name in GRAIN_LAYER_PATH_READS and receiver in ('', GRAIN_LAYER_OWNER):
            out.append(f'{rel}:{node.lineno}: {name}(<path>, …) — the grain '
                       f'layer read that turns a FILE into what a document '
                       f'says, and only a module that holds a file may call it')
    return out


def _renamed_owner_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every import that binds an owner, or a graded read out of one, under a
    name the classifier above cannot see.

    `_path_addressed_sites` matches the RECEIVER — `frontmatter.field_of`,
    `inventory.doc_grain` — so `from ...core import frontmatter as fm` and then
    `fm.field_of(p, k)` reads as somebody else's function and the gate is
    blind. The bare `from ...frontmatter import field_of` form is already
    caught at the CALL, because the reader accepts an empty receiver; the two
    spellings that are not are the renamed module and the renamed function, and
    both are bindings, so both are visible right here.
    """
    out = []
    for name, source, lineno in _import_bindings(rel, tree):
        for dotted, owner, graded in (
                (FRONTMATTER_DOTTED, FRONTMATTER_OWNER, STORAGE_FIELD_READS),
                (GRAIN_LAYER_DOTTED, GRAIN_LAYER_OWNER, GRAIN_LAYER_PATH_READS)):
            read = (source[len(dotted) + 1:]
                    if source.startswith(dotted + '.') else '')
            if source == dotted and name != owner:
                out.append(f'{rel}:{lineno}: binds {dotted} as {name!r} — the '
                           f'gate reads the receiver, so every {owner}.<read> '
                           f'call in this module is invisible to it')
            elif read in graded and name != read:
                out.append(f'{rel}:{lineno}: binds {dotted}.{read} as '
                           f'{name!r} — a graded read under another name is '
                           f'the same blindness one size down')
    return out


def _document_addressed(tree: ast.Module, roots: dict[str, int]) -> set[str]:
    """Every module-level function in one owner that hands a document read one
    of its OWN parameters — the census `DOCUMENT_READ_CENSUS` grades.

    A fixpoint, because the question arrives second-hand: `read_grain(cfg,
    path, kind)` never names `frontmatter.document`, it calls `doc_grain(path,
    kind)`, which does. `roots` says which ARGUMENT of each bottom read is the
    document, and a caller inherits the position it passed its own parameter
    in, so `read_grain`'s is 1 where `doc_grain`'s is 0.

    Two limits, stated rather than implied: a document arriving by KEYWORD and
    a read declared inside a `class` body are both invisible to this reader.
    Neither exists in either owner, and `Grain.field(key)` is a method holding
    `self.path`, which is the shape this whole primitive is FOR.
    """
    funcs = {node.name: node for node in tree.body
             if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    arrives: dict[str, set[int]] = {name: {pos} for name, pos in roots.items()}
    grown = True
    while grown:
        grown = False
        for name, node in funcs.items():
            params = [arg.arg for arg in node.args.args]
            for call in _calls(node):
                _, called = _called_name(call)
                for pos in tuple(arrives.get(called, ())):
                    if pos >= len(call.args):
                        continue
                    passed = call.args[pos]
                    if not isinstance(passed, ast.Name) or passed.id not in params:
                        continue
                    here = arrives.setdefault(name, set())
                    if params.index(passed.id) not in here:
                        here.add(params.index(passed.id))
                        grown = True
    # What THIS module exposes: the grain layer's roots are the storage
    # module's four reads, and they are graded where they are defined.
    return set(arrives) & set(funcs)


def _double_strip_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every `unquote(...)` whose argument is a reader that already unquoted."""
    out = []
    for node in _calls(tree):
        _, name = _called_name(node)
        if name != UNQUOTE or not node.args:
            continue
        inner = node.args[0]
        if not isinstance(inner, ast.Call):
            continue
        _, read = _called_name(inner)
        if read in ALREADY_UNQUOTED:
            out.append(f'{rel}:{node.lineno}: {UNQUOTE}({read}(…)) — {read} '
                       f'unquotes as it parses, so this strips twice')
    return out


class TheCensusIsTheRealTree(unittest.TestCase):
    """Before either allowlist means anything, it has to have scanned the tree.

    The floor itself is asserted inside `_sources()`, which every case below
    goes through — so the case that restated it here was the same assertion
    twice. What is NOT derivable from that is whether the floor ever fires, and
    that is what stayed.
    """

    def test_a_moved_SRC_breaks_the_build_instead_of_passing(self):
        import tempfile
        import unittest.mock
        with tempfile.TemporaryDirectory() as empty:
            with unittest.mock.patch(f'{__name__}.SRC', Path(empty)):
                with self.assertRaises(AssertionError):
                    _sources()


class OneWalk(unittest.TestCase):
    """PRIMITIVE 1 — filesystem enumeration lives in exactly one module."""

    PROTECTS = (
        'every filesystem enumeration under src/ goes through core/walk.py, so '
        'no census can reach a number without carrying what it dropped',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): a '
        'second rglob returns a shorter list, and nothing that RUNS can tell a '
        'narrowed census from a small tree. Six of them narrowed in silence '
        'before this existed',
    )

    CORPUS = (
        ("for path in root.rglob('*.py'):\n    pass", True),
        ("names = sorted(root.glob('*.md'))", True),
        ('for child in root.iterdir():\n    pass', True),
        ('for base, dirs, files in os.walk(root):\n    pass', True),
        ('names = os.listdir(root)', True),
        ('with os.scandir(root) as entries:\n    pass', True),
        # The receiver is what decides: `ast.walk` and this package's own
        # `walk` module are not enumerations, and neither is prose.
        ('for node in ast.walk(tree):\n    pass', False),
        ('found = walk.descendants(root, Kind.FILE)', False),
        ("HELP = 'rglob and iterdir and listdir'", False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_enumeration_sites(SCRATCH_MODULE, ast.parse(planted)))

    def test_only_the_walk_module_enumerates(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == WALK_MODULE:
                continue
            offenders.extend(_enumeration_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'filesystem enumeration outside ' + WALK_MODULE + '. A walk that '
            'returns one list has nowhere to put what it dropped, which is how '
            'six censuses came to narrow in silence. Route it through '
            '`core.walk`, whose result carries both halves:\n  '
            + '\n  '.join(offenders))

    def test_the_walk_module_does_enumerate(self):
        """The allowlist must not be vacuously satisfiable by a module that
        stopped enumerating — then every offender would move somewhere else and
        the test would still pass."""
        sites = _enumeration_sites(WALK_MODULE, _tree(SRC / WALK_MODULE))
        self.assertGreaterEqual(len(sites), 4, sites)


class OneApply(unittest.TestCase):
    """PRIMITIVE 2 — filesystem mutation lives in exactly one module."""

    PROTECTS = (
        'every filesystem mutation under src/ goes through core/apply.py, which '
        'decides the whole plan before it writes any of it',
        'load-bearing — sin 2 (a write that looks legitimate and is not): a '
        'writer that decides as it goes lands half a plan when step three '
        'refuses, which the scaffolder, install-agents and `pm collapse` each '
        'did, and each left a tree neither before nor after',
    )

    CORPUS = (
        ('target.write_text(payload)', True),
        ('target.write_bytes(payload)', True),
        ('target.unlink()', True),
        ('target.mkdir(parents=True)', True),
        ('os.replace(source, target)', True),
        ('shutil.rmtree(scratch)', True),
        # `Path.replace` takes ONE argument and `str.replace` needs two, which
        # is the only honest way an AST tells them apart.
        ('target.replace(other)', True),
        ("line.replace('a', 'b')", False),
        ('target.read_text()', False),
        ('apply.plan(steps).apply()', False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_sites_for(planted))

    def test_only_the_apply_module_writes(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == APPLY_MODULE:
                continue
            offenders.extend(_mutation_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'filesystem mutation outside ' + APPLY_MODULE + '. A writer that '
            'decides as it goes lands half a plan when step three refuses, '
            'which is how the scaffolder, install-agents and `pm collapse` each '
            'left a tree neither before nor after. Route it through '
            '`core.apply`, which decides the whole plan and then applies it:\n  '
            + '\n  '.join(offenders))

    def test_the_apply_module_does_write(self):
        sites = _mutation_sites(APPLY_MODULE, _tree(SRC / APPLY_MODULE))
        self.assertGreaterEqual(len(sites), 4, sites)


class OneSpawn(unittest.TestCase):
    """PRIMITIVE 11 — starting a process lives in exactly one module.

    The allowlist is EXACTLY `SPAWN_SEAM`, with no exemption roster: every
    one of the sixteen call sites takes its argv, its cwd and its timeout from
    the caller, so none of them needed anything the seam does not pass through.
    """

    PROTECTS = (
        'every process this package starts comes through core/spawn.py, so '
        'hard rule 2 — pure text, boots nothing, safe anywhere in parallel — '
        'is a question with ONE file to ask rather than nine',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): a '
        'spawn added anywhere else changes no result any behaviour test can '
        'see. It is a gate that stops being pure text, a unit test that starts '
        'running `make`, or a hook that hangs on the network, and all three '
        'report green until somebody times them',
    )

    CORPUS = (
        # The import, in every spelling — including the deferred one inside a
        # function, which is how "we only do it lazily" arrives.
        ('import subprocess', True),
        ('import subprocess as sp', True),
        ('from subprocess import run', True),
        ('def go():\n    import subprocess\n    return subprocess', True),
        # The attribute off the name, with no import in this snippet at all:
        # what a `sys.modules` lookup or a rebind leaves behind.
        ('done = subprocess.Popen(argv)', True),
        # The `os` spellings, which import nothing and so are invisible to
        # every reader built on the import.
        ('os.system(command)', True),
        ('os.execvp(argv[0], argv)', True),
        ('pid = os.fork()', True),
        # Reaching the owner is the point of the owner.
        ('from agentic_sdlc.core import spawn', False),
        ('done = spawn.run(argv, cwd=root, capture_output=True)', False),
        ('try:\n    go()\nexcept spawn.TimeoutExpired:\n    pass', False),
        # An `os` call that starts nothing, and prose.
        ("root = os.environ.get('PWD')", False),
        ("HELP = 'never subprocess.run, never os.system'", False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_spawn_sites(SCRATCH_MODULE, ast.parse(planted)))

    def test_only_the_spawn_module_starts_a_process(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == SPAWN_SEAM:
                continue
            offenders.extend(_spawn_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'a process started outside ' + SPAWN_SEAM + '. Hard rule 2 is '
            'what lets any verb run from a git hook and from CI without a '
            'sandbox, and it is only checkable while there is one file to '
            'check. Route it through `core.spawn`, which passes argv, cwd and '
            'timeout straight through and adds nothing:\n  '
            + '\n  '.join(offenders))

    def test_the_spawn_module_does_spawn(self):
        """The allowlist must not be vacuously satisfiable by a module that
        stopped spawning — then every offender would move somewhere else and
        the test would still pass."""
        sites = _spawn_sites(SPAWN_SEAM, _tree(SRC / SPAWN_SEAM))
        self.assertGreaterEqual(len(sites), 4, sites)
        self.assertIn(SPAWN_SEAM, {rel for rel, _ in _sources()},
                      f'{SPAWN_SEAM} is not in the census — the allowlist '
                      f'above is asserting emptiness over a module that moved')

    def test_the_seam_reaches_subprocess_by_attribute(self):
        """The trap this seam is one line away from, and it unarms the SUITE.

        `tests/conftest.py` enforces the unit tier by rebinding
        `subprocess.Popen` as a MODULE ATTRIBUTE, on the argument that it is
        the class every caller constructs. A `from subprocess import Popen`
        here would hold its own reference, the rebinding would never reach it,
        and the runtime guard would stop firing for every test in the suite
        with no symptom but `make unit` getting slower.
        """
        tree = _tree(SRC / SPAWN_SEAM)
        plain = [alias.name for node in ast.walk(tree)
                 if isinstance(node, ast.Import) for alias in node.names
                 if alias.name == SPAWN_MODULE and alias.asname is None]
        self.assertEqual(
            [SPAWN_MODULE], plain,
            f'{SPAWN_SEAM} does not `import {SPAWN_MODULE}` plainly. The '
            f'module attribute is the only reference tests/conftest.py can '
            f'rebind')
        renamed = [f'from {node.module} import {alias.name}'
                   for node in ast.walk(tree)
                   if isinstance(node, ast.ImportFrom)
                   and (node.module or '').split('.')[0] == SPAWN_MODULE
                   for alias in node.names]
        self.assertEqual(
            [], renamed,
            f'{SPAWN_SEAM} binds a name out of {SPAWN_MODULE} directly. '
            f'That reference is the real object forever, so the unit tier '
            f'stops being enforced and nothing says so: ' + ', '.join(renamed))
        started = [node.func.attr for node in _calls(tree)
                   if isinstance(node.func, ast.Attribute)
                   and isinstance(node.func.value, ast.Name)
                   and node.func.value.id == SPAWN_MODULE
                   and node.func.attr in SPAWNERS]
        self.assertTrue(
            started,
            f'{SPAWN_SEAM} makes no `{SPAWN_MODULE}.<starter>` call, so it '
            f'is not the owner and the allowlist is policing an empty room')


class OneStorage(unittest.TestCase):
    """PRIMITIVE 9 — frontmatter I/O lives in exactly one module.

    The allowlist is EXACTLY `FRONTMATTER_MODULE` and there is no exemption
    roster: the two implementations of `report.Source` reach the owner rather
    than the file, and the write side's `newline=` belongs to primitive 2. An
    empty roster is why there is no stale-entry case here — there is no entry
    to go stale.
    """

    PROTECTS = (
        'frontmatter I/O has exactly one implementation, so the byte-for-byte '
        'preservation rule 3 promises has one place to be true',
        'load-bearing — sin 2 (a write that looks legitimate and is not): a '
        'second parser carries a second set of preservation rules, and the line '
        'ending or the blank line it drops reads as a clean single-line write '
        'from outside',
    )

    CORPUS = (
        # A second module-level spelling of the mechanics, by any binding.
        ("def read_raw(path):\n    return path.read_text()", True),
        ("def _split(text):\n    return text.splitlines()", True),
        ('def _fence_bounds(lines):\n    return None', True),
        ('_DOCUMENTS = {}', True),
        # A re-export is a binding like any other — this is the exact line
        # a re-exported `field_of` would have survived behind.
        ('from agentic_sdlc.core.frontmatter import read_raw', True),
        ('from agentic_sdlc.core.frontmatter import write_raw as put', True),
        # The reader that reuses no name at all.
        ("with open(path, encoding='utf-8', newline='') as fh:\n    pass", True),
        ("text = p.open('r', newline='').read()", True),
        # Reaching the owner is the point of the owner.
        ('text = frontmatter.read_raw(path)', False),
        ('from agentic_sdlc.core import frontmatter', False),
        # A method on the declared source seam, delegating to the owner.
        ('class DiskSource(Source):\n'
         '    def read_raw(self, path):\n'
         '        return frontmatter.read_raw(path)', False),
        # The write side, and a plain read: primitive 2's and nobody's.
        ("p.open('w', newline='')", False),
        ("text = p.read_text(encoding='utf-8')", False),
        ("HELP = 'read_raw and write_raw and _split'", False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_frontmatter_sites(SCRATCH_MODULE, ast.parse(planted)))

    def test_only_the_storage_module_parses_frontmatter(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == FRONTMATTER_MODULE:
                continue
            offenders.extend(_frontmatter_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'frontmatter I/O outside ' + FRONTMATTER_MODULE + '. A second '
            'reader gets `newline=` or `splitlines()` wrong and a CRLF grain '
            'comes back LF; a second writer holds a parse the first one has '
            'already invalidated, which is a gate answering off bytes that '
            'moved on. Route it through `core.frontmatter`, which reads each '
            'document once and rewrites the line it was asked for:\n  '
            + '\n  '.join(offenders))

    def test_the_storage_module_does_read_and_write(self):
        """The allowlist must not be vacuously satisfiable by a module that
        stopped storing — then every offender would move somewhere else and the
        test would still pass. Both halves, because reading is where rule 3 is
        lost and writing is where rule 4 is."""
        tree = _tree(SRC / FRONTMATTER_MODULE)
        bound = {name for name, _ in _module_level_bindings(tree)}
        self.assertEqual(
            (), tuple(n for n in FRONTMATTER_INTERNALS if n not in bound),
            f'{FRONTMATTER_MODULE} no longer holds every internal the '
            f'allowlist names, so the allowlist is checking a name nothing '
            f'implements')
        reads = [n for n in _calls(tree) if _is_raw_frontmatter_read(n)]
        self.assertGreaterEqual(len(reads), 1, 'the owner makes no raw read')
        writes = [n for n in _calls(tree)
                  if isinstance(n.func, ast.Attribute)
                  and isinstance(n.func.value, ast.Name)
                  and n.func.value.id == 'apply']
        self.assertGreaterEqual(len(writes), 1,
                                'the owner reaches no writer, so nothing here '
                                'is a write at all')


class TheEngineAsksByIdNotByPath(unittest.TestCase):
    """PRIMITIVE 10 — a module that knows an id never names the file.

    `inventory.grain(cfg, gid)` is the id-addressed handle and `Grain.field(key)`
    is the read; `PATH_ADDRESSED_ROSTER` is the closed set of modules that
    legitimately hold a FILE instead, each with its reason.

    Halves, because this roster is the one that rots:
      * no module off the roster addresses a storage read by path,
      * every entry ON it still matches at least one site — an entry nothing
        matches is a hole waiting for a file to move into it,
      * the roster has not GROWN, because the convenient fourth entry is how
        this gate goes green while nothing improved,
      * every by-path read the two owners EXPOSE is either graded or excused by
        name — the half that was missing, and the one that let the substitution
        the banner forbids work one name over, and
      * neither owner is bound under a name the classifier cannot see.
    """

    PROTECTS = (
        'a module that knows a grain id never names its file: the storage '
        'reads that take a document are reachable from the grain layer, the '
        'rev-addressed source seam and one filename resolver, and nowhere '
        'else — and no reader strips a value a reader already stripped',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): the '
        'reads this moves are `check pm`/`pm validate`/`ready-for`, and a '
        'path-addressed one answers about whatever file the caller derived '
        'rather than about the grain it meant to ask — `_decision_log` joined '
        '`milestone.md` onto a pool and read the empty string for four '
        'releases. The double strip is the same sin one size down: `pm get` '
        'single-stripped and `pm list` double-stripped, so two verbs printed '
        'different answers for one `name:` and neither said so',
    )

    CORPUS = (
        # Asking a PATH what a grain says, in every spelling.
        ("status = frontmatter.field_of(grain.path, 'status')", True),
        ("order = frontmatter.list_field_of(parent.path, 'order')", True),
        ('fields = frontmatter.document(grain.path).fields', True),
        ("defect = frontmatter.sequence_defect(parent.path, 'order')", True),
        # The adapter, graded too: it is the one way to turn a path into a
        # grain, so it cannot be the way round this rule.
        ('beside = inventory.doc_grain(path)', True),
        ('beside = doc_grain(path)', True),
        # ...and its siblings, which answer the same question and were the
        # substitution that still worked (M1). The document arrives SECOND in
        # the first of them, which is why the reader grades the name.
        ("grain = inventory.read_grain(cfg, path, 'story')", True),
        ("why = inventory.empty_section(grain.path, 'Close')", True),
        ("why = empty_section(path, 'Ship')", True),
        # The owner under another name, in both spellings — the module and the
        # read — because the classifier matches the receiver (F2).
        ('from agentic_sdlc.core import frontmatter as fm', True),
        ('from agentic_sdlc.repo.pm import inventory as inv', True),
        ('from agentic_sdlc.core.frontmatter import field_of as grab', True),
        ('import agentic_sdlc.repo.pm.inventory as inv', True),
        # The owner under ITS name is how every module reaches it.
        ('from agentic_sdlc.core import frontmatter', False),
        ('from agentic_sdlc.repo.pm import inventory, vocabulary', False),
        ('from agentic_sdlc.core.frontmatter import unquote', False),
        # The bare re-export is not caught HERE — it is caught at the call,
        # where the reader accepts an empty receiver (the row below it).
        ('from agentic_sdlc.core.frontmatter import field_of', False),
        ("status = field_of(p, 'status')", True),
        # Asking the GRAIN. No path is handed to anything.
        ("why = grain.section_defect('Close')", False),
        ("status = grain.field('status')", False),
        ("order = parent.list_field('order')", False),
        ("found = inventory.grain(cfg, gid, 'story').field('status')", False),
        # A question about a FILE's bytes, not about what a grain says.
        ('text = frontmatter.read_raw(version_file)', False),
        # LINES, already read — there is no path in the call to hand over.
        ("kind = frontmatter.field_in(lines, 'kind')", False),
        # Prose is not a call.
        ("HELP = 'field_of and list_field_of and doc_grain'", False),
        # The double strip, and the two spellings that are not one.
        ("gid = frontmatter.unquote(frontmatter.field_of(path, 'id'))", True),
        ("gid = frontmatter.unquote(src.field_of(path, 'id'))", True),
        ("gid = frontmatter.unquote(grain.field('id'))", True),
        ("kind = frontmatter.unquote(frontmatter.field_in(lines, 'kind'))", True),
        # A value off the COMMAND LINE, which nothing has stripped yet.
        ('gid = frontmatter.unquote(value)', False),
        ("gid = frontmatter.unquote(args[1].strip())", False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        tree = ast.parse(planted)
        return bool(_path_addressed_sites(SCRATCH_MODULE, tree)
                    or _double_strip_sites(SCRATCH_MODULE, tree)
                    or _renamed_owner_sites(SCRATCH_MODULE, tree))

    def test_no_module_off_the_roster_asks_a_path(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel in PATH_ADDRESSED_ROSTER or rel == FRONTMATTER_MODULE:
                continue
            offenders.extend(_path_addressed_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'a storage read addressed by PATH outside the roster. A module '
            'that knows an id asks `inventory.grain(cfg, gid).field(key)`; one '
            'that really holds a file joins ' + ', '.join(
                sorted(PATH_ADDRESSED_ROSTER)) + ' with its reason written '
            'beside it, and that roster may only SHRINK:\n  '
            + '\n  '.join(offenders))

    def test_every_roster_entry_still_matches_a_site(self):
        """An entry nothing matches is a hole waiting for a file to move into
        it — the same reasoning `CONFIG_IMPORT_ALLOWLIST` prunes for."""
        census = {rel: path for rel, path in _sources()}
        stale = sorted(set(PATH_ADDRESSED_ROSTER) - set(census))
        self.assertEqual([], stale,
                         'rostered module(s) that no longer exist. Prune:\n  '
                         + '\n  '.join(stale))
        idle = sorted(rel for rel in PATH_ADDRESSED_ROSTER
                      if not _path_addressed_sites(rel, _tree(census[rel])))
        self.assertEqual(
            [], idle,
            'rostered module(s) that address nothing by path any more — the '
            'exemption has outlived what it was granted for. Delete the '
            'line:\n  ' + '\n  '.join(idle))

    def test_every_by_path_read_an_owner_exposes_is_named(self):
        """The half M1 found missing: the graded tuple was kept BY HAND beside
        a layer that kept growing, so `read_grain` — `doc_grain` plus a `None`
        filter, three lines below it — answered the same question ungraded and
        eight live sites used it.

        Derived, and asserted in BOTH directions, which is also this case's
        floor: a reader that went blind returns the roots alone, a moved owner
        returns nothing at all, and neither equals the tuples above.
        """
        for rel, roots, graded, excused in DOCUMENT_READ_CENSUS:
            with self.subTest(module=rel):
                found = _document_addressed(_tree(SRC / rel), roots)
                named = set(graded) | set(excused)
                self.assertEqual(
                    [], sorted(found - named),
                    f'{rel} hands a document read one of its own parameters '
                    f'under (a) name(s) this gate has never heard of, so a '
                    f'caller can ask by path through it and nothing says so — '
                    f'M1 exactly. Grade it beside {graded[0]!r}, or excuse it '
                    f'with the reason it answers a question about a FILE:\n  '
                    + '\n  '.join(sorted(found - named)))
                self.assertEqual(
                    [], sorted(named - found),
                    f'{rel} no longer exposes (a) name(s) this gate grades or '
                    f'excuses, so the classifier is policing a name nothing '
                    f'implements and a real one may have moved in behind '
                    f'it:\n  ' + '\n  '.join(sorted(named - found)))

    def test_no_module_binds_an_owner_under_another_name(self):
        """F2: both seams pinned the import name by convention. `from
        ...core import frontmatter as fm` then `fm.field_of(p, k)` passes every
        case above, because the classifier matches the receiver."""
        offenders: list[str] = []
        for rel, path in _sources():
            offenders.extend(_renamed_owner_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            f'an owner bound under a name the by-path classifier cannot see. '
            f'Import {FRONTMATTER_DOTTED} as {FRONTMATTER_OWNER!r} and '
            f'{GRAIN_LAYER_DOTTED} as {GRAIN_LAYER_OWNER!r}, which is what '
            f'every module in this package already does:\n  '
            + '\n  '.join(offenders))

    def test_the_roster_has_not_grown(self):
        self.assertLessEqual(
            len(PATH_ADDRESSED_ROSTER), ROSTER_OPENED_AT,
            f'the roster opened at {ROSTER_OPENED_AT} modules and may only '
            f'shrink; it now names {sorted(PATH_ADDRESSED_ROSTER)}. A '
            f'convenience entry is the defect this case exists to stop — if '
            f'the module really holds a FILE, say so here and lower '
            f'ROSTER_OPENED_AT by deleting one that does not.')

    def test_nothing_strips_a_value_that_is_already_unquoted(self):
        offenders: list[str] = []
        for rel, path in _sources():
            offenders.extend(_double_strip_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'an `unquote` around a reader that already unquoted. The second '
            'strip is not a no-op: a value whose unquoted form is itself '
            'quote-wrapped loses another pair, and `pm get` never did that, so '
            'two verbs answered differently about one field:\n  '
            + '\n  '.join(offenders))

    def test_the_grain_layer_holds_the_seam_the_roster_assumes(self):
        """The other side of the roster, in BOTH directions, because one case
        covers one claim: the id-addressed read has to exist (or the offender
        list above is empty because nobody can read a field at all), and the
        grain layer has to still be the module holding the path reads (or every
        offender moved somewhere else and these cases pass over nothing).
        """
        import inspect
        from agentic_sdlc.repo.pm import inventory
        for name, args in (('grain', ('cfg', 'gid', 'kind')),
                           ('doc_grain', ('path', 'kind')),
                           ('story_grain', ('cfg', 'sid'))):
            fn = getattr(inventory, name, None)
            self.assertTrue(callable(fn), f'{GRAIN_LAYER_OWNER}.{name} is gone')
            params = inspect.signature(fn).parameters
            for arg in args:
                self.assertIn(arg, params, f'{GRAIN_LAYER_OWNER}.{name}({arg})')
        for name in ('field', 'list_field', 'declares', 'sequence_defect',
                     'section_defect'):
            self.assertTrue(
                callable(getattr(inventory.Grain, name, None)),
                f'Grain.{name} is gone — every caller that stopped naming a '
                f'file reads through it')
        sites = _path_addressed_sites(GRAIN_LAYER_MODULE,
                                      _tree(SRC / GRAIN_LAYER_MODULE))
        self.assertGreaterEqual(len(sites), 8, sites)


# Every spelling of `open` the classifier has to get right, as
# (source, is a write). The mode MOVES between argument slots with the
# spelling — `p.open('w')` puts it where `open(p, 'w')` puts the path — and
# that is the whole of the defect this table exists to hold shut. A scratch
# module, not a real one: the gate is being MUTATED here, not observed.
OPEN_SPELLINGS = (
    # bound method — the mode is the FIRST argument.
    ("p.open('w')", True),
    ("p.open(mode='w')", True),
    ("Path(x).open('a')", True),
    ("p.open('x')", True),
    ("p.open('w+')", True),
    ("p.open('r+')", True),
    ("p.open('wb')", True),
    ("p.open('ab')", True),
    ("p.open('a', encoding='utf-8', newline='\\n')", True),
    ("p.open()", False),
    ("p.open('r')", False),
    ("p.open('rb')", False),
    ("p.open(encoding='utf-8')", False),
    # builtin — the mode is the SECOND argument, after the path.
    ("open(p, 'w')", True),
    ("open(p, mode='w')", True),
    ("open(p, 'a')", True),
    ("open(p, 'x')", True),
    ("open(p, 'w+')", True),
    ("open(p, 'r+')", True),
    ("open(p, 'wb')", True),
    ("open(p, 'ab')", True),
    ("open(p)", False),
    ("open(p, 'r')", False),
    ("open(p, 'rb')", False),
    ("open(p, encoding='utf-8')", False),
    # An unreadable mode is a write in both spellings: a guard that cannot read
    # the mode must refuse rather than wave the call through (rule 4).
    ("open(p, mode)", True),
    ("p.open(mode)", True),
)
# A module path that is emphatically NOT the ledger, for proving the exception
# is pinned to one file rather than granted to append mode generally.
SCRATCH_MODULE = 'repo/pm/scratch_not_the_ledger.py'
# The floor under the `open` census, in the same spirit as MIN_SOURCES: well
# under the real count (7 at the time of writing) and well over zero, so the
# classifier cannot be declared correct over a tree it never read.
MIN_OPEN_CALLS = 4


def _sites_for(source: str, rel: str = SCRATCH_MODULE) -> list[str]:
    """The real classifier, run over a source snippet as if it were `rel`."""
    return _mutation_sites(rel, ast.parse(source))


class TheOpenModeIsReadFromTheRightArgument(unittest.TestCase):
    """`Path.open('w')` is a write, and this gate used to say otherwise.

    `_is_write_open` read the mode from `args[1]` — correct for the builtin
    `open(path, 'w')`, and wrong for `p.open('w')`, whose `args[1]` is not the
    mode and is usually nothing at all. Every `p.open('w')` and `p.open('a')`
    under `src/` therefore classified as a READ and passed the one-writer
    boundary: a gate that missed real drift and printed PASS, which CLAUDE.md
    rule 4 calls the cardinal sin.
    """

    PROTECTS = (
        'the mutation classifier reads an open() mode off the right argument, '
        'so the one-writer boundary standing on it is graded rather than '
        'assumed',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): this '
        'IS the miss that shipped, every p.open(w) under src/ classified as a '
        'read. Its scratch-file plant and its non-empty open census are '
        'unduplicated; its OPEN_SPELLINGS loop is now a second scoreboard for '
        'test_guard_corpus.py::EveryGuardDeclaresWhatItMustCatch, which replays '
        'the same table through the same classifier',
    )

    # Already (planted, must it be caught) — the table this feature generalised.
    CORPUS = OPEN_SPELLINGS

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_sites_for(planted))

    def test_every_spelling_of_open_is_classified_by_its_real_mode(self):
        for source, is_write in OPEN_SPELLINGS:
            with self.subTest(source=source):
                sites = _sites_for(source)
                self.assertEqual(
                    is_write, bool(sites),
                    f'{source!r} classified as a '
                    f'{"read" if is_write else "write"}. The mode is the first '
                    'argument for the bound method and the second for the '
                    f'builtin; sites={sites}')

    def test_a_scratch_module_writing_by_Path_open_is_caught(self):
        """End to end, through the same path the gate walks: a real file on
        disk, parsed by `_tree`, classified by `_mutation_sites`."""
        import tempfile
        with tempfile.TemporaryDirectory() as scratch:
            module = Path(scratch) / 'scratch.py'
            module.write_text(
                'from pathlib import Path\n'
                '\n'
                '\n'
                'def sneak(target: Path, payload: str) -> None:\n'
                "    with target.open('w', encoding='utf-8') as handle:\n"
                '        handle.write(payload)\n',
                encoding='utf-8')
            sites = _mutation_sites(SCRATCH_MODULE, _tree(module))
        self.assertEqual([f'{SCRATCH_MODULE}:5: .open(..., write mode)'], sites)

    def test_the_open_census_is_not_empty(self):
        """The classifier above is only worth anything over a tree it read."""
        census = sum(1 for _, path in _sources()
                     for node in _calls(_tree(path)) if _is_an_open_call(node))
        self.assertGreaterEqual(
            census, MIN_OPEN_CALLS,
            f'{census} open() call(s) under {SRC} — expected at least '
            f'{MIN_OPEN_CALLS}. A correct mode classifier over nothing is '
            'still a gate that checks nothing.')


class TheLedgerAppendIsTheOneException(unittest.TestCase):
    """PRIMITIVE 2, continued — the single sanctioned writer outside apply.

    Decision D1 of `0.22.0/ledger`: `ledger.append_row` owns append as a
    PRIMITIVE, because a read-modify-write drops rows when two appenders
    collide. The exception it earns is one file in one mode — not an allowlist
    entry that would also excuse an overwrite, a `mkdir`, or a `write_text`.
    """

    PROTECTS = (
        'append outside ledger.append_row is a finding, and the exception it '
        'earns is one file in one mode rather than an allowlist entry',
        'load-bearing — sin 2 (a write that looks legitimate and is not): a '
        'read-modify-write of the ledger drops rows when two appenders collide, '
        'and the file it leaves behind is well-formed and short',
    )

    # Graded AS the ledger, so every case asks what the exception admits.
    # Append is what it was granted for; an overwrite there rewrites the bytes
    # `merge=union` relies on nobody rewriting, which is the defect D1 exists
    # to prevent; and the exception is by MODE, so it excuses no other
    # mutation of that same file.
    CORPUS = (
        ("p.open('a')", False),
        ("p.open('ab')", False),
        ("p.open(mode='a')", False),
        ("p.open('a', encoding='utf-8', newline='\\n')", False),
        ("p.open('w')", True),
        ("open(p, 'w')", True),
        ("p.open('w+')", True),
        ("p.open(mode='w')", True),
        ("p.open('x')", True),
        ('p.write_text(x)', True),
        ('p.mkdir()', True),
        ('p.unlink()', True),
        ('os.remove(p)', True),
        # A mode this file cannot read matches no entry in APPEND_MODES, so it
        # cannot buy the exception either.
        ('p.open(mode)', True),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_sites_for(planted, APPEND_ONLY_MODULE))

    def test_append_anywhere_else_is_a_finding(self):
        for rel in (SCRATCH_MODULE, 'cli.py', 'repo/pm/inventory.py'):
            for source in ("p.open('a')", "open(p, 'a')", "p.open('ab')"):
                with self.subTest(rel=rel, source=source):
                    self.assertNotEqual([], _sites_for(source, rel))

    def test_the_ledger_really_does_append(self):
        """The exception must not outlive the append it was granted for.

        An allowlist entry nothing matches is a hole waiting for a file to move
        into it — the same reasoning `CONFIG_IMPORT_ALLOWLIST` prunes for.
        """
        tree = _tree(SRC / APPEND_ONLY_MODULE)
        appends = [f'{APPEND_ONLY_MODULE}:{node.lineno}'
                   for node in _calls(tree)
                   if _is_an_open_call(node)
                   and _is_sanctioned_append(APPEND_ONLY_MODULE, node)]
        self.assertEqual(
            1, len(appends),
            f'{APPEND_ONLY_MODULE} should hold exactly ONE sanctioned append; '
            f'found {appends}. If the append is gone, delete the exception.')


class TheResolversCollapsed(unittest.TestCase):
    """0.4.0 — the addressing layer that existed BECAUSE the path was schema.

    Twenty functions that were one function with a kind baked in: `story_file`
    knew one three-segment shape, `milestone_dir` worked for milestones and
    nothing else, and a fifth kind meant writing four more. They are
    `grain_file(cfg, gid, kind)`, `children(cfg, kind, parent)` and
    `pool_walk(cfg, kind)` now.

    **Both halves are pinned, and the second is the one that rots.** Twelve are
    GONE, and a name coming back means somebody re-derived an id from a path.
    Eight SURVIVE as the nested reader, reachable only when `is_pooled(cfg)` is
    False — that is a deliberate compat layer with a stated retirement
    condition (D3 on `identity-lives-in-frontmatter`), and pinning the roster
    is what stops it becoming permanent by accident: delete the last nested
    tree and this case is what tells you the eight can go.
    """

    # Gone. Each answered a question about a PATH or a grain DIRECTORY, and a
    # pooled tree has neither.
    GONE = ('orphan_dirs', 'milestone_dir_of', '_building_ledger_dir')

    # Kept, and only for the nested layout. Shrinking this list is the goal;
    # GROWING it means a new path-shaped resolver got written, which is the
    # thing 0.4.0 deleted.
    NESTED_ONLY = ('_nested_index', '_nested_feature_files',
                   '_nested_story_files', 'milestone_dir', 'feature_dir',
                   'milestone_walk', 'milestone_dirs', 'AmbiguousStory')

    def test_the_path_shaped_resolvers_are_gone(self):
        source = (SRC / GRAIN_LAYER_MODULE).read_text(encoding='utf-8')
        for name in self.GONE:
            self.assertNotIn(f'def {name}(', source,
                             f'{name} is back in {GRAIN_LAYER_MODULE}. An id '
                             f'names no location in 0.4.0, so nothing derives '
                             f'one from a path.')

    def test_the_nested_reader_is_exactly_this_roster(self):
        source = (SRC / GRAIN_LAYER_MODULE).read_text(encoding='utf-8')
        for name in self.NESTED_ONLY:
            opener = f'class {name}(' if name[0].isupper() else f'def {name}('
            self.assertIn(opener, source,
                          f'{name} left without this roster being updated — '
                          f'if the nested reader is going, the whole of it '
                          f'goes together and D3 gets closed.')

    def test_the_three_general_resolvers_take_a_kind(self):
        from agentic_sdlc.repo.pm import inventory
        import inspect
        for name, arg in (('grain_file', 'kind'), ('children', 'kind'),
                          ('pool_walk', 'kind')):
            fn = getattr(inventory, name)
            self.assertIn(arg, inspect.signature(fn).parameters, name)


class OneRuleRoutesALedgerRow(unittest.TestCase):
    """0.4.0/D1 — a row is filed against the milestone that owns its GRAIN, and
    no write path reads a status to decide where bytes go.

    The deleted lookup (`_building_ledger_dir`) asked which milestone was
    `in_progress`: it refused when none was, which lost every row a tree wrote
    while it was still planning, and refused when two were, which is the
    workflow this package exists for. It was a SECOND answer to a question
    `_stamp` had always answered from the grain.

    A name test rather than a behaviour test, because the behaviour cases in
    `test_pm_ledger_record.py` prove where a row lands and cannot prove that
    the old mechanism is not sitting beside the new one, reachable from a path
    nobody thought to cover.
    """

    # Spelled as a string so grepping for the retired name finds this case:
    # the one hit in `src/` a reader gets is the gate that removed it.
    RETIRED = '_building_ledger_dir'

    def test_the_in_progress_lookup_is_not_in_the_source(self):
        offenders, scanned = [], 0
        for rel, path in _sources():
            scanned += 1
            if self.RETIRED in path.read_text(encoding='utf-8'):
                offenders.append(rel)
        self.assertEqual(offenders, [],
                         f'{self.RETIRED} is back. A row is routed by its '
                         f'grain (D1); a milestone status decides nothing '
                         f'about where a row is written.')
        self.assertGreaterEqual(scanned, MIN_SOURCES)


# The two halves a `Walk` carries. A count taken off either one is a number
# with its disclosures dropped, which is the shape `census(label)` exists for.
WALK_HALVES = ('kept', 'skipped')


def _half_length_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every `len(...)` in this module taken over one half of a `Walk`."""
    out: list[str] = []
    for node in _calls(tree):
        if not (isinstance(node.func, ast.Name) and node.func.id == 'len'):
            continue
        out.extend(f'{rel}:{node.lineno}: len(...{arg.attr})'
                   for arg in node.args
                   if isinstance(arg, ast.Attribute) and arg.attr in WALK_HALVES)
    return out


class WalkHasNoLength(unittest.TestCase):
    """A census must not be able to reach a number without its narrowings.

    `Walk.__len__` raises, and `len(x.kept)` is the way around it — so the way
    around it is a build break too. The counting API is `Walk.census(label)`,
    which renders the number and the disclosures as ONE string.
    """

    PROTECTS = (
        'no caller can reach a census number without the narrowings that '
        'produced it: Walk.__len__ raises, and len(x.kept) is a build break too',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS) '
        'expressed as a TypeError one layer below the gates, which is the '
        'cheapest place it can be expressed at all',
    )

    CORPUS = (
        ('total = len(found.kept)', True),
        ('total = len(found.skipped)', True),
        ('total = len(walk.descendants(root, Kind.FILE).kept)', True),
        ('total = len(entries)', False),
        ('total = len(found.census(label))', False),
        ("said = found.census('module(s)')", False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_half_length_sites(SCRATCH_MODULE, ast.parse(planted)))

    def test_len_of_a_walk_half_is_never_taken(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == WALK_MODULE:
                continue
            offenders.extend(_half_length_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'a count taken off half a Walk. Call `.census(label)` so the number '
            'and what it left out render together:\n  ' + '\n  '.join(offenders))

    def test_len_of_a_walk_raises(self):
        from agentic_sdlc.core.walk import Walk
        with self.assertRaises(TypeError):
            len(Walk((Path('a'),)))


# --- primitive 3: config through the guards -----------------------------------
# The exact modules that may IMPORT a raw config read (`config_section` /
# `load_config`). Every one of them routes each VALUE through the guards in
# `core/config.py` (`str_tuple`, `str_tuple_table`, `pattern`, `text`) — that
# is what the reviewer checks when a file joins this list. A closed list, not a
# pattern: a new module reading config either goes through a guard and gets
# named here, or it breaks the build. `tuple(cfg.get(...))` over a bare string
# is ('a','d','d','o','n','s','/') — the shape that shipped seven silently
# empty censuses in v0.9.0.
CONFIG_READERS = ('config_section', 'load_config')
CONFIG_OWNER = 'core/config.py'
CONFIG_IMPORT_ALLOWLIST = frozenset((
    CONFIG_OWNER,                 # the guard module itself
    'cli.py',
    # `[pm]` and `[repo_hygiene] mainline`, through `flag`/`number`/`relpath`/
    # `str_tuple_table`/`table`/`text`. The DECLARES half of the old `model.py`:
    # the CONTAINS half (`repo/pm/inventory.py`) reads no config at all, which
    # is why the split left one entry here and not two.
    'repo/pm/vocabulary.py',
    'repo/checks/doc.py',
    'repo/checks/grain_shape.py',
    'repo/checks/repo_hygiene.py',
    'repo/checks/shell.py',
    # `[tests] budget` — a table of tier ceilings, read through `number_table`,
    # which is the guard for exactly this shape. A bare `cfg.get('budget')`
    # would hand back whatever TOML held, and a ceiling that is a STRING
    # compares against a float in a way this gate would report as "under
    # budget" forever: the read-side cardinal sin, in the gate whose whole job
    # is to notice a number getting worse.
    'repo/checks/budget.py',
    # `[checks] all` — the roster `verify --plan` joins against the ledger's
    # gate rows, to say which named gate has never produced a cost. Read
    # through `str_tuple`, which is the guard for a list-of-strings, and NOT
    # through `cli.all_roster`: this package's layers point downward, so
    # `verify` reaching up into the router is the import next door refuses.
    # Validating the NAMES stays the router's job.
    'repo/verify/main.py',
    'repo/gates_extra.py',
    # `[dispatch] project` and `contracts`, read through `text` and
    # `relpath_tuple`. The preamble it renders is the only carrier a dispatched
    # agent's contracts have, so a value that arrived unguarded would be a
    # contract pointer nobody validated — and `contracts` is exactly the
    # list-of-strings a bare read would iterate one CHARACTER at a time.
    'repo/dispatch.py',
    # The conveyor reads `[release] steps`, `[release.commands]` and
    # `[<op>.version_files]`, and every one of those values goes through a
    # refusal before it is used: a step name through `name_defect`, a command
    # through the table check, a version file through the non-empty-table
    # check. A step list silently narrowed by a bad value would be a release
    # protocol that walked past what it was asked to prove — the same shape as
    # a gate roster narrowed by a typo, one altitude up.
    'repo/conveyor/steps.py',
    # `[emit] sink` and `[emit] kinds`, read through `relpath` and `str_tuple`.
    # The sink is the value with the sharpest edge in this package: a string a
    # consumer wrote, one `import_module` away from being a plugin system
    # (0.5.0/D1). It goes through a guard and then it is a PATH and nothing
    # else — `TheToolEmitsAndNeverExecutes` below holds that shut by AST.
    'repo/emit.py',
))
# Calls that build a collection straight from an unguarded value.
COLLECTORS = ('tuple', 'set', 'list', 'frozenset')
# --- primitive 4: import layering ----------------------------------------------
# (directory prefix, module prefixes it must NEVER import, census floor).
# `core/` is the floor — the walk, the writer, the config guards, the markdown
# reader — and it knows about nothing above it; `repo/` sits on `core/` and is
# reached only from the CLI, never the other way round. Two rows because the
# package is two layers deep: an upward import is the architecture running
# backwards, however locally convenient.
LAYER_RULES = (
    ('core/', ('agentic_sdlc.repo', 'agentic_sdlc.cli'), 4),
    ('repo/', ('agentic_sdlc.cli',), 4),
)
PACKAGE = 'agentic_sdlc'
# --- primitive 5: the tool EMITS, and never EXECUTES ---------------------------
# 0.5.0/D1. `repo/emit.py` takes a string a CONSUMER wrote and opens a file with
# it — the one value in this package that is a single `import_module` away from
# being a plugin system, which is the design D1 rejects and the package that
# owns our name on PyPI is the worked example of.
#
# Hard rule 2 — boots nothing, safe anywhere, any time, in parallel — is what
# makes every gate here runnable from a git hook and from CI without a sandbox,
# and ONE verb that spawns a consumer-named command ends that for every verb,
# because a caller can no longer tell which ones are safe.
#
# The pressure it has to survive is one sentence: *"just let the config name a
# command to run."* It is one commit and it will sound reasonable, so it breaks
# the BUILD here rather than resting on a reviewer noticing.
EMIT_MODULE = 'repo/emit.py'
# The closed set of modules the emit path may import. An allowlist rather than a
# ban list, because "imports a module named in config" is not a name you can
# enumerate: what makes it impossible is that the ONLY importable things here
# are five modules written down in this file.
EMIT_IMPORTS = frozenset((
    'sys', 'pathlib', 'typing',
    f'{PACKAGE}.core.config',      # the guards every config value crosses
    f'{PACKAGE}.repo.pm.ledger',   # `dumps`, `append_to`, and the row routing
))
# Calls that turn a STRING into behaviour. `import_module`/`__import__` import
# what a config value named, `eval`/`exec`/`compile` run it, `entry_points` is
# the discovery half of the rejected plugin design, and `getattr`/`setattr` are
# how an imported module becomes a callable.
EXECUTORS = ('eval', 'exec', 'compile', '__import__', 'import_module',
             'entry_points', 'getattr', 'setattr')
# `sys` is on the allowlist for `print(file=sys.stderr)` and nothing else, so a
# SUBSCRIPT on it — `sys.modules['subprocess'].run(...)` — reaches an already
# imported module with no import statement for the allowlist to see. Banned by
# name, because "impossible to route around" has to be literal.
MODULE_MAP_OWNER, MODULE_MAP_ATTR = 'sys', 'modules'
# `OS_SPAWNERS` — the spellings that start a process without importing
# `subprocess`, and so invisible to the `shell` derivation — is declared with
# primitive 11 above and read here too. One roster, because two copies of a ban
# list are two things to widen and one of them is always the quiet one.
# What the emit path must still BE, so this class cannot pass over a file that
# was emptied or moved: it appends to a sink and it reads its own section.
EMIT_MUST_CALL = ('append_to', 'config_section')
# (source, is it a route to behaviour) — the classifier graded on what it
# CATCHES rather than on the shipped file being empty, since three assertions
# of emptiness pass perfectly over a guard that stopped seeing anything. The
# last row is the legitimate `sys` use the allowlist exists to keep legal.
EMIT_EXECUTION_SPELLINGS = (
    ("sys.modules['subprocess'].run(cmd)", True),
    ("importlib.import_module(sink).write(row)", True),
    ("entry_points(group=sink)", True),
    ("getattr(mod, sink)()", True),
    ("os.system(cmd)", True),
    ("print(line, file=sys.stderr)", False),
)
# (source, does it reach a process) — the OTHER half, and the reason this one
# exists. The question here was `module_spawns(emit.py)`: *does this module's
# source import `subprocess`*. That was the whole question while nine modules
# did; with primitive 11 above there is exactly ONE importer in the package, so
# it answers False for every other file and the case would pass over an emit
# path calling `spawn.run(...)` forty times. A gate that cannot fail is rule
# 4's first sin, so the question is re-pointed: reaching the SEAM is reaching a
# process. The first three rows are the planted emit paths that prove the new
# form catches what the old one did; the import spelling is graded too, because
# an emit path that only imports the seam is one line from calling it.
EMIT_SPAWN_SPELLINGS = (
    ('done = spawn.run(argv, cwd=root)', True),
    ('from agentic_sdlc.core import spawn', True),
    ('from agentic_sdlc.core.spawn import run', True),
    # The old question, still asked: a direct import is still a spawn.
    ('import subprocess', True),
    ('done = subprocess.run(argv)', True),
    # What the emit path really does, and prose about what it must not.
    ('ledger.append_to(sink, row)', False),
    ("HELP = 'never spawn.run, never subprocess'", False),
)


def _import_bindings(rel: str, tree: ast.Module) -> list[tuple[str, str, int]]:
    """(bound name, imported dotted source, lineno) for every import.

    `import a.b.c` binds `a`; `from m import x as y` binds `y` from `m.x`. A
    relative import is resolved against the module's own package, so a
    hypothetical `from ..godot import x` cannot dodge the layering rules by
    spelling the target without its prefix.
    """
    package_parts = [PACKAGE] + rel.split('/')[:-1]
    out: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                bound = alias.asname or alias.name.split('.')[0]
                out.append((bound, alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = package_parts[:len(package_parts) - (node.level - 1)]
                module = '.'.join(base + ([node.module] if node.module else []))
            else:
                module = node.module or ''
            if module == '__future__':
                continue
            for alias in node.names:
                bound = alias.asname or alias.name
                out.append((bound, f'{module}.{alias.name}', node.lineno))
    return out


def _names_config_is_bound_to(tree: ast.Module) -> set[str]:
    """Every name assigned from a bare `config_section(...)`/`load_config(...)`
    call anywhere in the module — `_CFG = config_section('doc')` makes `_CFG`
    an unguarded section, and `tuple(_CFG.get(...))` the same defect one
    statement later."""
    bound: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if not (isinstance(value, ast.Call) and isinstance(value.func, ast.Name)
                and value.func.id in CONFIG_READERS):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        bound.update(t.id for t in targets if isinstance(t, ast.Name))
    return bound


def _is_config_lookup(node: ast.expr, section_names: set[str]) -> bool:
    """True for `config_section(...)`, `load_config(...)`, and a `.get(...)`
    on either of those or on a name bound to one."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if isinstance(func, ast.Name) and func.id in CONFIG_READERS:
        return True
    if isinstance(func, ast.Attribute) and func.attr == 'get':
        receiver = func.value
        if isinstance(receiver, ast.Name) and receiver.id in section_names:
            return True
        return _is_config_lookup(receiver, section_names)
    return False


def _raw_config_imports(rel: str, tree: ast.Module) -> list[str]:
    """Every import of a RAW config read in this module."""
    return [f'{rel}:{lineno}: imports {bound}'
            for bound, source, lineno in _import_bindings(rel, tree)
            if source.rsplit('.', 1)[-1] in CONFIG_READERS
            and source.startswith(f'{PACKAGE}.core.')]


def _unguarded_collection_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every collection built straight from a config lookup, guard skipped."""
    section_names = _names_config_is_bound_to(tree)
    out: list[str] = []
    for node in _calls(tree):
        if not (isinstance(node.func, ast.Name)
                and node.func.id in COLLECTORS):
            continue
        if any(_is_config_lookup(arg, section_names) for arg in node.args):
            out.append(f'{rel}:{node.lineno}: {node.func.id}(<config lookup>)')
    return out


class ConfigGoesThroughTheGuards(unittest.TestCase):
    """PRIMITIVE 3 — every config VALUE crosses `core/config.py` on its way in."""

    PROTECTS = (
        'every config VALUE crosses core/config.py on its way in, so no gate '
        'builds its population out of a raw lookup',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): a '
        'bare string is iterable, so tuple(cfg.get(...)) yields characters and '
        'the gate configured from it scans nothing while reporting a clean run',
    )

    # Graded as a module that is NOT on the allowlist, which is what every
    # module written after this one is.
    CORPUS = (
        ('from agentic_sdlc.core.project import load_config', True),
        ('from agentic_sdlc.core.config import config_section', True),
        ("names = tuple(config_section('doc').get('scope'))", True),
        ("_CFG = config_section('doc')\nnames = tuple(_CFG.get('scope'))", True),
        ("names = set(load_config().get('doc', {}).get('scope'))", True),
        ('from agentic_sdlc.core.config import str_tuple', False),
        ("names = str_tuple(section, 'scope', ())", False),
        ('names = tuple(sorted(found))', False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        tree = ast.parse(planted)
        return bool(_raw_config_imports(SCRATCH_MODULE, tree)
                    or _unguarded_collection_sites(SCRATCH_MODULE, tree))

    def test_raw_config_imports_are_allowlisted(self):
        census = {rel for rel, _ in _sources()}
        stale = sorted(CONFIG_IMPORT_ALLOWLIST - census)
        self.assertEqual([], stale,
                         'allowlisted module(s) that no longer exist — an entry '
                         'nothing can match is a hole waiting for a file to '
                         'move into it. Prune:\n  ' + '\n  '.join(stale))
        offenders: list[str] = []
        importers = 0
        for rel, path in _sources():
            hits = _raw_config_imports(rel, _tree(path))
            if hits and rel in CONFIG_IMPORT_ALLOWLIST:
                importers += 1
            elif hits:
                offenders.extend(hits)
        self.assertEqual(
            [], offenders,
            'a raw config read imported outside the allowlist. Config comes in '
            'through the guards in ' + CONFIG_OWNER + ' (`str_tuple` & co) — a '
            'bare `cfg.get` hands back whatever TOML holds, and a string is '
            'iterable:\n  ' + '\n  '.join(offenders))
        # The allowlist must not be vacuously satisfied: most of its members
        # really do import a config read today.
        self.assertGreaterEqual(importers, 6, 'config-importer census collapsed')

    def test_no_collection_is_built_from_an_unguarded_lookup(self):
        offenders: list[str] = []
        for rel, path in _sources():
            if rel == CONFIG_OWNER:
                continue  # the guards themselves collect, AFTER validating
            offenders.extend(_unguarded_collection_sites(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'a collection built straight from a config lookup. `tuple(...)` of '
            'a bare string is a tuple of its CHARACTERS — seven gates shipped '
            'a silent PASS that way in v0.9.0. Route the value through a '
            + CONFIG_OWNER + ' guard:\n  ' + '\n  '.join(offenders))


def _dead_imports(rel: str, tree: ast.Module) -> list[str]:
    """Every name this module imports and never reads."""
    # An import binds via `alias` nodes, never `ast.Name` — so every Name in
    # the tree is a READ (or a rebind, which also keeps the import from being
    # deletable without a look).
    used = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == '__all__'
                        for t in node.targets)
                and isinstance(node.value, (ast.List, ast.Tuple))):
            used.update(c.value for c in node.value.elts
                        if isinstance(c, ast.Constant)
                        and isinstance(c.value, str))
    return [f'{rel}:{lineno}: {bound} (from {source})'
            for bound, source, lineno in _import_bindings(rel, tree)
            if bound not in used]


class NoImportIsDead(unittest.TestCase):
    """PRIMITIVE 4a — an import nobody reads is a claim nobody checked.

    Eight dead `load_config` imports survived an extraction because nothing
    made them fail. A name counts as read when it appears as any `ast.Name`
    in the module (annotations included — `from __future__ import annotations`
    keeps them unquoted) or in `__all__` (the `__init__.py` re-export form).
    """

    PROTECTS = (
        'an import nobody reads is deleted, so the import block of a module is '
        'a true list of what it depends on',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): a '
        'dead import changes no behaviour by construction, so no behaviour test '
        'can ever see one. Eight dead load_config imports survived an '
        'extraction and left the claim that those modules read config',
    )

    CORPUS = (
        ('import os', True),
        ('from agentic_sdlc.core.config import str_tuple', True),
        # A name inside a STRING is prose, not a read.
        ("import os\nHELP = 'call os.getcwd()'", True),
        ('import os\nHERE = os.getcwd()', False),
        ('import os.path as osp\nHERE = osp.dirname(x)', False),
        ("from x import y\n__all__ = ['y']", False),
        # Annotations are reads, which is what `from __future__ import
        # annotations` keeps true without quoting them.
        ('from pathlib import Path\n\n\ndef f(p: Path) -> None:\n    pass',
         False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_dead_imports(SCRATCH_MODULE, ast.parse(planted)))

    def test_every_import_is_read(self):
        offenders: list[str] = []
        bindings_seen = 0
        for rel, path in _sources():
            tree = _tree(path)
            bindings_seen += len(_import_bindings(rel, tree))
            offenders.extend(_dead_imports(rel, tree))
        self.assertGreaterEqual(bindings_seen, 100,
                                'import census collapsed — this gate is '
                                'asserting emptiness over nothing')
        self.assertEqual(
            [], offenders,
            'imported and never read. Delete it — or read it, in this same '
            'change:\n  ' + '\n  '.join(offenders))


# --- primitive 12: a module binds each name once -------------------------------
# Primitive 4a asks whether every name in the table is READ. This asks whether
# the table has one entry per name — the other way the table can lie.
def _bound_names(tree: ast.Module):
    """(name, lineno) for every name this module binds at MODULE LEVEL, spelled
    the way PYTHON binds it.

    NOT `_module_level_bindings` above, and the difference is the whole reader:
    that one yields BOTH halves of an import, because primitive 9 asks *is this
    mechanic spelled here at all* and `from ...frontmatter import read_raw as
    put` has to answer for `read_raw`. The question here is which name the
    module's namespace ends up HOLDING, which is one per alias — so the
    re-export yields `put` alone, and two imports reaching one name through two
    spellings do not read as a collision Python never makes.

    Column 0 only, for the same reason: a `def` in a class body is a method, and
    a rebinding under `if TYPE_CHECKING:` or in a `try:` fallback is a BRANCH,
    where exactly one of the two runs. `AugAssign` is absent because `X += …`
    needs the name to already exist, so it mutates one binding rather than
    making a second.
    """
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)):
            yield node.name, node.lineno
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                # `A, B = 'a', 'b'` binds two; a subscript or an attribute
                # target binds no module-level name at all. `A, *REST = …`
                # binds `REST` too — unwrapped, because a reader blind to one
                # shape is a narrowing rather than a simpler rule.
                leaves = (target.elts
                          if isinstance(target, (ast.Tuple, ast.List))
                          else [target])
                for leaf in leaves:
                    if isinstance(leaf, ast.Starred):
                        leaf = leaf.value
                    if isinstance(leaf, ast.Name):
                        yield leaf.id, node.lineno
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target,
                                                            ast.Name):
            yield node.target.id, node.lineno
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != '*':
                    yield alias.asname or alias.name, node.lineno
        elif isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.asname or alias.name.split('.')[0], node.lineno


def _double_bound_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every module-level name bound more than once, with every line that binds
    it and which one wins."""
    seen: dict[str, list[int]] = {}
    for name, lineno in _bound_names(tree):
        seen.setdefault(name, []).append(lineno)
    return [f'{rel}: {name} bound at '
            + ', '.join(str(n) for n in lines)
            + f' — only line {lines[-1]} is reachable'
            for name, lines in seen.items() if len(lines) > 1]


class NoNameIsBoundTwice(unittest.TestCase):
    """PRIMITIVE 12 — one module-level name, one binding.

    `pm/cli.py` defined `_slugify` at line 549 and again at 1720, byte-identical
    bodies and differently worded docstrings, with the only call site below both
    (`bg-a-helper-is-defined-twice-and-nothing-could-see-it`). The first was
    dead from the line it was written on, and a 1,236-case suite could not see
    it because nothing asks this question and Python does not warn.

    Rule 11 from the source side: a capability nobody can find is a capability
    you do not have — here it existed TWICE, in one file, and the second author
    could not see the first.
    """

    PROTECTS = (
        'a module binds each of its top-level names exactly once, so the '
        'definition a reader finds is the definition that runs',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): the '
        'second binding makes the first CORRECT, not wrong — every call reaches '
        'the right answer from the wrong line — so no behaviour test can ever '
        'observe one. The suite ran 1,236 green cases over a dead `_slugify`',
    )

    CORPUS = (
        # The shipped defect's shape: two `def`s, one name.
        ('def slug(t):\n    return t\n\n\ndef slug(t):\n    return t', True),
        ('NAME = 1\nNAME = 2', True),
        # A `def` and a `class` collide exactly as two `def`s do.
        ('def Row(x):\n    return x\n\n\nclass Row:\n    pass', True),
        ('from a import b\nfrom c import b', True),
        # Both bind `os`; harmless at run, and one of the two is still dead.
        ('import os.path\nimport os', True),
        ('A, B = 1, 2\nB = 3', True),
        ('A, *REST = 1, 2, 3\nREST = []', True),
        # A BRANCH is not a second binding: one of the two runs.
        ('from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n'
         '    from a import Said\nSaid = 1', False),
        ('try:\n    import tomllib\nexcept ImportError:\n'
         '    import tomli as tomllib', False),
        # A METHOD sharing a module function's name. Column 0 is the question.
        ('def field(key):\n    return key\n\n\nclass Grain:\n'
         '    def field(self, key):\n        return key', False),
        ('A, B = 1, 2\nC = 3', False),
        # The import asymmetry that `_module_level_bindings` would fail on:
        # this binds `put` and `read_raw`, which is one each.
        ('from a import read_raw as put\nfrom c import read_raw', False),
        ('X = 1\nX += 1', False),
        # Prose naming it twice is not a binding.
        ("def slug(t):\n    return t\n\n\nHELP = 'slug, and slug again'",
         False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_double_bound_sites(SCRATCH_MODULE, ast.parse(planted)))

    def test_no_module_binds_a_top_level_name_twice(self):
        offenders: list[str] = []
        bound = 0
        for rel, path in _sources():
            tree = _tree(path)
            bound += sum(1 for _ in _bound_names(tree))
            offenders.extend(_double_bound_sites(rel, tree))
        # The zero-census floor, in the spirit of `MIN_SOURCES`: this case
        # asserts an EMPTY offender list, and a reader that stopped reading
        # hands back one too.
        self.assertGreaterEqual(
            bound, 500,
            f'{bound} module-level binding(s) across {len(_sources())} module(s) '
            f'— the name census collapsed, so this case is asserting emptiness '
            f'over nothing')
        self.assertEqual(
            [], offenders,
            'a module-level name bound twice. Python binds both and the LAST '
            'one wins, so the earlier definition is unreachable from the line '
            'it was written on and nothing that runs can tell you. Delete the '
            'dead one:\n  ' + '\n  '.join(offenders))


# A module in the bottom layer, for grading a planted import as `core/` sees it.
CORE_SCRATCH = 'core/scratch_not_a_layer.py'


def _upward_imports(rel: str, tree: ast.Module) -> list[str]:
    """Every import this module makes against the layering."""
    banned = tuple(name for prefix, names, _ in LAYER_RULES
                   if rel.startswith(prefix) for name in names)
    return [f'{rel}:{lineno}: {source}'
            for _, source, lineno in _import_bindings(rel, tree)
            if any(source == b or source.startswith(b + '.') for b in banned)]


class LayersPointDownward(unittest.TestCase):
    """PRIMITIVE 4b — core/ -> repo/ -> cli.py, downward only. An upward
    import is the architecture running backwards, however locally
    convenient."""

    PROTECTS = (
        'core/ -> repo/ -> cli.py, downward only, so core never learns what a '
        'grain family is',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): an '
        'upward import runs perfectly until it cycles, so the architecture is '
        'invisible to anything that executes and visible only to a reader of '
        'the imports',
    )

    CORPUS = (
        ('from agentic_sdlc.repo import emit', True),
        ('import agentic_sdlc.cli', True),
        ('from agentic_sdlc.repo.pm import inventory', True),
        # Relative, and resolved against the module's own package — spelling
        # the target without its prefix dodges nothing.
        ('from ..repo import emit', True),
        ('from agentic_sdlc.core import walk', False),
        ('from agentic_sdlc.core.config import str_tuple', False),
        ('import tomllib', False),
    )

    # The two halves `repo/pm/model.py` split into, in import order. Siblings
    # at one altitude, so `LAYER_RULES` above cannot see a cycle between them:
    # both spell `agentic_sdlc.repo.pm`, which is neither layer reaching up.
    SIBLING_HALVES = (f'{PACKAGE}.repo.pm.vocabulary',
                      f'{PACKAGE}.repo.pm.inventory')

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_upward_imports(CORE_SCRATCH, ast.parse(planted)))

    def test_each_sibling_half_imports_with_the_other_absent(self):
        """The DECLARES half does not know the CONTAINS half exists.

        Executed rather than read, because the defect it catches is the one a
        reader of the imports waves through: `inventory` needs 28 names from
        `vocabulary`, and the tempting way to resolve a reference running the
        other way is an import inside a function, which no import-block reader
        sees. So each half is imported with the whole package purged from
        `sys.modules`: `vocabulary` alone must leave `inventory` UNIMPORTED —
        nothing in it reaches forward, at module level or from inside a call —
        and `inventory` alone must pull `vocabulary` in, which is the one
        direction being real rather than deferred.

        Probed both ways. A planted `import inventory` in `vocabulary.py` reds
        it as a circular ImportError; deleting `inventory.py`'s module-level
        import reds it too, as the NameError the 28 module-level uses raise.
        """
        import importlib
        import sys
        declares, contains = self.SIBLING_HALVES
        for dotted, wanted, absent in ((declares, (), contains),
                                       (contains, (declares,), '')):
            saved = {name: module for name, module in sys.modules.items()
                     if name.split('.')[0] == PACKAGE}
            for name in saved:
                del sys.modules[name]
            try:
                importlib.import_module(dotted)
                for name in wanted:
                    self.assertIn(name, sys.modules,
                                  f'{dotted} does not import {name} at module '
                                  f'level — a deferred import is how a cycle '
                                  f'hides from a reader of the import block')
                if absent:
                    self.assertNotIn(
                        absent, sys.modules,
                        f'{dotted} reached {absent}: what a project DECLARES '
                        f'cannot depend on what a tree CONTAINS')
            finally:
                sys.modules.update(saved)

    def test_no_layer_imports_upward(self):
        sources = _sources()
        offenders: list[str] = []
        for prefix, banned, floor in LAYER_RULES:
            in_layer = [(rel, path) for rel, path in sources
                        if rel.startswith(prefix)]
            self.assertGreaterEqual(
                len(in_layer), floor,
                f'{prefix} census too small ({len(in_layer)}) — a moved layer '
                'passes this rule by not being scanned')
            for rel, path in in_layer:
                offenders.extend(_upward_imports(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'an import against the layering. A layer imports DOWNWARD only '
            '(core/ -> repo/ -> cli.py; nothing below reaches up):\n  '
            + '\n  '.join(offenders))


def _imported_modules(tree: ast.Module) -> list[tuple[str, str, int]]:
    """(module, module.name, lineno) for every import in the file.

    Two spellings because `from a.b import c` is ambiguous in the syntax: `c`
    is a module in `from agentic_sdlc.repo.pm import ledger` and a function in
    `from agentic_sdlc.core.config import str_tuple`. An allowlist matches
    EITHER, so it can name a package's public face (`agentic_sdlc.core.config`)
    or one module inside it (`agentic_sdlc.repo.pm.ledger`) and mean exactly
    what it says.

    `ast.walk`, not `tree.body`: a deferred `import x` inside a function is
    still an import, and "we only do it lazily" is exactly how a spawn would
    arrive here.
    """
    out: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend((alias.name, alias.name, node.lineno)
                       for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module != '__future__':
            module = '.' * node.level + (node.module or '')
            out.extend((module, f'{module}.{alias.name}', node.lineno)
                       for alias in node.names)
    return out


def _execution_sites(rel: str, tree: ast.Module) -> list[str]:
    """Every call in this module that could turn a string into behaviour."""
    out: list[str] = []
    for node in _calls(tree):
        func = node.func
        name = (func.id if isinstance(func, ast.Name)
                else func.attr if isinstance(func, ast.Attribute) else '')
        if name in EXECUTORS:
            out.append(f'{rel}:{node.lineno}: {name}()')
        elif (isinstance(func, ast.Attribute)
              and isinstance(func.value, ast.Name) and func.value.id == 'os'
              and func.attr in OS_SPAWNERS):
            out.append(f'{rel}:{node.lineno}: os.{func.attr}()')
    for node in ast.walk(tree):
        owner = node.value if isinstance(node, ast.Subscript) else None
        if (isinstance(owner, ast.Attribute) and owner.attr == MODULE_MAP_ATTR
                and isinstance(owner.value, ast.Name)
                and owner.value.id == MODULE_MAP_OWNER):
            out.append(f'{rel}:{node.lineno}: '
                       f'{MODULE_MAP_OWNER}.{MODULE_MAP_ATTR}[...]')
    return out


class TheToolEmitsAndNeverExecutes(unittest.TestCase):
    """PRIMITIVE 5 — the emit path writes a sink and does nothing else.

    A sink is opened, appended to, closed. Nothing on this path spawns a
    process, imports a module named in config, or resolves a config string to a
    callable — and that is asserted rather than reviewed, because the change
    that would break it is one line long and reads as a convenience.
    """

    PROTECTS = (
        'the emit path opens a sink, appends and closes: it spawns nothing, '
        'imports nothing named in config, and resolves no config string to a '
        'callable',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): rule '
        '2 is what lets a caller run any verb from a git hook, and the moment '
        'one verb spawns, no caller can tell which ones are safe. Its '
        'EMIT_EXECUTION_SPELLINGS loop is a second scoreboard for '
        'test_guard_corpus.py::EveryGuardDeclaresWhatItMustCatch; the offender '
        'list over the shipped module in the same case is not',
    )

    CORPUS = EMIT_EXECUTION_SPELLINGS + EMIT_SPAWN_SPELLINGS

    @staticmethod
    def catches(planted: str) -> bool:
        tree = ast.parse(planted)
        return bool(_execution_sites(EMIT_MODULE, tree)
                    or _spawn_sites(EMIT_MODULE, tree)
                    or _seam_reach_sites(EMIT_MODULE, tree))

    def test_the_emit_path_never_spawns_a_process(self):
        """Three questions, because one of them stopped being able to fail.

        `module_spawns` is the question `tests/conftest.py` derives the `shell`
        mark from, and it is still asked so the two spellings cannot drift —
        but since primitive 11 it is NECESSARY AND NOT SUFFICIENT: one module
        in `src/` imports `subprocess`, so it answers False for every other
        file whatever that file does. The seam reach is what it has become, and
        the `os` spellings are what neither of them can see.
        """
        for source, reaches in EMIT_SPAWN_SPELLINGS:
            with self.subTest(source=source):
                planted = ast.parse(source)
                sites = (_spawn_sites(EMIT_MODULE, planted)
                         + _seam_reach_sites(EMIT_MODULE, planted))
                self.assertEqual(
                    reaches, bool(sites),
                    f'{source!r} classified as '
                    f'{"harmless" if reaches else "a reach to a process"} — '
                    f'the offender list below is only worth what this can '
                    f'still see')
        tree = _tree(SRC / EMIT_MODULE)
        offenders = (_spawn_sites(EMIT_MODULE, tree)
                     + _seam_reach_sites(EMIT_MODULE, tree))
        self.assertEqual(
            [], offenders,
            f'{EMIT_MODULE} reaches a process. An event is WRITTEN here, '
            f'never run (0.5.0/D1): the moment one verb spawns a '
            f'consumer-named command, no caller can tell which verbs are safe '
            f'to run from a git hook, and hard rule 2 is gone for all of '
            f'them:\n  ' + '\n  '.join(offenders))
        self.assertFalse(
            module_spawns(SRC / EMIT_MODULE),
            f'{EMIT_MODULE} imports `subprocess` — which is now the seam\'s '
            f'alone, and would make the emit path the second module in the '
            f'package that can start one.')

    def test_the_emit_path_resolves_no_string_to_a_callable(self):
        for source, is_execution in EMIT_EXECUTION_SPELLINGS:
            with self.subTest(source=source):
                sites = _execution_sites(EMIT_MODULE, ast.parse(source))
                self.assertEqual(
                    is_execution, bool(sites),
                    f'{source!r} classified as '
                    f'{"harmless" if is_execution else "a route to behaviour"} '
                    f'— the guard below is only worth what it can still see')
        offenders = _execution_sites(EMIT_MODULE, _tree(SRC / EMIT_MODULE))
        self.assertEqual(
            [], offenders,
            'the emit path can turn a value into behaviour. `[emit] sink` is a '
            'string a CONSUMER wrote; imported, evaluated or looked up in an '
            'entry-point group, it is the plugin system D1 rejected — and the '
            'tool has stopped being a reader/writer and become a runtime that '
            'owns lifecycle, timeouts and error isolation:\n  '
            + '\n  '.join(offenders))

    def test_the_emit_path_imports_only_the_allowlist(self):
        offenders = [f'{EMIT_MODULE}:{lineno}: {dotted}'
                     for module, dotted, lineno in
                     _imported_modules(_tree(SRC / EMIT_MODULE))
                     if module not in EMIT_IMPORTS
                     and dotted not in EMIT_IMPORTS]
        self.assertEqual(
            [], offenders,
            'an import the emit path does not need. The allowlist is the '
            'mechanism: "imports a module named in config" cannot be '
            'enumerated as a ban list, so the only importable things here are '
            'the five written down in EMIT_IMPORTS. Widening it is a '
            'DECISION:\n  ' + '\n  '.join(offenders))

    def test_the_emit_path_is_the_real_one(self):
        """Rule 4's floor: three assertions of emptiness above pass perfectly
        over a file that was emptied, renamed or never written."""
        self.assertIn(EMIT_MODULE, {rel for rel, _ in _sources()},
                      f'{EMIT_MODULE} is not in the census — the class above '
                      f'is asserting emptiness over a module that moved')
        tree = _tree(SRC / EMIT_MODULE)
        called = {func.attr if isinstance(func, ast.Attribute) else
                  func.id if isinstance(func, ast.Name) else ''
                  for func in (node.func for node in _calls(tree))}
        missing = sorted(set(EMIT_MUST_CALL) - called)
        self.assertEqual(
            [], missing,
            f'{EMIT_MODULE} no longer {" or ".join(missing)}s — it is not '
            f'reading a sink out of config and appending to it, so this class '
            f'is policing something that does not happen')


# --- primitive 6: every field of an emitted event is DERIVED -------------------
# 0.5.0/ft-one-event-shape-serves-three-readers. Three taps carry the belts'
# events, and the line the feature is written against is one sentence:
# `next_checks: ["stories-done", "findings-landed"]` is the engine reading its
# own registry back; `suggested_action: "run a review"` is the engine deciding,
# and rule 9 forbids it. The two are indistinguishable in a review of the row
# and trivially distinguishable in the source that mints it, which is why this
# is here rather than in a checklist.
#
# THE RULE: in a minter, a field's VALUE may not be a string this file wrote.
# It comes from a parameter, from the kind constant, or from the clock —
# `''` is admitted because it spells "the tree did not say", never a sentence.
# Keys are excluded (they are the schema); values are not.
EVENT_MINTERS = (
    ('repo/pm/ready_for.py', '_enter_row'),
    ('repo/conveyor/driver.py', 'verdict_row'),
    ('repo/pm/ledger.py', 'leave_row'),
    ('repo/pm/ledger.py', 'lesson_row'),
)

# The guard is a reader, and the way a reader dies is silently, so every shape
# a minter is written in is probed before anything is graded — whole FUNCTIONS,
# because the shape that defeated the first version of this rule was the
# function-level one (E1).
MINTER_SPELLINGS = (
    ("def m():\n return {'kind': KIND, 'rung': rung}", []),
    ("def m():\n return dict(zip(KEYS, (utc_now(), KIND, rung,"
     " nxt.belt if nxt else '')))", []),
    ("def m():\n return [{'path': c.path, 'why': c.why} for c in have]", []),
    ("def m():\n return {'kind': KIND, 'suggested_action': 'run a review'}",
     ['run a review']),
    ("def m():\n return dict(zip(KEYS, (KIND, 'stories-done')))",
     ['stories-done']),
    # `leave_row`'s own shape: built, subscripted, returned by NAME. Graded on
    # the RETURN VALUE these two are indistinguishable and both invisible.
    ("def m():\n row = dict(zip(KEYS, (a, b)))\n row['value'] = said.value"
     "\n return row", []),
    ("def m():\n row = dict(zip(KEYS, (a, b)))"
     "\n row['suggested_action'] = 'run a review'\n return row",
     ['run a review']),
    # A docstring and a refusal are not fields the row carries.
    ('def m():\n """Mint a row."""\n raise ValueError(\'refusing to mint\')',
     []),
    # A module constant is a sentence this file wrote with a name on it (E6).
    ("SUGGESTED = 'run a review'\ndef m():\n"
     " return dict(zip(KEYS, (KIND, SUGGESTED)))", ['run a review']),
    ("KIND_LEAVE = 'rung.leave'\ndef m():\n"
     " return dict(zip(KEYS, (KIND_LEAVE, rung)))", []),
)

# The ONE string source a minter may name: the kind, which IS the schema. Any
# other module constant reaching a value position is a sentence this file
# wrote, so a new kind has to be admitted here BY NAME.
ADMITTED_CONSTANTS = ('KIND_ENTER', 'KIND_VERDICT', 'KIND_LEAVE',
                      'KIND_LESSON')


def _module_strings(tree: ast.AST) -> dict[str, str]:
    """Top-level `NAME = '…'`, minus the kinds: what a bare `Name` in a value
    position resolves to. A dotted `mod.NAME` is another module's schema and is
    not resolved here."""
    found: dict[str, str] = {}
    for node in getattr(tree, 'body', []):
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str) and node.value.value):
            continue
        if node.targets[0].id not in ADMITTED_CONSTANTS:
            found[node.targets[0].id] = node.value.value
    return found


def _zip_values(node: ast.AST) -> list[ast.AST] | None:
    """`zip(KEYS, (…))`'s VALUE arguments, or None: the first argument is the
    schema, exactly as a `Dict`'s keys are."""
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == 'zip' and len(node.args) > 1):
        return list(node.args[1:])
    return None


def _minted_strings(node: ast.AST, constants: dict[str, str]) -> list[str]:
    """Every string a row's VALUES resolve to. A `Dict`'s keys and a `zip`'s
    key tuple are the schema and are skipped; everything else is walked, so a
    hardcoded sentence inside a comprehension, a conditional or a module
    constant is still seen."""
    found: list[str] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, ast.Dict):
            stack.extend(current.values)
            continue
        keyed = _zip_values(current)
        if keyed is not None:
            stack.extend(keyed)
            continue
        if isinstance(current, ast.Constant):
            if isinstance(current.value, str) and current.value:
                found.append(current.value)
            continue
        if isinstance(current, ast.Name) and current.id in constants:
            found.append(constants[current.id])
            continue
        stack.extend(ast.iter_child_nodes(current))
    return found


def _row_values(func: ast.AST) -> list[ast.AST]:
    """Every expression a minter puts in a VALUE position, anywhere in its
    body: a dict literal's values, `dict(zip(KEYS, …))`'s value tuple, and a
    later `row[key] = …`.

    The BODY, never `ast.Return`'s value — that is E1. `leave_row`'s only
    return is `return row`, a bare Name, so grading return VALUES graded
    nothing in the one minter carrying the next-step fields, and a planted
    `row['suggested_action'] = 'run a review'` was invisible. A docstring and a
    `raise`'s message are in no value position and stay ungraded."""
    found: list[ast.AST] = []
    stack: list[ast.AST] = [func]
    while stack:
        current = stack.pop()
        if isinstance(current, ast.Dict):
            found.extend(current.values)
            continue
        keyed = _zip_values(current)
        if keyed is not None:
            found.extend(keyed)
            continue
        if (isinstance(current, ast.Assign)
                and any(isinstance(t, ast.Subscript)
                        for t in current.targets)):
            found.append(current.value)
            continue
        stack.extend(ast.iter_child_nodes(current))
    return found


def _minted_by(func: ast.AST, constants: dict[str, str]) -> list[str]:
    """What one minter WROTE into its row, sorted: the readers, composed."""
    return sorted(word for value in _row_values(func)
                  for word in _minted_strings(value, constants))


def _graded(source: str) -> list[str]:
    """The whole reader over one module — its constants, then its minter."""
    module = ast.parse(source)
    minter = [n for n in ast.walk(module) if isinstance(n, ast.FunctionDef)][-1]
    return _minted_by(minter, _module_strings(module))


class EveryEventFieldIsDerived(unittest.TestCase):
    """PRIMITIVE 6 — a payload holds what the tree said, never what the tool
    thinks. The same shape as the breadcrumb's guard: assert the TRACE, not the
    sentence, because a hardcoded next-step passes every substring check."""

    PROTECTS = (
        'a minted payload carries what the tree said and never what the tool '
        'decided, asserted against the TRACE rather than against the sentence',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): this '
        'is the 0.5.0 incident itself. The reader walked ast.Return in a '
        'function whose only return is a bare name, so a planted field was '
        'invisible while the guard reported 4-of-4 and the count went to the '
        'orchestrator as proof',
    )

    # The table above says WHICH words a minter wrote; the corpus asks the one
    # question a blind reader fails — did it see anything at all.
    CORPUS = tuple((source, bool(expected))
                   for source, expected in MINTER_SPELLINGS)

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_graded(planted))

    def test_the_reader_can_still_tell_a_derived_field_from_a_written_one(self):
        for source, expected in MINTER_SPELLINGS:
            with self.subTest(source=source):
                self.assertEqual(expected, _graded(source))

    def test_no_minter_writes_a_field_this_package_decided(self):
        seen = 0
        offenders: list[str] = []
        for rel, name in EVENT_MINTERS:
            tree = _tree(SRC / rel)
            constants = _module_strings(tree)
            for node in ast.walk(tree):
                if not (isinstance(node, ast.FunctionDef)
                        and node.name == name):
                    continue
                seen += 1
                offenders.extend(f'{rel}::{name}: {word!r}'
                                 for word in _minted_by(node, constants))
        self.assertEqual(
            len(EVENT_MINTERS), seen,
            f'{seen} of {len(EVENT_MINTERS)} minters found — one was renamed '
            f'or moved, and this rule is grading what is left')
        self.assertEqual(
            [], offenders,
            'a field an emitted row carries that nothing in the tree said. '
            'Every key must resolve to `[pm.states.*]`, to '
            '`registry_for(operation)` or to a frontmatter field — a value '
            'written here is the engine deciding what should happen next, '
            'which rule 9 forbids and a review would pass:\n  '
            + '\n  '.join(offenders))


# --- primitive 6: config is read PER RUN, never at import ---------------------
# Found 2026-09-05: `repo/checks/doc.py` bound `[doc] scope` and `[doc]
# ephemeral` into module-level constants at import. Once the module was in
# `sys.modules` — which `check all` does, and which any test touching the gate
# roster does — a later run in a repo whose `[doc]` section was MALFORMED used
# the first repo's values and never raised. The gate reported findings, or
# none, where the contract says exit 2.
#
# It passed alone and failed after a peer imported first, which is the worst
# shape a defect can have: the suite's answer depended on its own order.
CONFIG_CALLS = ('config_section', 'load_config')


def _import_time_config_reads(label: str, tree: ast.Module) -> list[str]:
    """`config_section(...)` / `load_config(...)` called at module scope."""
    hits = []
    # TOP LEVEL ONLY. A `def`/`class` body is where these calls BELONG, so a
    # walk that descends into one reports the fix as the defect.
    executable = [n for n in tree.body
                  if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                        ast.ClassDef))]
    for node in executable:
        for inner in ast.walk(node):
            if not isinstance(inner, ast.Call):
                continue
            name = getattr(inner.func, 'id', None) or getattr(
                inner.func, 'attr', None)
            if name in CONFIG_CALLS:
                hits.append(f'{label}:{inner.lineno}: {name}() at import')
    return hits


def module_level_config_reads(path: Path) -> list[str]:
    """The same reader over a file, with the one thing a snippet cannot have."""
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'))
    except (OSError, SyntaxError, UnicodeDecodeError):
        # A module this walk cannot READ is a module it cannot clear, so it is
        # reported rather than skipped. (`UNREADABLE` was a name that did not
        # exist: the one branch here that could not itself be exercised raised
        # NameError instead of naming the file.)
        return [f'{path.name}: unreadable — not parsed, so not cleared']
    return _import_time_config_reads(path.name, tree)


class ConfigIsReadPerRunNeverAtImport(unittest.TestCase):
    """PRIMITIVE 6b — nothing binds a config value while it is being imported."""

    PROTECTS = (
        'no module binds a config value while it is being imported, so the '
        'exit-2 contract is true every run rather than the first one',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): a '
        'value bound at import belongs to whichever repo imported the module '
        'first, and a malformed section in any later one silently stops raising',
    )

    CORPUS = (
        ("SCOPE = config_section('doc')", True),
        ("SCOPE = tuple(load_config().get('doc', {}))", True),
        ("if True:\n    SCOPE = config_section('doc')", True),
        # Where these calls BELONG. A walk that descends into a body reports
        # the fix as the defect, so both spellings are probed.
        ("def scope():\n    return config_section('doc')", False),
        ("class C:\n    def scope(self):\n        return load_config()", False),
        ("SCOPE = ('doc', 'ephemeral')", False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        return bool(_import_time_config_reads(SCRATCH_MODULE,
                                              ast.parse(planted)))

    def test_no_module_reads_its_config_at_import_time(self):
        """A config value bound at import is a refusal that fires once per
        process.

        The cwd does not move mid-run in production, and `config_section` is
        `lru_cache`d — so reading inside the function that needs it costs one
        cached lookup and buys the exit-2 contract being true every time rather
        than the first time.
        """
        offenders: list[str] = []
        for path in sorted((REPO_ROOT / 'src').rglob('*.py')):
            if '__pycache__' in path.parts:
                continue
            offenders.extend(module_level_config_reads(path))
        self.assertEqual(
            [], offenders,
            'config read at import — the value is bound to whichever repo '
            'imported the module FIRST, and a malformed section in any later '
            'one stops raising:\n  ' + '\n  '.join(offenders))


# Everything that turns a version string into something ordered or numeric.
VERSION_PARSERS = (
    'packaging', 'pkg_resources', 'distutils', 'LooseVersion',
    'StrictVersion', 'parse_version', 'version_tuple', 'VERSION_RE',
)
# Splitting a version on its SEPARATOR is the shape a comparator grows back
# as; splitting a file on newlines is how you read one, so the ARGUMENT is
# what decides.
VERSION_SEPARATORS = ('.', '-', '+')
ORDERING_CALLS = ('int', 'float', 'sorted', 'max', 'min')


def _version_comparator_imports(rel: str, tree: ast.Module) -> list[str]:
    """Every import in this module of something that orders a version."""
    out: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or '']
        out.extend(f'{rel}: imports {name}' for name in names
                   if name.split('.')[0] in VERSION_PARSERS)
    return out


def _version_split_sites(label: str, func: ast.AST) -> list[str]:
    """Every place inside one function that takes a version APART."""
    out: list[str] = []
    for node in ast.walk(func):
        if not isinstance(node, ast.Call):
            continue
        if (isinstance(node.func, ast.Attribute)
                and node.func.attr == 'split'
                and any(isinstance(a, ast.Constant)
                        and a.value in VERSION_SEPARATORS for a in node.args)):
            out.append(f'{label} splits on a version separator')
        if (isinstance(node.func, ast.Name)
                and node.func.id in ORDERING_CALLS):
            out.append(f'{label} calls {node.func.id}()')
    return out


class NoCodePathParsesAVersion(unittest.TestCase):
    """0.3.0: order is a DECLARED list, so the engine never reads a version
    string as a structure.

    The claim `a-milestone-declares-its-version` makes to consumers is that
    `"1.1.1"` and `"cow"` are equally valid — scheme-agnosticism as a
    consequence of ordering by position rather than as a promise. A comparator
    creeping back in would break every tree whose versions are not semver
    (`0.90.3.2` is the real one that motivated this), and it would do it
    silently, by sorting wrong rather than by raising.

    This is a source-shaped gate because the behaviour it protects is an
    ABSENCE, and an absence has no call site to assert against.
    """

    PROTECTS = (
        'order is a declared list, and no module turns a version string into '
        'something ordered or numeric',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS), and '
        'the guard argues it itself: the behaviour protected is an ABSENCE and '
        'an absence has no call site to assert against. A comparator creeping '
        'back sorts 0.90.3.2 wrong rather than raising',
    )

    CORPUS = (
        ('import packaging', True),
        ('from distutils.version import LooseVersion', True),
        ('from packaging.version import parse as parse_version', True),
        ("def bumped(v):\n    return v.split('.')[0]", True),
        ('def bumped(v):\n    return int(v)', True),
        ('def bumped(order):\n    return sorted(order)[-1]', True),
        ('import re', False),
        ("def read(text):\n    return text.splitlines()", False),
        ("def read(text):\n    return text.split('\\n')", False),
        ('def bumped(order, v):\n    return order.index(v) + 1', False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        tree = ast.parse(planted)
        return bool(_version_comparator_imports(SCRATCH_MODULE, tree)
                    or any(_version_split_sites(SCRATCH_MODULE, node)
                           for node in ast.walk(tree)
                           if isinstance(node, (ast.FunctionDef,
                                                ast.AsyncFunctionDef))))

    def test_no_module_imports_a_version_comparator(self):
        offenders = []
        for rel, path in _sources():
            offenders.extend(_version_comparator_imports(rel, _tree(path)))
        self.assertEqual(
            [], offenders,
            'a version comparator was imported — order is a POSITION in '
            '`order`, and a comparator cannot sort `0.90.3.2` anyway')

    def test_the_release_helpers_never_split_a_version_into_components(self):
        """The modules that HANDLE versions do not take one apart.

        Scoped to the release surface rather than to all of `src`: `.split('.')`
        is how every module reads a dotted grain id, and a repo-wide ban would
        be a gate nobody could keep green. The census floor below is what keeps
        the narrowing honest.
        """
        surface = {
            'repo/pm/inventory.py': ('releases_file', 'declared_order',
                                 'milestone_version', 'version_claims',
                                 'milestone_of_version', 'entry_is_shipped',
                                 'entry_is_dangling', 'current_release',
                                 'current_milestone',
                                 # Review F4: the two likeliest regrowth sites.
                                 # Both READ a version out of a file, which is
                                 # one step from taking one apart.
                                 'shipped_version'),
            'repo/checks/pm.py': ('_release_findings',),
            'repo/conveyor/steps.py': ('check_version_sync', '_version_in'),
        }
        by_rel = {rel: path for rel, path in _sources()}
        offenders, scanned = [], 0
        for rel, wanted in surface.items():
            self.assertIn(rel, by_rel, f'{rel} moved — this gate now scans nothing')
            found = {n.name: n for n in ast.walk(_tree(by_rel[rel]))
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            for name in wanted:
                self.assertIn(name, found,
                              f'{rel}:{name} is gone — rename it here too, or '
                              f'this gate silently stops checking it')
                scanned += 1
                # The argument is what decides, not the call — otherwise the
                # gate could not cover `shipped_version`, which is exactly
                # where a parser would reappear.
                offenders.extend(_version_split_sites(f'{rel}:{name}',
                                                      found[name]))
        # Rule 4: a gate scanning nothing FAILS rather than passing quietly.
        self.assertGreaterEqual(scanned, 11,
                                'the release surface collapsed — this gate is '
                                'asserting emptiness over almost nothing')
        self.assertEqual([], offenders,
                         'a release helper took a version apart — "did it '
                         'increase" is a position in `order`, never a parse')


# --- primitive 7: one project, said the same way in both files -----------------
# `bg-the-package-docstring-names-another-project`. `src/agentic_sdlc/__init__.py`
# is two lines, and the first one was about a different project: headless scene
# introspection for a game engine, copied from the sibling repo this package was
# extracted from and shipped in every release since. It is the MODULE docstring,
# so it is what `help(agentic_sdlc)` prints and the first thing a reader opening
# the package sees.
#
# `[project] description` held the true sentence the whole time — one fact stored
# twice, in disagreement, with nothing that could say so out loud. That is hard
# rule 7's shape one altitude up: `__version__` and `version` move together
# because a gate makes them, and these two do now as well.
#
# THE RULE, both directions, with neither sentence written down in this file:
#   * the docstring NAMES this package — every word of `[project] name` is in it;
#   * and it names nothing else — every word IT uses is a word `[project] name`
#     or `[project] description` already uses.
#
# A subset rather than a ban list, for the reason `EMIT_IMPORTS` is one: "a
# sentence about somebody else's project" is not a vocabulary anybody can
# enumerate, and a roster of foreign project names would be this package knowing
# about a repo that is not it (rule 8). What makes the drift impossible is that
# the only words admitted here are the ones the description already chose —
# widening the docstring means widening the description in the same change,
# which is the two sites moving together, which is the whole point.
PYPROJECT = REPO_ROOT / 'pyproject.toml'
PROJECT_TABLE = 'project'
NAME_FIELD = 'name'
DESCRIPTION_FIELD = 'description'
PACKAGE_INIT = '__init__.py'
# Floors, in the spirit of MIN_SOURCES: a subset test passes perfectly over an
# empty docstring, and over a description nobody wrote. Both sit well under what
# is really there (20 and 40 distinct words) and well over zero.
MIN_DOCSTRING_WORDS = 10
MIN_DESCRIPTION_WORDS = 20
# (sentence, vocabulary, the words the vocabulary never used). Graded against a
# SYNTHETIC vocabulary, so the reader is proven on what it CATCHES without
# pinning the probe to whatever `[project] description` happens to say. The
# foreign sentence names a SHAPE and never a repo (rule 8).
DOCSTRING_SPELLINGS = (
    ('gizmo — a tracker and its gate.', 'gizmo a tracker and its gate', []),
    ('gizmo — headless scene introspection for a game engine.',
     'gizmo a tracker and its gate',
     ['engine', 'for', 'game', 'headless', 'introspection', 'scene']),
    # Case is not a hiding place, and neither is a hyphen: a compound word is
    # its parts, so `markdown-and-frontmatter` cannot carry a foreign name past
    # the comparison by being punctuated into one token.
    ('GIZMO — a TRACKER, and its gate.', 'gizmo a tracker and its gate', []),
    ('a markdown-and-frontmatter tracker.',
     'a markdown and frontmatter tracker', []),
    ('gizmo — a tracker, 4.x.', 'gizmo a tracker', ['x']),
)


def _words(text: str) -> set[str]:
    """The alphabetic words of a sentence, case-folded."""
    return set(re.findall(r'[a-z]+', text.lower()))


def _foreign_words(sentence: str, vocabulary: str) -> list[str]:
    """Every word `sentence` uses that `vocabulary` never does, sorted."""
    return sorted(_words(sentence) - _words(vocabulary))


def _package_docstring() -> str | None:
    """What `help(agentic_sdlc)` prints, read from the shipped file.

    By AST rather than by import, like everything else here: the docstring is a
    literal in the source, so reading it this way boots nothing (rule 2) and is
    exactly the sentence a reader opening the file gets.
    """
    return ast.get_docstring(_tree(SRC / PACKAGE_INIT))


def _project_naming_fields() -> tuple[str, str]:
    """(`[project] name`, `[project] description`) from the real pyproject.toml.

    READ, never restated. A copy of either sentence in this file would be the
    THIRD copy, and a third copy drifts exactly the way the second one did.
    """
    with PYPROJECT.open('rb') as handle:
        table = tomllib.load(handle)[PROJECT_TABLE]
    return table[NAME_FIELD], table[DESCRIPTION_FIELD]


class TheDocstringAndTheDescriptionNameOneProject(unittest.TestCase):
    """PRIMITIVE 7 — the package describes itself the same way in both files.

    The sentence was wrong for four releases and no gate could have said so:
    `check doc` holds this repo's prose to its make-target and file-path claims,
    and its scope is markdown, while a docstring is prose making a claim about
    what the package IS from inside a `.py` file. Nothing was pointed at it.
    """

    PROTECTS = (
        'the package describes itself with the same sentence in pyproject.toml '
        'and in its own top-level docstring',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS) on the '
        'read side: the sentence was wrong for four releases because check doc '
        'grades markdown, and a docstring is a claim about what this package IS '
        'made from inside a .py file that nothing was pointed at',
    )

    # This reader takes TWO strings, so a planted case is the pair. The gate
    # replaying it hands `catches` whatever the guard put here and reads
    # nothing into it.
    CORPUS = tuple(((sentence, vocabulary), bool(expected))
                   for sentence, vocabulary, expected in DOCSTRING_SPELLINGS)

    @staticmethod
    def catches(planted: tuple[str, str]) -> bool:
        sentence, vocabulary = planted
        return bool(_foreign_words(sentence, vocabulary))

    def test_the_reader_names_the_words_a_vocabulary_never_used(self):
        """The comparison is only worth what it can still see: three assertions
        of emptiness pass perfectly over a reader that stopped comparing."""
        for sentence, vocabulary, expected in DOCSTRING_SPELLINGS:
            with self.subTest(sentence=sentence):
                self.assertEqual(expected, _foreign_words(sentence, vocabulary))

    def test_the_docstring_names_this_package_and_no_other(self):
        docstring = _package_docstring()
        name, description = _project_naming_fields()
        self.assertIsNotNone(
            docstring,
            f'{PACKAGE_INIT} has no module docstring — `help(agentic_sdlc)` '
            f'prints nothing, and an absence is a finding (rule 11)')
        self.assertGreaterEqual(
            len(_words(docstring)), MIN_DOCSTRING_WORDS,
            f'{len(_words(docstring))} distinct word(s) in the docstring — a '
            f'subset check over a sentence this short is a gate that checks '
            f'nothing')
        self.assertGreaterEqual(
            len(_words(description)), MIN_DESCRIPTION_WORDS,
            f'{len(_words(description))} distinct word(s) in [project] '
            f'description — the vocabulary below would admit almost anything')
        self.assertEqual(
            [], _foreign_words(name, docstring),
            'the module docstring does not name this package. `help()` opens '
            'with it, so it says what the thing IS, starting with what it is '
            'called')
        self.assertEqual(
            [], _foreign_words(docstring, f'{name} {description}'),
            'the module docstring uses words [project] description never does. '
            'One fact, two files: a sentence here that pyproject.toml does not '
            'support is the second copy drifting — this one shipped four '
            'releases describing a different project. Say it in the '
            "description's words, or widen the description in this same change")


# --- primitive 8: no test points `git` at THIS checkout ------------------------
# `bg-the-suite-can-flip-the-host-repo-to-bare`. Twice on 2026-09-06 a full-suite
# run left the real checkout's `.git/config` holding `bare = true`, after which
# every git command in the worktree failed with *fatal: this operation must be
# run in a work tree*. No commits were lost and no module reproduced it alone:
# each git-spawning module was run on its own against this checkout with
# `.git/config` hashed either side, and all six left it unchanged. All three
# occurrences happened while subagents ran their own test processes against this
# same worktree.
#
# THIS GATE NAMES NO CAUSE, and the bug is filed unresolved on purpose. It
# removes the PRECONDITION instead: whatever rewrites `.git/config`, it is a
# `git` process pointed at this repository, and a suite that never points one
# here cannot be the writer however the race is shaped. That is assertable from
# source, which a race is not.
#
# A spawn reaches this checkout in four ways and every one of them is visible in
# the syntax:
#   * no `cwd=` at all — the call runs wherever pytest was started, which is the
#     repo root. That was the one real offender: `git init -q --bare <path>`,
#     a verb whose whole job is writing a `.git/config`, spawned loose;
#   * a `cwd=` rooted at this file tree;
#   * `GIT_DIR`/`GIT_WORK_TREE` in `env=`, and `-C`/`--git-dir`/`--work-tree` in
#     the argv. Both OUTRANK `cwd=`, so neither can be read as a confinement —
#     they are banned outright rather than checked against a target this file
#     cannot resolve. `cwd=` already says where a git command runs, and one
#     mechanism is the point.
TESTS_DIR = REPO_ROOT / 'tests'
# Floors in the spirit of MIN_SOURCES: this gate asserts an EMPTY offender list,
# and an empty list is what a moved `tests/` produces too. Both sit well under
# what is really there (56 modules and 48 `git` call sites at the time of
# writing) and well over zero.
MIN_TEST_MODULES = 30
MIN_GIT_SPAWNS = 20
# `SPAWN_MODULE` and `SPAWNERS` — the one module a spawn crosses and the
# constructors that reach it — are declared with primitive 11 above and read
# here too, since primitive 11 is the rule that a spawn crosses that module and
# this one is the rule about where it may point.
GIT = 'git'
# What `tests/support` calls a path inside this checkout. A `cwd=` naming any of
# them is the host repository: git discovers upward, so `tests/fixtures` is this
# repository exactly as the root is.
SUPPORT_ROOTS = ('REPO_ROOT', 'TESTS', 'FIXTURES', 'SUPPORT')
SUPPORT_PACKAGES = ('support', 'conftest')
# The other way a module names itself: anything derived from its own `__file__`
# is under `tests/`, whatever it is called locally (`REPO`, `ROOT`, …). Derived
# rather than rostered, because a roster of variable NAMES goes stale silently
# and the next spelling would walk straight past it.
FILE_ANCHOR = '__file__'
GIT_LOCATION_ENV = ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR',
                    'GIT_INDEX_FILE', 'GIT_OBJECT_DIRECTORY')
GIT_LOCATION_FLAGS = ('-C', '--git-dir', '--work-tree')
NO_CWD = 'no cwd='
HOST_CWD = 'cwd= names this checkout'


def _test_sources() -> list[tuple[str, Path]]:
    """(repo-relative posix path, file) for every module under `tests/`.

    Through `core.walk` for the reason `_sources()` is: a gate that hand-rolled
    an `rglob` to police the suite would be policing itself with the thing it
    bans one directory over.
    """
    from agentic_sdlc.core import walk as walkmod
    from agentic_sdlc.core.walk import Kind
    found = walkmod.descendants(TESTS_DIR, Kind.FILE, suffix='.py')
    out = [(p.relative_to(REPO_ROOT).as_posix(), p) for p in found.kept]
    assert len(out) >= MIN_TEST_MODULES, (
        f'{len(out)} test module(s) under {TESTS_DIR} — expected at least '
        f'{MIN_TEST_MODULES}. The gate below asserts an EMPTY offender list, so '
        f'a census this small passes it while checking nothing.')
    return out


def _argv0(node: ast.Call) -> str | None:
    """The program a spawn runs, when the syntax says so.

    `['git', …]` and `('git', …)` are the list forms; a bare `'git status'` is
    the `shell=True` one. Anything else — `[sys.executable, …]`, `[exe, *argv]`
    — is not a `git` call this file can identify, and is not counted as one.
    """
    if not node.args:
        return None
    first = node.args[0]
    if isinstance(first, (ast.List, ast.Tuple)) and first.elts:
        head = first.elts[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            return head.value
        return None
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        words = first.value.split()
        return words[0] if words else None
    return None


def _own_scope(node: ast.AST):
    """Every node under `node` that belongs to `node`'s OWN scope.

    Descent stops at a nested `def`/`class`, because its names are its own. A
    walk that did not stop there put every `other = parent / name` in the module
    into one namespace, and one function's `source = REPO_ROOT / …` then made
    `cwd=other` in an unrelated helper read as this checkout — a gate reporting
    a call that was already correct, which is rule 4's other half.
    """
    stack = list(ast.iter_child_nodes(node))
    while stack:
        current = stack.pop()
        yield current
        if not isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef,
                                    ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(current))


def _host_rooted_names(scope: ast.AST, inherited: frozenset[str]) -> set[str]:
    """`inherited`, plus the names THIS scope roots in the checkout.

    Two seeds and a fixpoint, the shape `support_spawn_names()` uses in
    `tests/conftest.py`: a `SUPPORT_ROOTS` name imported from `support`, and an
    assignment whose value mentions `__file__`. Then repeat, so
    `SRC = REPO_ROOT / 'src'` joins on the pass after `REPO_ROOT` does.
    """
    names = set(inherited)
    assignments: list[ast.Assign | ast.AnnAssign] = []
    for node in _own_scope(scope):
        if isinstance(node, ast.ImportFrom) and (
                (node.module or '').split('.')[0] in SUPPORT_PACKAGES):
            names.update(alias.asname or alias.name for alias in node.names
                         if alias.name in SUPPORT_ROOTS)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)) and node.value:
            assignments.append(node)
    changed = True
    while changed:
        changed = False
        for node in assignments:
            targets = (node.targets if isinstance(node, ast.Assign)
                       else [node.target])
            bound = {t.id for t in targets if isinstance(t, ast.Name)}
            if bound <= names or not _is_host_rooted(node.value, names):
                continue
            names |= bound
            changed = True
    return names


def _is_host_rooted(node: ast.expr, names: set[str]) -> bool:
    """True when this expression is built from this module's own file or from a
    name already known to hold a path inside the checkout."""
    return any(isinstance(inner, ast.Name)
               and (inner.id == FILE_ANCHOR or inner.id in names)
               for inner in ast.walk(node))


def _leading_literal(node: ast.expr) -> str | None:
    """The literal an argv element STARTS with, through the two spellings a
    computed one takes: `'--git-dir=' + d` and `f'--git-dir={d}'`. The flag is
    what decides, and it is a constant in all three."""
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _leading_literal(node.left)
    if isinstance(node, ast.JoinedStr) and node.values:
        return _leading_literal(node.values[0])
    return None


def _reaches_the_host(node: ast.Call, names: set[str]) -> list[str]:
    """Why this `git` spawn is pointed at this checkout; empty when it is not.

    All four reasons are collected rather than the first one returned: a call
    fixed by adding `cwd=` while it still exports `GIT_DIR` has moved the
    problem, and a reader has to see both lines to know that.
    """
    keywords = {kw.arg: kw.value for kw in node.keywords if kw.arg}
    why: list[str] = []
    cwd = keywords.get('cwd')
    if cwd is None:
        why.append(NO_CWD)
    elif _is_host_rooted(cwd, names):
        why.append(HOST_CWD)
    env = keywords.get('env')
    if isinstance(env, ast.Dict):
        why.extend(f'env= sets {key.value}' for key in env.keys
                   if isinstance(key, ast.Constant)
                   and key.value in GIT_LOCATION_ENV)
    argv = node.args[0] if node.args else None
    if isinstance(argv, (ast.List, ast.Tuple)):
        for element in argv.elts:
            literal = _leading_literal(element)
            flag = literal.split('=')[0] if literal else None
            if flag in GIT_LOCATION_FLAGS:
                why.append(f'argv carries {flag}')
    return why


def _is_a_git_spawn(node: ast.Call) -> bool:
    """`subprocess.<spawner>(['git', …])` — the module spelled the way
    `tests/conftest.py` derives the `shell` mark from, so the tier and this
    boundary read one mechanism rather than two."""
    func = node.func
    return (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
            and func.value.id == SPAWN_MODULE and func.attr in SPAWNERS
            and _argv0(node) == GIT)


def _git_spawn_sites(tree: ast.Module) -> list[tuple[int, list[str]]]:
    """(lineno, reasons) for every `git` spawn in one module, scope by scope.

    Both halves matter and both are graded: what this counts as a `git` spawn at
    all, and which of those it says reach the host. A classifier that stopped
    seeing `git` would report an empty offender list forever.
    """
    out: list[tuple[int, list[str]]] = []

    def visit(scope: ast.AST, inherited: frozenset[str]) -> None:
        names = _host_rooted_names(scope, inherited)
        for node in _own_scope(scope):
            if isinstance(node, ast.Call) and _is_a_git_spawn(node):
                out.append((node.lineno, _reaches_the_host(node, names)))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                   ast.ClassDef)):
                visit(node, frozenset(names))

    visit(tree, frozenset())
    return sorted(out)


# (source, what the classifier must say) — the confined spellings this suite is
# already written in, the four ways a spawn reaches this checkout, and the
# spawns that are not `git` at all and must stay uncounted. `[[]]` is one git
# call with nothing against it; `[]` is no git call found.
GIT_SPAWN_SPELLINGS = (
    # Confined: a directory this file can see is not the checkout.
    ("subprocess.run(['git', 'init', '-q'], cwd=root, check=True)", [[]]),
    ("subprocess.run(['git', 'status'], cwd=tmp_path / 'x')", [[]]),
    ("subprocess.check_output(['git', 'log'], cwd=repo.root)", [[]]),
    ("subprocess.run(('git', 'add', '-A'), cwd=other, check=True)", [[]]),
    # Loose: the pytest process stands in the repo root, so this IS the host.
    ("subprocess.run(['git', 'status'])", [[NO_CWD]]),
    ("subprocess.run(['git', 'init', '-q', '--bare', str(o)], check=True)",
     [[NO_CWD]]),
    ("subprocess.Popen(['git', 'gc'])", [[NO_CWD]]),
    ("subprocess.run('git status', shell=True)", [[NO_CWD]]),
    # Named, and the name is this checkout — by import or by `__file__`.
    ("from support import REPO_ROOT\nsubprocess.run(['git', 'gc'],"
     " cwd=REPO_ROOT)", [[HOST_CWD]]),
    ("REPO = Path(__file__).resolve().parents[1]\n"
     "subprocess.run(['git', 'gc'], cwd=REPO)", [[HOST_CWD]]),
    # One hop further out: a name built from a name built from `__file__`.
    ("REPO = Path(__file__).parent\nWORK = REPO / 'sub'\n"
     "subprocess.run(['git', 'gc'], cwd=WORK)", [[HOST_CWD]]),
    # The overrides, which outrank `cwd=` and so cannot be excused by one.
    ("subprocess.run(['git', 'gc'], cwd=tmp, env={'GIT_DIR': str(tmp)})",
     [['env= sets GIT_DIR']]),
    ("subprocess.run(['git', 'gc'], cwd=tmp,"
     " env={'GIT_WORK_TREE': str(tmp)})", [['env= sets GIT_WORK_TREE']]),
    ("subprocess.run(['git', '-C', str(tmp), 'status'], cwd=tmp)",
     [['argv carries -C']]),
    ("subprocess.run(['git', '--git-dir=' + d, 'status'], cwd=tmp)",
     [['argv carries --git-dir']]),
    ("subprocess.run(['git', f'--work-tree={d}', 'status'], cwd=tmp)",
     [['argv carries --work-tree']]),
    # Every reason at once, and every one of them named: a call fixed halfway
    # is a call still pointed here.
    ("from support import REPO_ROOT\n"
     "subprocess.run(['git', '-C', d, 'gc'], cwd=REPO_ROOT,"
     " env={'GIT_DIR': d})",
     [[HOST_CWD, 'env= sets GIT_DIR', 'argv carries -C']]),
    # Not `git`, and this gate does not widen into the rest of the suite:
    # `make` against REPO_ROOT is what test_makefile_gates.py IS.
    ("subprocess.run(['make', 'check'], cwd=REPO_ROOT)", []),
    ("subprocess.run([sys.executable, '-m', 'agentic_sdlc.cli'])", []),
    ("subprocess.run(['bash', str(hook)], input=event)", []),
    # An argv this file cannot read is not a `git` call it can name. Stated
    # rather than implied: it is the honest limit of an AST, the same one
    # `_replace_is_a_path_replace` runs into.
    ("subprocess.run([exe, 'status'])", []),
)


class NoTestSpawnsGitAgainstThisCheckout(unittest.TestCase):
    """PRIMITIVE 8 — every `git` in this suite runs in a scratch tree.

    Not "no test corrupts the repo", which is a hope. The assertion is
    syntactic and total: a `git` spawn either names a directory that is not this
    checkout, or it is a finding by `file:line`.
    """

    PROTECTS = (
        'every git spawn in this suite names a directory that is not this '
        'checkout',
        'load-bearing — sin 2 (a write that looks legitimate and is not), '
        'turned on the suite rather than on the tool: a test that commits into '
        'this checkout leaves a tree that looks like work somebody did. The '
        'assertion is syntactic and total by file:line rather than the hope '
        'that no test corrupts the repo',
    )

    # `[[]]` is one git call with nothing against it — a CLEAN case that is
    # not an empty result, which is why "caught" is the guard's own word here
    # rather than the truthiness of what its reader returned.
    CORPUS = tuple((source, any(reasons for reasons in expected))
                   for source, expected in GIT_SPAWN_SPELLINGS)

    @staticmethod
    def catches(planted: str) -> bool:
        return any(reasons for _, reasons
                   in _git_spawn_sites(ast.parse(planted)))

    def test_the_classifier_can_still_tell_a_confined_spawn_from_a_loose_one(self):
        for source, expected in GIT_SPAWN_SPELLINGS:
            with self.subTest(source=source):
                graded = [reasons for _, reasons in
                          _git_spawn_sites(ast.parse(source))]
                self.assertEqual(expected, graded)

    def test_no_test_module_spawns_git_against_this_checkout(self):
        offenders: list[str] = []
        for rel, path in _test_sources():
            offenders.extend(
                f'{rel}:{lineno}: {reason}'
                for lineno, reasons in _git_spawn_sites(_tree(path))
                for reason in reasons)
        self.assertEqual(
            [], offenders,
            'a `git` spawn pointed at THIS checkout. A full-suite run twice '
            'left `.git/config` holding `bare = true`, and the cause was never '
            'established — so the precondition goes instead: every `git` in '
            'this suite names a scratch directory with `cwd=`, and none of them '
            'inherits this repository, exports GIT_DIR at it, or reaches it '
            'with `-C`:\n  ' + '\n  '.join(offenders))

    def test_the_git_census_is_the_real_suite(self):
        """Rule 4's floor. The case above asserts an EMPTY list, and empty is
        also what a renamed `tests/`, a moved `subprocess` spelling or a
        classifier that stopped recognising `git` all produce."""
        modules = _test_sources()
        spawns = [(rel, lineno) for rel, path in modules
                  for lineno, _ in _git_spawn_sites(_tree(path))]
        self.assertGreaterEqual(
            len(spawns), MIN_GIT_SPAWNS,
            f'{len(spawns)} `git` spawn(s) across {len(modules)} test '
            f'module(s) — expected at least {MIN_GIT_SPAWNS}. A boundary over '
            f'calls nobody makes is a boundary that holds nothing shut.')
        self.assertGreaterEqual(
            len({rel for rel, _ in spawns}), 5,
            f'{len({rel for rel, _ in spawns})} module(s) spawn `git` — the '
            f'integration tier collapsed, or the census stopped seeing it')


# --- primitive 13: every module opens with one sentence, and no two the same ---
# `ft-the-module-says-what-it-does`. Four stories split this package's biggest
# modules and the fifth graded the result; this is the gate under it, and the
# reason it is a gate rather than a review note is what the grading found: SIX of
# the 47 docstrings here opened with a FRAGMENT wrapped onto the second line
# (`report.py — … a milestone's raw rows, added up, or`), which reads as a
# sentence in a diff and is not one in `help()`, and nothing could say so.
#
# WHAT IT HOLDS, AND WHAT IT DOES NOT. It holds that every shipped module opens
# with a terminated sentence, and that no two modules open with the SAME one
# after their own name prefix is stripped. Whether a sentence is TRUE of its
# module is judgement, graded in the audit at
# `st-every-module-opens-with-one-true-sentence`'s close, and a test asserting it
# would be a second scoreboard with no ground truth to read. So this is the
# cheap half — and it is the half that fails the day someone copy-pastes a
# header, which is the defect that was sitting in the tree when it was written:
# `conveyor/__init__.py` and `conveyor/driver.py` shipped ONE claim in two
# spellings, close enough that an exact comparison passed over both.
TERMINAL = ('.', '?', '!')
HEADING_MARK = '#'
# In the spirit of `MIN_SOURCES`: `"""walk.py"""` is a label and `"""The one
# place this package enumerates a filesystem."""` is a sentence. Nothing shipped
# here is under six words, so this is a floor and not a style rule — 0.6.0's
# ruling against size gates stands, and a LENGTH rule on a docstring is out of
# scope for the story that added this.
MIN_SENTENCE_WORDS = 4
# The house prefix — `driver.py — `, `check budget — `, `templates/ — `, `pm — `.
# STRIPPED before the collision comparison, because two modules saying the same
# thing after their own names is exactly the finding, and keeping the prefix
# would let a pasted header hide behind the filename it was pasted into. At most
# two bare tokens, so `What a project DECLARES — the categories…` keeps its whole
# sentence: that em dash is prose, not a name.
SENTENCE_PREFIX = re.compile(r'^[\w./-]+(?: [\w./-]+)? — ')
# The floor under the census of SENTENCES rather than of files. `_sources()`
# already refuses an empty tree; this refuses a READER that stopped returning
# sentences, which is the other way an empty offender list is produced. Well
# under the 47 really there and well over zero.
MIN_SENTENCES = 20
# The three zero-length package markers, exempt BY NAME with the reason written
# down: `core/`, `repo/` and `repo/checks/` declare nothing and re-export
# nothing, so `help(agentic_sdlc.core)` has no subject and a sentence there would
# be prose about an empty file. `repo/pm/__init__.py` and `repo/verify/__init__.py`
# are NOT here, because they say what their package is and earn their line.
#
# THE ROSTER FAILS IN THREE DIRECTIONS, all three of them build failures, which
# is the property `tests/test_guard_corpus.py`'s `UNCOVERED` has: a module with
# no docstring that is not named here is a finding; an entry whose file has
# GAINED CONTENT is a module now and owes a sentence (graded by
# `_docstring_findings`, probed in `CORPUS`); and an entry naming nothing in the
# census has moved or been renamed, so the line goes. An entry matching nothing
# is as much a finding as a file missing from the list.
EMPTY_PACKAGES = frozenset((
    'core/__init__.py',
    'repo/__init__.py',
    'repo/checks/__init__.py',
))


def _opening_sentence(source: str) -> str | None:
    """The first line of a module's docstring, or None when there is none.

    By AST and never by import, for `_package_docstring`'s reason one primitive
    up: the docstring is a literal in the source, so reading it this way boots
    nothing (rule 2) and returns exactly the line `help()` opens with.
    """
    doc = ast.get_docstring(ast.parse(source), clean=False)
    if doc is None or not doc.strip():
        return None
    return doc.strip().splitlines()[0].strip()


def _sentence_defect(source: str) -> str:
    """Why this module's opening line is not a sentence, or '' when it is."""
    first = _opening_sentence(source)
    if first is None:
        return 'no module docstring — `help()` prints nothing about it'
    if first.startswith(HEADING_MARK):
        return f'opens with a heading rather than a sentence: {first!r}'
    if not first.endswith(TERMINAL):
        return (f'the first line is a FRAGMENT — it does not end in one of '
                f'{TERMINAL}, so the sentence wraps and `help()` opens on half '
                f'of it: {first!r}')
    if len(first.split()) < MIN_SENTENCE_WORDS:
        return f'the first line is a label rather than a sentence: {first!r}'
    return ''


def _collation(sentence: str) -> str:
    """One opening sentence, as the collision comparison sees it."""
    return ' '.join(SENTENCE_PREFIX.sub('', sentence).split()).casefold()


def _docstring_findings(census: Iterable[tuple[str, str]]) -> list[str]:
    """Every module in `census` that does not open with its OWN sentence.

    `census` is (module-relative posix path, source) pairs: the real tree for the
    case below, a planted one for `CORPUS`. Both halves of the question live in
    this one reader so that one corpus covers both — a module with no sentence,
    and two modules with the same sentence. A collision is a relation BETWEEN two
    modules, and a classifier handed one file at a time could never see one.
    """
    out: list[str] = []
    by_sentence: dict[str, list[str]] = {}
    for rel, source in census:
        if rel in EMPTY_PACKAGES:
            if source.strip():
                out.append(
                    f'{rel}: named on EMPTY_PACKAGES and not empty any more — '
                    f'it holds code now, so it is a module and owes a sentence, '
                    f'and the exemption line goes in the same change')
            continue
        defect = _sentence_defect(source)
        if defect:
            out.append(f'{rel}: {defect}')
            continue
        sentence = _opening_sentence(source)
        assert sentence is not None  # `_sentence_defect` already said so
        by_sentence.setdefault(_collation(sentence), []).append(rel)
    out.extend(f'{" and ".join(sorted(rels))}: both open with the same sentence '
               f'— two modules cannot each be the one place something happens'
               for rels in by_sentence.values() if len(rels) > 1)
    return sorted(out)


class EveryModuleSaysWhatItDoes(unittest.TestCase):
    """PRIMITIVE 13 — one module, one opening sentence, and no two the same.

    The first line of a module docstring is what `help()` opens with and what a
    reader opening the file lands on, and it was the one prose surface in `src/`
    with nothing pointed at it: `check doc` grades markdown, primitive 7 grades
    the PACKAGE docstring against `pyproject.toml`, and between them 49 modules
    could say anything, or nothing, or the same thing twice.
    """

    PROTECTS = (
        'every shipped module opens with a terminated sentence, no two modules '
        'open with the same one, and the three empty package markers are exempt '
        'by name in a roster that fails in both directions',
        'load-bearing — sin 1 (a gate that misses drift and prints PASS): a '
        'docstring is prose inside a .py file, so no behaviour test can see one '
        'go missing or go stale, and a pasted header leaves two modules each '
        'claiming to be the one place something happens. Six modules opened on a '
        'fragment and `conveyor/__init__.py` and `conveyor/driver.py` shipped one '
        'claim in two spellings when this was written',
    )

    # The planted input is a whole CENSUS — ((rel, source), …) — because half of
    # what this guard grades is a relation between two modules. One corpus, both
    # halves, and the exemption's content direction probed in it rather than
    # asserted twice.
    CORPUS = (
        ((('a.py', ''),), True),
        ((('a.py', '"""# The walker"""\n'),), True),
        ((('a.py', '"""walk.py"""\n'),), True),
        # The real defect at HEAD: a sentence wrapped onto line two, which reads
        # as a sentence in the diff and is a fragment in `help()`.
        ((('a.py', '"""the four belt-entry conditions, each answering with an\n'
                   'exit code.\n"""\n'),), True),
        # Two modules, one sentence: the pasted header.
        ((('a.py', '"""The one place this package enumerates a filesystem."""\n'),
          ('b.py', '"""The one place this package enumerates a filesystem."""\n')),
         True),
        # The same collision behind the house prefix, which is why the prefix is
        # stripped BEFORE the comparison and not after.
        ((('a.py', '"""a.py — the belts: every check, then one write."""\n'),
          ('b.py', '"""b.py — the belts: every check, then one write."""\n')),
         True),
        # The exemption's own direction: a named marker that gained content.
        ((('core/__init__.py', 'X = 1\n'),), True),
        ((('a.py', '"""The one place this package enumerates a filesystem."""\n'),),
         False),
        ((('a.py', '"""a.py — the engine all four belts run on."""\n'),
          ('b.py', '"""b.py — the four check lists that engine runs."""\n')), False),
        # An empty marker that IS named, which is what all three really are.
        ((('core/__init__.py', ''),), False),
    )

    @staticmethod
    def catches(planted: tuple[tuple[str, str], ...]) -> bool:
        return bool(_docstring_findings(planted))

    def test_every_module_opens_with_one_sentence_and_no_two_the_same(self):
        """Three questions of one census read, for `test_guard_corpus.py`'s
        reason: the suite has no case headroom under `[tests] cases`, and a
        second and third walk of 50 modules to assert the roster's other
        direction would buy nothing the named messages below do not already say.
        """
        census = [(rel, path.read_text(encoding='utf-8'))
                  for rel, path in _sources()]
        findings = _docstring_findings(census)
        self.assertEqual(
            [], findings,
            'a module that does not open with its own sentence. The first line '
            'is what `help()` prints and what a reader lands on, so it says what '
            'this module IS in one sentence — terminated, on one line — and no '
            'other module says the same thing:\n  ' + '\n  '.join(findings))
        sentences = [rel for rel, source in census
                     if rel not in EMPTY_PACKAGES
                     and _opening_sentence(source) is not None]
        self.assertGreaterEqual(
            len(sentences), MIN_SENTENCES,
            f'{len(sentences)} opening sentence(s) read across '
            f'{len(census)} module(s) — expected at least {MIN_SENTENCES}. The '
            f'assertion above is an EMPTY offender list, and a reader that '
            f'stopped returning sentences produces one too.')
        dangling = sorted(EMPTY_PACKAGES - {rel for rel, _ in census})
        self.assertEqual(
            [], dangling,
            'EMPTY_PACKAGES names a module that is not in the census — it moved '
            'or was renamed, and an entry nothing matches is a hole waiting for '
            'a module to move into it. Delete the line:\n  '
            + '\n  '.join(dangling))
