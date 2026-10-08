#!/usr/bin/env bash
set -euo pipefail
# Run only on the Oracle Linux/Ubuntu VM, from this repository's deployment folder.
[[ "$(uname -s)" == Linux ]] || { echo 'Deploy on the Oracle VM only.'; exit 1; }
cd "$(dirname "$0")/.."
[[ -f .env ]] || { echo 'Create a private production .env on the VM first.'; exit 1; }
[[ -f /etc/letsencrypt/live/gnkalgo.com/fullchain.pem ]] || { echo 'Provision the gnkalgo.com TLS certificate first; see docs/ORACLE_PRODUCTION.md.'; exit 1; }
[[ -f /etc/letsencrypt/live/gnkalgo.com/privkey.pem ]] || { echo 'TLS private key missing.'; exit 1; }
[[ "$(git remote get-url origin)" == 'https://github.com/Boop-12/GNK_AI.git' ]] || { echo 'Unexpected Git remote.'; exit 1; }
[[ -z "$(git status --porcelain --untracked-files=no)" ]] || { echo 'Tracked deployment files have local changes; review them before deploying.'; exit 1; }
compose=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
"${compose[@]}" config --quiet
mkdir -p backups
chmod 700 backups
# Preserve the existing database before any migrations. Never delete volumes.
if "${compose[@]}" ps --status running --services | grep -qx postgres; then
  backup="backups/pre-deploy-$(date -u +%Y%m%dT%H%M%SZ).sql"
  "${compose[@]}" exec -T postgres pg_dump -U app gnkalgo > "$backup"
  chmod 600 "$backup"
  [[ -s "$backup" ]] || { echo 'Backup failed; deployment stopped.'; exit 1; }
fi
"${compose[@]}" build api web
"${compose[@]}" up -d --wait postgres redis
"${compose[@]}" run --rm --no-deps api alembic upgrade head
"${compose[@]}" up -d --wait api web nginx
# Require both database schema and Redis readiness before calling the release healthy.
"${compose[@]}" exec -T api python -c "from urllib.request import urlopen; assert urlopen('http://127.0.0.1:8000/readyz', timeout=10).status == 200"
curl --fail --silent --show-error --retry 5 --retry-delay 3 https://www.gnkalgo.com/ > /dev/null
"${compose[@]}" ps
printf 'Deployed commit: %s\n' "$(git rev-parse HEAD)"
