/**
 * Typed API for Phase 2 resources: states, clubs, players, dashboard stats.
 */

import { apiDownload, apiFetch, apiUpload } from "@/lib/api";

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ---------------------------------------------------------------- states
export interface State {
  id: string;
  federation_id: string;
  name: string;
  code: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  created_at: string;
  updated_at: string;
}

export type StateInput = {
  name: string;
  code?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
};

// ---------------------------------------------------------------- clubs
export interface Club {
  id: string;
  federation_id: string;
  state_id: string | null;
  name: string;
  coach_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  address: string | null;
  logo_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface ClubDetail extends Club {
  state_name: string | null;
  player_count: number;
}

export type ClubInput = {
  name: string;
  state_id?: string | null;
  coach_name?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  address?: string | null;
};

// ---------------------------------------------------------------- players
export type Gender = "M" | "F" | "O";
export type PlayerStatus = "active" | "inactive" | "suspended" | "retired";

export interface Player {
  id: string;
  federation_id: string;
  federation_player_code: string;
  full_name: string;
  gender: Gender;
  date_of_birth: string | null;
  nationality: string | null;
  photo_url: string | null;
  phone: string | null;
  email: string | null;
  status: PlayerStatus;
  club_id: string | null;
  state_id: string | null;
  age: number | null;
  age_category: string | null;
  created_at: string;
  updated_at: string;
}

export interface PlayerDetail extends Player {
  club_name: string | null;
  state_name: string | null;
}

export type PlayerInput = {
  federation_player_code: string;
  full_name: string;
  gender: Gender;
  date_of_birth?: string | null;
  nationality?: string | null;
  phone?: string | null;
  email?: string | null;
  status?: PlayerStatus;
  club_id?: string | null;
  state_id?: string | null;
};

export interface PlayerFilters {
  q?: string;
  status?: PlayerStatus | "";
  gender?: Gender | "";
  club_id?: string;
  state_id?: string;
  page?: number;
  size?: number;
}

export interface ImportResult {
  created: number;
  updated: number;
  skipped: number;
  errors: { row: number; message: string }[];
}

export interface Overview {
  total_players: number;
  active_players: number;
  total_clubs: number;
  total_states: number;
  total_tournaments: number;
  active_tournaments: number;
}

// ------------------------------------------------------------------ helpers
function qs(params: Record<string, string | number | undefined | null>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

// ------------------------------------------------------------------ states API
export const statesApi = {
  list: (q = "", page = 1, size = 20) =>
    apiFetch<Paginated<State>>(`/states${qs({ q, page, size })}`),
  create: (data: StateInput) =>
    apiFetch<State>("/states", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<StateInput>) =>
    apiFetch<State>(`/states/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id: string) => apiFetch<{ detail: string }>(`/states/${id}`, { method: "DELETE" }),
};

// ------------------------------------------------------------------ clubs API
export const clubsApi = {
  list: (q = "", state_id = "", page = 1, size = 20) =>
    apiFetch<Paginated<Club>>(`/clubs${qs({ q, state_id, page, size })}`),
  get: (id: string) => apiFetch<ClubDetail>(`/clubs/${id}`),
  create: (data: ClubInput) =>
    apiFetch<Club>("/clubs", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<ClubInput>) =>
    apiFetch<Club>(`/clubs/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id: string) => apiFetch<{ detail: string }>(`/clubs/${id}`, { method: "DELETE" }),
};

// ------------------------------------------------------------------ players API
export const playersApi = {
  list: (f: PlayerFilters = {}) =>
    apiFetch<Paginated<Player>>(
      `/players${qs({
        q: f.q,
        status: f.status,
        gender: f.gender,
        club_id: f.club_id,
        state_id: f.state_id,
        page: f.page ?? 1,
        size: f.size ?? 20,
      })}`,
    ),
  get: (id: string) => apiFetch<PlayerDetail>(`/players/${id}`),
  create: (data: PlayerInput) =>
    apiFetch<Player>("/players", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<PlayerInput>) =>
    apiFetch<Player>(`/players/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id: string) => apiFetch<{ detail: string }>(`/players/${id}`, { method: "DELETE" }),
  importFile: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiUpload<ImportResult>("/players/import", fd);
  },
  exportFile: (format: "csv" | "xlsx") => apiDownload(`/players/export?format=${format}`),
};

// ------------------------------------------------------------------ stats API
export const statsApi = {
  overview: () => apiFetch<Overview>("/stats/overview"),
};
