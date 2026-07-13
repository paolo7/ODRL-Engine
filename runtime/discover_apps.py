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

    if apps:
        print(f"[discover_apps] Found {len(apps)} app(s):", flush=True)
        for app in apps:
            print(f"  - {app['name']} ({app['file']}) -> port {app['port']}", flush=True)
    else:
        print(f"[discover_apps] No apps found in {APPS_DIR}", flush=True)

    return apps