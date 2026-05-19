import docker
from docker import errors
import os
from pathlib import Path


class SandboxManager:
    def __init__(self):
        self.client = docker.from_env()
        self.image_name = "clear-executor:latest"

    def run_code(self, code: str, timeout: int = 5):
        """
        Spins up an ephemeral container, executes the code,
        and returns stdout/stderr.
        """
        with open("temp_script.py", "w", encoding="utf-8") as f:
            f.write(code)

        try:
            local_script_path = str(Path("temp_script.py").resolve().as_posix())

            # Removed 'timeout' keyword parameter to comply with Docker SDK constraints
            container_output = self.client.containers.run(
                image=self.image_name,
                command="python /app/temp_script.py",
                volumes={
                    local_script_path: {"bind": "/app/temp_script.py", "mode": "ro"}
                },
                working_dir="/app",
                detach=False,
                stdout=True,
                stderr=True,
                remove=True,
                network_disabled=True,
                mem_limit="128m",
            )

            if isinstance(container_output, bytes):
                output_str = container_output.decode("utf-8")
            else:
                output_str = str(container_output or "")

            return {"status": "success", "output": output_str}

        except errors.ContainerError as e:
            if isinstance(e.stderr, bytes):
                error_str = e.stderr.decode("utf-8")
            else:
                error_str = str(e.stderr or "")

            return {"status": "failed", "error": error_str}

        except Exception as e:
            return {"status": "error", "message": str(e)}

        finally:
            if os.path.exists("temp_script.py"):
                os.remove("temp_script.py")

    def run_workspace_tests(self, workspace_path: str) -> dict:
        """
        Mounts the target workspace into the container and executes pytest.

        Args:
            workspace_path (str): Absolute path to the local directory containing code and tests.

        Returns:
            dict: Execution status and formatted stdout/stderr payload.
        """
        try:
            local_dir = str(Path(workspace_path).resolve().as_posix())

            # Removed 'timeout' parameter to address the Docker-py signature mismatch
            container_output = self.client.containers.run(
                image=self.image_name,
                command="pytest /workspace -p no:cacheprovider -v",
                volumes={local_dir: {"bind": "/workspace", "mode": "ro"}},
                working_dir="/workspace",
                detach=False,
                stdout=True,
                stderr=True,
                remove=True,
                network_disabled=True,
                mem_limit="256m",
            )

            output_str = (
                container_output.decode("utf-8")
                if isinstance(container_output, bytes)
                else str(container_output or "")
            )
            return {"status": "success", "output": output_str}

        except errors.ContainerError as e:
            error_str = (
                e.stderr.decode("utf-8")
                if isinstance(e.stderr, bytes)
                else str(e.stderr or "")
            )
            return {"status": "failed", "error": error_str}

        except Exception as e:
            return {
                "status": "error",
                "message": f"Sandbox configuration fault: {str(e)}",
            }
