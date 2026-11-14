# Static site for earthpod.earth: the arcade at / and the GISTEMP player at /player/.
# Built and deployed by Kamal (config/deploy.yml) from GitHub Actions (.github/workflows/ci.yml).
FROM nginx:1.27-alpine

COPY infra/nginx.conf /etc/nginx/conf.d/default.conf
COPY frontend/arcade/ /usr/share/nginx/html/
COPY frontend/player/ /usr/share/nginx/html/player/

EXPOSE 80
