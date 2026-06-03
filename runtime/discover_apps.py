import os
from pathlib import Path

APPS_DIR = Path("/app/apps")

def discover_apps(start_port=8501):
    apps = []
    port = start_port

    for file in sorted(APPS_DIR.glob("*.py")):
        if file.name.startswith("_"):
            continue

        name = file.stem  # evaluator_demo
        route = name.replace("_", "-")

        apps.append({
            "name": name,
            "route": route,
            "file": str(file),
            "port": port
        })

        port += 1

    return apps