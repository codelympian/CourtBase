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
function qs(params: Record<string, string | number | boolean | undefined | null>): string {
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
  uploadLogo: (id: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiUpload<Club>(`/clubs/${id}/logo`, fd);
  },
  deleteLogo: (id: string) => apiFetch<Club>(`/clubs/${id}/logo`, { method: "DELETE" }),
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
  uploadPhoto: (id: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiUpload<Player>(`/players/${id}/photo`, fd);
  },
  deletePhoto: (id: string) => apiFetch<Player>(`/players/${id}/photo`, { method: "DELETE" }),
};

// ------------------------------------------------------------------ stats API
export const statsApi = {
  overview: () => apiFetch<Overview>("/stats/overview"),
};

// ------------------------------------------------------------ event categories
export type Discipline = "singles" | "doubles";
export type GenderScope = "men" | "women" | "mixed" | "any";

export interface EventCategory {
  id: string;
  federation_id: string | null;
  code: string;
  name: string;
  discipline: Discipline;
  gender_scope: GenderScope;
  age_min: number | null;
  age_max: number | null;
  is_active: boolean;
}

export type EventCategoryInput = {
  code: string;
  name: string;
  discipline: Discipline;
  gender_scope?: GenderScope;
  age_min?: number | null;
  age_max?: number | null;
};

export const categoriesApi = {
  list: (activeOnly = true) =>
    apiFetch<EventCategory[]>(`/event-categories${qs({ active_only: activeOnly })}`),
  create: (data: EventCategoryInput) =>
    apiFetch<EventCategory>("/event-categories", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<EventCategoryInput> & { is_active?: boolean }) =>
    apiFetch<EventCategory>(`/event-categories/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),
  remove: (id: string) =>
    apiFetch<{ detail: string }>(`/event-categories/${id}`, { method: "DELETE" }),
};

// ---------------------------------------------------------------- tournaments
export type TournamentLevel =
  | "national_championship"
  | "open"
  | "invitational"
  | "ranking";
export type TournamentStatus =
  | "draft"
  | "registration_open"
  | "registration_closed"
  | "ongoing"
  | "completed";

export interface Tournament {
  id: string;
  federation_id: string;
  name: string;
  venue: string | null;
  start_date: string | null;
  end_date: string | null;
  level: TournamentLevel;
  status: TournamentStatus;
  organizer: string | null;
  created_at: string;
  updated_at: string;
}

export interface TournamentDetail extends Tournament {
  event_count: number;
}

export type TournamentInput = {
  name: string;
  venue?: string | null;
  start_date?: string | null;
  end_date?: string | null;
  level: TournamentLevel;
  organizer?: string | null;
};

export type EventStatus = "pending" | "draw_published" | "ongoing" | "completed";

export interface TournamentEvent {
  id: string;
  federation_id: string;
  tournament_id: string;
  category_id: string;
  name: string;
  draw_size: number | null;
  status: EventStatus;
  created_at: string;
  updated_at: string;
}

export interface TournamentEventDetail extends TournamentEvent {
  category_name: string | null;
  registration_count: number;
}

export const tournamentsApi = {
  list: (q = "", status: TournamentStatus | "" = "", page = 1, size = 20) =>
    apiFetch<Paginated<Tournament>>(`/tournaments${qs({ q, status, page, size })}`),
  get: (id: string) => apiFetch<TournamentDetail>(`/tournaments/${id}`),
  create: (data: TournamentInput) =>
    apiFetch<Tournament>("/tournaments", { method: "POST", body: JSON.stringify(data) }),
  update: (id: string, data: Partial<TournamentInput> & { status?: TournamentStatus }) =>
    apiFetch<Tournament>(`/tournaments/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id: string) => apiFetch<{ detail: string }>(`/tournaments/${id}`, { method: "DELETE" }),
  finalize: (id: string) => apiFetch<Tournament>(`/tournaments/${id}/finalize`, { method: "POST" }),
  listEvents: (id: string) => apiFetch<TournamentEvent[]>(`/tournaments/${id}/events`),
  createEvent: (id: string, category_id: string, name?: string) =>
    apiFetch<TournamentEvent>(`/tournaments/${id}/events`, {
      method: "POST",
      body: JSON.stringify({ category_id, name }),
    }),
};

// --------------------------------------------------------------------- events
export const eventsApi = {
  get: (id: string) => apiFetch<TournamentEventDetail>(`/events/${id}`),
  remove: (id: string) => apiFetch<{ detail: string }>(`/events/${id}`, { method: "DELETE" }),
  listRegistrations: (id: string, page = 1, size = 100) =>
    apiFetch<Paginated<Registration>>(`/events/${id}/registrations${qs({ page, size })}`),
  createRegistration: (id: string, data: RegistrationInput) =>
    apiFetch<Registration>(`/events/${id}/registrations`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  generateDraw: (id: string) =>
    apiFetch<BracketMatch[]>(`/events/${id}/draw`, { method: "POST" }),
  getDraw: (id: string) => apiFetch<BracketMatch[]>(`/events/${id}/draw`),
  resetDraw: (id: string) => apiFetch<{ detail: string }>(`/events/${id}/draw`, { method: "DELETE" }),
};

// --------------------------------------------------------------- registrations
export type RegistrationStatus = "pending" | "confirmed" | "withdrawn" | "rejected";

export interface Registration {
  id: string;
  federation_id: string;
  event_id: string;
  player_id: string;
  partner_player_id: string | null;
  seed: number | null;
  status: RegistrationStatus;
  created_at: string;
  player_name?: string | null;
  partner_name?: string | null;
}

export type RegistrationInput = {
  player_id: string;
  partner_player_id?: string | null;
  seed?: number | null;
};

export const registrationsApi = {
  update: (id: string, data: { seed?: number | null; status?: RegistrationStatus }) =>
    apiFetch<Registration>(`/registrations/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  remove: (id: string) =>
    apiFetch<{ detail: string }>(`/registrations/${id}`, { method: "DELETE" }),
};

// -------------------------------------------------------------------- matches
export type MatchStatus = "scheduled" | "in_progress" | "completed" | "walkover" | "bye";

export interface Match {
  id: string;
  federation_id: string;
  event_id: string;
  round: number;
  position: number;
  player1_id: string | null;
  player2_id: string | null;
  winner_id: string | null;
  score: number[][] | null;
  status: MatchStatus;
  scheduled_at: string | null;
  next_match_id: string | null;
  player1_name?: string | null;
  player2_name?: string | null;
  winner_name?: string | null;
}

export interface BracketMatch extends Match {
  round_name: string;
}

export type MatchScoreInput =
  | { score: number[][]; walkover_winner_id?: never }
  | { walkover_winner_id: string; score?: never };

export const matchesApi = {
  get: (id: string) => apiFetch<Match>(`/matches/${id}`),
  score: (id: string, data: MatchScoreInput) =>
    apiFetch<Match>(`/matches/${id}/score`, { method: "POST", body: JSON.stringify(data) }),
};
