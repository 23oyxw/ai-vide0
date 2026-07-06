-- L8 analytics metrics (Postgres / Neon / Vercel Postgres)
-- Apply: psql $DATABASE_URL -f scripts/l8_schema.sql

CREATE TABLE IF NOT EXISTS l8_daily_metrics (
    job_id VARCHAR(64) NOT NULL DEFAULT 'all',
    metric_date DATE NOT NULL,
    clicks INTEGER NOT NULL DEFAULT 0,
    unique_clicks INTEGER NOT NULL DEFAULT 0,
    conversions INTEGER NOT NULL DEFAULT 0,
    orders INTEGER NOT NULL DEFAULT 0,
    gmv NUMERIC(12, 2) NOT NULL DEFAULT 0,
    PRIMARY KEY (job_id, metric_date)
);

INSERT INTO l8_daily_metrics (job_id, metric_date, clicks, unique_clicks, conversions, orders, gmv)
VALUES
    ('all', '2026-07-01', 4200, 3100, 186, 102, 20398.00),
    ('all', '2026-07-02', 4800, 3600, 210, 118, 23456.00),
    ('all', '2026-07-03', 5100, 3800, 228, 125, 24890.00)
ON CONFLICT (job_id, metric_date) DO NOTHING;
