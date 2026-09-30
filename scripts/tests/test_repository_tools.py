"""Regression tests for failure detection and non-destructive GitHub setup."""

import contextlib
import copy
import json
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from check_docs import check_markdown
from check_repository import suspicious, validate_configuration
from check_release_plan import validate as validate_release_plan

spec = importlib.util.spec_from_file_location('github_setup', SCRIPTS / 'github-setup/setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class DocumentationTests(unittest.TestCase):
    def test_link_and_anchor_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'target.md').write_text('# Real heading\n')
            source = root / 'source.md'
            source.write_text('[good](target.md#real-heading)\n[bad](target.md#missing)\n[absent](none.md)\n')
            errors = check_markdown(source, root)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any('missing heading' in error for error in errors))
            self.assertTrue(any('missing local target' in error for error in errors))

    def test_examples_and_external_urls_are_not_fetched(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.md'
            source.write_text('```md\n[example](missing.md)\n```\n[site](https://example.invalid/)\n')
            self.assertEqual(check_markdown(source, root), [])

    def test_escape_and_whitespace_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source.md'
            source.write_text('[escape](../outside.md)  ')
            self.assertEqual(len(check_markdown(source, root)), 2)

    def test_absolute_repository_and_wiki_links_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'target.md').write_text('# Existing heading\n')
            (root / 'docs/wiki').mkdir(parents=True)
            (root / 'docs/wiki/Home.md').write_text('# Wiki home\n')
            source = root / 'source.md'
            base = 'https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/'
            source.write_text(
                f'[good]({base}blob/main/target.md#existing-heading)\n'
                f'[home]({base}wiki/Home)\n'
                f'[missing]({base}blob/main/absent.md)\n'
                f'[missing wiki]({base}wiki/Absent)\n'
            )
            self.assertEqual(len(check_markdown(source, root)), 2)


class SecurityTests(unittest.TestCase):
    def test_private_key_and_token_detection(self):
        key = ('-----BEGIN ' + 'PRIVATE KEY-----').encode()
        token = ('ghp_' + 'a' * 36).encode()
        self.assertTrue(suspicious(Path('notes.txt'), key))
        self.assertTrue(suspicious(Path('notes.txt'), token))
        self.assertTrue(suspicious(Path('.env.local'), b''))
        self.assertFalse(suspicious(Path('.env.example'), b'APP_MODE=development'))

    def test_unsafe_workflow_permissions_fail(self):
        with self.assertRaises(AssertionError):
            validate_configuration(Path('.github/workflows/ci.yml'), {
                'on': {'pull_request': {}, 'push': {'branches': ['main']}},
                'permissions': {'contents': 'write'}, 'jobs': {},
            })


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.record = {'name': 'feature:example', 'color': '123456', 'description': 'Example'}

    def test_preview_never_writes(self):
        with patch.object(setup, 'gh_json') as api, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.reconcile('owner/repo', 'labels', [self.record], []), 0)
            api.assert_not_called()

    def test_existing_drift_is_preserved(self):
        old = dict(self.record, color='654321')
        with patch.object(setup, 'gh_json') as api, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.reconcile('owner/repo', 'labels', [self.record], [old], True), 2)
            api.assert_not_called()

    def test_apply_then_rerun_is_idempotent(self):
        with patch.object(setup, 'gh_json') as api, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.reconcile('owner/repo', 'labels', [self.record], [], True), 0)
            self.assertEqual(api.call_count, 1)
            self.assertEqual(setup.reconcile('owner/repo', 'labels', [self.record], [self.record], True), 0)
            self.assertEqual(api.call_count, 1)

    def test_pagination_includes_closed_milestones(self):
        with patch.object(setup, 'gh_json', side_effect=[[{'title': str(i)} for i in range(100)], []]) as api:
            self.assertEqual(len(setup.existing_records('owner/repo', 'milestones')), 100)
            self.assertIn('page=2&state=all', api.call_args.args[0][1])

    def test_normalized_milestone_time_is_not_drift(self):
        desired = {'title': 'Iteration 1', 'due_on': '2026-10-06T23:59:59Z'}
        existing = dict(desired, due_on='2026-10-06T00:00:00Z')
        with patch.object(setup, 'gh_json') as api, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.reconcile('owner/repo', 'milestones', [desired], [existing], True), 0)
            api.assert_not_called()

    def test_different_milestone_date_is_preserved_and_reported(self):
        desired = {'title': 'Iteration 1', 'due_on': '2026-10-06T23:59:59Z'}
        existing = dict(desired, due_on='2026-10-07T00:00:00Z')
        with patch.object(setup, 'gh_json') as api, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(setup.reconcile('owner/repo', 'milestones', [desired], [existing], True), 2)
            api.assert_not_called()


class ReleasePlanTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((SCRIPTS.parent / 'docs/planning/release-1-backlog.json').read_text())

    def test_professor_cannot_receive_engineering_assignment(self):
        invalid = copy.deepcopy(self.plan)
        invalid['items'][0]['owner'] = 'moar82'
        with self.assertRaises(AssertionError):
            validate_release_plan(invalid)

    def test_same_iteration_dependency_cycle_is_rejected(self):
        invalid = copy.deepcopy(self.plan)
        sdk = next(x for x in invalid['items'] if x['key'] == 'I1-05')
        sdk['dependencies'].append('I1-06')
        with self.assertRaises(AssertionError):
            validate_release_plan(invalid)


if __name__ == '__main__':
    unittest.main()
