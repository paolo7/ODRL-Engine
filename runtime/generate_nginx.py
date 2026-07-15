from jinja2 import Template
import os

NGINX_TEMPLATE = r"""
events {}

http {

    {% if rate_limit_rps %}
    limit_req_zone $http_x_forwarded_for zone=api_limit:10m rate={{ rate_limit_rps }}r/s;
    {% endif %}

    server {
        listen 80;

        # ---------------- API ----------------

        location {{ prefix }}/api/ {

            {% if max_body_size_mb %}
            client_max_body_size {{ max_body_size_mb }}m;
            {% endif %}

            {% if eval_timeout_s %}
            proxy_read_timeout {{ eval_timeout_s }}s;
            {% endif %}

            {% if rate_limit_rps %}
            limit_req zone=api_limit burst={{ rate_limit_burst }} nodelay;
            limit_req_status 429;
            {% endif %}

            proxy_pass http://127.0.0.1:8000/;

            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;

            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            {% if prefix %}
            proxy_set_header X-Forwarded-Prefix {{ prefix }};
            {% endif %}
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

    max_body_size_mb = os.environ.get("ODRL_MAX_BODY_SIZE_MB", "").strip()
    eval_timeout_s = os.environ.get("ODRL_EVAL_TIMEOUT_SECONDS", "").strip()
    rate_limit_rps = os.environ.get("ODRL_RATE_LIMIT_RPS", "").strip()

    # burst allows short bursts above the sustained rate; default to 2x the rate
    rate_limit_burst = os.environ.get(
        "ODRL_RATE_LIMIT_BURST",
        str(int(rate_limit_rps) * 2) if rate_limit_rps.isdigit() else ""
    )

    return Template(NGINX_TEMPLATE).render(
        apps=apps,
        prefix=prefix,
        max_body_size_mb=max_body_size_mb,
        eval_timeout_s=eval_timeout_s,
        rate_limit_rps=rate_limit_rps,
        rate_limit_burst=rate_limit_burst,
    )