import os
import subprocess

BASE_PATH = os.environ.get("ODRL_BASE_PATH", "").strip("/")


def start_streamlit(app):

    parts = []

    if BASE_PATH:
        parts.append(BASE_PATH)

    parts.append(app["route"])

    base_url = "/".join(parts)

    return subprocess.Popen([
        "streamlit",
        "run",
        app["file"],
        "--server.port", str(app["port"]),
        "--server.address", "127.0.0.1",
        "--client.toolbarMode", "minimal",
        "--server.baseUrlPath", base_url,
        "--server.headless", "true",
    ])