"""
CLEAR Docker Sandbox Manager

Responsible for:
- Executing LLM-generated repair candidates safely.
- Running the human-authored pytest oracle inside an isolated container.
- Preventing host execution of machine-generated code.
- Returning structured execution results (with full output) to the agent.
"""

import tempfile
from pathlib import Path
from dataclasses import dataclass

import docker
from docker import errors


# ---------------------------------------------------------------------
# Execution Result Object
# ---------------------------------------------------------------------


@dataclass
class SandboxResult:
    """
    Structured result returned after sandbox execution.

    Attributes:
        success: True only if the pytest oracle exits 0 (all tests pass).
        output:  Combined stdout + stderr from the container (always populated).
        error:   Convenience copy of output when success is False.
    """

    success: bool
    output: str = ""
    error: str = ""


# ---------------------------------------------------------------------
# Sandbox Manager
# ---------------------------------------------------------------------


class SandboxManager:
    """
    Manages ephemeral Docker containers for secure code execution.

    Security properties:
    - Generated code never executes on the host.
    - Containers are deleted after execution.
    - Network access is disabled.
    - Memory usage is restricted.
    - A hard timeout prevents unbounded hangs.
    """

    def __init__(self, timeout_seconds: int = 60):
        self.client = docker.from_env()
        self.image_name = "clear-executor:latest"
        self.timeout_seconds = timeout_seconds

    # -----------------------------------------------------------------
    # Main execution entry point
    # -----------------------------------------------------------------

    def execute(self, code: str, test_suite: str) -> SandboxResult:
        """
        Execute a candidate repair against its pytest oracle.

        Workspace layout inside the container (/app):

            target.py         repaired implementation
            test_target.py    the human-authored pytest oracle

        The oracle imports `from target import ...`, so target.py must sit
        alongside it on the import path (working_dir=/app handles this).
        """

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            target_file = temp_path / "target.py"
            # Name it test_*.py so pytest auto-discovers it.
            test_file = temp_path / "test_target.py"

            target_file.write_text(code, encoding="utf-8")
            test_file.write_text(test_suite, encoding="utf-8")

            container = None
            try:
                # Run DETACHED so we can capture the exit code AND the full
                # logs (stdout+stderr) regardless of pass/fail. `-p no:cacheprovider`
                # keeps the read-only mount from tripping over .pytest_cache.
                container = self.client.containers.run(
                    image=self.image_name,
                    command=(
                        "python -m pytest test_target.py "
                        "-q --no-header -p no:cacheprovider"
                    ),
                    volumes={
                        str(temp_path.resolve()): {
                            "bind": "/app",
                            "mode": "ro",
                        }
                    },
                    working_dir="/app",
                    network_disabled=True,
                    mem_limit="256m",
                    detach=True,
                    stdout=True,
                    stderr=True,
                )

                try:
                    exit_status = container.wait(timeout=self.timeout_seconds)
                except Exception:
                    # Timed out or the daemon connection dropped: treat as failure.
                    try:
                        container.kill()
                    except Exception:
                        pass
                    logs = self._safe_logs(container)
                    return SandboxResult(
                        success=False,
                        output=logs,
                        error=(logs or "Execution timed out")
                        + f"\n[CLEAR] Killed after {self.timeout_seconds}s timeout.",
                    )

                exit_code = exit_status.get("StatusCode", 1)
                logs = self._safe_logs(container)

                if exit_code == 0:
                    return SandboxResult(success=True, output=logs)

                return SandboxResult(success=False, output=logs, error=logs)

            except errors.ContainerError as e:
                # Fallback path (shouldn't normally trigger in detached mode).
                detail = ""
                if e.stderr:
                    detail = (
                        e.stderr.decode("utf-8")
                        if isinstance(e.stderr, bytes)
                        else str(e.stderr)
                    )
                return SandboxResult(success=False, output=detail, error=detail)

            except errors.ImageNotFound:
                msg = (
                    f"Docker image '{self.image_name}' not found. "
                    "Build it first (see Dockerfile)."
                )
                return SandboxResult(success=False, output=msg, error=msg)

            except Exception as e:
                return SandboxResult(success=False, output=str(e), error=str(e))

            finally:
                if container is not None:
                    try:
                        container.remove(force=True)
                    except Exception:
                        pass

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    @staticmethod
    def _safe_logs(container) -> str:
        """Pull combined stdout+stderr from a container, tolerant of errors."""
        try:
            raw = container.logs(stdout=True, stderr=True)
            return (
                raw.decode("utf-8", errors="replace")
                if isinstance(raw, bytes)
                else str(raw)
            )
        except Exception as exc:
            return f"[CLEAR] Could not retrieve container logs: {exc}"
