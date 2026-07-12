# CLEAR Documentation Index

Welcome to the CLEAR documentation hub.

Use this page as the entry point for framework usage, benchmark design, evaluation, and reproducibility.

---

## Getting Started

- **Project overview and quickstart:** [`../README.md`](../README.md)

---

## Core Documentation

- **CLI reference (all command-line options):** [`cli_reference.md`](cli_reference.md)
- **Benchmark specification (tiers, layout, oracle rules):** [`benchmark_spec.md`](benchmark_spec.md)
- **Evaluation metrics and formulas:** [`metrics.md`](metrics.md)
- **Failure taxonomy (structured failure reasons):** [`failure_taxonomy.md`](failure_taxonomy.md)
- **Reproducibility guide (environment + repeatable runs):** [`reproducibility.md`](reproducibility.md)
- **Model reporting template:** [`model_matrix.md`](model_matrix.md)
- **Contribution guide:** [`contributing.md`](contributing.md)

---

## Suggested Reading Order

If you're new to CLEAR:

1. [`../README.md`](../README.md)
2. [`cli_reference.md`](cli_reference.md)
3. [`benchmark_spec.md`](benchmark_spec.md)
4. [`metrics.md`](metrics.md)
5. [`reproducibility.md`](reproducibility.md)

If you're adding or curating benchmarks:

1. [`benchmark_spec.md`](benchmark_spec.md)
2. [`reproducibility.md`](reproducibility.md)
3. [`contributing.md`](contributing.md)

If you're writing results/analysis:

1. [`metrics.md`](metrics.md)
2. [`failure_taxonomy.md`](failure_taxonomy.md)
3. [`model_matrix.md`](model_matrix.md)

---

## Notes

- `README.md` is the canonical project front page.
- Files in `docs/` provide detailed, task-specific reference material.
- Keep CLI docs synced with `argparse` definitions in source code.
  