# Server Deployment

This deploys the course book and the RAG API on one Linux server:

```text
https://YOUR_DOMAIN/            -> static book site
https://YOUR_DOMAIN/api/answer  -> Flask/Gunicorn RAG API
```

The book widget keeps local testing on `http://127.0.0.1:5055`, but on a real
domain it automatically calls the same origin, so Nginx can route `/api/*` to the
backend.

## 1. Server Packages

Ubuntu example:

```bash
sudo apt update
sudo apt install -y git rsync nginx python3 python3-venv python3-pip
```

Create directories:

```bash
sudo useradd --system --home /srv/mle-course-helper --shell /usr/sbin/nologin mlehelper || true
sudo mkdir -p /srv/mle-course-helper/backend /srv/mle-course-helper/book
sudo chown -R "$USER":"$USER" /srv/mle-course-helper
```

## 2. Upload Repositories

On your laptop, upload the backend repo:

```bash
rsync -az --delete \
  --exclude .git --exclude .env --exclude __pycache__ \
  /path/to/mle4217_5219_AIdesk/ \
  USER@SERVER:/srv/mle-course-helper/backend/
```

Build the book locally or on the server:

```bash
cd /path/to/MLE4217_5219_book
make web
```

Then upload the generated static site:

```bash
rsync -az --delete \
  /path/to/MLE4217_5219_book/_build/html/ \
  USER@SERVER:/srv/mle-course-helper/book/
```

## 3. Install Backend Python Environment

On the server:

```bash
cd /srv/mle-course-helper/backend
bash deploy/install_backend.sh
mkdir -p /srv/mle-course-helper/backend/.cache/huggingface
sudo chown -R mlehelper:mlehelper /srv/mle-course-helper/backend/.cache
```

The first run may take a while because `sentence-transformers` installs model
dependencies.

## 4. Configure Secrets

On the server:

```bash
sudo cp /srv/mle-course-helper/backend/deploy/env.example /etc/mle-course-helper.env
sudo nano /etc/mle-course-helper.env
sudo chmod 600 /etc/mle-course-helper.env
```

Fill in one provider. For example, for the Anthropic-compatible relay:

```bash
ANTHROPIC_BASE_URL=https://your-relay.example.com
ANTHROPIC_AUTH_TOKEN=replace-me
ANTHROPIC_MODEL=claude-sonnet-4-6
```

If you leave all keys unset, the API runs in `dry_run` mode.

## 5. Install systemd Service

```bash
sudo cp /srv/mle-course-helper/backend/deploy/mle-course-helper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mle-course-helper
sudo systemctl status mle-course-helper --no-pager
```

Check the local API:

```bash
curl http://127.0.0.1:5055/api/health
curl -X POST http://127.0.0.1:5055/api/answer \
  -H 'Content-Type: application/json' \
  -d '{"query":"What is MACE?"}'
```

Logs:

```bash
sudo journalctl -u mle-course-helper -f
```

## 6. Install Nginx Site

Edit the domain in the config:

```bash
sudo cp /srv/mle-course-helper/backend/deploy/nginx-mle-course-helper.conf /etc/nginx/sites-available/mle-course-helper
sudo nano /etc/nginx/sites-available/mle-course-helper
sudo ln -sf /etc/nginx/sites-available/mle-course-helper /etc/nginx/sites-enabled/mle-course-helper
sudo nginx -t
sudo systemctl reload nginx
```

Open:

```text
http://YOUR_DOMAIN/
```

Then test the widget in the bottom-right corner.

## 7. HTTPS

If the server is public and the domain DNS points to it, use Certbot:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d YOUR_DOMAIN
```

## 8. Updating Later

Backend update:

```bash
rsync -az --delete --exclude .git --exclude .env --exclude __pycache__ \
  /path/to/mle4217_5219_AIdesk/ USER@SERVER:/srv/mle-course-helper/backend/
ssh USER@SERVER 'cd /srv/mle-course-helper/backend && bash deploy/install_backend.sh && sudo systemctl restart mle-course-helper'
```

Book update:

```bash
cd /path/to/MLE4217_5219_book
make web
rsync -az --delete _build/html/ USER@SERVER:/srv/mle-course-helper/book/
```

## Important

Do not upload local `.env` files or API keys to git. If a key was ever committed
or copied into a shell script, rotate it before deployment.
