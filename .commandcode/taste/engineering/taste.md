# Engineering & Quality Preferences

- Values reproducibility, auditability, and preserving the original dataset throughout data pipelines. Confidence: 0.90
- Requires invalid or unrepairable records to be quarantined with explicit reasons rather than silently removed; never fabricate customer or business data. Confidence: 0.95
- Wants independent validation layers (e.g., SQL checks in DuckDB) that can catch mistakes in the primary processing logic. Confidence: 0.85
- Expects production-quality engineering practices: modular code, type hints, configurable file paths, idempotent execution, logging, input schema validation, and safe handling of client datasets. Confidence: 0.90
- Expects automated testing with both unit tests and integration tests, plus CI (e.g., GitHub Actions). Confidence: 0.90
- Prefers lightweight MVPs and explicitly defers optional UI, cloud deployment, or orchestration tools to future phases. Confidence: 0.80
- Wants synthetic datasets to use fixed random seeds, document expected defect counts, and contain no real personal information. Confidence: 0.85
