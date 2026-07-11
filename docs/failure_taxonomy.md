# Failure Taxonomy

CLEAR records structured failure reasons to support diagnosis beyond binary pass/fail.

## Common Categories

- `No valid repair attempt generated`
- `Sandbox verification failure`
- `Malformed candidate code`
- `Candidate runtime failure`
- `Candidate import failure`
- `Sandbox timeout`
- `Sandbox infrastructure failure`
- `Repair budget exhausted`
- `Model protocol failure`
- `Model stagnation`

## Why This Matters

Failure taxonomy enables:

- model-level weakness profiling;
- category-level failure clustering;
- targeted prompt/agent improvements;
- reproducible error analysis across runs.