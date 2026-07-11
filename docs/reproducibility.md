# Reproducibility Guide

## Environment Baseline

- Python version (record exact patch version)
- Docker version
- Ollama version
- GPU/CPU hardware
- OS version

## Recommended Procedure

1. Validate benchmarks:
   ```bash
   python tests/validate_benchmarks.py
   ```

2. Ensure a clean benchmark state:
   ```bash
   python -m run_benchmarks --git-reset-benchmarks
   ```

3. Run fixed configuration:
   ```bash
   python -m run_benchmarks --models codegemma:7b --types logic security
   ```

4. Archive generated `tests/logs/run_*` outputs.

## Repeated Runs

Use multiple repeated runs to estimate variance in:

- success rate
- TTR
- iteration counts
- failure distribution