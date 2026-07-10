# CLEAR: Closed-Loop Engine for Autonomous Repair

**Author:** Rohan Burman
**Programme:** MSc Artificial Intelligence, Queen Mary University of London
**Year:** 2026

---

## Overview

CLEAR (Closed-Loop Engine for Autonomous Repair) is a local, autonomous software repair framework designed to evaluate whether Small Language Models (SLMs) can autonomously detect, repair, and verify faulty Python programs.

Unlike traditional code generation systems that evaluate models on static code quality, CLEAR evaluates repair agents through execution-based verification. A repair is only considered successful when the generated code:

1. Is produced by the language model.
2. Is correctly applied to the target program.
3. Executes inside an isolated Docker environment.
4. Passes the supplied verification test suite.

CLEAR implements a closed-loop architecture in which the agent observes execution feedback and iteratively improves its solution until either the repair succeeds or the iteration budget is exhausted. The system follows a Hybrid Orchestrator architecture, cleanly separating deterministic software engineering operations from probabilistic language model reasoning.

---

## Research Objective

CLEAR investigates the following question:

> How effectively can locally deployed Small Language Models perform autonomous software repair when constrained by execution feedback and automated verification?

The framework evaluates models across eleven fault categories: syntax errors, logical defects, exception handling failures, API misuse, security vulnerabilities, data structure errors, edge case handling, algorithmic faults, object-oriented programming issues, Python language feature misuse, and concurrency problems.

---

## System Architecture

CLEAR consists of four major components arranged in an autonomous feedback loop:

```text
        ┌────────────────────┐
        │   Small Language   │
        │  Model  (Ollama)   │
        └─────────┬──────────┘
                  │  candidate repair
                  ▼
        ┌────────────────────┐
        │    Repair Agent    │
        │    (LangGraph)     │
        └─────────┬──────────┘
                  │  tool invocation
                  ▼
        ┌────────────────────┐
        │  Repair Executor   │
        │  (Docker sandbox)  │
        └─────────┬──────────┘
                  │  test results
                  ▼
        ┌────────────────────┐
        │  Test Validation   │
        │     Feedback       │
        └─────────┬──────────┘
                  │
                  └──────────► fed back to the model until
                               success or budget exhaustion
```

---

## Core Features

### Hybrid Agent Orchestration

CLEAR separates operations to keep the agent's search space small and its behaviour observable:

- **Deterministic operations** (framework): benchmark loading, file management, code execution, Docker sandbox orchestration, test execution, metric collection, and result exporting.
- **Probabilistic operations** (SLM): fault analysis, repair planning, code modification, and iterative debugging.

The orchestration layer uses LangGraph to provide controlled state transitions, bounded repair attempts, and observable repair states.

### Closed-Loop Repair Process

```text
Faulty Program → Fault Analysis → Generate Repair → Apply Code Change
      ▲                                                    │
      │                                                    ▼
      └──── Feedback Returned ◄──────────────────── Execute Tests
                    │
                    ▼
        Repair Success  /  Retry (until iteration budget exhausted)
```

The model is never trusted without verification: a textual claim of success is insufficient, and only a passing test suite terminates the loop.

### Local Small Language Model Inference

CLEAR uses [Ollama](https://ollama.com) for local inference, ensuring zero external API dependencies, offline experimentation, reproducible evaluation, and strict data privacy.

Models evaluated:

| Model | Parameters | Class |
|---|---|---|
| qwen2.5-coder:7b | 7B | Code-specialised |
| deepseek-coder:6.7b | 6.7B | Code-specialised |
| codegemma:7b | 7B | Code-specialised |
| codellama:7b | 7B | Code-specialised |
| llama3.1:8b | 8B | General-purpose |
| gemma2:9b | 9B | General-purpose |
| mistral-nemo:12b | 12B | General-purpose |
| qwen2.5-coder:3b | 3B | Resource-efficient |
| phi3:mini | 3.8B | Resource-efficient |

---

## Benchmark Framework

CLEAR contains a manually designed benchmark taxonomy. Each benchmark is a directory containing an intentionally faulty implementation (`target.py`) and a verification oracle (`test_*.py`):

```text
benchmark_name/
├── target.py                  # intentionally faulty implementation
└── test_benchmark_name.py     # verification oracle
```

### Benchmark Categories

```text
tests/benchmarks/
├── logic/            factorial, fibonacci, prime, palindrome,
│                     average, max, sort, temperature
├── syntax/           missing_colon, missing_bracket, missing_comma,
│                     bad_indent, unterminated_string
├── exception/        divide, json, file, dictionary, index,
│                     int_conversion, list
├── api/              calculator, parser, validator
├── data_structure/   list_mutation, nested_null, type_mismatch
├── edge_case/        duplicates, empty_list, empty_string,
│                     negative_numbers
├── algorithm/        binary_search, merge_sort, bfs, dfs
├── oop/              inheritance, dataclass, property
├── python/           context_manager, generator, decorator
├── concurrency/      race_condition, thread_lock
└── security/         command_injection, sql_injection, xss,
                      path_traversal, insecure_deserialization,
                      hardcoded_secret
```

---

## Project Structure

```text
CLEAR/
├── src/
│   ├── agent/
│   │   └── logic.py            # LangGraph repair agent
│   ├── core/
│   │   └── sandbox.py          # Docker sandbox management
│   ├── tools/
│   │   └── repair_tools.py     # repair execution tools
│   ├── utils/
│   │   ├── config.py
│   │   ├── diff.py
│   │   ├── parsers.py
│   │   └── result_export.py    # CSV / JSON / graph export
│   └── main.py                 # single-repair CLI entry point
├── tests/
│   ├── benchmarks/             # fault taxonomy dataset
│   ├── logs/                   # experiment logs
│   └── results/                # structured results and graphs
├── workspace/                  # sandbox working directory
├── Dockerfile                  # execution environment
├── run_benchmarks.py           # evaluation pipeline
├── run_benchmarks.bat          # repeated-run wrapper (Windows)
├── pyproject.toml
└── README.md
```

---

## Installation

### Requirements

- Python 3.10+
- Docker Desktop
- Ollama

Recommended: NVIDIA GPU for faster local inference.

### Setup

#### 1. Clone the repository

```bash
git clone https://github.com/rrburman23/CLEAR.git
cd CLEAR
```

#### 2. Create a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux/macOS
python -m venv .venv
source .venv/bin/activate
```

#### 3. Install CLEAR

```bash
pip install -e .
```

#### 4. Pull a local model

```bash
ollama pull codegemma:7b
```

---

## Usage

### Single Repair

Run the framework on a specific file and test suite:

```bash
python -m src.main \
  --code tests/benchmarks/logic/factorial/target.py \
  --test tests/benchmarks/logic/factorial/test_logic.py
```

### Benchmark Evaluation

Run the entire suite sequentially across all models:

```bash
python -m run_benchmarks
```

Evaluate specific models or categories:

```bash
# Specific model
python -m run_benchmarks --models codegemma:7b

# Multiple models
python -m run_benchmarks --models qwen2.5-coder:7b deepseek-coder:6.7b

# Specific fault categories
python -m run_benchmarks --types logic security oop python

# Skip graph generation (CSV and JSON are always exported)
python -m run_benchmarks --no-graphs
```

### Repeated Experiments (Windows)

For repeated experiments (e.g. measuring run-to-run TTR variance under identical configurations), the `run_benchmarks.bat` wrapper executes the evaluation pipeline multiple times in sequence, with a cooldown between runs. It accepts the same arguments as `run_benchmarks` and passes them straight through:

```bat
:: Run the full suite 3 times (default)
run_benchmarks.bat

:: Repeat a specific model / category configuration
run_benchmarks.bat --models qwen2.5-coder:7b --types logic
```

The number of repetitions is set by the `RUNS` variable at the top of the script (default: 3). Combined console output is appended to `batch_master.log` with per-run separators, and each repetition produces its own timestamped directory under `tests/results/`.

### Help

Both entry points are standard `argparse` CLIs — pass `-h` or `--help` to list all available options:

```bash
python -m src.main --help
python -m run_benchmarks --help
```

---

## Experiment Outputs

Each evaluation produces two kinds of output: human-readable execution logs and machine-readable structured results.

### Logs

Every run writes a descriptive log file to `tests/logs/`, named with the timestamp, models, and categories evaluated:

```text
tests/logs/
└── benchmark_20260709_220104_qwen2.5-coder-7b_logic_automated_repair.log
```

### Structured Results

Every run creates a timestamped results directory containing granular repair metrics for downstream academic analysis:

```text
tests/results/
└── 20260709_220104/
    ├── results.csv
    ├── results.json
    └── graphs/
        ├── success_rate_by_model.png
        ├── mean_ttr_by_model.png
        └── success_heatmap.png
```

**results.csv** contains one row per model-benchmark attempt:

| Field | Description |
|---|---|
| model | model evaluated |
| benchmark | benchmark identifier (e.g. `logic:factorial`) |
| category | fault taxonomy category |
| passed | whether the repair was verified successful |
| ttr | time to resolution in seconds |
| iterations | repair attempts used |
| failure_reason | failure taxonomy label (empty on success) |

**results.json** contains the same records plus per-model aggregate metrics. Example record:

```json
{
  "model": "codegemma:7b",
  "benchmark": "logic:factorial",
  "category": "logic",
  "passed": true,
  "ttr": 3.66,
  "iterations": 1,
  "failure_reason": null
}
```

### Generated Graphs

Each experiment automatically produces (requires `matplotlib`):

- `success_rate_by_model.png` — repair success rate per model
- `mean_ttr_by_model.png` — mean time to repair per model (successful repairs only)
- `success_heatmap.png` — success rate per model per fault category

---

## Evaluation Metrics

CLEAR evaluates models using six primary metrics.

### 1. Success Rate (SR)

Percentage of benchmarks successfully repaired. Higher is better.

$$ SR = \frac{N_{successful}}{N_{total}} \times 100 $$

### 2. Pass@1 (First-Iteration Success Rate)

Percentage of benchmarks the model repaired on its very first attempt ($k=1$). This separates "zero-shot" code generation capability from "multi-turn" ReAct reasoning.

$$ Pass@1 = \frac{N_{successful\_at\_1}}{N_{total}} \times 100 $$

### 3. Time To Resolution (TTR)

Mean time in seconds required to produce a verified repair. Lower is better.

$$ TTR = \frac{\sum T_i}{N_{successful}} $$

where $T_i$ is the repair execution time for benchmark $i$.

### 4. Iteration Efficiency (IE)

How efficiently the agent repairs programs. Higher values indicate fewer required repair attempts.

$$ IE = \frac{1}{N_{successful}} \sum_{i=1}^{N_{successful}} \frac{1}{k_i} $$

where $k_i$ is the number of repair iterations for benchmark $i$.

### 5. Average Repair Iterations (ARI)

Mean number of repair cycles across successful repairs. Lower values indicate more direct repairs.

$$ ARI = \frac{\sum k_i}{N_{successful}} $$

### 6. Failure Rate (FR)

Percentage of unsuccessful repairs. Lower is better.

$$ FR = \frac{N_{failed}}{N_{total}} \times 100 $$

---

## Failure Analysis

CLEAR records structured failure categories rather than a binary pass/fail, enabling empirical analysis of model constraints:

- No repaired code returned
- Verification failed (sandbox tests did not pass)
- Repair generated but not applied
- Agent exceeded iteration budget
- Sandbox execution failure

This taxonomy allows investigation of *where and why* models fail, beyond aggregate success rates.

---

## Research Context

CLEAR was developed as an MSc Artificial Intelligence dissertation project at Queen Mary University of London. The project investigates autonomous software repair using locally deployed Small Language Models through hybrid agent architectures, execution-based verification, sandbox isolation, iterative feedback, and benchmark-driven evaluation.

**Rohan Burman**
MSc Artificial Intelligence
Queen Mary University of London
2026
