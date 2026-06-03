import subprocess

def start_streamlit(app):
    return subprocess.Popen([
        "streamlit", "run", app["file"],
        "--server.port", str(app["port"]),
        "--server.address", "127.0.0.1",
        "--server.baseUrlPath", f"apps/{app['route']}"
    ])