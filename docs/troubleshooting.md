# Troubleshooting

This guide covers common runtime and experiment issues in CLEAR and how to resolve them quickly.

---

## 1) Docker not running / sandbox failures

### Symptoms

- Repair attempts fail immediately.
- Failure reason includes:
  - `Sandbox infrastructure failure`
  - Docker daemon / container errors
- No tests actually execute in sandbox.

### Checks

```bash
docker version
docker ps
docker images
```

### Fix

1. Start Docker Desktop (or Docker daemon).
2. Rebuild executor image from repo root:
   ```bash
   docker build -t clear-executor .
   ```
3. Re-run benchmark or single repair.

### Notes

- CLEAR expects the sandbox image tag: `clear-executor`.
- If Docker is running but image is missing, builds/tests still fail.

---

## 2) Model not pulled / Ollama model unavailable

### Symptoms

- Model invocation fails before repair loop starts.
- Errors referencing unknown/missing model in Ollama.
- Benchmark fails for selected model(s) only.

### Checks

```bash
ollama list
```

### Fix

Pull missing model(s):

```bash
ollama pull codegemma:7b
```

Or use CLEAR pull utility:

```bash
# list configured models
python -m src.utils.pull_models --list

# pull selected
python -m src.utils.pull_models --models codegemma:7b phi3:mini

# pull all configured
python -m src.utils.pull_models --all
```

### Notes

- Available benchmark models are defined in `src/utils/config.py` (`AVAILABLE_MODELS`).
- Single-run default model is `CLEAR_MODEL` env var fallback (commonly `codegemma:7b`).

---

## 3) Timeout errors

Timeouts can happen at different layers.

### A) Benchmark subprocess timeout (`--timeout`)

#### Symptoms
- Attempt marked timed out at runner level.
- Failure reason may indicate benchmark/agent timeout.

#### Fix
Increase per-benchmark timeout:

```bash
python -m run_benchmarks --timeout 600
```

---

### B) Agent budget/graph exhaustion

#### Symptoms
- Failure reason:
  - `Repair budget exhausted (Graph recursion limit)`
  - or repeated retries without completion.

#### Fix
- For `src.main`, increase recursion budget:
  ```bash
  python -m src.main --code ... --test ... --recursion-limit 41
  ```
- For benchmarks, tune:
  - `--max-iterations`
  - `--timeout`

---

### C) Slow model/hardware

#### Symptoms
- High TTR, frequent timeouts on larger models.

#### Fix
- Use smaller/faster model for baseline.
- Reduce concurrent system load.
- Prefer GPU inference if available.

---

## 4) No `CLEAR_RESULT` returned

### Symptoms

- Runner reports missing structured result.
- Failure reason includes `No CLEAR_RESULT returned`.
- Subprocess exits without expected result block.

### Likely Causes

- Unhandled exception in `src.main`.
- Process terminated before result emission.
- Output parsing disrupted by crash/interrupt.

### Fix Workflow

1. Re-run the same case directly via `src.main`:
   ```bash
   python -m src.main --code <target.py> --test <test_file.py>
   ```
2. Inspect terminal traceback and `execution.log`.
3. Check:
   - benchmark files exist and are readable;
   - test file is valid Python;
   - Docker/Ollama availability;
   - model availability.
4. Fix root cause and retry.

---

## 5) Benchmark appears to “pass instantly” (invalid benchmark)

### Symptoms

- Faulty `target.py` already passes tests.
- Unrealistically high success with zero meaningful repair.

### Fix

Validate benchmark corpus:

```bash
python tests/validate_benchmarks.py
```

Then manually ensure faulty target fails at least one oracle test before repair.

---

## 6) Quick pre-run checklist

- [ ] Docker running
- [ ] `clear-executor` image built
- [ ] Ollama running
- [ ] Required model(s) pulled
- [ ] Benchmark corpus validated
- [ ] Correct CLI filters (`--models`, `--tiers`, `--types`)