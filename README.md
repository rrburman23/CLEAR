# CLEAR: Closed-Loop Engine for Autonomous Repair

**Author:** Rohan Burman
**Programme:** MSc Artificial Intelligence, Queen Mary University of London

---

## 📖 Overview

CLEAR (Closed-Loop Engine for Autonomous Repair) is a local autonomous software repair framework that investigates the ability of Small Language Models (SLMs) to automatically detect, modify, and verify faulty Python programs.

Unlike traditional code completion systems, CLEAR implements a **closed-loop repair architecture** where the language model is not trusted to simply generate a solution. Instead, the agent must:

1. Analyse the provided faulty program.
2. Generate a candidate repair.
3. Execute the repair attempt inside a controlled validation environment.
4. Observe test feedback.
5. Iterate until the supplied verification suite passes or the repair budget is exhausted.

The system uses a **Hybrid Orchestrator architecture**, separating deterministic program execution and validation from probabilistic model reasoning.

CLEAR is designed around the principle that autonomous repair agents should be evaluated through verified execution rather than generated code quality alone.

---

## 🚀 Core Features

### Hybrid Agent Orchestration

CLEAR separates:

- **Deterministic operations**
  - File handling
  - Test execution
  - Verification
  - Benchmark management
  - Metric collection

from:

- **Probabilistic reasoning**
  - Fault analysis
  - Code modification
  - Repair strategy generation

The orchestration layer is implemented using LangGraph, providing controlled state transitions and bounded repair iterations.

### Closed-Loop Verification

Repairs are only considered successful when:

1. The generated code is applied.
2. The validation suite executes successfully.
3. The repaired program passes all tests.

A model response alone is never considered a successful repair.

### Local Small Language Model Inference

CLEAR supports local inference through Ollama, allowing experiments without external API calls.

Advantages:

- No cloud dependency
- Reproducible experiments
- Reduced privacy concerns
- Offline-compatible evaluation

Currently evaluated models include:

- qwen2.5-coder
- deepseek-coder
- codegemma
- codellama
- llama3.1
- gemma2
- mistral-nemo
- phi3

### Automated Benchmark Framework

CLEAR includes a benchmark suite designed around common software fault categories:

```
tests/
└── benchmarks/
    ├── logic/
    │   ├── factorial/
    │   ├── fibonacci/
    │   └── sort/
    │
    ├── syntax/
    │   ├── missing_colon/
    │   └── unterminated_string/
    │
    ├── exception/
    │   ├── divide/
    │   └── json/
    │
    ├── api/
    ├── security/
    ├── data_structure/
    └── edge_case/
```

Each benchmark contains:

```
benchmark_name/
├── target.py   # intentionally faulty program
└── test_x.py   # validation oracle
```

---

## 📁 Project Structure

```
CLEAR/
│
├── src/
│   ├── agent/
│   │   └── logic.py         # LangGraph repair agent
│   │
│   ├── core/
│   │   └── sandbox management
│   │
│   ├── tools/
│   │   └── repair execution tools
│   │
│   ├── utils/
│   │   └── terminal formatting utilities
│   │
│   └── main.py               # CLEAR repair CLI
│
├── tests/
│   ├── benchmarks/            # fault taxonomy dataset
│   └── logs/                  # experiment logs
│
├── Dockerfile                 # execution environment
├── run_benchmarks.py          # evaluation pipeline
├── requirements.txt
└── README.md
```

---

## 🛠️ Prerequisites

Required:

- Python 3.10+
- Docker Desktop
- Ollama

Recommended:

- NVIDIA GPU for faster local inference

---

## ⚙️ Installation

### 1. Clone Repository

```bash
git clone https://github.com/rrburman23/CLEAR.git
cd CLEAR
```

### 2. Create Virtual Environment

**Windows:**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS:**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -e .
```

### 4. Install Local Model

Example:

```bash
ollama pull qwen2.5-coder:7b
```

---

## 💻 Usage

### Single Repair Experiment

CLEAR can repair an individual Python program:

```bash
python -m src.main \
  --code path/to/broken_program.py \
  --test path/to/test_suite.py
```

Example:

```bash
python -m src.main \
  --code tests/benchmarks/logic/factorial/target.py \
  --test tests/benchmarks/logic/factorial/test_logic.py
```

Successful repairs produce:

```
Benchmark: logic:factorial

REPAIR_SUCCESS | Benchmark=logic:factorial
Successfully overwritten target.py
```

Failed repairs include a failure reason:

```
REPAIR_FAILED |
Benchmark=edge_case:duplicates |
Reason=Verification failed: sandbox tests did not pass
```

---

## 📊 Benchmark Evaluation

Run the complete benchmark suite:

```bash
python -m run_benchmarks
```

Specific models:

```bash
python -m run_benchmarks --models qwen2.5-coder:7b
```

Specific categories:

```bash
python -m run_benchmarks --types logic exception
```

---

## 📈 Evaluation Metrics

CLEAR records:

- Repair success
- Failure reason
- Time to resolution
- Number of repair iterations
- Model performance by benchmark category

### Success Rate ($S_R$)

Percentage of benchmarks successfully repaired:

$$
S_R = \frac{N_{successful}}{N_{total}} \times 100
$$

### Mean Time To Resolution ($TTR$)

Average time required for a successful repair:

$$
TTR = \frac{\sum T_i}{N_{successful}}
$$

where $T_i$ is the repair execution time for benchmark $i$.

### Iteration Efficiency ($I_E$)

Measures repair precision based on tool usage:

$$
I_E = \frac{1}{N_{successful}} \sum_{i=1}^{N_{successful}} \frac{1}{k_i}
$$

where $k_i$ is the number of repair iterations for benchmark $i$. Higher values indicate fewer repair attempts.

---

## 🔎 Failure Analysis

CLEAR records unsuccessful repairs using structured failure categories, for example:

- Verification failed: sandbox tests did not pass
- No CLEAR_RESULT returned
- Repair generated but code was not applied
- Agent terminated without verified fix

This allows evaluation beyond simple pass/fail rates by analysing where models fail.

---

## 📝 Research Context

CLEAR was developed as an MSc Artificial Intelligence research project at Queen Mary University of London.

The project investigates whether locally deployed Small Language Models can perform reliable autonomous software repair through controlled execution, verification, and iterative feedback.

Developed by **Rohan Burman**
MSc Artificial Intelligence
Queen Mary University of London
2026