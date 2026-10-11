CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(100) PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS energy_observations (
    id BIGSERIAL PRIMARY KEY,
    source_name VARCHAR(40) NOT NULL,
    site_id VARCHAR(80) NOT NULL,
    asset_id VARCHAR(120) NOT NULL,
    reading_time TIMESTAMPTZ NOT NULL,
    energy_vector VARCHAR(20) NOT NULL CHECK (energy_vector IN ('electricity', 'heat')),
    consumption_value NUMERIC NOT NULL,
    unit VARCHAR(20) NOT NULL,
    interval_minutes INTEGER CHECK (interval_minutes > 0),
    source_file VARCHAR(255) NOT NULL,
    source_row_number BIGINT,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_name, site_id, asset_id, reading_time, energy_vector)
);

CREATE INDEX IF NOT EXISTS idx_energy_observations_asset_time
    ON energy_observations (source_name, site_id, asset_id, reading_time);

CREATE TABLE IF NOT EXISTS experiment_runs (
    id UUID PRIMARY KEY,
    git_commit VARCHAR(64) NOT NULL,
    data_checksum VARCHAR(128) NOT NULL,
    split_definition JSONB NOT NULL,
    feature_definition JSONB NOT NULL,
    target_unit VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS expert_reliability (
    experiment_id UUID NOT NULL REFERENCES experiment_runs(id),
    expert_name VARCHAR(80) NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    ewma_error NUMERIC NOT NULL CHECK (ewma_error >= 0),
    reliability_weight NUMERIC NOT NULL CHECK (reliability_weight >= 0 AND reliability_weight <= 1),
    PRIMARY KEY (experiment_id, expert_name, observed_at)
);

CREATE TABLE IF NOT EXISTS moe_predictions (
    id BIGSERIAL PRIMARY KEY,
    experiment_id UUID NOT NULL REFERENCES experiment_runs(id),
    asset_id VARCHAR(120) NOT NULL,
    prediction_time TIMESTAMPTZ NOT NULL,
    target_unit VARCHAR(20) NOT NULL,
    forecast_value NUMERIC NOT NULL,
    gating_weights JSONB NOT NULL,
    expert_forecasts JSONB NOT NULL,
    observed_value NUMERIC,
    observed_at TIMESTAMPTZ,
    CHECK ((observed_value IS NULL) = (observed_at IS NULL))
);

CREATE INDEX IF NOT EXISTS idx_moe_predictions_experiment_time
    ON moe_predictions (experiment_id, prediction_time);

INSERT INTO schema_migrations (version)
VALUES ('001_feature1_canonical_schema')
ON CONFLICT (version) DO NOTHING;
