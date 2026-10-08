# Broker connection flow

Home → Login → Broker → Dashboard. Dashboard navigation checks the authenticated
user's recent broker verification. Dhan, FYERS and XTS have read-only credential
verification adapters; other names remain visibly unavailable.

For Dhan and FYERS set VALID_BROKERS=dhan,fyers (include xts if needed).
Dhan users enter Client ID and an existing Access Token. Verification calls the
fixed https://api.dhan.co/v2/profile endpoint and requires the returned Client ID
to match. FYERS users enter App ID and an existing Access Token. Verification calls
https://api-t1.fyers.in/api/v3/profile using Authorization: AppID:AccessToken.
FYERS App Secret alone is not an Access Token. Generate a token through FYERS'
official authorization flow first; its registered callback is required there.
This release does not implement token generation or automatic renewal.

Optional admin-owned credentials on Oracle: DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN,
FYERS_APP_ID and FYERS_ACCESS_TOKEN. Only the admin role can use these settings.

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

REDIRECT_URL stays blank for existing-token verification and XTS direct login.
Future broker OAuth adapters will need their exact registered HTTPS callback URLs.

Reference: https://github.com/symphonyfintech/xts-pythonclient-api-sdk
References: https://dhanhq.co/docs/v2/authentication/
https://github.com/FyersDev/fyers-skills/blob/master/skills/fyers-trading/references/auth.md
