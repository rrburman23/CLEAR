import ipaddress
import subprocess


def run_ping(ip: str) -> int:
    """
    Safely ping a validated IP address.
    """

    validated_ip = str(ipaddress.ip_address(ip))

    result = subprocess.run(
        [
            "ping",
            "-c",
            "1",
            validated_ip,
        ],
        shell=False,
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode
