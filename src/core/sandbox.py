"""
CLEAR Docker Sandbox Manager

Responsible for:
- Executing LLM-generated repair candidates safely.
- Running generated tests inside an isolated Docker container.
- Preventing host execution of machine-generated code.
- Returning structured execution results to the agent.

Architecture:

LLM
 |
 v
run_repair_attempt()
 |
 v
SandboxManager.execute()
 |
 v
Docker container
 |
 v
SUCCESS / FAILURE
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
        success:
            True if the repair passes all tests.

        output:
            stdout produced by the container.

        error:
            stderr or execution failure information.
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
    - Files are mounted read-only.
    """

    def __init__(self):
        """
        Connect to Docker daemon and configure execution image.
        """

        self.client = docker.from_env()

        # Docker image containing Python execution environment
        self.image_name = "clear-executor:latest"

    # -----------------------------------------------------------------
    # Main execution entry point
    # -----------------------------------------------------------------

    def execute(
        self,
        code: str,
        test_suite: str,
    ) -> SandboxResult:
        """
        Execute a candidate repair against its test suite.

        Creates an isolated temporary directory:

            /tmp/random_id/
                target.py
                temp_script.py

        target.py:
            Contains the repaired implementation.

        temp_script.py:
            Contains tests supplied by CLEAR.

        The container executes:

            python /app/temp_script.py

        The test script imports:

            from target import function

        and verifies correctness.
        """

        # -------------------------------------------------------------
        # Create temporary workspace
        # -------------------------------------------------------------

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            target_file = temp_path / "target.py"
            test_file = temp_path / "temp_script.py"

            # Write repaired code
            target_file.write_text(code, encoding="utf-8")

            # Write validation tests
            test_file.write_text(test_suite, encoding="utf-8")

            try:
                # -----------------------------------------------------
                # Execute inside Docker
                # -----------------------------------------------------

                container_output = self.client.containers.run(
                    image=self.image_name,
                    # Run test suite inside container
                    command="python /app/temp_script.py",
                    # Mount temporary files
                    volumes={
                        str(temp_path.resolve()): {
                            "bind": "/app",
                            "mode": "ro",
                        }
                    },
                    working_dir="/app",
                    # Security restrictions
                    network_disabled=True,
                    mem_limit="128m",
                    # Automatically delete container
                    remove=True,
                    # Capture output
                    stdout=True,
                    stderr=True,
                )

                # Docker returns bytes normally
                output_text = (
                    container_output.decode("utf-8")
                    if isinstance(container_output, bytes)
                    else str(container_output)
                )

                return SandboxResult(
                    success=True,
                    output=output_text,
                )

            # ---------------------------------------------------------
            # Python/test failure inside container
            # ---------------------------------------------------------

            except errors.ContainerError as e:
                error_text = (
                    e.stderr.decode("utf-8")
                    if isinstance(e.stderr, bytes)
                    else str(e.stderr or "")
                )

                return SandboxResult(
                    success=False,
                    error=error_text,
                )

            # ---------------------------------------------------------
            # Docker configuration failure
            # ---------------------------------------------------------

            except Exception as e:
                return SandboxResult(
                    success=False,
                    error=str(e),
                )
