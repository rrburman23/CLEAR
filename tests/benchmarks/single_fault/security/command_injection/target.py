import os


def run_ping(ip: str):
    return os.system("ping -c 1 " + ip)
