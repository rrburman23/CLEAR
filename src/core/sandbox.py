"""
CLEAR Docker Sandbox Manager

Responsible for:
- Executing LLM-generated repair candidates safely.
- Running the human-authored pytest oracle inside an isolated container.
- Preventing host execution of machine-generated code.
- Returning structured execution results with complete sandbox diagnostics.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import docker
from docker import errors
from docker.models.containers import Container


# =========================================================
# Sandbox Result Types
# =========================================================


SandboxStatus = Literal[
    "SUCCESS",
    "FAILURE",
    "INFRASTRUCTURE_ERROR",
]

PYTEST_SUCCESS = 0
PYTEST_NO_TESTS_COLLECTED = 5


@dataclass(slots=True)
class SandboxResult:
    """
    Structured result returned after sandbox execution.

    Attributes
    ----------
    status:
        ``SUCCESS`` when every collected test passes.

        ``FAILURE`` when pytest successfully evaluates the candidate but the
        candidate fails, raises an exception, contains invalid syntax, or
        exceeds the execution timeout.

        ``INFRASTRUCTURE_ERROR`` when the benchmark cannot be evaluated due
        to invalid test infrastructure or a Docker failure.

    output:
        Combined standard output and standard error captured from the
        container.

    error:
        Failure or infrastructure diagnostics.

    message:
        Concise human-readable description of the result.

    exit_code:
        Pytest or container process exit code when available.
    """

    status: SandboxStatus
    output: str = ""
    error: str = ""
    message: str = ""
    exit_code: int | None = None

    @property
    def success(self) -> bool:
        """
        Maintain compatibility with code that previously inspected a boolean
        ``success`` field.
        """

        return self.status == "SUCCESS"


# =========================================================
# Sandbox Manager
# =========================================================


class SandboxManager:
    """
    Manage ephemeral Docker containers for secure candidate execution.

    Security properties
    -------------------
    - Generated source is never executed directly on the host.
    - Every candidate is evaluated inside an ephemeral container.
    - Container network access is disabled.
    - Container memory is restricted.
    - The mounted benchmark workspace is read-only.
    - A hard timeout prevents unbounded execution.
    - Containers are removed after every execution.
    """

    def __init__(
        self,
        timeout_seconds: int = 60,
    ) -> None:
        self.client = docker.from_env()
        self.image_name = "clear-executor:latest"
        self.timeout_seconds = timeout_seconds

    # =====================================================
    # Main Execution Entry Point
    # =====================================================

    def execute(
        self,
        code: str,
        test_suite: str,
    ) -> SandboxResult:
        """
        Execute a candidate implementation against its pytest oracle.

        The temporary workspace is mounted inside the container as:

        ``/app/target.py``
            Candidate repaired implementation.

        ``/app/test_target.py``
            Human-authored pytest oracle.

        The benchmark test imports from ``target``, so both files must remain
        in the same working directory.
        """

        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_path = Path(temporary_directory)

            target_file = temporary_path / "target.py"
            test_file = temporary_path / "test_target.py"

            target_file.write_text(
                code,
                encoding="utf-8",
            )

            test_file.write_text(
                test_suite,
                encoding="utf-8",
            )

            container = None

            try:
                container = self.client.containers.run(
                    image=self.image_name,
                    command=[
                        "python",
                        "-m",
                        "pytest",
                        "test_target.py",
                        "-q",
                        "--no-header",
                        "-p",
                        "no:cacheprovider",
                    ],
                    volumes={
                        str(temporary_path.resolve()): {
                            "bind": "/app",
                            "mode": "ro",
                        }
                    },
                    working_dir="/app",
                    network_disabled=True,
                    mem_limit="256m",
                    environment={
                        # Prevent Python from attempting to create __pycache__
                        # inside the read-only benchmark mount.
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                    detach=True,
                    stdout=True,
                    stderr=True,
                )

                try:
                    exit_status = container.wait(
                        timeout=self.timeout_seconds,
                    )
                except Exception:
                    # A candidate timeout is considered a normal repair
                    # failure because generated code may hang or loop
                    # indefinitely.
                    try:
                        container.kill()
                    except Exception:
                        pass

                    logs = self._safe_logs(container)

                    timeout_message = (
                        f"[CLEAR] Candidate execution was killed after "
                        f"{self.timeout_seconds} seconds."
                    )

                    error_output = (
                        f"{logs}\n{timeout_message}".strip()
                        if logs
                        else timeout_message
                    )

                    return SandboxResult(
                        status="FAILURE",
                        output=logs,
                        error=error_output,
                        message="Sandbox execution timed out.",
                        exit_code=None,
                    )

                raw_exit_code = exit_status.get(
                    "StatusCode",
                    1,
                )

                try:
                    exit_code = int(raw_exit_code)
                except (TypeError, ValueError):
                    exit_code = 1

                logs = self._safe_logs(container)

                if exit_code == PYTEST_SUCCESS:
                    return SandboxResult(
                        status="SUCCESS",
                        output=logs,
                        error="",
                        message="All supplied tests passed.",
                        exit_code=exit_code,
                    )

                if exit_code == PYTEST_NO_TESTS_COLLECTED:
                    infrastructure_message = (
                        "Pytest collected no tests. The benchmark test-suite "
                        "path or copied test file is invalid."
                    )

                    infrastructure_error = f"{infrastructure_message}\n\n{logs}".strip()

                    return SandboxResult(
                        status="INFRASTRUCTURE_ERROR",
                        output=logs,
                        error=infrastructure_error,
                        message=infrastructure_message,
                        exit_code=exit_code,
                    )

                # Other pytest exit codes are candidate failures. This
                # includes assertion failures, candidate import errors and
                # candidate syntax errors. Intentional syntax benchmarks must
                # therefore remain eligible for model repair.
                return SandboxResult(
                    status="FAILURE",
                    output=logs,
                    error=logs,
                    message=("The candidate did not pass the supplied tests."),
                    exit_code=exit_code,
                )

            except errors.ImageNotFound:
                message = (
                    f"Docker image '{self.image_name}' was not found. "
                    "Build the CLEAR executor image before running repairs."
                )

                return SandboxResult(
                    status="INFRASTRUCTURE_ERROR",
                    output=message,
                    error=message,
                    message="CLEAR sandbox image was not found.",
                    exit_code=None,
                )

            except errors.ContainerError as exc:
                detail = self._container_error_detail(exc)

                return SandboxResult(
                    status="INFRASTRUCTURE_ERROR",
                    output=detail,
                    error=detail,
                    message="Docker container execution failed.",
                    exit_code=getattr(
                        exc,
                        "exit_status",
                        None,
                    ),
                )

            except errors.DockerException as exc:
                diagnostic = f"{type(exc).__name__}: {exc}"

                return SandboxResult(
                    status="INFRASTRUCTURE_ERROR",
                    output=diagnostic,
                    error=diagnostic,
                    message="Docker sandbox infrastructure failure.",
                    exit_code=None,
                )

            except Exception as exc:
                diagnostic = f"{type(exc).__name__}: {exc}"

                return SandboxResult(
                    status="INFRASTRUCTURE_ERROR",
                    output=diagnostic,
                    error=diagnostic,
                    message="Unexpected sandbox infrastructure failure.",
                    exit_code=None,
                )

            finally:
                if container is not None:
                    try:
                        container.remove(
                            force=True,
                        )
                    except Exception:
                        # Cleanup failures should not replace the actual
                        # benchmark result.
                        pass

    # =====================================================
    # Helpers
    # =====================================================

    @staticmethod
    def _safe_logs(
        container: Container,
    ) -> str:
        """
        Retrieve combined container stdout and stderr without raising.
        """

        try:
            raw_logs = container.logs(
                stdout=True,
                stderr=True,
            )

            if isinstance(raw_logs, bytes):
                return raw_logs.decode(
                    "utf-8",
                    errors="replace",
                )

            return str(raw_logs)

        except Exception as exc:
            return (
                "[CLEAR] Could not retrieve container logs: "
                f"{type(exc).__name__}: {exc}"
            )

    @staticmethod
    def _container_error_detail(
        exception: errors.ContainerError,
    ) -> str:
        """
        Extract a readable diagnostic from a Docker ContainerError.
        """

        stderr = getattr(
            exception,
            "stderr",
            None,
        )

        if isinstance(stderr, bytes):
            detail = stderr.decode(
                "utf-8",
                errors="replace",
            )
        elif stderr:
            detail = str(stderr)
        else:
            detail = str(exception)

        return detail.strip()
