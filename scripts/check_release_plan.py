#!/usr/bin/env python3
"""Validate Release 1 estimates, student-only ownership and dependency integrity."""

from collections import Counter
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'ham340i', 'aboudka2003', 'adamoug', 'al-yousef', 'joedaswagger',
           'karimikhaeil', 'marcelhaddad1', 'menaboulus'}


def validate(plan):
    students = plan['students']
    assert len(students) == 8 and {x.casefold() for x in students} == ALLOWED
    assert plan['professor']['login'] == 'moar82'
    assert plan['professor']['engineering_assignments'] == 0
    assert [(plan['milestones'][str(i)]['title'], plan['milestones'][str(i)]['due']) for i in range(1, 5)] == [
        ('Iteration 1', '2026-10-06'), ('Iteration 2', '2026-10-20'),
        ('Iteration 3', '2026-11-03'), ('Iteration 4 (Release 1)', '2026-11-17'),
    ]
    items = plan['items']
    by_key = {x['key']: x for x in items}
    assert len(items) == len(by_key)
    for x in items:
        assert x['owner'] in students and x['reviewer'] in students
        assert x['owner'] != x['reviewer']
        assert x['story_points'] in {1, 2, 3, 5, 8, 13} and x['ideal_hours'] > 0
        assert x['review_hours'] > 0 and x['iteration'] in {1, 2, 3, 4}
        assert x['priority'] in {'Critical', 'High', 'Medium', 'Low'}
        assert x['risk'] in {'High', 'Medium', 'Low'}
        assert x['type'] in {'story', 'task', 'spike'}
        assert x['feature'].startswith('feature:') and len(x['acceptance']) >= 4
        assert all(x[k] for k in ['persona', 'want', 'value', 'engineering_notes',
                                  'unit_tests', 'integration_tests', 'e2e_tests', 'manual_tests'])
        assert len(set(x['dependencies'])) == len(x['dependencies'])
        for key in x['dependencies']:
            assert key in by_key and key != x['key']
            assert by_key[key]['iteration'] <= x['iteration']
    complete, active = set(), set()

    def visit(key):
        assert key not in active, 'Dependency cycle: ' + key
        if key in complete:
            return
        active.add(key)
        for dependency in by_key[key]['dependencies']:
            visit(dependency)
        active.remove(key)
        complete.add(key)

    for key in by_key:
        visit(key)
    for i in range(1, 5):
        assert {x['owner'] for x in items if x['iteration'] == i} == set(students)
    assert {x['reviewer'] for x in items} == set(students)
    assert plan['umbrella']['owner'] is None
    assert plan['umbrella']['story_points'] == plan['umbrella']['ideal_hours'] == 0
    ids = [x['issue_number'] for x in items if x.get('issue_number')]
    assert len(ids) == len(set(ids))
    return Counter(x['type'] for x in items)


def main():
    plan = json.loads((ROOT / 'docs/planning/release-1-backlog.json').read_text())
    types = validate(plan)
    print(f"Release 1 plan passed: {len(plan['items'])} items, 8 students, no professor assignments, acyclic dependencies; {dict(types)}")
    for i in range(1, 5):
        items = [x for x in plan['items'] if x['iteration'] == i]
        print(f"Iteration {i}: {len(items)} items, {sum(x['story_points'] for x in items)} SP, {sum(x['ideal_hours'] for x in items)} ideal hours")


if __name__ == '__main__':
    main()
