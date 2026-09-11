"""The one place this package reads and writes a frontmatter block.

`document()` parses a file once and holds that parse against the file's `stat`, so a
tree is read once per process; `field_of`, `list_field_of` and the three writers all
answer from it, and every write rewrites the lines it was asked for and preserves every
other byte, terminators included. `tests/test_boundaries.py` forbids the parse, the raw
read and the raw write elsewhere.
"""
from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from agentic_sdlc.core import apply


# Split on '\n' only: `splitlines()` also breaks on U+2028, U+2029, form feed
# and lone CR, and would rewrite them on join (rule 3).
_FENCE = re.compile(r'^---[ \t]*\r?$')


def _split(text: str) -> list[str]:
    return text.split('\n')


# `newline=''` disables universal-newline translation both ways, so a CRLF file
# stays CRLF; `Path.read_text` only gained the parameter in 3.13.
def read_raw(path: Path) -> str:
    with path.open('r', encoding='utf-8', newline='') as fh:
        return fh.read()


def write_raw(path: Path, text: str) -> None:
    """The grain-file write, through `core.apply` with the same disabled
    newline translation; a failure comes back as `OSError`."""
    try:
        apply.raise_on_error(apply.write(path, text))
    finally:
        # However the write ended, the parse held here is a claim about
        # bytes that may be gone.
        forget_document(path)


def _eol(line: str) -> str:
    """The CR half of a CRLF terminator, so a rewritten line keeps the file's
    convention."""
    return '\r' if line.endswith('\r') else ''


def _fence_bounds(lines: list[str]) -> tuple[int, int] | None:
    """Index of the opening and closing `---` of the leading block, or None."""
    if not lines or not _FENCE.match(lines[0]):
        return None
    for i in range(1, len(lines)):
        if _FENCE.match(lines[i]):
            return 0, i
    return None


def field_in(lines: Sequence[str], key: str) -> str:
    """`field_of` over lines already read."""
    bounds = _fence_bounds(lines)
    if bounds is None:
        return ''
    for line in lines[bounds[0] + 1:bounds[1]]:
        if line.startswith(f'{key}:'):
            # .strip() also removes the CRLF carriage return.
            return unquote(line[len(key) + 1:].strip())
    return ''


# --- ONE READ PER DOCUMENT ----------------------------------------------------
# Every field used to be its own `open()` plus a re-split of the whole file —
# 2.1M opens over a 700-document tree, `make check` at 87s
# (bg-check-pm-reopens-every-file-per-field).
#
# PER PROCESS and nothing else: a module dict, never written anywhere. Every hit
# re-`stat`s the file and re-parses when the stamp moved, and `write_raw` drops
# what it rewrote — a gate answering off bytes that have moved on is rule 4's
# first cardinal sin wearing a speedup.


@dataclass(frozen=True)
class Document:
    """One document read once. `lines` is a TUPLE because the cache hands one
    object to every reader, and a reader that could edit it would be editing
    the next reader's answer.
    """

    lines: tuple[str, ...]
    bounds: tuple[int, int] | None
    fields: dict[str, str]

    @property
    def text(self) -> str:
        """The bytes as read — `_split` is `str.split`, so the join is exact."""
        return '\n'.join(self.lines)

    def field(self, key: str) -> str:
        """`field_in`'s answer, off the parsed dict. A key carrying a `:`
        cannot be keyed on — `a:b` matches the line `a:b: v`, whose key is
        `a` — so the scan itself answers that one."""
        if ':' in key:
            return field_in(self.lines, key)
        return self.fields.get(key, '')

    def list_field(self, key: str) -> list[str]:
        """`list_field_of`'s answer, off the bounds already found."""
        return _list_in(self.lines, self.bounds, key)


def parse_document(text: str) -> Document:
    """One document's text, parsed. The scalars are read exactly as `field_in`
    reads them — first line wins, the key is what precedes the first `:` at
    column 0 — so the dict answers what a scan would answer."""
    lines = _split(text)
    bounds = _fence_bounds(lines)
    fields: dict[str, str] = {}
    if bounds is not None:
        for line in lines[bounds[0] + 1:bounds[1]]:
            key, sep, value = line.partition(':')
            if sep:
                fields.setdefault(key, unquote(value.strip()))
    return Document(lines=tuple(lines), bounds=bounds, fields=fields)


# A cap rather than an unbounded dict: a tree big enough for the cache to
# matter must not turn a gate into a memory hog. Entries leave oldest-first.
DOCUMENT_CACHE_MAX_CHARS = 64_000_000

# {str(path): (stamp, characters, the parse)}; `_stamp` says what a stamp is.
_DOCUMENTS: dict[str, tuple[tuple[int, ...], int, Document]] = {}
_DOCUMENT_CHARS = 0


def _stamp(path) -> tuple[int, ...] | None:
    """What must be unchanged for a parse to still be this file's, or None when
    the thing read is not a file on disk. `pm report --rev` reads git BLOBS
    through these functions and a blob has no `stat`, so those reads are never
    cached rather than cached under a key nothing could invalidate."""
    stat = getattr(path, 'stat', None)
    if stat is None:
        return None
    st = stat()
    return (st.st_mtime_ns, st.st_size, st.st_ino, st.st_dev)


def document(path) -> Document:
    """This file's parse — from the cache when the file has not moved since.
    Raises what `read_raw` raises, which every caller here already answers."""
    key = str(path)
    try:
        stamp = _stamp(path)
    except OSError:
        forget_document(path)
        raise
    if stamp is not None:
        held = _DOCUMENTS.get(key)
        if held is not None and held[0] == stamp:
            return held[2]
    text = read_raw(path)
    doc = parse_document(text)
    if stamp is not None:
        _remember(key, stamp, len(text), doc)
    return doc


def _remember(key: str, stamp: tuple[int, ...], chars: int,
              doc: Document) -> None:
    global _DOCUMENT_CHARS
    replaced = _DOCUMENTS.pop(key, None)
    if replaced is not None:
        _DOCUMENT_CHARS -= replaced[1]
    _DOCUMENTS[key] = (stamp, chars, doc)
    _DOCUMENT_CHARS += chars
    while _DOCUMENT_CHARS > DOCUMENT_CACHE_MAX_CHARS and len(_DOCUMENTS) > 1:
        # Insertion order is eviction order; the entry just added stays.
        _DOCUMENT_CHARS -= _DOCUMENTS.pop(next(iter(_DOCUMENTS)))[1]


def forget_document(path) -> None:
    """Drop one document's parse. Every write through `write_raw` comes here."""
    global _DOCUMENT_CHARS
    dropped = _DOCUMENTS.pop(str(path), None)
    if dropped is not None:
        _DOCUMENT_CHARS -= dropped[1]


def documents_held() -> int:
    """How many parses the cache is holding — the only way to ask."""
    return len(_DOCUMENTS)


def field_of(path: Path, key: str) -> str:
    """Scalar value of `key` inside the leading frontmatter block, or '' —
    never from the prose body."""
    try:
        return document(path).field(key)
    except (OSError, UnicodeDecodeError):
        return ''


def unquote(value: str) -> str:
    """Strip the quotes a milestone id carries (`id: "0.28"` -> `0.28`)."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


# A block-style list is the only non-scalar frontmatter this package reads:
# reordering is the main edit and a block diff shows what MOVED (0.4.0/D4).
def _without_trailing_comment(value: str) -> str:
    """`"0.1.0"  # the first` -> `"0.1.0"`.

    An inline comment was read INTO the value, which then failed to unquote and
    left the quotes on — one annotated entry silently changed the spelling of
    every version the reader returned (review A3). Only a `#` OUTSIDE the
    quotes ends the value.
    """
    value = value.strip()
    if value[:1] in ('"', "'"):
        close = value.find(value[0], 1)
        if close != -1:
            return value[:close + 1]
        return value
    head = value.split('#', 1)[0]
    return head.strip() or value


_LIST_ITEM = re.compile(r'^[ \t]+-[ \t]*(?P<value>.*?)[ \t]*\r?$')


def list_field_of(path: Path, key: str) -> list[str]:
    """Block-style list under `key` in the leading frontmatter, or []. `key:`
    must carry nothing but a comment on its own line; a scalar on it is a
    different shape and reads as no list at all, never a one-element one.
    """
    try:
        doc = document(path)
    except (OSError, UnicodeDecodeError):
        return []
    return doc.list_field(key)


def _list_in(lines: Sequence[str], bounds: tuple[int, int] | None,
             key: str) -> list[str]:
    """`list_field_of` over lines and bounds already found."""
    if bounds is None:
        return []
    open_i, close_i = bounds
    for i in range(open_i + 1, close_i):
        if not lines[i].startswith(f'{key}:'):
            continue
        rest = lines[i][len(key) + 1:].strip()
        if rest and not rest.startswith('#'):
            return []
        out: list[str] = []
        for line in lines[i + 1:close_i]:
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                # Blank lines SPACE a long plan and comment lines ANNOTATE
                # one. Truncating at either dropped every entry below it —
                # silently, and `--append` then wrote a duplicate and reported
                # a successful append (review A2).
                continue
            m = _LIST_ITEM.match(line)
            if m is None:
                break
            out.append(unquote(_without_trailing_comment(m.group('value'))))
        return out
    return []


def sequence_defect(path: Path, key: str) -> str:
    """Why the block list under `key` here cannot be rewritten, or ''.

    The KEY is the caller's word, not this module's: `order:` is the PM layer's
    vocabulary and nothing here knows it. Every branch spells the key it was
    given, so the message cannot name one key while the scan reads another.
    """
    try:
        doc = document(path)
    except (OSError, UnicodeDecodeError) as err:
        return f'could not be read as UTF-8 text ({err.__class__.__name__})'
    lines, bounds = doc.lines, doc.bounds
    if bounds is None:
        return f'has no frontmatter block to hold `{key}:`'
    open_i, close_i = bounds
    for i in range(open_i + 1, close_i):
        if lines[i].startswith(f'{key}:'):
            rest = lines[i][len(key) + 1:].strip()
            if rest and not rest.startswith('#'):
                return (f'carries `{key}:` as a scalar ({rest!r}) rather '
                        f'than a block list — one `- "<id>"` per line')
    return ''


def set_field(path: Path, key: str, value: str) -> bool:
    """Set-or-insert one frontmatter scalar, preserving every other byte;
    False without writing when there is no frontmatter block or the write
    fails."""
    return set_fields(path, {key: value})


def set_fields(path: Path, updates: dict[str, str]) -> bool:
    """Set-or-insert several frontmatter scalars in one read and one write, so
    a multi-key rewrite (`pm move`'s three) cannot land half (rule 3)."""
    try:
        text = read_raw(path)
    except (OSError, UnicodeDecodeError):
        return False
    lines = _split(text)
    bounds = _fence_bounds(lines)
    if bounds is None:
        return False
    open_i, close_i = bounds
    for key, value in updates.items():
        for i in range(open_i + 1, close_i):
            if lines[i].startswith(f'{key}:'):
                lines[i] = f'{key}: {value}{_eol(lines[i])}'
                break
        else:
            lines.insert(close_i, f'{key}: {value}{_eol(lines[close_i])}')
            close_i += 1
    try:
        write_raw(path, '\n'.join(lines))
    except OSError:
        return False
    return True


def set_list_field(path: Path, key: str, values: list[str]) -> bool:
    """Rewrite the block list under `key`, preserving every other byte.

    The writer that has to be byte-honest: a diff showing what MOVED is why the
    plan is a grain and not TOML. Indent and quote character come from the first
    item already there. An empty `values` leaves the key with no items, never
    deletes it.
    """
    try:
        text = read_raw(path)
    except (OSError, UnicodeDecodeError):
        return False
    lines = _split(text)
    bounds = _fence_bounds(lines)
    if bounds is None:
        return False
    open_i, close_i = bounds

    key_i = None
    for i in range(open_i + 1, close_i):
        if lines[i].startswith(f'{key}:'):
            rest = lines[i][len(key) + 1:].strip()
            if rest and not rest.startswith('#'):
                # A scalar sits there. Rewriting it as a block would be this
                # writer deciding the file meant something else.
                return False
            key_i = i
            break

    indent, quote, eol = '  ', '"', ''
    kept: list[str] = []
    if key_i is None:
        # A plan that has no `order` yet: mint the key at the end of the block.
        eol = _eol(lines[close_i])
        key_i = close_i
        head = [f'{key}:{eol}']
        tail_from = close_i
    else:
        eol = _eol(lines[key_i])
        end_i = key_i
        for j in range(key_i + 1, close_i):
            stripped = lines[j].strip()
            if not stripped or stripped.startswith('#'):
                # The READER spans these (`_list_in`, review A2), so the
                # writer must too: spanned lines are kept ahead of the
                # rewritten items, so annotations survive the edit.
                kept.append(lines[j])
                continue
            m = _LIST_ITEM.match(lines[j])
            if m is None:
                break
            if end_i == key_i:
                # Copy the file's own shape off its first item.
                raw = lines[j]
                indent = raw[:len(raw) - len(raw.lstrip(' \t'))]
                value = m.group('value')
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    quote = value[0]
                else:
                    quote = ''
            end_i = j
        head = [lines[key_i]]
        tail_from = end_i + 1

    items = [f'{indent}- {quote}{v}{quote}{eol}' for v in values]
    rewritten = lines[:key_i] + head + kept + items + lines[tail_from:]
    try:
        write_raw(path, '\n'.join(rewritten))
    except OSError:
        return False
    return True
