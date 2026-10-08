# GNK ALGO — production website and research workspace

Production domain: https://www.gnkalgo.com
Source repository: https://github.com/Boop-12/GNK_AI.git
Deployment target: Oracle Cloud VM. This computer stores source only.

## Delivered first release

- Responsive GNK landing page using the unmodified supplied bull/bear artwork.
- Login, registration with password confirmation, visibility controls, recovery.
- Read-only authenticated dashboard; unavailable broker balances remain unavailable.
- Broker selection form with honest adapter availability, not credential collection.
- AI research panel using a server-configured OpenAI Responses provider, explicit
  consent, bounded output, timeouts, per-account/IP rate limits, and no execution tools.
- Cash-funded risk sizing from user-entered capital, stop, entry, and lot size.
- Light, Dark, Carbon, System themes and eight accents; browser preference storage only.
- Account page and permission-protected read-only user administration.
- Production Docker/Nginx/TLS configuration, dependency readiness, cloud CI and manual deployment.

## Cloud-only operation

Do not run development servers, application builds, containers, or tests on the
source-storage computer. The development start command has been removed. GitHub
Actions runs checks and production builds on hosted runners. Oracle runs the
production services. CI's disposable HTTP test server is isolated to GitHub runners.

Follow [Oracle production deployment](docs/ORACLE_PRODUCTION.md). The manual
Deploy Oracle production workflow requires a successful Cloud verification run
for the exact commit and configured production environment secrets.

## Safety and availability

Production defaults to secure cookies and HTTPS. Access tokens remain in memory;
refresh cookies are HttpOnly; password checks and auth protections are retained.
BROKER_TRADING_ENABLED=true is rejected. No order endpoints exist in this release.
PAPER / READ-ONLY identifies the execution boundary, not a paper-trading simulator.

AI is disabled until AI_ENABLED, OPENAI_API_KEY, and OPENAI_MODEL are configured
on the VM. The public browser receives no provider key. Provider configuration
is not proof of a successful provider response; failed requests display an error.
Questions go to OpenAI only after consent. store=false requests no response storage
through the Responses API; it does not promise zero provider retention. Operator
billing limits and provider data policies must be configured independently.
Reference: https://developers.openai.com/api/reference/python/resources/responses/methods/create

XTS currently has a configuration registry only. All broker authentication,
live market data, account values, orders, signals, trade history, automated
strategies, app TOTP, API keys and webhooks are future work. Do not enter broker
credentials into this release. No trading entitlement or AI accuracy is claimed.

Source lineage and original asset preservation: [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md).
