"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { Brand } from "@/components/Brand";
import { ThemeControls } from "@/components/ThemeProvider";
import { authRequest, protectedRequest, SessionExpiredError, setAccessToken, type AuthUser } from "@/lib/auth";

type View = "dashboard" | "broker" | "account" | "appearance" | "admin";
type Status = { mode: string; liveExecutionEnabled: boolean; ai: { available: boolean; status: string }; brokerVerified: boolean; lastChecked: string };
type Broker = { broker: string; name: string; status: string; marketDataStatus: string; tradingStatus: string; connectionAvailable: boolean; adminCredentialsAvailable: boolean; verifiedAt?: string };
const brokerNames = ["Dhan", "Fyers", "Zerodha", "Upstox", "Angel One", "5paisa", "Alice Blue", "Groww", "HDFC", "Kotak", "Shoonya", "Samco", "IndMoney", "XTS"];
const nav = [["dashboard", "/dashboard", "◫", "Dashboard"], ["broker", "/broker", "⇄", "Broker connection"], ["account", "/account", "◎", "My account"], ["appearance", "/profile/appearance", "◐", "Appearance"]];
const titles: Record<View, string> = { dashboard: "Your research workspace", broker: "Choose your broker", account: "Your account", appearance: "Make it your workspace", admin: "User administration" };
const money = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value);

export function Workspace({ view = "dashboard" }: { view?: View }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<Status | null>(null);
  const [brokers, setBrokers] = useState<Broker[]>([]);
  const [users, setUsers] = useState<AuthUser[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [loggingOut, setLoggingOut] = useState(false);

  async function refresh() {
    setLoading(true); setError("");
    try {
      const me = await protectedRequest<AuthUser>("/users/me");
      setUser(me);
      const results = await Promise.all([protectedRequest<Status>("/workspace/status"), protectedRequest<Broker[]>("/brokers")]);
      setStatus(results[0]); setBrokers(results[1]);
      if (view === "dashboard" && !results[0].brokerVerified) router.replace("/broker");
      if (view === "admin" && me.authorities.includes("users:read")) setUsers(await protectedRequest<AuthUser[]>("/admin/users"));
    } catch (cause) {
      if (cause instanceof SessionExpiredError) { setUser(null); router.replace("/login"); }
      else { setStatus(null); setBrokers([]); setError(cause instanceof Error ? cause.message : "Unable to load your workspace."); }
    } finally { setLoading(false); }
  }
  useEffect(() => { void refresh(); }, [view]); // All data is fetched from authenticated server endpoints.

  async function logout() {
    setLoggingOut(true); setError("");
    try { await authRequest("/auth/logout"); setAccessToken(null); setUser(null); router.replace("/login"); }
    catch { setError("Sign out could not revoke your session. Please try again."); }
    finally { setLoggingOut(false); }
  }

return <main className="terminal"><a className="skip-link" href="#workspace-content">Skip to workspace</a><aside className="terminal-sidebar"><Brand /><nav aria-label="Workspace navigation">{nav.map(([id, href, icon, label]) => <Link key={id} href={href} aria-current={id === view ? "page" : undefined}><span aria-hidden="true">{icon}</span>{label}</Link>)}{user?.authorities.includes("users:read") && <Link href="/admin/users" aria-current={view === "admin" ? "page" : undefined}>⚙ Users</Link>}</nav><div className="sidebar-foot"><span className="status-dot" /> READ-ONLY WORKSPACE<br />Live orders are disabled.<br />Asia/Kolkata · INR</div></aside><div className="terminal-main"><header className="terminal-top"><div><span className="pill">PAPER / READ-ONLY</span><span className="pill">{status?.brokerVerified ? "BROKER LOGIN VERIFIED" : "BROKER UNVERIFIED"}</span></div><div><Link href="/account">{user?.name.split(" ")[0] ?? "Account"}</Link><button onClick={logout} disabled={loggingOut}>{loggingOut ? "Signing out…" : "Sign out ↗"}</button></div></header><div id="workspace-content" className="terminal-heading"><div><h1>{titles[view]}</h1><p>{status ? `Checked ${new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" }).format(new Date(status.lastChecked))} IST` : "Secure access · Indian market focus"}</p></div><button className="gnk-button ghost" onClick={refresh} disabled={loading}>{loading ? "Loading…" : "Refresh ↻"}</button></div>{error && <p className="notice" role="alert">{error}</p>}{loading && !user && <p className="notice" role="status">Checking your session…</p>}
    {user && <>
      {view === "dashboard" && status?.brokerVerified && <><div className="notice">Your broker login was verified. Live prices and account balances are not integrated yet. Verification expires after 10 minutes. <Link href="/broker">Review connection ↗</Link></div><div className="summary-grid">{["Available margin", "Used margin", "Total balance", "Day’s P&L"].map(label => <article className="summary-card" key={label}><p>{label}</p><strong>—</strong><small>Awaiting verified broker data</small></article>)}</div><div className="workspace-grid"><AIResearch available={status?.ai.available ?? false} /><RiskPlanner /></div></>}
      {view === "broker" && <BrokerSelection brokers={brokers} onConnected={refresh} />}
      {view === "appearance" && <section className="work-panel"><div className="panel-heading"><h2>Your appearance preferences</h2></div><p>Choose a theme and accent. Settings are saved on this browser.</p><ThemeControls /></section>}
      {view === "account" && <section className="work-panel"><div className="panel-heading"><h2>{user.name}</h2><span className="pill">SIGNED IN</span></div><p>{user.email}</p><div className="broker-facts"><div><small>Account roles</small>{user.roles.join(", ")}</div><div><small>Application security</small>Password + secure refresh session</div></div><p>Application two-factor authentication is not available in this release.</p><Link href="/forgot-password" className="gnk-button ghost">Reset your password ↗</Link></section>}
      {view === "admin" && (user.authorities.includes("users:read") ? <section className="work-panel admin-list"><table><caption>Registered application users</caption><thead><tr><th>Name</th><th>Email</th><th>Roles</th></tr></thead><tbody>{users.map(item => <tr key={item.id}><td>{item.name}</td><td>{item.email}</td><td>{item.roles.join(", ")}</td></tr>)}</tbody></table></section> : <div className="notice">Your account does not have permission to view users.</div>)}
    </>}
    </div></main>;
}

function AIResearch({ available }: { available: boolean }) {
  const [prompt, setPrompt] = useState(""); const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false); const [answer, setAnswer] = useState(""); const [error, setError] = useState("");
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!available || !consent || busy) return;
    setBusy(true); setError(""); setAnswer("");
    try { const result = await protectedRequest<{ text: string }>("/workspace/research", { method: "POST", body: { prompt, consent } }); setAnswer(result.text); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Research is temporarily unavailable."); }
    finally { setBusy(false); }
  }
  return <section className="work-panel"><div className="panel-heading"><h2><span style={{ color: "var(--cyan)" }}>✳</span> GNK Intelligence</h2><span className="pill">{available ? "PROVIDER CONFIGURED" : "SETUP REQUIRED"}</span></div><p>Build a research brief from your own observations. The assistant has no live prices, account data, or ability to place orders.</p><form onSubmit={submit}><div className="prompt-chips">{["Challenge my market thesis", "Explain option time decay", "Build a research checklist"].map(text => <button key={text} type="button" onClick={() => setPrompt(text)}>{text} ↗</button>)}</div><label htmlFor="research-prompt" className="sr-only">Your research question</label><textarea id="research-prompt" value={prompt} onChange={event => setPrompt(event.target.value)} placeholder="Describe your question, timeframe, and the evidence you have…" required minLength={10} maxLength={4000} /><label className="consent"><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} />I agree to send this question to the configured AI provider. I have excluded credentials and personal account details.</label><button className="gnk-button primary" disabled={!available || !consent || busy || prompt.trim().length < 10}>{busy ? "Preparing research…" : "Generate research brief"} <span>↗</span></button></form>{!available && <p className="small-note">Your operator needs to enable an AI provider before questions can be sent.</p>}{error && <p role="alert" className="error-message">{error}</p>}{answer && <div className="ai-response" aria-live="polite">{answer}</div>}</section>;
}

function RiskPlanner() {
  const [values, setValues] = useState({ capital: "", risk: "1", entry: "", stop: "", lot: "1" });
  const capital = Number(values.capital), risk = Number(values.risk), entry = Number(values.entry), stop = Number(values.stop), lot = Number(values.lot);
  const valid = [capital, risk, entry, stop, lot].every(Number.isFinite) && capital > 0 && risk > 0 && risk <= 5 && entry > 0 && stop > 0 && entry !== stop && lot > 0 && Number.isInteger(lot);
  const budget = capital * risk / 100, distance = Math.abs(entry - stop);
  const quantity = valid ? Math.floor(Math.min(budget / distance, capital / entry) / lot) * lot : 0;
  const fields: [keyof typeof values, string, string][] = [["capital", "Capital (₹)", "100000"], ["risk", "Risk budget (%)", "1"], ["entry", "Entry price (₹)", ""], ["stop", "Stop price (₹)", ""], ["lot", "Lot size (units)", "1"]];
  return <section className="work-panel"><div className="panel-heading"><h2>Position risk planner</h2><span className="pill">CALCULATOR</span></div><p>Calculate a cash-funded position from your own inputs. Risk percentage is a planning input, not a recommendation.</p><div className="risk-fields">{fields.map(([key, label, placeholder]) => <label key={key}>{label}<input type="number" inputMode="decimal" min={key === "risk" ? "0.01" : key === "lot" ? "1" : "0.01"} max={key === "risk" ? "5" : undefined} step={key === "lot" ? "1" : "0.01"} value={values[key]} placeholder={placeholder} onChange={event => setValues({ ...values, [key]: event.target.value })} /></label>)}</div><div className="risk-result" aria-live="polite"><p>Planned quantity</p><strong>{valid ? `${quantity.toLocaleString("en-IN")} units` : "—"}</strong><p>{valid ? `Risk budget ${money(budget)} · planned stop risk ${money(quantity * distance)}` : "Enter valid capital, entry, stop, lot size, and a risk budget up to 5%."}</p><small>Rounded down to whole lots and capped by cash capital. Excludes fees, slippage, gaps, and margin rules. Stops do not guarantee an exit price. Not a derivatives margin calculator.</small></div></section>;
}

function BrokerSelection({ brokers, onConnected }: { brokers: Broker[]; onConnected: () => Promise<void> }) {
  const router = useRouter();
  const [selected, setSelected] = useState("Dhan");
  const [apiKey, setApiKey] = useState("");
  const [apiSecret, setApiSecret] = useState("");
  const [useServer, setUseServer] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const status = brokers.find(item => item.name.toLowerCase() === selected.toLowerCase());
  const keyLabel = selected === "Dhan" ? "Client ID" : selected === "Fyers" ? "App ID" : "API Key";
  const secretLabel = selected === "XTS" ? "API Secret" : "Access Token";
  async function connect(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError("");
    try {
      const result = await protectedRequest<Broker>(`/brokers/${status?.broker}/connect`, { method: "POST", body: { api_key: useServer ? "" : apiKey, api_secret: useServer ? "" : apiSecret, use_server_credentials: useServer } });
      setApiKey(""); setApiSecret("");
      if (result.status !== "VERIFIED") throw new Error("Broker verification was not confirmed.");
      await onConnected(); router.push("/dashboard");
    } catch (cause) { setApiSecret(""); setError(cause instanceof Error ? cause.message : "Connection could not be verified."); }
    finally { setBusy(false); }
  }
  return <section className="work-panel broker-form"><div className="panel-heading"><h2>Connect your broker</h2><span className="pill">STEP 3 OF 4</span></div><p>Select your broker and verify your market-data credentials to open the dashboard.</p><label>Broker<select aria-label="Broker" value={selected} disabled={busy} onChange={event => { setSelected(event.target.value); setApiKey(""); setApiSecret(""); setUseServer(false); setError(""); }}>{brokerNames.map(name => <option key={name}>{name}</option>)}</select></label>
    {status ? <><div className="notice">{selected === "XTS" ? "Use XTS market-data API credentials." : selected === "Dhan" ? "Use your Dhan Client ID and an Access Token generated in Dhan Web." : "Use your FYERS App ID and Access Token generated through FYERS authorization. An App Secret alone cannot authenticate this connection."} Credentials are sent over HTTPS to the backend for verification and are not saved. Passwords, MPINs, and TOTP codes are not needed.</div><form onSubmit={connect}>
      {status?.adminCredentialsAvailable && <label className="consent"><input type="checkbox" checked={useServer} disabled={busy} onChange={event => { setUseServer(event.target.checked); setApiKey(""); setApiSecret(""); }} />Use server-configured credentials (admin only)</label>}
      {!useServer && <div className="broker-credentials"><label htmlFor="broker-api-key">{keyLabel}<input id="broker-api-key" type="password" autoComplete="off" value={apiKey} onChange={event => setApiKey(event.target.value)} required maxLength={1024} disabled={busy} /></label><label htmlFor="broker-api-secret">{secretLabel}<input id="broker-api-secret" type="password" autoComplete="off" value={apiSecret} onChange={event => setApiSecret(event.target.value)} required maxLength={8192} disabled={busy} /></label></div>}
      {!status?.connectionAvailable && <p className="small-note">Administrator setup required: configure the broker-provided XTS market-data base URL on the server.</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      <button className="gnk-button primary" disabled={busy || !status?.connectionAvailable || (!useServer && (!apiKey.trim() || !apiSecret))}>{busy ? "Verifying with broker…" : "Verify connection & open dashboard"}<span>↗</span></button>
    </form>{status?.status === "VERIFIED" && <p role="status">Broker login verified. <Link href="/dashboard">Open dashboard ↗</Link></p>}<p className="small-note">Verification lasts 10 minutes. Provider tokens are not retained; live feeds and account balances need further integration. Live orders remain disabled. REDIRECT_URL is not needed when verifying an existing token. FYERS token generation requires the callback registered with FYERS.</p></> : <><div className="notice">{selected} is a requested integration. Its adapter is not available in this release.</div><button className="gnk-button ghost" disabled>Broker authentication unavailable</button></>}
    <div className="broker-facts"><div><small>Credential verification</small>{status?.status.replaceAll("_", " ") ?? "UNAVAILABLE"}</div><div><small>Order execution</small>DISABLED</div></div>
  </section>;
}
