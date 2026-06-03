import subprocess
import time

from runtime.discover_apps import discover_apps
from runtime.generate_nginx import generate_nginx
from runtime.start_streamlit import start_streamlit


def write_nginx(conf: str):
    with open("/etc/nginx/nginx.conf", "w") as f:
        f.write(conf)


def main():

    apps = discover_apps()

    print(f"Discovered apps: {[a['route'] for a in apps]}")

    # 1. generate nginx
    nginx_conf = generate_nginx(apps)
    write_nginx(nginx_conf)

    # 2. start FastAPI
    subprocess.Popen([
        "uvicorn", "api.main:app",
        "--host", "127.0.0.1",
        "--port", "8000"
    ])

    # 3. start streamlit apps
    processes = []
    for app in apps:
        p = start_streamlit(app)
        processes.append(p)

    # 4. start nginx
    nginx = subprocess.Popen(["nginx", "-g", "daemon off;"])

    # 5. keep alive
    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()