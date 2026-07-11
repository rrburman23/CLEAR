# Contributing Guide

## Development Setup

```bash
git clone [<repo-url>](https://github.com/rrburman23/CLEAR.git)
cd CLEAR
python -m venv .venv
# activate venv
pip install -e .
```

## Before Opening a PR

- Run benchmark validator:
  ```bash
  python tests/validate_benchmarks.py
  ```
- Run tests (if configured):
  ```bash
  pytest
  ```
- Ensure formatting/lint checks pass (if configured).

## Benchmark Contribution Rules

When adding a benchmark:

- include `target.py`;
- include at least one `test_*.py`;
- include at least 3 deterministic tests;
- avoid forbidden oracle patterns;
- place benchmark in the correct tier/category path.

## PR Checklist

- [ ] Change is scoped and documented
- [ ] No benchmark oracle weakening
- [ ] Output schema compatibility preserved
- [ ] README/docs updated if behaviour changed