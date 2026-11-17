# Documented exception: test modules and migrations

Recorded November 17, 2026 for Release 1. Related work item: [#36](https://github.com/ham340i/Industrial-Data-Pipelinen-Platform/issues/36).

## Test modules over 500 lines

| File | Lines |
|---|---:|
| `tests/test_transform_blocks.py` | 1250 |
| `tests/test_blocks.py` | 896 |
| `tests/test_metadata.py` | 597 |
| `frontend/src/PreviewPanel.test.tsx` | 556 |
| `tests/test_preview.py` | 525 |
| `tests/test_quality.py` | 501 |

A test module here is a flat list of independent cases, each named for the behaviour it checks. There is no shared control flow that grows harder to follow as the file grows, which is the problem the file-size limit exists to prevent. The modules are organized one per feature so that a failing test name leads to one file. `tests/test_transform_blocks.py` now covers two production modules after the transform split and will be divided to match them (`test_transform_blocks.py` and `test_relational_blocks.py`); the others stay as they are.

Seven test functions exceed 50 lines. They are end-to-end scenarios that build a graph, run it and assert on every output; the length is fixture data, not logic.

## Migration functions over 50 lines

`migrations/versions/0001_initial_metadata_foundation.py::upgrade` (181 lines) and `0002_run_telemetry.py::upgrade` (87 lines) are declarative lists of table and index definitions with no branching. A migration that has been applied to a user's database must not be edited afterwards, because Alembic identifies it by revision and would not re-run it; restructuring these files could only introduce a difference between what the file says and what existing databases contain.
