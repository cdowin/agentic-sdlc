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

from agentic_sdlc.core import apply
from agentic_sdlc.repo.pm import model

# grain -> template filename; shared docs are addressed by slot name, so there
# is no table to sync.
GRAINS = ('milestone', 'feature', 'story', 'bug')
DOCS = ('handoff', 'decisions')


class MissingTemplate(Exception):
    """No packaged or project template by that name."""


def _packaged(name: str) -> str | None:
    try:
        return (resources.files('agentic_sdlc.repo.pm.templates')
                .joinpath(f'{name}.md').read_text(encoding='utf-8'))
    except (FileNotFoundError, ModuleNotFoundError):
        return None


def load(cfg: model.PmConfig, name: str) -> str:
    """The template text for `name`, project override winning."""
    if cfg.template_dir:
        tdir = cfg.root / cfg.template_dir
        # Exact name from a listing: `Path.is_file()` is case-insensitive on
        # macOS and not on Linux.
        if model.dir_entries(tdir).get(f'{name}.md') == 'file':
            return model.read_raw(tdir / f'{name}.md')
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
    want = model.SLOT_HEADER.get(slot)
    if want is None:
        return ''
    got = model.header_of(path)
    return '' if got == want or got in set(model.SLOT_HEADER.values()) else want


def _fill_header(path: Path, slot: str, actions: list[tuple[str, Path]]) -> None:
    """Prepend the slot's instruction line to a doc that predates it;
    additive, one line. Writability was settled in the pre-pass.
    """
    want = _header_wanted(path, slot)
    if not want:
        return
    try:
        body = model.read_raw(path)
    except (OSError, UnicodeDecodeError):
        return
    eol = '\r\n' if '\r\n' in body else '\n'
    model.write_raw(path, f'{want}{eol}{eol}{body}')
    actions.append(('restored the header line of', path))


def scaffold(cfg: model.PmConfig, kind: str, gdir: Path,
             values: dict[str, str]) -> list[tuple[str, Path]]:
    """Fill one grain dir's required slots. Idempotent and never clobbers: an
    existing slot is left byte-identical, a slot under another case is
    refused, and no shared doc or directory is minted — those appear on
    first write.
    """
    file_slots = (model.MILESTONE_FILE_SLOTS if kind == 'milestone'
                  else model.FEATURE_FILE_SLOTS)
    # Renamed and header-repaired when PRESENT, never created when absent.
    managed = file_slots + (model.MILESTONE_OPTIONAL_SLOTS if kind == 'milestone'
                            else model.FEATURE_OPTIONAL_SLOTS)
    actions: list[tuple[str, Path]] = []
    # The grain directory is the first byte written, so a name the filesystem
    # refuses or an unwritable roadmap is a refusal that can truthfully say
    # nothing was written.
    try:
        apply.raise_on_error(apply.make_dir(gdir))
    except OSError as err:
        raise ScaffoldRefused(
            f'{cfg.rel(gdir)}/ could not be created ({err}) — nothing was '
            f'written; shorten the id or name, or make {cfg.rel(gdir.parent)}/ '
            f'writable, and re-run') from err

    # Every refusal for the whole grain is raised before the first slot write
    # (rule 3). A slot under another case is refused, never renamed or written
    # past: that would mint a twin or truncate the legacy bytes.
    entries = model.dir_entries(gdir)
    for slot in managed:
        variants = model.case_variants(entries, slot)
        if variants:
            raise ScaffoldRefused(
                f'{cfg.rel(gdir)}/ holds {", ".join(variants)} where this '
                f'package expects {slot} — nothing was written; rename it '
                f'yourself (`git mv --force {cfg.rel(gdir / variants[0])} '
                f'{cfg.rel(gdir / slot)}`), then re-run')
        if slot not in entries:
            continue
        # The link before the kind: `is_dir()` follows a symlink, and a
        # symlinked slot points outside the grain.
        if (gdir / slot).is_symlink():
            raise ScaffoldRefused(
                f'{cfg.rel(gdir / slot)} is a SYMLINK to '
                f'{os.readlink(gdir / slot)} — the scaffolder writes inside '
                f'the grain it was asked to fill and does not follow a link '
                f'out of it; nothing was written; replace it with the real '
                f'file')
        if entries[slot] == 'dir':
            # Refused, not crashed: exit 1 is reserved for findings.
            raise ScaffoldRefused(
                f'{cfg.rel(gdir / slot)} is a DIRECTORY and {slot} is a '
                f'file slot — nothing was written; move it aside')

    # The fill phase is decided here too: every template is loaded and decoded,
    # every header prepend proved writable, before a byte moves.
    bodies: dict[str, str] = {}
    for slot in file_slots:
        if entries.get(slot) == 'file':
            continue
        name = model.SLOT_TEMPLATE[slot]
        try:
            bodies[slot] = render(load(cfg, name), values)
        except (OSError, UnicodeDecodeError) as err:
            raise ScaffoldRefused(
                f'the {name} template cannot be read ({err}) — nothing was '
                f'written' + (f'; fix it under {cfg.template_dir}/, or delete '
                              f'it there to fall back to the packaged one'
                              if cfg.template_dir else '')) from err
    for slot in managed:
        now = gdir / slot
        if slot in bodies or entries.get(slot) != 'file':
            continue
        want = _header_wanted(now, slot)
        if want and not os.access(now, os.W_OK):
            raise ScaffoldRefused(
                f'{cfg.rel(now)} is missing its header line and is not '
                f'writable — nothing was written; make it writable, or prepend '
                f'the line yourself: {want!r}')

    # A real write can still fail on what no listing shows; it becomes a
    # refusal naming what already landed.
    try:
        for slot in managed:
            if slot in bodies:
                write(gdir / slot, bodies[slot])
                actions.append(('created', gdir / slot))
            elif entries.get(slot) == 'file':
                _fill_header(gdir / slot, slot, actions)
    except (OSError, UnicodeDecodeError) as err:
        did = '; '.join(f'{what} {cfg.rel(p)}' for what, p in actions)
        raise ScaffoldRefused(
            f'{cfg.rel(gdir)}/ could not be filled ({err}) — this one could not '
            f'be decided in advance, so the grain is PART-FILLED: '
            + (did or 'nothing had been written yet')
            + '; fix it and re-run, which fills only the gaps') from err
    return actions


def install(cfg: model.PmConfig, force: bool = False) -> tuple[list[Path],
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
    entries = model.dir_entries(target_dir)
    for name in (*GRAINS, *DOCS):
        text = _packaged(name)
        if text is None:
            continue
        slot = f'{name}.md'
        others = model.case_variants(entries, slot)
        if others:
            variants.extend((other, slot) for other in others)
            continue
        if entries.get(slot) == 'file' and not force:
            continue
        target = target_dir / slot
        write(target, text)
        out.append(target)
    return out, variants
