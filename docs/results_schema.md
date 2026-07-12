# Results Schema

This document defines the structured output fields used by CLEAR experiment exports.

Primary artifacts:

- `dataset.csv`
- `dataset.json`

Both represent one record per **model × benchmark attempt**.

---

## Record Granularity

Each row/object corresponds to one attempted repair run for:

- one model
- one benchmark case
- one difficulty tier
- one category

---

## Core Fields

| Field | Type | Description |
|---|---|---|
| `model` | string | Model name evaluated (e.g., `codegemma:7b`) |
| `difficulty` | string | Tier directory name (e.g., `single_fault`) |
| `difficulty_tier` | integer | Numeric tier (`1`, `2`, `3`) when available |
| `difficulty_code` | string | Short tier code (`T1`, `T2`, `T3`) |
| `difficulty_label` | string | Human-readable tier label |
| `difficulty_definition` | string | Tier definition text |
| `category` | string | Fault category (e.g., `logic`, `security`) |
| `benchmark` | string | Benchmark name (directory-level case name) |
| `benchmark_id` | string | Unique benchmark identifier (typically composed from difficulty/category/benchmark) |

---

## Outcome Fields

| Field | Type | Description |
|---|---|---|
| `passed` | boolean | True if benchmark repair is successful |
| `verified` | boolean | True if sandbox verification returned a valid SUCCESS payload |
| `failure_reason` | string \| null | Structured failure label (null/empty on success) |
| `return_code` | integer | Subprocess return code for the attempt |
| `timed_out` | boolean | Whether subprocess timed out |

---

## Performance Fields

| Field | Type | Description |
|---|---|---|
| `ttr` | number | Time to resolution in seconds (attempt-level repair duration) |
| `wall_time` | number | End-to-end subprocess wall-clock time |
| `iterations` | integer | Number of completed repair attempts/tool calls |

---

## Artifact Path Fields

| Field | Type | Description |
|---|---|---|
| `patch_file` | string \| null | Path to exported unified patch for successful repair |
| `repaired_file` | string \| null | Path to exported repaired source for successful repair |

---

## Typical Success Record

```json
{
  "model": "codegemma:7b",
  "difficulty": "single_fault",
  "difficulty_code": "T1",
  "category": "logic",
  "benchmark": "factorial",
  "benchmark_id": "single_fault:logic:factorial",
  "passed": true,
  "verified": true,
  "ttr": 3.66,
  "wall_time": 4.12,
  "iterations": 1,
  "failure_reason": null,
  "return_code": 0,
  "timed_out": false,
  "patch_file": "tests/logs/run_.../patches/codegemma-7b__single_fault__logic__factorial.patch",
  "repaired_file": "tests/logs/run_.../repairs/codegemma-7b__single_fault__logic__factorial.py"
}
```

---

## Typical Failure Record

```json
{
  "model": "qwen2.5-coder:3b",
  "difficulty": "single_fault",
  "difficulty_code": "T1",
  "category": "security",
  "benchmark": "sql_injection",
  "benchmark_id": "single_fault:security:sql_injection",
  "passed": false,
  "verified": false,
  "ttr": 120.0,
  "wall_time": 120.3,
  "iterations": 4,
  "failure_reason": "Sandbox verification failure",
  "return_code": 1,
  "timed_out": false,
  "patch_file": null,
  "repaired_file": null
}
```

---

## Notes

- Not all fields are guaranteed in every historical run format.
- Optional fields may be null/empty depending on run outcome and exporter version.
- Prefer schema-tolerant loading in analysis scripts (handle missing columns gracefully).