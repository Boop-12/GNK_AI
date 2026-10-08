const API = process.env.NEXT_PUBLIC_API_URL ?? "";
let accessToken: string | null = null;
let refreshing: Promise<void> | null = null;
export class SessionExpiredError extends Error {}

export type AuthUser = { id: number; name: string; email: string; roles: string[]; authorities: string[] };
export function setAccessToken(token: string | null) { accessToken = token; }
export function getAccessToken() { return accessToken; }

export async function authRequest<T>(path: string, body?: unknown): Promise<T> {
  const response = await fetch(`${API}/api/v1${path}`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json", ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    const detail = data?.detail;
    const message = typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail.map(item => item?.msg).filter((item): item is string => typeof item === "string").join(". ")
        : "";
    throw new Error(message || "Something went wrong. Please try again.");
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}

async function refreshSession() {
  if (!refreshing) refreshing = authRequest<{ access_token: string }>("/auth/refresh")
    .then(result => setAccessToken(result.access_token))
    .catch(() => { setAccessToken(null); throw new SessionExpiredError("Please sign in to continue."); })
    .finally(() => { refreshing = null; });
  return refreshing;
}

export async function protectedRequest<T>(path: string, options: { method?: "GET" | "POST"; body?: unknown } = {}): Promise<T> {
  if (!accessToken) await refreshSession();
  const send = () => fetch(`${API}/api/v1${path}`, {
    method: options.method ?? "GET", credentials: "include", cache: "no-store",
    headers: { Authorization: `Bearer ${accessToken}`, "Content-Type": "application/json" },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  let response = await send();
  if (response.status === 401) { await refreshSession(); response = await send(); }
  if (response.status === 401) throw new SessionExpiredError("Please sign in to continue.");
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(typeof data?.detail === "string" ? data.detail : "Request unavailable. Please try again.");
  }
  return response.json();
}
