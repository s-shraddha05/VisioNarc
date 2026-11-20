// Mirrors backend/app/schemas. Keep both sides in sync.

export interface AdminProfile {
  id: number;
  username: string;
  full_name: string | null;
  last_login_at: string | null;
  password_changed_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_at: string;
  admin: AdminProfile;
}

export interface MessageResponse {
  message: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface HealthResponse {
  status: "ok";
  app: string;
  full_name: string;
  version: string;
  environment: string;
  server_time: string;
}

export interface ReadinessResponse {
  status: "ok" | "degraded";
  database: "ok" | "unavailable";
}

export interface DiagnosticsResponse {
  status: "ok" | "degraded";
  app_version: string;
  environment: string;
  python_version: string;
  database_dialect: string;
  database_server_version: string | null;
  database_reachable: boolean;
  migration_current: string | null;
  migration_head: string | null;
  migrations_up_to_date: boolean;
  admin_count: number | null;
  store_raw_media: boolean;
  data_retention_days: number;
  errors: string[];
}

// ---- Analysis sessions -------------------------------------------------------

export const SESSION_STATUSES = [
  "draft",
  "consented",
  "in_progress",
  "completed",
  "failed",
  "cancelled",
] as const;
export type SessionStatus = (typeof SESSION_STATUSES)[number];
export type Modality = "face" | "motion" | "voice";

export interface ConsentInput {
  consent_given: true;
  consented_by_label: string;
  allow_face: boolean;
  allow_motion: boolean;
  allow_voice: boolean;
  allow_raw_media_storage: boolean;
}

export interface SessionCreateInput {
  subject_label: string;
  notes: string | null;
  consent: ConsentInput;
}

export interface Consent {
  consent_given: boolean;
  consent_text_version: string;
  consented_by_label: string;
  allow_face: boolean;
  allow_motion: boolean;
  allow_voice: boolean;
  allow_raw_media_storage: boolean;
  consented_at: string;
  withdrawn_at: string | null;
}

export interface MeasurementCounts {
  face: number;
  motion: number;
  voice: number;
  results: number;
}

export interface SessionSummary {
  id: number;
  reference_code: string;
  subject_label: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  retain_until: string | null;
  created_by: string | null;
  allow_face: boolean;
  allow_motion: boolean;
  allow_voice: boolean;
  consent_withdrawn: boolean;
  counts: MeasurementCounts;
  /** Created by scripts.seed_synthetic_demo from synthetic signals; never a real person. */
  is_synthetic: boolean;
}

export interface Measurement {
  id: number;
  source: string;
  quality_score: number | null;
  is_reliable: boolean;
  feature_schema_version: string;
  extractor_version: string | null; // null = recorded before migration 0002
  features: Record<string, unknown>;
  warnings: string[];
  captured_at: string;
}

export interface FacialMeasurement extends Measurement {
  image_width: number | null;
  image_height: number | null;
  face_detected: boolean;
  brightness: number | null;
  sharpness: number | null;
}

export interface MotionMeasurement extends Measurement {
  duration_seconds: number | null;
  frames_processed: number;
  frames_with_pose: number;
}

export interface VoiceMeasurement extends Measurement {
  duration_seconds: number | null;
  sample_rate: number | null;
  snr_db: number | null;
}

export type IntegrationFeatureStatus = "measured" | "not_measured" | "missing" | "not_consented" | "excluded_low_quality";

export interface IntegrationFeature {
  index: number;
  modality: Modality;
  key: string;
  label: string;
  unit: string;
  provenance: Provenance;
  value: unknown;
  status: IntegrationFeatureStatus;
  measurement_id: number | null;
}

export interface IntegrationSource {
  modality: Modality;
  measurement_id: number;
  captured_at: string;
  source: string;
  quality_score: number | null;
  feature_schema_version: string;
  extractor_version: string | null;
}

/** Saved combined record. For mode "feature_integration" the indicator/confidence fields are always null. */
export interface CombinedResult {
  id: number;
  mode: string;
  processing_status: "complete" | "partial" | null;
  modalities_used: Modality[];
  indicator_score: number | null;
  indicator_level: string | null;
  confidence: number | null;
  data_quality: number | null;
  explanation: { method?: string; modality_status?: Record<Modality, string> } & Record<string, unknown>;
  limitations: string[];
  feature_schema_version: string | null;
  extractor_version: string | null;
  features: IntegrationFeature[] | null;
  source_measurements: IntegrationSource[] | null;
  model_version_id: number | null;
  created_at: string;
}

export interface SessionDetail extends SessionSummary {
  notes: string | null;
  consent: Consent | null;
  facial_measurements: FacialMeasurement[];
  motion_measurements: MotionMeasurement[];
  voice_measurements: VoiceMeasurement[];
  combined_results: CombinedResult[];
  screening_results: ScreeningResult[];
}

export type ScreeningModelStatus = "synthetic_demo" | "experimental" | "validated" | "unavailable" | "insufficient_input";

/** Stored experimental screening result. Only synthetic demo sessions ever have one. */
export interface ScreeningResult {
  id: number;
  combined_result_id: number;
  model_name: string;
  model_version: string;
  model_status: ScreeningModelStatus;
  is_synthetic: boolean;
  target_definition: string;
  feature_schema_version: string | null;
  input_measurement_ids: Partial<Record<Modality, number>>;
  modality_status: Partial<Record<Modality, string>>;
  missing_modalities: Modality[];
  coverage: number | null;
  /** Output of a hand-set demo formula (0–1), not a probability about a person. */
  estimate: number | null;
  classification: string | null;
  decision_threshold: number | null;
  explanation: { method?: string; reasons?: string[]; contributions?: { feature: string; value: number; contribution: number }[] };
  limitations: string[];
  created_at: string;
}

export interface ScreeningOverview {
  mode: "off" | "synthetic_demo";
  session_is_synthetic: boolean;
  can_run: boolean;
  model_status: ScreeningModelStatus;
  message: string;
  results: ScreeningResult[];
}

export interface SessionFilters {
  status?: SessionStatus[];
  q?: string;
  date_from?: string;
  date_to?: string;
}

// ---- Phase 3 analysis (mirrors backend/app/schemas/analysis.py) -------------------

export interface PixelStats {
  brightness_mean: number;
  contrast_std: number;
  sharpness_laplacian_var: number;
  eye_redness_image_left: number | null;
  eye_redness_image_right: number | null;
  pupil_to_iris_ratio_image_left: number | null;
  pupil_to_iris_ratio_image_right: number | null;
}

export interface FaceSubmission {
  source: "webcam" | "upload";
  image_width: number;
  image_height: number;
  landmarks: [number, number, number][];
  pixel_stats: PixelStats;
  expressions: Record<string, number>;
}

export interface PoseFrame {
  t_ms: number;
  landmarks: number[][] | null; // 33 × [x, y, z, visibility]
}

export interface MotionSubmission {
  source: "webcam" | "upload";
  video_width: number;
  video_height: number;
  frames: PoseFrame[];
}

export type Provenance = "server_audio" | "server_landmarks" | "browser_pixels" | "browser_model";

export interface FeatureSpec {
  key: string;
  modality: Modality;
  label: string;
  unit: string;
  provenance: Provenance;
  description: string;
  source: string | null;
  summary: boolean;
}

export interface FeatureCatalogue {
  version: string;
  provenance: Record<Provenance, string>;
  features: FeatureSpec[];
  limitations: string[];
  sources: Record<string, string>;
  extractors: Record<Modality, string>;
  integration: { version: string; feature_order: string[] };
}

export interface FeatureValue {
  key: string;
  label: string;
  unit: string;
  value: unknown;
  provenance: Provenance;
  provenance_label: string;
}

export interface ModalitySummary {
  modality: Modality;
  status: "available" | "low_quality" | "missing" | "not_consented" | "consent_withdrawn";
  status_reason: string;
  measurement_count: number;
  measurement_id: number | null;
  captured_at: string | null;
  source: string | null;
  quality_score: number | null;
  is_reliable: boolean | null;
  warnings: string[];
  key_features: FeatureValue[];
}

export interface MultimodalSummary {
  session_id: number;
  reference_code: string;
  session_status: SessionStatus;
  generated_at: string;
  feature_schema_version: string;
  available_modalities: Modality[];
  missing_modalities: Modality[];
  modalities: ModalitySummary[];
  limitations: string[];
  method_sources: Record<string, string>;
}

// ---- Dashboard / audit / settings ------------------------------------------------

export interface AuditEvent {
  id: number;
  action: string;
  admin_username: string | null;
  entity_type: string | null;
  entity_id: string | null;
  details: Record<string, unknown> | null;
  ip_address: string | null;
  created_at: string;
}

export interface DashboardSummary {
  generated_at: string;
  totals: {
    sessions: number;
    active_sessions: number;
    completed_sessions: number;
    face_measurements: number;
    motion_measurements: number;
    voice_measurements: number;
    combined_results: number;
  };
  sessions_by_status: Partial<Record<SessionStatus, number>>;
  sessions_per_day: { date: string; count: number }[];
  recent_activity: AuditEvent[];
}

export interface ExpiredSession {
  id: number;
  reference_code: string;
  subject_label: string;
  status: string;
  retain_until: string;
  consent_records: number;
  face_measurements: number;
  motion_measurements: number;
  voice_measurements: number;
  combined_records: number;
}

export interface RetentionPreview {
  checked_at: string;
  retention_days: number;
  auto_purge_enabled: boolean;
  interval_hours: number;
  last_automatic_run: { at: string; deleted: number; error: string | null } | null;
  sessions: ExpiredSession[];
}

export interface PurgeResult {
  deleted: ExpiredSession[];
  skipped_ids: number[];
}

export interface MeasurementDeleted {
  modality: Modality;
  measurement_id: number;
  removed_combined_records: number[];
}

export interface AdminSessionInfo {
  id: number;
  issued_at: string;
  expires_at: string;
  ip_address: string | null;
  user_agent: string | null;
  current: boolean;
}

export interface Capabilities {
  face_analysis: boolean;
  motion_analysis: boolean;
  voice_analysis: boolean;
  multimodal_analysis: boolean;
  pdf_reports: boolean;
}

export interface ServerSettings {
  environment: string;
  store_raw_media: boolean;
  data_retention_days: number;
  retention_enforcement: boolean;
  access_token_expire_minutes: number;
  login_max_failed_attempts: number;
  login_lockout_minutes: number;
  consent_text_version: string;
  capabilities: Capabilities;
}
