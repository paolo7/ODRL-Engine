from jinja2 import Template
import os

BASE_PATH = os.environ.get("ODRL_BASE_PATH", "").strip("/")
PREFIX = f"/{BASE_PATH}" if BASE_PATH else ""

NGINX_TEMPLATE = r"""
events {}

http {

    server {
        listen 80;

        # ---------------- API ----------------

        location {{ prefix }}/api/ {
            proxy_pass http://127.0.0.1:8000/;
        }

        # ---------------- APPS ----------------

        {% for app in apps %}

        location {{ prefix }}/{{ app.route }}/ {

            proxy_pass http://127.0.0.1:{{ app.port }};

            proxy_http_version 1.1;

            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        {% endfor %}

        location / {
            return 200 "ODRL Engine running";
        }
    }
}
"""

def generate_nginx(apps):

    base_path = os.environ.get("ODRL_BASE_PATH", "").strip("/")

    prefix = f"/{base_path}" if base_path else ""

    return Template(NGINX_TEMPLATE).render(
        apps=apps,
        prefix=prefix,
    )