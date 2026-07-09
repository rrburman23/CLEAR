import os


def run_ping(ip: str):
    # BUG: Vulnerable to shell injection (e.g., "127.0.0.1; rm -rf /")
    return os.system("ping -c 1 " + ip)
