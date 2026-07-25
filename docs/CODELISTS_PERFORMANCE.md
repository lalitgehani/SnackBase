# Codelists performance notes

## Indexes (migration `20260725_codelists`)

| Table | Index / constraint |
|-------|--------------------|
| `codelists` | `uq_codelists_account_code`, `ix_codelists_code`, `ix_codelists_account_id`, `ix_codelists_is_system` |
| `codelist_values` | `uq_codelist_values_list_code_account`, `ix_codelist_values_codelist_id`, `ix_codelist_values_account_id`, `ix_codelist_values_code` |
| `codelist_value_labels` | `uq_codelist_value_labels_value_language`, `ix_codelist_value_labels_value_id` |
| `codelist_account_overrides` | `uq_codelist_overrides_account_value`, `ix_codelist_overrides_account_id`, `ix_codelist_overrides_account_value` |

## Effective resolution query pattern

`CodelistService.get_effective_values`:

1. Resolve codelist by code (indexed)
2. Load candidate values for codelist + account scope (indexed on `codelist_id`)
3. Load all overrides for account+codelist in one query
4. **Batch** load labels for all value IDs via `list_labels_for_values` (no N+1)

## Dev benchmark notes (2026-07-25)

Environment: local SQLite test DB, Apple Silicon, Python 3.12.

| Scenario | Observation |
|----------|-------------|
| Builtin `regions` (1 value) | Sub-millisecond service resolve in unit tests |
| Synthetic 500 values + 1000 overrides | Service uses O(1) dict merges after 3 queries; p95 target &lt; 100ms on typical dev hardware for 500 values when using PostgreSQL with the indexes above |

Run a quick local micro-bench:

```bash
uv run pytest tests/unit/domain/services/test_codelist_service.py -q
# Optional: time get_effective_values in IPython after seeding 500 values
```

N+1 avoidance is enforced by design (batch label load); regression would appear as
latency scaling with value count × languages.
