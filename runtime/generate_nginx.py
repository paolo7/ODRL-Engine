from jinja2 import Template
from runtime.discover_apps import discover_apps

NGINX_TEMPLATE = """
events {}

http {

    server {
        listen 80;

        # ---------------- API ----------------
        location /ODRL-Engine/api/ {
            rewrite ^/ODRL-Engine/api/(.*)$ /$1 break;
            proxy_pass http://127.0.0.1:8000;
        }

        location /api/ {
            rewrite ^/api/(.*)$ /$1 break;
            proxy_pass http://127.0.0.1:8000;
        }

        # ---------------- APPS ----------------
        {% for app in apps %}

        location /ODRL-Engine/apps/{{ app.route }}/ {
            rewrite ^/ODRL-Engine/apps/{{ app.route }}/(.*)$ /$1 break;

            proxy_pass http://127.0.0.1:{{ app.port }};

            proxy_http_version 1.1;
    	    proxy_set_header Host $host;
    	    proxy_set_header X-Forwarded-Proto $scheme;
    	    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location /apps/{{ app.route }}/ {
            proxy_pass http://127.0.0.1:{{ app.port }};

            proxy_http_version 1.1;
    	    proxy_set_header Host $host;
    	    proxy_set_header X-Forwarded-Proto $scheme;
   	    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        {% endfor %}

        location / {
            return 200 "ODRL Engine running";
        }
    }
}
"""

def generate_nginx(apps):
    return Template(NGINX_TEMPLATE).render(apps=apps)