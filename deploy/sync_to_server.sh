#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 USER@SERVER /absolute/path/to/MLE4217_5219_book"
  echo "Example: $0 ubuntu@course.example.edu.sg /Users/me/work/MLE4217_5219_book"
  exit 2
fi

REMOTE="$1"
BOOK_REPO="$2"
BACKEND_REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -d "$BOOK_REPO" ]]; then
  echo "Book repo not found: $BOOK_REPO"
  exit 1
fi

echo "Building book..."
(cd "$BOOK_REPO" && make web)

echo "Syncing backend to $REMOTE:/srv/mle-course-helper/backend/"
rsync -az --delete \
  --exclude .git \
  --exclude .env \
  --exclude __pycache__ \
  --exclude '*.pyc' \
  "$BACKEND_REPO/" "$REMOTE:/srv/mle-course-helper/backend/"

echo "Syncing book HTML to $REMOTE:/srv/mle-course-helper/book/"
rsync -az --delete \
  "$BOOK_REPO/_build/html/" "$REMOTE:/srv/mle-course-helper/book/"

echo "Done. On the server, run:"
echo "  cd /srv/mle-course-helper/backend && bash deploy/install_backend.sh"
echo "  sudo systemctl restart mle-course-helper"
