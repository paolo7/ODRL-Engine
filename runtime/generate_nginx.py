from jinja2 import Template
import os

NGINX_TEMPLATE = r"""
events {}

http {

    {% if rate_limit_rps %}
    limit_req_zone $http_x_forwarded_for zone=api_limit:10m rate={{ rate_limit_rps }}r/s;
    {% endif %}

    {% if streamlit_conn_limit %}
    limit_conn_zone $http_x_forwarded_for zone=streamlit_conn:10m;
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

            {% if streamlit_max_body_size_mb %}
            client_max_body_size {{ streamlit_max_body_size_mb }}m;
            {% endif %}

            {% if streamlit_ws_timeout_s %}
            proxy_read_timeout {{ streamlit_ws_timeout_s }}s;
            proxy_send_timeout {{ streamlit_ws_timeout_s }}s;
            {% endif %}

            {% if streamlit_conn_limit %}
            limit_conn streamlit_conn {{ streamlit_conn_limit }};
            limit_conn_status 429;
            {% endif %}

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

    # ---- API limits ----
    max_body_size_mb = os.environ.get("ODRL_MAX_BODY_SIZE_MB", "").strip()
    eval_timeout_s = os.environ.get("ODRL_EVAL_TIMEOUT_SECONDS", "").strip()
    rate_limit_rps = os.environ.get("ODRL_RATE_LIMIT_RPS", "").strip()
    rate_limit_burst = os.environ.get(
        "ODRL_RATE_LIMIT_BURST",
        str(int(rate_limit_rps) * 2) if rate_limit_rps.isdigit() else ""
    )

    # ---- Streamlit limits ----
    streamlit_max_body_size_mb = os.environ.get("ODRL_STREAMLIT_MAX_BODY_SIZE_MB", "").strip()
    streamlit_ws_timeout_s = os.environ.get("ODRL_STREAMLIT_WS_TIMEOUT_SECONDS", "").strip()
    streamlit_conn_limit = os.environ.get("ODRL_STREAMLIT_MAX_CONN_PER_IP", "").strip()

    return Template(NGINX_TEMPLATE).render(
        apps=apps,
        prefix=prefix,
        max_body_size_mb=max_body_size_mb,
        eval_timeout_s=eval_timeout_s,
        rate_limit_rps=rate_limit_rps,
        rate_limit_burst=rate_limit_burst,
        streamlit_max_body_size_mb=streamlit_max_body_size_mb,
        streamlit_ws_timeout_s=streamlit_ws_timeout_s,
        streamlit_conn_limit=streamlit_conn_limit,
    )