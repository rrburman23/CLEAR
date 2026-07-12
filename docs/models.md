# Model and Runtime Configuration

This page explains how CLEAR selects models, how to manage available benchmark models, and required runtime dependencies.

---

## Source of Truth

The canonical model configuration lives in:

- `src/utils/config.py`

Key fields:

- `MODEL_NAME` → default model used by `src.main`
- `AVAILABLE_MODELS` → models allowed for benchmark runs
- `SUPPORTED_TOOL_MODELS` → families with native tool-calling support

---

## Default Model for Single Repairs

`python -m src.main` uses:

```python
MODEL_NAME = os.getenv("CLEAR_MODEL", "codegemma:7b")
```

So default is `codegemma:7b` unless overridden by environment variable.

Example override:

```bash
# Windows PowerShell
$env:CLEAR_MODEL="qwen2.5-coder:7b"
python -m src.main --code ... --test ...

# Linux/macOS
CLEAR_MODEL=qwen2.5-coder:7b python -m src.main --code ... --test ...
```

---

## Available Benchmark Models

Benchmark model options are read from `AVAILABLE_MODELS` in `src/utils/config.py`.

Current configured list:

- `qwen2.5-coder:7b`
- `granite-code:8b`
- `codegemma:7b`
- `codellama:7b`
- `llama3.1:8b`
- `gemma2:9b`
- `mistral-nemo:12b`
- `deepseek-r1:8b`
- `phi3:mini`
- `qwen2.5-coder:3b`
- `ornith:9b`

Use them with:

```bash
python -m run_benchmarks --models codegemma:7b qwen2.5-coder:7b
```

---

## Pulling Models with CLEAR Utility

CLEAR provides a helper CLI:

- `src/utils/pull_models.py`

### Show configured models

```bash
python -m src.utils.pull_models --list
```

### Pull selected models

```bash
python -m src.utils.pull_models --models codegemma:7b phi3:mini
```

### Pull all configured models

```bash
python -m src.utils.pull_models --all
```

> If a model is configured but not pulled in Ollama, inference will fail at runtime.

---

## Adding New Models

To add a model to benchmark runs:

1. Add model name to `AVAILABLE_MODELS` in `src/utils/config.py`.
2. Pull it locally:
   ```bash
   ollama pull <model_name>
   ```
3. Run benchmarks with `--models <model_name>`.

If model family supports native tool calling, consider updating `SUPPORTED_TOOL_MODELS`.

---

## Docker Runtime Requirement

CLEAR verification runs in Docker sandbox containers.

Build required image from repository root:

```bash
docker build -t clear-executor .
```

Ensure Docker Desktop is running before executing repairs/benchmarks.

---

## Quick Checklist

- [ ] Docker running
- [ ] `clear-executor` image built
- [ ] Ollama running
- [ ] Required models pulled
- [ ] `CLEAR_MODEL` set if overriding default single-run model