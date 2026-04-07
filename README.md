# CLEAR: Closed-Loop Engine for Autonomous Repair

CLEAR is an autonomous, local-first agentic framework designed to transform code generation from a passive text-completion task into a closed-loop control problem. By utilizing Small Language Models (SLMs) and secure Docker sandboxing, CLEAR observes its own execution errors and iterates until the generated code passes validation.

## 🚀 Core Features

- **Self-Correction Loop:** Implements a ReAct (Reasoning and Acting) state machine to analyze tracebacks and self-heal code.
- **Local Sovereignty:** Designed for local inference using Ollama/vLLM, ensuring data privacy and offline capability.
- **Infrastructure Safety:** A "containment-first" approach using ephemeral Docker containers to safely execute and test agent-generated code.
- **Structured Tool-Use:** A dedicated API for the agent to interact with the file system and test runners via JSON commands.

## 📁 Project Structure

```text
CLEAR/
├── docker/             # Dockerfile and sandbox configurations
├── notebooks/          # Evaluation benchmarks and data analysis
├── src/
│   ├── agent/          # LangGraph state machine and reasoning logic
│   ├── core/           # Docker SDK orchestration and sandbox management
│   ├── tools/          # Agent-invocable Python tools (file I/O, pytest)
│   └── main.py         # Primary entry point
└── tests/              # Unit tests for the CLEAR framework
