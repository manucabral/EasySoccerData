# Validation, coverage and metrics

`EasySoccerData` includes offline inspection functions to verify dataset integrity (`validate_dataset`), check which normalized columns a provider populates (`get_dataset_field_capabilities`), audit observed non-null rates (`inspect_dataset_coverage`) and compute per-90 rates and ratios (`derive_statistics`).

## Validate a dataset (`validate_dataset`)

`esd.validate_dataset(dataset)` checks schema types, primary keys, non-negative scores and counts, date bounds, task accounting and cross-table references without network access:

```py
import esd

report = esd.validate_dataset(dataset)
print("Valid:", report.valid)
print("Errors:", len(report.errors))
print("Warnings:", len(report.warnings))

for issue in report.issues:
    print(issue.severity, issue.code, issue.table, issue.row_index, issue.message)
```

## Static field capabilities (`get_dataset_field_capabilities`)

Use `esd.get_dataset_field_capabilities(source, table)` to inspect every column in a normalized table before downloading data. Each `DatasetFieldCapability` reports:

- `support`: `"always"`, `"mapped"`, `"derived"` or `"unavailable"`
- `dtype`: Nullable DataFrame dtype (`"string"`, `"Int64"`, `"Float64"`, `"boolean"`, `"datetime64[ns, UTC]"`)
- `unit`: `"minutes"`, `"seconds"`, `"percentage_points"`, `"native_coordinates"` or `None`
- `model`: Provider model identifier for `xg`, `xgot`, `xa`, forecasts and ratings
- `coordinate_system`: Native coordinate axes for shot maps

```py
import esd

caps = esd.get_dataset_field_capabilities("sofascore", "shots")
for name, cap in caps.items():
    if cap.support != "unavailable":
        print(f"{name:20s} support={cap.support:8s} dtype={cap.dtype:10s} model={cap.model}")
```

## Observed dataset coverage (`inspect_dataset_coverage`)

`esd.inspect_dataset_coverage(dataset, tables=...)` summarizes row counts, task completion status (`"complete"`, `"partial"`, `"failed"`, `"pending"`) and per-field non-null, zero, boolean and blank string counts:

```py
import esd

coverage = esd.inspect_dataset_coverage(dataset, tables=("player_match_stats", "match_stats"))

for table_cov in coverage.tables:
    print(table_cov.table, table_cov.row_count, table_cov.task_status)

# Export field coverage to a DataFrame (requires EasySoccerData[pandas])
fields_df = coverage.to_dataframe()
print(fields_df[["table", "field", "support", "present_count", "null_count"]].head(10))
```

## Derived per-90 rates and ratios (`derive_statistics`)

`esd.derive_statistics(record)` computes per-90 rates, `pass_accuracy_pct`, `shot_accuracy_pct` and `xg_per_shot` from a single `NormalizedPlayerMatchStats`, `NormalizedPlayerStats` or `NormalizedMatchStats` record.

- Player per-90 rates use the record's own reported `minutes` field.
- Missing operands or zero denominators return `value=None` with a diagnostic `status` (`"missing_numerator"`, `"missing_denominator"`, `"zero_denominator"` or `"inconsistent_inputs"`).

```py
import esd

derived_rows = [esd.derive_statistics(row) for row in dataset.player_match_stat_records]
for metric in derived_rows[0].metrics:
    print(f"{metric.name:25s} value={metric.value!s:8s} status={metric.status}")

# Convert a collection of DerivedStatistics into a DataFrame
df = esd.derived_statistics_to_dataframe(derived_rows)
```
