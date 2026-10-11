# Backend Controllers

The initial local endpoint is `GET /health`, implemented by `src.backend.app`. It verifies PostgreSQL availability without returning credentials or raw observations. Forecast and experiment endpoints are added only after canonical ingestion and model artifacts are validated.
