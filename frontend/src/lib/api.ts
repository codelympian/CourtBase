/**
 * Lightweight API client for the BFMS backend.
 * Handles JWT storage and transparent access-token refresh on 401.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_V1 = `${API_URL}/api/v1`;

const ACCESS_KEY = "bfms_access_token";
const REFRESH_KEY = "bfms_refresh_token";

export const tokenStore = {
  get access() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface Tokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json();
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) return data.detail.map((d: { msg: string }) => d.msg).join(", ");
    return res.statusText;
  } catch {
    return res.statusText;
  }
}

async function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.refresh;
  if (!refresh) return false;
  const res = await fetch(`${API_V1}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  });
  if (!res.ok) {
    tokenStore.clear();
    return false;
  }
  const tokens: Tokens = await res.json();
  tokenStore.set(tokens.access_token, tokens.refresh_token);
  return true;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  const access = tokenStore.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const res = await fetch(`${API_V1}${path}`, { ...options, headers });

  if (res.status === 401 && retry && tokenStore.refresh) {
    const ok = await refreshTokens();
    if (ok) return apiFetch<T>(path, options, false);
  }

  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function apiUpload<T>(path: string, formData: FormData, retry = true): Promise<T> {
  const headers = new Headers();
  const access = tokenStore.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);
  const res = await fetch(`${API_V1}${path}`, { method: "POST", body: formData, headers });
  if (res.status === 401 && retry && tokenStore.refresh) {
    const ok = await refreshTokens();
    if (ok) return apiUpload<T>(path, formData, false);
  }
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return res.json() as Promise<T>;
}

export async function apiDownload(path: string, retry = true): Promise<Blob> {
  const headers = new Headers();
  const access = tokenStore.access;
  if (access) headers.set("Authorization", `Bearer ${access}`);
  const res = await fetch(`${API_V1}${path}`, { headers });
  if (res.status === 401 && retry && tokenStore.refresh) {
    const ok = await refreshTokens();
    if (ok) return apiDownload(path, false);
  }
  if (!res.ok) throw new ApiError(res.status, await parseError(res));
  return res.blob();
}

// ---------------------------------------------------------------- auth API
export interface Me {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superuser: boolean;
  federation_id: string | null;
  roles: string[];
  permissions: string[];
}

export async function login(email: string, password: string): Promise<Tokens> {
  const tokens = await apiFetch<Tokens>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  tokenStore.set(tokens.access_token, tokens.refresh_token);
  return tokens;
}

export async function register(email: string, password: string, full_name: string) {
  return apiFetch("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, full_name }),
  });
}

export async function fetchMe(): Promise<Me> {
  return apiFetch<Me>("/auth/me");
}

export async function logout(): Promise<void> {
  const refresh = tokenStore.refresh;
  if (refresh) {
    try {
      await apiFetch("/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refresh }),
      });
    } catch {
      /* ignore */
    }
  }
  tokenStore.clear();
}
