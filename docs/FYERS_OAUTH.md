# FYERS OAuth on Oracle

Register this exact redirect URL in your FYERS application's settings:

    https://www.gnkalgo.com/api/v1/brokers/fyers/oauth/callback

Configure /opt/gnkalgo_AI/.env privately on Oracle:

    VALID_BROKERS=dhan,fyers,xts
    FYERS_APP_ID=YOUR_FYERS_APP_ID
    FYERS_APP_SECRET=YOUR_FYERS_APP_SECRET
    REDIRECT_URL=https://www.gnkalgo.com/api/v1/brokers/fyers/oauth/callback

Never paste the App Secret into chat or commit .env. Keep existing keys, database
password, JWT secret and BROKER_TRADING_ENABLED=false. The callback must exactly
match FRONTEND_URL plus /api/v1/brokers/fyers/oauth/callback.

After changing .env recreate the API container on Oracle (restart alone does not
load new container environment variables):

    cd /opt/gnkalgo_AI
    docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-deps --force-recreate --wait api
    docker compose exec -T nginx nginx -s reload

Sign in to GNK, select Fyers on /broker and click Connect with FYERS. Enter broker
credentials only on FYERS. It redirects to the GNK backend callback, which exchanges
the authorization code, verifies the profile and redirects to /dashboard on success.
Missing configuration keeps the OAuth button disabled; existing-token verification
still works. Dhan continues using Client ID and Access Token; no Dhan OAuth route is
implemented by this FYERS release.

State expires after 600 seconds, is bound to the initiating user and an HttpOnly,
Secure, SameSite=Lax browser cookie, and is consumed atomically once. Invalid,
cancelled, expired, wrong-browser and failed-provider callbacks return to /broker
without exposing authorization codes or secrets. State contains only identity and
hashes; no App Secret or broker token is stored. Profile verification is required
before setting the user-scoped, 10-minute verification record. Access and refresh
tokens are discarded. Live feeds, balances, order execution and automatic token
renewal are not part of this release.

Nginx disables callback request/error logging; API access logs are disabled and
middleware removes callback query strings from ASGI scope. Application errors use
generic messages. Cloudflare or other upstream proxies must also redact callback
query strings if their request logging is enabled.

Reference: https://github.com/FyersDev/fyers-skills/blob/master/skills/fyers-trading/references/auth.md
