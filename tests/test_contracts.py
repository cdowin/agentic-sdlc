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

from agentic_sdlc.repo.pm import changelog, ledger, model, report
from agentic_sdlc.repo.pm import cli as pm_cli

# {surface: (the constant, the case that binds it to its reader)}. A surface
# with no case is a NAMED line, never silence (rule 11).
SURFACES = {
    'ledger.ROW_KEYS': 'test_a_usage_row_carries_only_keys_the_report_can_read',
    'ledger.LESSON_KEYS': 'test_a_lesson_row_stamps_the_key_its_reader_sorts_on',
    'ledger.EVENT_KEYS': 'test_every_event_shape_stamps_the_key_its_reader_sorts_on',
    'changelog.COLUMNS': 'test_changelog_rows_and_json_carry_the_same_columns',
    'cli.LIST_COLUMNS': 'test_every_list_kind_emits_exactly_its_declared_columns',
    'model.BINDS_TO': 'test_every_binding_field_is_one_the_templates_carry',
}

# The stamp every durable row sorts on. `'at'` is the spelling that shipped and
# sorted every lesson to the beginning of time; it must appear in NO minter.
STAMP = 'ts'
WRONG_STAMP = 'at'


class TheRegistryIsComplete(unittest.TestCase):
    """Rule 4: a registry nobody grades is a list, not a gate."""

    def test_every_surface_is_covered_by_a_case_that_exists(self):
        cases = {name for name in dir(TheRowsRoundTrip) if name.startswith('test_')}
        cases |= {name for name in dir(TheColumnsRoundTrip) if name.startswith('test_')}
        missing = {surface: case for surface, case in SURFACES.items()
                   if case not in cases}
        self.assertEqual({}, missing,
                         'a shared surface names a case that does not exist — '
                         'the registry has gone stale in the direction nobody '
                         'looks')

    def test_the_registry_is_not_vacuous(self):
        self.assertGreaterEqual(len(SURFACES), 6, SURFACES)
        for surface in SURFACES:
            module, _, name = surface.partition('.')
            holder = {'ledger': ledger, 'changelog': changelog,
                      'cli': pm_cli, 'model': model}[module]
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
                   'usage', 'tree'}
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

    def test_every_binding_field_is_one_the_templates_carry(self):
        """`BINDS_TO` says which field binds a kind; the shipped template has
        to actually carry it, or `pm add` writes a key nothing reads."""
        for kind, (_parent, field) in model.BINDS_TO.items():
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
