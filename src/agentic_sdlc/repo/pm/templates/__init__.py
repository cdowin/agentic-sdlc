"""templates/ — the grain and doc templates, and where a project overrides
them.

The package holds both the loader and the `.md` files, addressed through
`importlib.resources`. `{name}` placeholders are filled by `render`. A file
under `[pm] template_dir` wins; anything missing falls back to the package.
"""
from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

from agentic_sdlc.core import apply, frontmatter
from agentic_sdlc.repo.pm import inventory, vocabulary

# grain -> template filename; shared docs are addressed by slot name, so there
# is no table to sync.
GRAINS = vocabulary.FLOW_KINDS
DOCS = ('handoff', 'decisions')


class MissingTemplate(Exception):
    """No packaged or project template by that name."""


def _packaged(name: str) -> str | None:
    try:
        return (resources.files('agentic_sdlc.repo.pm.templates')
                .joinpath(f'{name}.md').read_text(encoding='utf-8'))
    except (FileNotFoundError, ModuleNotFoundError):
        return None


def load(cfg: vocabulary.PmConfig, name: str) -> str:
    """The template text for `name`, project override winning."""
    if cfg.template_dir:
        tdir = cfg.root / cfg.template_dir
        # Exact name from a listing: `Path.is_file()` is case-insensitive on
        # macOS and not on Linux.
        if inventory.dir_entries(tdir).get(f'{name}.md') == 'file':
            return frontmatter.read_raw(tdir / f'{name}.md')
    text = _packaged(name)
    if text is None:
        raise MissingTemplate(
            f'no template {name!r} — packaged templates are '
            f'{", ".join((*GRAINS, *DOCS))}'
            + (f', and none was found in {cfg.template_dir}/'
               if cfg.template_dir else ''))
    return text


def render(text: str, values: dict[str, str]) -> str:
    """Fill `{placeholder}`s; an unknown one is left visible, never blanked,
    because prose contains braces.
    """
    out = text
    for key, val in values.items():
        out = out.replace('{' + key + '}', val)
    return out


def write(path: Path, text: str) -> None:
    """Create a grain file through `core.apply`, preserving the template's
    line endings; `decide=False` because the refusals here are worded in
    slots, not paths.
    """
    apply.raise_on_error(apply.write(path, text))


class ScaffoldRefused(Exception):
    """The scaffolder cannot guarantee a correct result, so it did nothing."""


def _header_wanted(path: Path, slot: str) -> str:
    """The instruction line this doc is missing, or '' when it has one — so a
    wording change can never stack two headers.
    """
    want = vocabulary.SLOT_HEADER.get(slot)
    if want is None:
        return ''
    got = inventory.header_of(path)
    return '' if got == want or got in vocabulary.KNOWN_SLOT_HEADERS else want


def _fill_header(path: Path, slot: str, actions: list[tuple[str, Path]]) -> None:
    """Prepend the slot's instruction line to a doc that predates it;
    additive, one line. Writability was settled in the pre-pass.
    """
    want = _header_wanted(path, slot)
    if not want:
        return
    try:
        body = frontmatter.read_raw(path)
    except (OSError, UnicodeDecodeError):
        return
    eol = '\r\n' if '\r\n' in body else '\n'
    frontmatter.write_raw(path, f'{want}{eol}{eol}{body}')
    actions.append(('restored the header line of', path))


def slot_paths(kind: str, doc: Path) -> dict[str, Path]:
    """{slot name: where it sits} for one grain.

    A grain used to be a DIRECTORY with named slots inside it. It is a
    DOCUMENT in a pool now, and its shared docs sit beside it under its own
    filename — `ft-x.md`, `ft-x-decisions.md`, `ft-x-review.md`. Same slots,
    one function deciding where each one lives, so the scaffolder below never
    joins a name onto a directory itself.
    """
    file_slots = (vocabulary.MILESTONE_FILE_SLOTS if kind == vocabulary.GRAIN_MILESTONE
                  else vocabulary.FEATURE_FILE_SLOTS)
    optional = (vocabulary.MILESTONE_OPTIONAL_SLOTS if kind == vocabulary.GRAIN_MILESTONE
                else vocabulary.FEATURE_OPTIONAL_SLOTS)
    out = {slot: doc for slot in file_slots}
    for slot in optional:
        out[slot] = doc.with_name(f'{doc.stem}-{slot}')
    return out


def scaffold(cfg: vocabulary.PmConfig, kind: str, doc: Path,
             values: dict[str, str]) -> list[tuple[str, Path]]:
    """Fill one grain's slots. Idempotent and never clobbers: an existing slot
    is left byte-identical, and no shared doc is minted — those appear on
    first write, which is why an absent handoff is a signal `check pm` can
    report (0.4.0/D6).
    """
    slots = slot_paths(kind, doc)
    file_slots = (vocabulary.MILESTONE_FILE_SLOTS if kind == vocabulary.GRAIN_MILESTONE
                  else vocabulary.FEATURE_FILE_SLOTS)
    actions: list[tuple[str, Path]] = []
    # The pool is the first byte written, so an unwritable roadmap is a
    # refusal that can truthfully say nothing was written.
    try:
        apply.raise_on_error(apply.make_dir(doc.parent))
    except OSError as err:
        raise ScaffoldRefused(
            f'{cfg.rel(doc.parent)}/ could not be created ({err}) — nothing '
            f'was written; make {cfg.rel(doc.parent.parent)}/ writable and '
            f're-run') from err

    # Every refusal for the whole grain is raised before the first slot write
    # (rule 3). A slot under another case is refused, never renamed or written
    # past: on a case-insensitive filesystem `0.1-decisions.md` and
    # `0.1-DECISIONS.md` are the same bytes, and on a sensitive one they are a
    # twin nobody reads.
    entries = inventory.dir_entries(doc.parent)
    for slot, path in slots.items():
        variants = inventory.case_variants(entries, path.name)
        if variants:
            raise ScaffoldRefused(
                f'{cfg.rel(doc.parent)}/ holds {", ".join(variants)} where '
                f'this package expects {path.name} — nothing was written; '
                f'rename it yourself (`git mv --force '
                f'{cfg.rel(doc.parent / variants[0])} {cfg.rel(path)}`), then '
                f're-run')
        if not path.exists() and not path.is_symlink():
            continue
        # The link before the kind: `is_dir()` follows a symlink, and a
        # symlinked slot points outside the pool.
        if path.is_symlink():
            raise ScaffoldRefused(
                f'{cfg.rel(path)} is a SYMLINK to {os.readlink(path)} — the '
                f'scaffolder writes the grain it was asked to fill and does '
                f'not follow a link out of it; nothing was written; replace '
                f'it with the real file')
        if path.is_dir():
            raise ScaffoldRefused(
                f'{cfg.rel(path)} is a DIRECTORY and {slot} is a file slot — '
                f'nothing was written; move it aside')

    # The fill phase is decided here too: every template is loaded and decoded,
    # every header prepend proved writable, before a byte moves.
    bodies: dict[str, str] = {}
    for slot in file_slots:
        if slots[slot].is_file():
            continue
        name = vocabulary.SLOT_TEMPLATE[slot]
        try:
            bodies[slot] = render(load(cfg, name), values)
        except (OSError, UnicodeDecodeError) as err:
            raise ScaffoldRefused(
                f'the {name} template cannot be read ({err}) — nothing was '
                f'written' + (f'; fix it under {cfg.template_dir}/, or delete '
                              f'it there to fall back to the packaged one'
                              if cfg.template_dir else '')) from err
    for slot, path in slots.items():
        if slot in bodies or not path.is_file():
            continue
        want = _header_wanted(path, slot)
        if want and not os.access(path, os.W_OK):
            raise ScaffoldRefused(
                f'{cfg.rel(path)} is missing its header line and is not '
                f'writable — nothing was written; make it writable, or prepend '
                f'the line yourself: {want!r}')

    # A real write can still fail on what no listing shows; it becomes a
    # refusal naming what already landed.
    try:
        for slot, path in slots.items():
            if slot in bodies:
                write(path, bodies[slot])
                actions.append(('created', path))
            elif path.is_file():
                _fill_header(path, slot, actions)
    except (OSError, UnicodeDecodeError) as err:
        did = '; '.join(f'{what} {cfg.rel(p)}' for what, p in actions)
        raise ScaffoldRefused(
            f'{cfg.rel(doc)} could not be filled ({err}) — this one could not '
            f'be decided in advance, so the grain is PART-FILLED: '
            + (did or 'nothing had been written yet')
            + '; fix it and re-run, which fills only the gaps') from err
    return actions


def install(cfg: vocabulary.PmConfig, force: bool = False) -> tuple[list[Path],
                                                              list[tuple[str, str]]]:
    """Copy the packaged templates into `template_dir`; returns (written, case
    variants). A case variant is reported and never written past, `--force`
    included: on a case-insensitive filesystem the write would truncate it.
    """
    if not cfg.template_dir:
        raise MissingTemplate(
            'no [pm] template_dir configured — set one before installing '
            'templates to edit (e.g. template_dir = "pm/templates")')
    out: list[Path] = []
    variants: list[tuple[str, str]] = []
    target_dir = cfg.root / cfg.template_dir
    entries = inventory.dir_entries(target_dir)
    for name in (*GRAINS, *DOCS):
        text = _packaged(name)
        if text is None:
            continue
        slot = f'{name}.md'
        others = inventory.case_variants(entries, slot)
        if others:
            variants.extend((other, slot) for other in others)
            continue
        if entries.get(slot) == 'file' and not force:
            continue
        target = target_dir / slot
        write(target, text)
        out.append(target)
    return out, variants
