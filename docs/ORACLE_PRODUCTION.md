# Oracle production deployment — www.gnkalgo.com

Only execute these commands on the Oracle VM. No local startup is required.
This is a new repository. Do not overwrite an existing deployment or create a
second stack binding ports 80/443 on an already occupied VM. Inspect any current
site before choosing a migration/cutover; preserve its .env, project name, volumes,
and certificates. No VM connection or deployment has been verified by this source release.

## 1. Prepare the host

Use an Ubuntu/Oracle Linux VM with Docker Engine, Compose v2, Git, curl, OpenSSL,
and Certbot installed by the operator. Point gnkalgo.com and www.gnkalgo.com to
its public IP. Allow TCP 80/443 in Oracle NSG/security lists and the host firewall;
restrict SSH to trusted sources. Do not expose PostgreSQL, Redis, API, or Next.js ports.

The example path below is a proposed new deployment, not a verified existing path.
The SSH identity must be able to use Docker. Docker-group access is effectively root.

```bash
sudo mkdir -p /opt/gnkalgo-ai
sudo chown "$USER:$USER" /opt/gnkalgo-ai
git clone https://github.com/Boop-12/GNK_AI.git /opt/gnkalgo-ai
cd /opt/gnkalgo-ai
cp .env.example .env
chmod 600 .env
openssl rand -hex 32
openssl rand -hex 32
```

Paste the two independent generated values into JWT_SECRET_KEY and POSTGRES_PASSWORD
in the VM's .env using the operator's editor. Use hex for the database password to
avoid URL-encoding ambiguity. Compose injects DATABASE_URL from POSTGRES_PASSWORD;
the placeholder DATABASE_URL in .env.example is not used by the API container.
Keep APP_ENV=production, COOKIE_SECURE=true, HTTPS frontend origin, and
BROKER_TRADING_ENABLED=false. Configure SMTP so recovery mail can be delivered.
AI is optional: set AI_ENABLED=true, a server-side OPENAI_API_KEY, and an explicitly
chosen OPENAI_MODEL that your provider account can use. Set provider spending caps.
Never paste these secret values into chat or commit .env.

## 2. Provision first TLS certificate

Skip issuance if a valid certificate covering both names already exists at the
expected path. These bootstrap commands assume ports 80/443 are free for this stack.

```bash
cd /opt/gnkalgo-ai
mkdir -p certbot/www
docker compose -f docker-compose.yml -f docker-compose.acme.yml up -d --no-deps nginx
sudo certbot certonly --webroot --webroot-path /opt/gnkalgo-ai/certbot/www \
  --email YOUR_OPERATOR_EMAIL --agree-tos --no-eff-email \
  -d gnkalgo.com -d www.gnkalgo.com
```

The ACME-only Nginx intentionally serves no public app. For an existing site,
use its verified ACME webroot instead of starting a competing Nginx container.

## 3. Deploy and verify

```bash
cd /opt/gnkalgo-ai
git pull --ff-only origin main
bash scripts/deploy-production.sh
curl --fail --head https://www.gnkalgo.com
```

The script validates Compose, backs up a running PostgreSQL service, builds production
images on Oracle, starts databases, applies migrations before serving the new API,
and checks schema/Redis readiness plus public HTTPS. It never removes volumes.
Check registration, login, logout, recovery mail, mobile pages, and certificate
names on the real HTTPS site. AI provider connectivity and broker availability
remain externally unverified until exercised in the configured environment.

## 4. GitHub deployment setup

Set repository environment `production` secrets:
ORACLE_HOST, ORACLE_USER, ORACLE_SSH_KEY, ORACLE_KNOWN_HOSTS.
The known-hosts entry must be verified against the VM's host fingerprint through
an independent trusted channel. Do not disable SSH host verification.

The workflow uses /opt/gnkalgo-ai and requires the existing checkout on main,
exact origin URL, and no tracked local changes. If using a different directory,
edit the workflow's fixed path deliberately. Run Cloud verification and wait for
success, then manually dispatch Deploy Oracle production from main. It refuses
to deploy a commit without a successful cloud check. Configure required reviewers
on the production environment if desired. Secrets are not included in source.

## 5. Renewal, backup, and rollback

Enable certbot.timer and configure a renewal deploy hook to run:

```bash
docker compose --project-directory /opt/gnkalgo-ai \
  -f /opt/gnkalgo-ai/docker-compose.yml -f /opt/gnkalgo-ai/docker-compose.prod.yml \
  exec -T nginx nginx -s reload
sudo certbot renew --dry-run
```

Use the command as the contents of an operator-owned executable renewal hook,
not a scheduled browser task. Verify timer and hook permissions on the VM.

Pre-deploy SQL backups stay under ignored backups/ with restricted permissions.
Also schedule off-VM encrypted backups with a retention policy, and prove restore
on an isolated cloud database before relying on them. Protect .env and certificate
storage separately. Monitor HTTPS, readyz inside the API service, disk space,
container restarts, SMTP failures, and backup age.

For code rollback, create a Git revert of the failed release, pass cloud CI, and
redeploy the resulting main commit. This retains history and .env/volumes. A code
rollback does not roll back data; inspect migration compatibility first. Database
restoration is a separate operator procedure requiring an approved backup and
maintenance window. Never use docker compose down -v for release or rollback.
