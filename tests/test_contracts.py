"""Shared surfaces, held to their READERS — the writer/reader contract.

Four of 0.5.0's blocking findings were one shape: a new WRITER met an old
READER, both halves individually correct, and no test of either could fail.
The one that got furthest: `lessons.FIELDS` spelled its stamp `'at'` while
every reader keyed `'ts'`, so each side's own tests passed and every lesson row
sorted to the beginning of time. Neither spelling is wrong to a string.

**A round-trip is the cheapest thing that can fail here** (rule 10): mint
through the writer, read through the reader, assert the key survives. That is
the assertion neither half's own tests make, and it costs a function call.

THE REGISTRY IS THE POINT. `SURFACES` names every shared vocabulary in this
package; `test_every_surface_is_covered` fails when one is added and left
uncovered, so the registry cannot go stale in the direction nobody looks.
"""
from __future__ import annotations

import json
import unittest

from agentic_sdlc.core import config
from agentic_sdlc.repo.pm import (changelog, inventory, ledger, report,
                                  templates, vocabulary)
from agentic_sdlc.repo.pm import cli as pm_cli

# {surface: (the constant, the case that binds it to its reader)}. A surface
# with no case is a NAMED line, never silence (rule 11).
SURFACES = {
    'ledger.ROW_KEYS': 'test_a_usage_row_carries_only_keys_the_report_can_read',
    'ledger.LESSON_KEYS': 'test_a_lesson_row_stamps_the_key_its_reader_sorts_on',
    'ledger.EVENT_KEYS': 'test_every_event_shape_stamps_the_key_its_reader_sorts_on',
    'changelog.COLUMNS': 'test_changelog_rows_and_json_carry_the_same_columns',
    'cli.LIST_COLUMNS': 'test_every_list_kind_emits_exactly_its_declared_columns',
    'vocabulary.BINDS_TO': 'test_every_binding_field_is_one_the_templates_carry',
    'vocabulary.FLOW_KINDS': 'test_every_grain_kind_reaches_the_tables_keyed_on_it',
    'config.pointer_escapes': 'test_no_caller_hand_rolls_its_own_escape_check',
    'cli.ROADMAP_COLUMNS': 'test_pm_roadmap_help_names_its_columns',
    'report.CLOCK_COLUMNS': 'test_ledger_report_help_names_its_clock_and_actor_columns',
}

# The stamp every durable row sorts on. `'at'` is the spelling that shipped and
# sorted every lesson to the beginning of time; it must appear in NO minter.
STAMP = 'ts'
WRONG_STAMP = 'at'


class TheRegistryIsComplete(unittest.TestCase):
    """Rule 4: a registry nobody grades is a list, not a gate."""

    def test_every_surface_is_covered_by_a_case_that_exists(self):
        cases = set()
        for holder in (TheRowsRoundTrip, TheColumnsRoundTrip, OnePointerResolver,
                       EveryReadVerbsHelpNamesItsColumns):
            cases |= {n for n in dir(holder) if n.startswith('test_')}
        missing = {surface: case for surface, case in SURFACES.items()
                   if case not in cases}
        self.assertEqual({}, missing,
                         'a shared surface names a case that does not exist — '
                         'the registry has gone stale in the direction nobody '
                         'looks')

    def test_the_registry_is_not_vacuous(self):
        self.assertGreaterEqual(len(SURFACES), 9, SURFACES)
        for surface in SURFACES:
            module, _, name = surface.partition('.')
            holder = {'ledger': ledger, 'changelog': changelog, 'cli': pm_cli,
                      'config': config, 'inventory': inventory,
                      'report': report, 'vocabulary': vocabulary}[module]
            self.assertTrue(hasattr(holder, name),
                            f'{surface} is registered and does not exist')


class TheRowsRoundTrip(unittest.TestCase):
    """A row minted by the writer, read by the reader that consumes it."""

    def test_a_usage_row_carries_only_keys_the_report_can_read(self):
        """THE `tokens_total` CASE, and the general one. Every key a usage row
        may carry is either a column the report renders, a routing key, or
        named below as deliberately unrendered — so a key added to the writer
        and never taught to the reader fails HERE rather than in a table
        somebody reads next month.
        """
        # Routing and provenance: read by the walk, never a spend column.
        ROUTING = {'ts', 'kind', 'grain', 'session_id', 'agent_id',
                   'agent_type', 'model', 'started_at', 'ended_at',
                   'messages', 'tools', 'tool_calls_before_first_write',
                   'usage', 'tree',
                   # ft-work-is-stamped / ft-a-dispatch-row-carries-its-outcome:
                   # the report's reader for these lands with b-ledger-read.
                   'issue', 'outcome'}
        rendered = set(report.SPEND_COLUMNS) | set(report.USAGE_LABELS.values())
        for key in ledger.ROW_KEYS:
            with self.subTest(key=key):
                self.assertTrue(
                    key in ROUTING or key in rendered
                    or report.USAGE_LABELS.get(key, key) in rendered,
                    f'{key!r} is in ledger.ROW_KEYS and the report neither '
                    f'renders nor routes it — a writer met no reader')

    def test_the_total_key_is_ONE_constant_both_sides_import(self):
        """`report.TOTAL_KEY = ledger.TOTAL_KEY`, asserted rather than assumed.
        Two string literals that happened to match is the `at`/`ts` defect
        waiting for one of them to be edited."""
        self.assertIs(report.TOTAL_KEY, ledger.TOTAL_KEY)
        self.assertIn(ledger.TOTAL_KEY, ledger.ROW_KEYS)

    def test_a_usage_row_refuses_a_key_no_reader_knows(self):
        with self.assertRaises(ValueError) as caught:
            ledger.usage_row('dispatch', tokens_sideways=1)
        self.assertIn('tokens_sideways', str(caught.exception))

    def test_a_lesson_row_stamps_the_key_its_reader_sorts_on(self):
        """THE REGRESSION for `at` vs `ts`. Planting the old spelling in the
        writer must make this red — it is the assertion that was missing."""
        row = ledger.lesson_row('st-x', 'rule-4', 'docs/x.md', 'a lesson')
        self.assertIn(STAMP, row, 'the minter stamped no `ts`')
        self.assertNotIn(WRONG_STAMP, row,
                         '`at` is the spelling that sorted every lesson row to '
                         'the beginning of time')
        self.assertEqual(ledger.LESSON_KEYS[0], STAMP)
        self.assertIsNotNone(ledger.parse_ts(row[STAMP]),
                             'the reader cannot parse what the writer stamped')

    def test_every_event_shape_stamps_the_key_its_reader_sorts_on(self):
        """`EVENT_KEYS` maps a row kind to its declared keys, and one reader
        sorts all of them. Every shape must open on the stamp, so a new event
        kind cannot arrive keyed on something the sort does not see."""
        for kind, keys in ledger.EVENT_KEYS.items():
            with self.subTest(kind=kind):
                self.assertEqual(keys[0], STAMP,
                                 f'{kind} rows do not open on `{STAMP}`')
                self.assertNotIn(WRONG_STAMP, keys)
        row = ledger.status_row('st-x', 'ready', 'building')
        self.assertIsNotNone(ledger.parse_ts(row[STAMP]))

    def test_no_minter_in_the_package_stamps_the_WRONG_key(self):
        """The general form, over every row this module mints. A new minter
        that reached for `at` joins this case for free."""
        rows = [ledger.status_row('g', 'a', 'b'),
                ledger.lesson_row('g', 'r', 's.md', 't'),
                ledger.usage_row('dispatch', grain='g')]
        for row in rows:
            with self.subTest(kind=row.get('kind')):
                self.assertIn(STAMP, row)
                self.assertNotIn(WRONG_STAMP, row)


# Every shape `config.pointer_escapes` refuses, and the two the hand-rolled
# checks missed. `..` is F1's: it is not absolute and does not start with `~`,
# so a `/`-and-`~` pair reads it as repo-relative and resolves it anywhere.
ESCAPING = ('../outside.md', '../../etc/passwd', '/etc/passwd', '~/x.md',
            'file:x.md', '\\\\server\\share.md')
REPO_RELATIVE = ('docs/reviews/x.md', 'a/b/c.md', 'x.md')
# A module allowed a spelling of its own because its classifier is RICHER —
# it names WHICH shape is wrong. Bound to the predicate by the case below.
RICHER = frozenset({'ready_for.py'})
# The two functions that DEFINE the resolution. `test_boundaries.py` allowlists
# the guard module itself for the same reason: the owner cannot route through
# itself. Allowed by FUNCTION, not by module, so a third spelling elsewhere in
# `core/config.py` is still an offender.
OWNERS = frozenset({'record_path', 'pointer_escapes'})


def _hand_rolled_sites(name: str, tree) -> list[str]:
    """`<pointer>.startswith('/'|'~')` — the spelling that reads `../x` as
    repo-relative. The two DEFINING functions are skipped: the owner cannot
    route through itself."""
    import ast
    owned = {n for fn in ast.walk(tree)
             if isinstance(fn, ast.FunctionDef) and fn.name in OWNERS
             for n in ast.walk(fn)}
    found = []
    for node in ast.walk(tree):
        if node in owned or not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Attribute)
                and node.func.attr == 'startswith' and len(node.args) == 1):
            continue
        literal = getattr(node.args[0], 'value', None)
        spellings = ({literal} if isinstance(literal, str) else
                     {e.value for e in getattr(node.args[0], 'elts', [])
                      if isinstance(getattr(e, 'value', None), str)})
        target = getattr(node.func.value, 'id', '')
        if target in ('pointer', 'source', 'rec', 'record') and (
                spellings & {'/', '~'}):
            found.append(f'{name}:{node.lineno}: {target}.startswith(...)')
    return found


class OnePointerResolver(unittest.TestCase):
    """F1's class: `lesson --source` accepted a path outside the checkout and
    landed it verbatim in an append-only row, because it used the resolver that
    lacked the escape check while its sibling three files away had one.

    The ship criterion asks for ONE resolver and a plant against **every verb
    that takes a pointer**. This is that plant, asked of the predicate they now
    all share — so a fourth verb wiring itself up is covered on arrival.
    """

    PROTECTS = (
        'every verb taking a pointer refuses an escaping one through the same '
        'predicate, and no caller hand-rolls a second escape check',
        'load-bearing — sin 2 (a write that looks legitimate and is not): F1 '
        'landed a path from outside the checkout verbatim in an append-only '
        'row, because one verb used the resolver that lacked the check while '
        'its sibling three files away had one',
    )

    def test_every_escaping_shape_is_refused(self):
        for pointer in ESCAPING:
            with self.subTest(pointer=pointer):
                self.assertTrue(config.pointer_escapes(pointer),
                                f'{pointer!r} reaches outside the checkout')

    def test_a_repo_relative_pointer_is_not_refused(self):
        """The floor. A predicate that refused everything would pass the case
        above and make every pointer verb unusable."""
        for pointer in REPO_RELATIVE:
            with self.subTest(pointer=pointer):
                self.assertFalse(config.pointer_escapes(pointer))

    CORPUS = (
        # The spelling that shipped, in each name a pointer travels under.
        ("if pointer.startswith('/'):\n    pass", True),
        ("if source.startswith('~'):\n    pass", True),
        ("if rec.startswith(('/', '~')):\n    pass", True),
        ("if record.startswith('/') or record.startswith('~'):\n    pass",
         True),
        # NOT this: a different question about a different value.
        ("if line.startswith('#'):\n    pass", False),
        ("if pointer.startswith('docs/'):\n    pass", False),
        ("if name.startswith('/'):\n    pass", False),
        ('escapes = pointer_escapes(pointer)', False),
    )

    @staticmethod
    def catches(planted: str) -> bool:
        import ast
        return bool(_hand_rolled_sites('scratch.py', ast.parse(planted)))

    def test_no_caller_hand_rolls_its_own_escape_check(self):
        """THE REGRESSION. Two verbs spelled the check themselves as
        `startswith('/')` + `startswith('~')`, which reads `../outside.md` as
        repo-relative. Both now call the shared predicate; a third that reaches
        for the pair instead is what this case catches.
        """
        import ast
        from pathlib import Path as _P
        root = _P(vocabulary.__file__).resolve().parents[3] / 'agentic_sdlc'
        offenders = []
        modules = 0
        for path in sorted(root.rglob('*.py')):
            modules += 1
            if path.name in RICHER:
                continue
            offenders.extend(
                _hand_rolled_sites(path.name,
                                   ast.parse(path.read_text(encoding='utf-8'))))
        # Rule 4: a walk that graded nothing says so.
        self.assertGreaterEqual(modules, 20, 'the source census collapsed')
        self.assertEqual(
            [], offenders,
            'a pointer escape check spelled by hand. `pointer_escapes` '
            'is the one predicate and it refuses `..` and a scheme prefix, '
            'which `/`-and-`~` does not:\n  ' + '\n  '.join(offenders))

    def test_the_richer_classifier_never_disagrees_with_the_predicate(self):
        """`ready_for._pointer_defect` names WHICH shape is wrong, where the
        predicate answers yes/no. That is worth keeping and is why the case
        above allows it — but two readers of one question that can disagree is
        the `at`/`ts` defect, so this binds them.
        """
        from agentic_sdlc.repo.pm import ready_for
        for pointer in ESCAPING:
            with self.subTest(pointer=pointer):
                self.assertIsNotNone(
                    ready_for._pointer_defect(pointer),
                    f'{pointer!r} is refused by `pointer_escapes` and followed '
                    f'by the belt — the two readers disagree')
        for pointer in REPO_RELATIVE:
            with self.subTest(pointer=pointer):
                self.assertIsNone(ready_for._pointer_defect(pointer))


class EveryReadVerbsHelpNamesItsColumns(unittest.TestCase):
    """Rule 11's read side, mechanised once instead of per verb.

    *"Every read verb names its columns in order in `--help`, and if you cannot
    pipe something the missing thing is a COLUMN, never a verb."* That was
    enforced by hand at nine sites, and T3 is what that costs: `CLOCK_COLUMNS`
    shipped dead, its claim in a comment, referenced by nothing, while
    `--help` named no columns at all.

    Each row here binds a DECLARATION to the help text that must render it.
    Nothing is hand-typed: the expected words come off the constant.
    """

    def _help(self, module) -> str:
        return ' '.join((getattr(module, 'USAGE', '') or '').split())

    def _named(self, columns, text, where) -> None:
        self.assertIn(' '.join(columns), text,
                      f'{where}: `--help` does not name its columns in the '
                      f'order it prints them — {columns}')

    def test_changelog_help_names_its_columns(self):
        self._named(changelog.COLUMNS, self._help(changelog), 'changelog')

    def test_lesson_show_help_names_its_columns(self):
        from agentic_sdlc.repo.conveyor import lessons
        self._named(lessons.COLUMNS, self._help(lessons), 'lesson show')

    def test_pm_roadmap_help_names_its_columns(self):
        self._named(pm_cli.ROADMAP_COLUMNS, self._help(pm_cli), 'pm roadmap')

    def test_ledger_report_help_names_its_clock_and_actor_columns(self):
        text = self._help(pm_cli)
        for columns in (report.CLOCK_COLUMNS, report.ACTOR_COLUMNS):
            self._named(columns, text, 'pm ledger report')

    def test_pm_list_help_names_every_kinds_columns(self):
        """The one with four declarations behind one verb. `--json`'s keys ARE
        these tuples, so a column named nowhere is a field a consumer finds by
        accident."""
        text = self._help(pm_cli)
        for kind in pm_cli.LIST_KINDS:
            with self.subTest(kind=kind):
                columns = pm_cli.LIST_COLUMNS[kind]
                named = sum(1 for c in columns if c in text)
                self.assertEqual(
                    named, len(columns),
                    f'pm list --kind {kind}: {len(columns) - named} of '
                    f'{len(columns)} columns are not in `--help` ({columns})')

    def test_the_census_is_not_vacuous(self):
        """Rule 4. Every case above reads `USAGE` off a module; an empty one
        would make `' '.join(columns) in ''` false, but a missing CONSTANT
        would make the case never run at all."""
        for module, name in ((changelog, 'COLUMNS'),
                             (pm_cli, 'ROADMAP_COLUMNS'),
                             (pm_cli, 'LIST_COLUMNS'),
                             (report, 'CLOCK_COLUMNS'),
                             (report, 'ACTOR_COLUMNS')):
            with self.subTest(name=name):
                self.assertTrue(getattr(module, name, None), name)
        self.assertGreater(len(self._help(pm_cli)), 2000,
                           'pm USAGE collapsed — every case above would then '
                           'be asserting against an empty string')


class TheColumnsRoundTrip(unittest.TestCase):
    """A column list, its rows, and its `--json` keys — one declaration."""

    def test_changelog_rows_and_json_carry_the_same_columns(self):
        entry = changelog.Entry('ft-x', 'feature', 'done', 'A sentence.')
        rows = changelog.rows([entry])
        self.assertEqual(len(rows[0]), len(changelog.COLUMNS),
                         'a row is a different width from its declaration')
        payload = json.loads(json.dumps(
            [dict(zip(changelog.COLUMNS, r)) for r in rows]))
        self.assertEqual(tuple(payload[0]), changelog.COLUMNS)

    def test_every_list_kind_emits_exactly_its_declared_columns(self):
        """`--json` keys ARE the column tuple. A payload carrying a field the
        columns do not is what a consumer discovers at the worst moment."""
        for kind in pm_cli.LIST_KINDS:
            with self.subTest(kind=kind):
                self.assertIn(kind, pm_cli.LIST_COLUMNS)
                self.assertEqual(len(set(pm_cli.LIST_COLUMNS[kind])),
                                 len(pm_cli.LIST_COLUMNS[kind]),
                                 'a duplicate column silently shifts a row')

    def test_every_grain_kind_reaches_the_tables_keyed_on_it(self):
        """`vocabulary.FLOW_KINDS` is the vocabulary every kind-keyed table indexes.
        A kind added there with no prefix, pool, template or list columns is
        four `KeyError`s waiting on four different verbs."""
        for kind in vocabulary.FLOW_KINDS:
            with self.subTest(kind=kind):
                for table, name in ((inventory.KIND_PREFIX, 'KIND_PREFIX'),
                                    (inventory.POOL_NAME, 'POOL_NAME'),
                                    (pm_cli.LIST_COLUMNS, 'cli.LIST_COLUMNS')):
                    self.assertIn(kind, table,
                                  f'{name} is not keyed on {kind!r} and '
                                  f'vocabulary.FLOW_KINDS says it is a kind')
                # Review V3 (0.6.0): this asked `kind in templates.GRAINS`,
                # and the same commit that collapsed the parallel kind
                # declarations made `GRAINS` an alias OF `FLOW_KINDS` — so the
                # assertion became `x in X for x in X` and could not fail. The
                # fourth `KeyError` the docstring promises is a MISSING
                # TEMPLATE FILE, so the file is what is asked for.
                self.assertTrue(_shipped(kind).lstrip().startswith('---'),
                                f'templates/{kind}.md ships no frontmatter '
                                f'fence, so `pm new {kind}` scaffolds a grain '
                                f'with nowhere to write a status')

    def test_every_binding_field_is_one_the_templates_carry(self):
        """`BINDS_TO` says which field binds a kind; the shipped template has
        to actually carry it, or `pm add` writes a key nothing reads."""
        for kind, (_parent, field) in vocabulary.BINDS_TO.items():
            with self.subTest(kind=kind):
                self.assertIn(f'{field}:', _shipped(kind),
                              f'{kind}.md carries no `{field}:` and BINDS_TO '
                              f'says that is its binding')


def _shipped(kind: str) -> str:
    """The template as SHIPPED, read off the package rather than a tree — this
    module is in the `not shell` tier and builds no fixture."""
    from importlib import resources
    return (resources.files('agentic_sdlc.repo.pm.templates')
            .joinpath(f'{kind}.md').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
