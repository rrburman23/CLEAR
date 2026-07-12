import subprocess


def run_ping(ip: str) -> int:
    """
    Ping an IP address and return the process exit code.
    """

    command = f"ping -c 1 {ip}"

    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode
