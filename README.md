# CLEAR: Closed-Loop Engine for Autonomous Repair
**Author:** Rohan Burman | **MSc Artificial Intelligence**, Queen Mary University of London

## 📖 Overview
CLEAR is a localized, autonomous software engineering agent designed to safely generate, compile, test, and self-heal code without external dependencies. Moving beyond passive text-completion paradigms, CLEAR utilizes a **Hybrid Orchestrator** architecture to decouple deterministic host-system operations from probabilistic Small Language Model (SLM) inference.

By constraining the agent to an "Atomic Logic Engine," the framework eliminates navigational hallucinations and state-space exhaustion. The agent autonomously executes its generated abstract syntax trees (AST) within an ephemeral, air-gapped Docker sandbox, iterating on standard error tracebacks until the code passes validation.

## 🚀 Core Features

- **Hybrid Orchestrator**: Separates deterministic host-level file I/O (Python) from probabilistic reasoning (LLM) to maximize context-window efficiency.
- **Ephemeral Sandboxing**: A "containment-first" approach using resource-throttled, network-disabled Docker containers to safely execute agent-generated code without risking the host OS.
- **Linter-Fallback Mechanism**: A deterministic static analysis interceptor that preempts recursive agent loops caused by unparseable structural syntax errors.
- **Local Sovereignty**: Optimized for local inference using Ollama, ensuring absolute data privacy, GDPR compliance, and zero API dependency.

## 📁 Project Structure

```plaintext
CLEAR/
├── src/
│   ├── agent/            # LangGraph state machine, Linter-Fallback, and reasoning logic
│   ├── core/             # Docker SDK orchestration and sandbox management
│   ├── tools/            # Agent-invocable Python tools and Docker SDK interaction
│   └── main.py           # CLI entry point (Hybrid Orchestrator)
├── tests/
│   └── benchmarks/       # Empirical fault taxonomy dataset (Logic, Syntax, Exception)
├── Dockerfile            # Secure ephemeral execution environment blueprint
├── run_benchmarks.py     # Automated evaluation pipeline for comparative analysis
└── requirements.txt      # Python dependencies
```

## 🛠️ Prerequisites

- **Docker Desktop**: Mandatory for the isolated execution sandbox.
- **Ollama**: For serving local models.
- **Python 3.10+**

## ⚙️ Installation & Setup

1. **Clone the Repository**

```bash
git clone https://github.com/rrburman23/CLEAR.git
cd CLEAR
```

2. **Initialize Virtual Environment**

```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

3. **Install Dependencies & CLI Tool**

```bash
pip install -e .
```

4. **Build the Execution Sandbox**

```bash
docker build -t clear-executor .
```

5. **Prepare the Reasoning Core**

*(Note: Empirical evaluation demonstrated Qwen2.5-Coder to be the most effective model for this architecture.)*

```bash
ollama pull qwen2.5-coder:7b
```

## 💻 Usage Instructions

### 1. Single-File Autonomous Repair

You can use the CLEAR CLI tool to autonomously repair any Python file, provided it has a corresponding test suite to act as the verification oracle.

```bash
clear-repair --code path/to/broken_code.py --test path/to/test_suite.py
```

### 2. Run the Empirical Benchmark Suite

To replicate the evaluation data presented in the dissertation, run the automated benchmarking pipeline. This will test the agent against a taxonomy of Logic, Syntax, and Exception faults.

```bash
python run_benchmarks.py
```

## 📊 Evaluation Metrics

The framework's performance was evaluated against three distinct fault taxonomies using local SLMs. The automated pipeline captures the following metrics:

### 1. Success Rate ($S_R$)

The percentage of bugs successfully resolved within the graph recursion limit ($K_{max}$).

$$S_R = \frac{1}{N}\sum_{i=1}^{N} \mathbb{1}(k_i \leq K_{max})$$

### 2. Mean Time to Resolution ($TTR$)

The average execution time required for the agent to resolve the fault, verify it against the oracle, and terminate the graph.

### 3. Iteration Efficiency ($I_E$)

A metric to evaluate the reasoning precision of the model, calculated by tracking the total number of tool calls ($k$) required for successful runs.

$$I_E = \frac{1}{N_{success}}\sum_{i=1}^{N_{success}} \frac{1}{k_i}$$

*Developed as a Master's Research Project at Queen Mary University of London, 2026.*
