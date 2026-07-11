# CLI Reference

This document reflects the current command-line interfaces for:

- `python -m run_benchmarks`
- `python -m src.main`

---

## `run_benchmarks` CLI

```bash
python -m run_benchmarks [OPTIONS]
```

### Purpose

Runs multi-model benchmark evaluation sequentially and exports structured results.

### Options

| Option | Type | Default | Description |
|---|---|---:|---|
| `-h, --help` | flag | — | Show help and exit |
| `--models MODEL [MODEL ...]` | list[str] | all configured models | Models to evaluate sequentially |
| `--tiers TIER [TIER ...]` | list[str] | all tiers | Benchmark difficulty tiers to evaluate |
| `--types TYPE [TYPE ...]` | list[str] | all categories | Benchmark categories to evaluate |
| `--max-iterations N` | int | `15` | Maximum accepted repair attempts per benchmark |
| `--timeout SECONDS` | float | `300` | Wall-clock timeout per benchmark subprocess |
| `--git-reset-benchmarks` | flag | `False` | Run `git restore tests/benchmarks` before evaluation |
| `--stop-on-error` | flag | `False` | Stop experiment on catastrophic benchmark-runner error |

### Valid `--tiers` values

- `single_fault` (T1)
- `compound_same_category` (T2)
- `compound_cross_category` (T3)

> Current status: today most benchmarks may still be in `single_fault`.  
> `compound_same_category` and `compound_cross_category` are supported and can be populated incrementally.

### Valid `--types` values

- `algorithm`
- `api`
- `concurrency`
- `data_structure`
- `edge_case`
- `exception`
- `logic`
- `oop`
- `python`
- `security`
- `syntax`

### Examples

```bash
# Run all configured models, tiers, and categories
python -m run_benchmarks

# Run one model on Tier 1 only
python -m run_benchmarks --models codegemma:7b --tiers single_fault

# Run multiple tiers (future-ready)
python -m run_benchmarks --tiers single_fault compound_same_category

# Run selected categories across selected tiers
python -m run_benchmarks --tiers single_fault --types logic security

# Increase timeout
python -m run_benchmarks --timeout 600

# Restore benchmark files before running
python -m run_benchmarks --git-reset-benchmarks
```

---

## `src.main` CLI

```bash
python -m src.main --code <PATH> --test <PATH> [OPTIONS]
```

### Purpose

Runs one autonomous repair task and emits machine-readable `CLEAR_RESULT`.

### Required Arguments

| Option | Type | Required | Description |
|---|---|---|---|
| `--code PATH` | str | yes | Path to broken `target.py` |
| `--test PATH` | str | yes | Path to benchmark verification test file |

### Optional Arguments

| Option | Type | Default | Description |
|---|---|---:|---|
| `-h, --help` | flag | — | Show help and exit |
| `--recursion-limit N` | int | `31` | LangGraph recursion limit |

### Model selection note

`src.main` uses the configured default model from project config (commonly `codegemma:7b`).  
Benchmark comparisons should be run through `run_benchmarks` using `--models`.

### Example

```bash
python -m src.main \
  --code tests/benchmarks/single_fault/logic/factorial/target.py \
  --test tests/benchmarks/single_fault/logic/factorial/test_factorial.py
```

---

## Benchmark Directory Layout

```text
tests/benchmarks/
├── single_fault/
│   └── <category>/
│       └── <benchmark_name>/
│           ├── target.py
│           └── test_<benchmark_name>.py
├── compound_same_category/
│   └── <category>/
│       └── <benchmark_name>/
│           ├── target.py
│           └── test_<benchmark_name>.py
└── compound_cross_category/
    └── <category_or_mixed>/
        └── <benchmark_name>/
            ├── target.py
            └── test_<benchmark_name>.py
```

---

## Notes

- Use canonical flags (`-h` / `--help`) in scripts.
- Keep CLI docs in sync with argparse definitions when options change.