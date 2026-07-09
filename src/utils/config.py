"""
CLEAR Global Configuration Module
Ensures environment variables and capabilities are loaded exactly once.
"""

import os
from dotenv import load_dotenv

# Load environment variables once for the entire lifecycle
load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
USE_REAL_LLM = os.getenv("USE_REAL_LLM", "False").lower() == "true"
MODEL_NAME = os.getenv("CLEAR_MODEL", "codegemma:7b")

# Tool compatibility detection
SUPPORTED_TOOL_MODELS = [
    "qwen2.5",
    "llama3.1",
    "mistral-nemo",
    "codegemma",
    "codellama",
]
SUPPORTS_NATIVE_TOOLS = any(x in MODEL_NAME.lower() for x in SUPPORTED_TOOL_MODELS)

# Directory paths
WORKSPACE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../workspace")
)
LOGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tests/logs"))
