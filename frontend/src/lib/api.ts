import axios, { AxiosError } from "axios";
import type {
  AdminProfile,
  AdminSessionInfo,
  AuditEvent,
  MeasurementDeleted,
  Modality,
  PurgeResult,
  RetentionPreview,
  CombinedResult,
  DashboardSummary,
  DiagnosticsResponse,
  FaceSubmission,
  FacialMeasurement,
  FeatureCatalogue,
  HealthResponse,
  MotionMeasurement,
  MotionSubmission,
  MultimodalSummary,
  ScreeningOverview,
  ScreeningResult,
  VoiceMeasurement,
  MessageResponse,
  Page,
  ReadinessResponse,
  ServerSettings,
  SessionCreateInput,
  SessionDetail,
  SessionFilters,
  SessionSummary,
  TokenResponse,
} from "@/lib/types";

const TOKEN_KEY = "visonarc.token";

// sessionStorage: the token disappears when the tab closes. The backend also revokes it on logout.
export const tokenStore = {
  get(): string | null {
    try {
      return sessionStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set(token: string) {
    try {
      sessionStorage.setItem(TOKEN_KEY, token);
    } catch {
      /* storage unavailable: token lives only for this page load */
    }
  },
  clear() {
    try {
      sessionStorage.removeItem(TOKEN_KEY);
    } catch {
      /* ignore */
    }
  },
};

export const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
  timeout: 20000,
  // FastAPI expects repeated keys for lists: ?status=a&status=b
  paramsSerializer: { indexes: null },
});

http.interceptors.request.use((config) => {
  const token = tokenStore.get();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let onUnauthorized: (() => void) | null = null;
export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler;
}

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const isLogin = error.config?.url?.endsWith("/auth/login");
    if (error.response?.status === 401 && !isLogin) {
      tokenStore.clear();
      onUnauthorized?.();
    }
    return Promise.reject(error);
  },
);

/** Human-readable message for any API failure, including FastAPI validation errors. */
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const unreachable = "Cannot reach the VisoNarc server. Check that the backend is running on port 8000 (scripts\\run_backend.ps1), then try again.";
    if (!error.response) return unreachable;
    // In development the Vite proxy answers for a stopped backend (ECONNREFUSED) with an empty-bodied
    // 500; FastAPI's own errors always carry a body. 502/504 come from proxies as well.
    const { status, data } = error.response;
    const emptyBody = data === undefined || data === null || data === "" || (data instanceof Blob && data.size === 0);
    if (status === 502 || status === 504 || (status >= 500 && emptyBody)) return unreachable;
    const detail = (error.response.data as { detail?: unknown } | undefined)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => {
          if (typeof d === "string") return d;
          const item = d as { msg?: string; loc?: unknown[] };
          const field = item.loc?.filter((p) => p !== "body").join(" › ");
          const msg = (item.msg ?? "Invalid input").replace(/^Value error, /, "");
          return field ? `${field}: ${msg}` : msg;
        })
        .join(" ");
    }
    if (error.response.status === 503) return "The database is unavailable. Check that MySQL is running.";
    return `Request failed (HTTP ${error.response.status}).`;
  }
  return error instanceof Error ? error.message : "Unexpected error.";
}

function filenameFrom(disposition: string | undefined, fallback: string) {
  const match = disposition?.match(/filename="?([^";]+)"?/i);
  return match?.[1] ?? fallback;
}

/** Save an authenticated download (the Bearer header rules out a plain <a href>). */
async function download(url: string, fallbackName: string, params?: object) {
  const response = await http.get<Blob>(url, { params, responseType: "blob" });
  const name = filenameFrom(response.headers["content-disposition"], fallbackName);
  const href = URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(href), 1000);
  return name;
}

export const api = {
  login: (username: string, password: string) =>
    http.post<TokenResponse>("/auth/login", { username, password }).then((r) => r.data),
  logout: () => http.post<MessageResponse>("/auth/logout").then((r) => r.data),
  me: () => http.get<AdminProfile>("/auth/me").then((r) => r.data),
  updateProfile: (full_name: string | null) =>
    http.patch<AdminProfile>("/auth/me", { full_name }).then((r) => r.data),
  changePassword: (current_password: string, new_password: string) =>
    http
      .post<MessageResponse>("/auth/change-password", { current_password, new_password })
      .then((r) => r.data),

  health: () => http.get<HealthResponse>("/health").then((r) => r.data),
  readiness: () =>
    http
      .get<ReadinessResponse>("/health/ready", { validateStatus: (s) => s === 200 || s === 503 })
      .then((r) => r.data),
  diagnostics: () => http.get<DiagnosticsResponse>("/health/details").then((r) => r.data),

  dashboard: () => http.get<DashboardSummary>("/dashboard/summary").then((r) => r.data),
  settings: () => http.get<ServerSettings>("/settings").then((r) => r.data),

  listSessions: (params: SessionFilters & { page: number; page_size: number }) =>
    http.get<Page<SessionSummary>>("/sessions", { params }).then((r) => r.data),
  getSession: (id: number) => http.get<SessionDetail>(`/sessions/${id}`).then((r) => r.data),
  createSession: (body: SessionCreateInput) =>
    http.post<SessionDetail>("/sessions", body).then((r) => r.data),
  withdrawConsent: (id: number) =>
    http.post<SessionDetail>(`/sessions/${id}/withdraw-consent`).then((r) => r.data),
  deleteSession: (id: number) => http.delete(`/sessions/${id}`).then(() => undefined),
  downloadSessionsCsv: (filters: SessionFilters) =>
    download("/sessions/export.csv", "visonarc-sessions.csv", filters),
  downloadSessionJson: (id: number, reference: string) =>
    download(`/sessions/${id}/export`, `visonarc-${reference}.json`),
  downloadSessionPdf: (id: number, reference: string) =>
    download(`/sessions/${id}/report.pdf`, `visonarc-${reference}.pdf`),

  // ---- Phase 3 analysis --------------------------------------------------------
  featureSchema: () => http.get<FeatureCatalogue>("/analysis/feature-schema").then((r) => r.data),
  analyzeFace: (sessionId: number, body: FaceSubmission) =>
    http.post<FacialMeasurement>(`/sessions/${sessionId}/analysis/face`, body).then((r) => r.data),
  analyzeMotion: (sessionId: number, body: MotionSubmission) =>
    http.post<MotionMeasurement>(`/sessions/${sessionId}/analysis/motion`, body, { timeout: 60000 }).then((r) => r.data),
  /** Sends the WAV recording to the server. Only call after the user explicitly confirmed the upload. */
  analyzeVoice: (sessionId: number, wav: Blob, source: "microphone" | "upload") =>
    http
      .post<VoiceMeasurement>(`/sessions/${sessionId}/analysis/voice`, wav, {
        params: { source, upload_consent: true },
        headers: { "Content-Type": "audio/wav" },
        timeout: 60000,
      })
      .then((r) => r.data),
  multimodalSummary: (sessionId: number) =>
    http.get<MultimodalSummary>(`/sessions/${sessionId}/multimodal-summary`).then((r) => r.data),
  createIntegration: (sessionId: number) =>
    http.post<CombinedResult>(`/sessions/${sessionId}/integrations`).then((r) => r.data),
  listIntegrations: (sessionId: number) =>
    http.get<CombinedResult[]>(`/sessions/${sessionId}/integrations`).then((r) => r.data),
  screening: (sessionId: number) =>
    http.get<ScreeningOverview>(`/sessions/${sessionId}/screening`).then((r) => r.data),
  runScreening: (sessionId: number) =>
    http.post<ScreeningResult>(`/sessions/${sessionId}/screening`).then((r) => r.data),
  completeSession: (sessionId: number) =>
    http.post<SessionDetail>(`/sessions/${sessionId}/complete`).then((r) => r.data),

  deleteMeasurement: (sessionId: number, modality: Modality, measurementId: number) =>
    http
      .delete<MeasurementDeleted>(`/sessions/${sessionId}/measurements/${modality}/${measurementId}`)
      .then((r) => r.data),

  retentionPreview: () => http.get<RetentionPreview>("/retention/preview").then((r) => r.data),
  retentionPurge: (sessionIds: number[]) =>
    http.post<PurgeResult>("/retention/purge", { session_ids: sessionIds, confirm: true }).then((r) => r.data),

  adminSessions: () => http.get<AdminSessionInfo[]>("/auth/sessions").then((r) => r.data),
  revokeAdminSession: (id: number) => http.post<MessageResponse>(`/auth/sessions/${id}/revoke`).then((r) => r.data),
  revokeOtherAdminSessions: () => http.post<MessageResponse>("/auth/sessions/revoke-others").then((r) => r.data),

  auditLogs: (params: { page: number; page_size: number; action?: string; date_from?: string; date_to?: string }) =>
    http.get<Page<AuditEvent>>("/audit-logs", { params }).then((r) => r.data),
  auditActions: () => http.get<string[]>("/audit-logs/actions").then((r) => r.data),
};
