# Benchmark Specification

## Tier Definitions

| Folder                    | Tier | Label                               | Definition                                      |
| ------------------------- | ---- | ----------------------------------- | ----------------------------------------------- |
| `single_fault`            | T1   | Single-Fault Repair                 | One intentionally seeded defect                 |
| `compound_same_category`  | T2   | Homogeneous Compound-Fault Repair   | Multiple defects from same category             |
| `compound_cross_category` | T3   | Heterogeneous Compound-Fault Repair | Multiple defects from different categories      |

## Directory Layout

```text
tests/benchmarks/
├── single_fault/<category>/<benchmark_name>/
├── compound_same_category/<category>/<benchmark_name>/
└── compound_cross_category/<category_or_mixed>/<benchmark_name>/
```

Each benchmark must include:

- `target.py` (faulty implementation)
- `test_<benchmark_name>.py` (deterministic oracle)

## Categories

- algorithm
- api
- concurrency
- data_structure
- edge_case
- exception
- logic
- oop
- python
- security
- syntax

## Oracle Requirements

Each benchmark oracle must:

- contain at least 3 discoverable pytest tests;
- validate normal + edge/exception behaviour where appropriate;
- avoid non-deterministic checks.

Disallowed patterns:

- module-level assertions;
- manual AssertionError wrappers;
- printed success markers;
- `exit()` / `quit()`;
- order-dependent tests.

## Validation Command

```bash
python tests/validate_benchmarks.py
```

Validation confirms benchmark structure and oracle quality before model evaluation.