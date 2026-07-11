# CLEAR: Closed-Loop Engine for Autonomous Repair

**Author:** Rohan Burman  
**Programme:** MSc Artificial Intelligence, Queen Mary University of London  
**Year:** 2026

CLEAR is a local autonomous software-repair framework for evaluating whether Small Language Models (SLMs) can detect, repair, and verify faulty Python programs using execution feedback.

A repair is counted as successful **only** when the generated candidate is executed inside an isolated sandbox and passes the benchmark verification tests.

---

## Why CLEAR

Many coding benchmarks evaluate static output quality. CLEAR evaluates **verified repair behaviour** in an execution loop:

1. The model proposes a candidate repair.
2. The candidate is executed in a sandbox.
3. Deterministic tests return structured feedback.
4. The model iterates until success or budget exhaustion.

This enables research into practical autonomous repair, not just one-shot code generation.

---

## Core Features

- **Closed-loop orchestration** with LangGraph.
- **Execution-based verification** with deterministic pytest oracles.
- **Sandboxed execution** via Docker.
- **Local SLM inference** via Ollama (offline, private, reproducible).
- **Structured result export** for analysis and reporting.
- **Failure taxonomy** for diagnosing why repairs fail.

---

## System Architecture

```text
Model (Ollama)
   │ candidate repair
   ▼
Agent Orchestrator (LangGraph)
   │ run_repair_attempt tool call
   ▼
Sandbox Executor (Docker + pytest)
   │ structured verification feedback
   └──────────────► returned to model (retry loop)
```

---

## Installation

### Requirements

- Python 3.10+
- Docker Desktop
- Ollama

(Optional) NVIDIA GPU for faster local inference.

### Setup

```bash
git clone https://github.com/rrburman23/CLEAR.git
cd CLEAR

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -e .
```

Pull at least one local model:

```bash
ollama pull codegemma:7b
```

---

## Quick Start

### 1) Validate benchmark structure (recommended)

```bash
python tests/validate_benchmarks.py
```

### 2) Run a single repair task

`--code` and `--test` are required:

```bash
python -m src.main \
  --code tests/benchmarks/single_fault/logic/factorial/target.py \
  --test tests/benchmarks/single_fault/logic/factorial/test_factorial.py
```

> `src.main` uses the configured default model (commonly `codegemma:7b`) from project config.

### 3) Run multi-model benchmark evaluation

```bash
python -m run_benchmarks
```

Filtered example:

```bash
python -m run_benchmarks \
  --models codegemma:7b qwen2.5-coder:7b \
  --tiers single_fault \
  --types logic security
```

### 4) Show CLI help

```bash
python -m src.main --help
python -m run_benchmarks --help
```

---

## Benchmark Framework (Summary)

CLEAR benchmarks are organized into three difficulty tiers:

- **T1 (`single_fault`)**: one seeded defect
- **T2 (`compound_same_category`)**: multiple defects in the same category
- **T3 (`compound_cross_category`)**: multiple defects across different categories

Current datasets may be concentrated in T1 while T2/T3 are expanded incrementally.

### Benchmark directory layout

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

Supported categories:

`algorithm, api, concurrency, data_structure, edge_case, exception, logic, oop, python, security, syntax`

For complete benchmark rules, see:
- [`docs/benchmark_spec.md`](docs/benchmark_spec.md)

---

## Outputs

Each benchmark run creates a timestamped directory under `tests/logs/`:

```text
tests/logs/run_<timestamp>_<models>_<tiers>_<categories>_automated_repair/
```

Typical outputs include:

- `execution.log`
- `dataset.csv`
- `dataset.json`
- summary CSV files
- `analysis_report.md`
- `graphs/*.png` (when graph export is enabled)

---

## Evaluation Metrics

CLEAR reports:

- **SR**: Success Rate
- **Pass@1**: First-attempt success rate
- **TTR**: Time To Resolution
- **IE**: Iteration Efficiency
- **ARI**: Average Repair Iterations
- **FR**: Failure Rate

Definitions and formulas:
- [`docs/metrics.md`](docs/metrics.md)

---

## Project Structure

```text
CLEAR/
├── docs/
│   ├── index.md
│   ├── cli_reference.md
│   ├── benchmark_spec.md
│   ├── model_matrix.md
│   ├── metrics.md
│   ├── failure_taxonomy.md
│   ├── reproducibility.md
│   └── contributing.md
│
├── src/
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── candidate.py
│   │   ├── logic.py
│   │   ├── model_adapter.py
│   │   ├── prompts.py
│   │   ├── routing.py
│   │   └── state.py
│   │
│   ├── benchmarking/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── constants.py
│   │   ├── difficulty.py
│   │   ├── discovery.py
│   │   ├── execution.py
│   │   ├── failures.py
│   │   ├── metrics.py
│   │   ├── models.py
│   │   └── runner.py
│   │
│   ├── core/
│   │   └── sandbox.py
│   │
│   ├── reporting/
│   │   ├── __init__.py
│   │   ├── exporter.py
│   │   ├── graphs.py
│   │   ├── markdown.py
│   │   └── tables.py
│   │
│   ├── tools/
│   │   └── agent_tools.py
│   │
│   ├── utils/
│   │   ├── config.py
│   │   ├── diff.py
│   │   ├── parsers.py
│   │   └── terminal.py
│   │
│   └── main.py
│
├── tests/
│   ├── benchmarks/
│   │   ├── single_fault/
│   │   ├── compound_same_category/
│   │   └── compound_cross_category/
│   ├── logs/
│   └── validate_benchmarks.py
│
├── run_benchmarks.py
├── run_benchmarks.bat
├── Dockerfile
├── pyproject.toml
└── README.md
```

---

## Documentation

- [Documentation Index](docs/index.md)
- [CLI Reference](docs/cli_reference.md)
- [Benchmark Specification](docs/benchmark_spec.md)
- [Model Matrix Template](docs/model_matrix.md)
- [Metrics and Evaluation](docs/metrics.md)
- [Failure Taxonomy](docs/failure_taxonomy.md)
- [Experiment Reproducibility Guide](docs/reproducibility.md)
- [Contributor Guide](docs/contributing.md)

---

## Research Context

CLEAR was developed as an MSc Artificial Intelligence dissertation project at Queen Mary University of London.

**Rohan Burman**  
MSc Artificial Intelligence  
Queen Mary University of London  
2026