# CLEAR: Closed-Loop Engine for Autonomous Repair

CLEAR is an autonomous, local-first agentic framework designed to transform code generation from a passive text-completion task into a closed-loop control problem. By utilizing Small Language Models (SLMs) and secure Docker sandboxing, CLEAR observes its own execution errors and iterates until the generated code passes validation.

## 🚀 Core Features

- **Self-Correction Loop**: Implements a ReAct (Reasoning and Acting) state machine to analyze tracebacks and self-heal code.
- **Local Sovereignty**: Optimized for local inference using Ollama or vLLM, ensuring data privacy and removing API dependency.
- **Infrastructure Safety**: A "containment-first" approach using ephemeral Docker containers to safely execute and test agent-generated code without risking the host system.
- **Structured Tool-Use**: A dedicated API for the agent to interact with the file system and test runners via structured JSON commands.

## 📁 Project Structure

```plaintext
CLEAR/
├── docker/             # Dockerfile and sandbox execution configurations
├── notebooks/          # Evaluation benchmarks and data visualization
├── src/
│   ├── agent/          # LangGraph state machine and reasoning logic
│   ├── core/           # Docker SDK orchestration and sandbox management
│   ├── tools/          # Agent-invocable Python tools (file I/O, test runners)
│   └── main.py         # Primary framework entry point
└── tests/              # Unit tests for the CLEAR framework itself
```

## 🛠️ Prerequisites

- **Docker Desktop**: Mandatory for the isolated execution sandbox.
- **Ollama**: For serving local models (Recommended: deepseek-coder-v2 or llama3.1:8b).
- **Python 3.10+**
- **Tailscale** (Optional): For secure remote access to high-VRAM GPU hosts.

## ⚙️ Installation & Setup

### Clone the Repository

```bash
git clone https://github.com/USERNAME/CLEAR.git
cd CLEAR
```

### Initialize Virtual Environment

```bash
python -m venv venv

# Windows
.\venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Prepare the Reasoning Core

```bash
ollama pull deepseek-coder-v2
```

## 📊 Evaluation Metrics

The framework's performance is quantified using two primary metrics across standardized benchmarks (e.g., HumanEval or SWE-bench):

### 1. Success Rate (SR)

The percentage of bugs successfully resolved within a maximum of K iterations.

$$SR = \frac{1}{N}\sum_{i=1}^{N} \mathbb{1}(k_i \leq K_{max})$$

### 2. Iteration Efficiency (IE)

A metric to penalize agents that require excessive loops, calculated for successful runs.

$$IE = \frac{1}{N_{success}}\sum_{i=1}^{N_{success}} \frac{1}{k_i}$$

---

Developed as part of an MSc AI (Languages and Agents) Research Project at Queen Mary University of London.
