# Broker connection flow

Home → Login → Broker → Dashboard. Dashboard navigation checks the authenticated
user's recent broker verification. XTS is the implemented market-data login adapter;
other names remain visibly unavailable.

On Oracle, configure VALID_BROKERS=xts and XTS_MARKET_DATA_BASE_URL with the broker's
actual HTTPS API root, optionally ending in /marketdata. The adapter posts appKey,
secretKey and source=WebAPI to /marketdata/auth/login. Confirm the endpoint with the
broker; do not use interactive/trading keys for market-data login.

Users enter their own API Key and API Secret. Only users with the admin role can
choose server credentials (XTS_MARKET_DATA_APP_KEY and XTS_MARKET_DATA_SECRET_KEY).
Credentials configured on Oracle stay in its private .env; no UI reveals them.
The backend rejects redirects, bounds response size and time, enforces rate limits,
requires authentication and the application Origin, and sanitizes provider errors.

Keys and provider tokens are not saved. Redis keeps only a user-scoped login
verification timestamp for 600 seconds. VERIFIED means the login was accepted at
that timestamp; it does not promise a currently live data feed. A new failed login
clears previous verification. Live quotes, account balances and persistent broker
sessions are not implemented. Order execution remains disabled.

REDIRECT_URL stays blank for this direct market-data API-key login. Future broker
OAuth adapters will need their exact registered HTTPS callback URLs.

Reference: https://github.com/symphonyfintech/xts-pythonclient-api-sdk
