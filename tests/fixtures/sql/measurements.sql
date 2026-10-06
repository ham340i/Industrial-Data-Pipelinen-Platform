CREATE TABLE measurements (
    asset_id INTEGER NOT NULL,
    measurement_name TEXT NOT NULL,
    measurement_value REAL NOT NULL,
    observed_at TEXT NOT NULL,
    quality_status TEXT NOT NULL
);

INSERT INTO measurements (
    asset_id,
    measurement_name,
    measurement_value,
    observed_at,
    quality_status
)
VALUES
    (1001, 'temperature', 72.5, '2026-10-05T08:00:00Z', 'valid'),
    (1002, 'pressure', 31.8, '2026-10-05T08:05:00Z', 'review'),
    (1001, 'temperature', 73.1, '2026-10-05T08:10:00Z', 'valid');
