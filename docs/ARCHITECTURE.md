# VisoNarc – Drug Detection Using Voice and Motion · Architecture

> Experimental academic behavioural-analysis system. Facial appearance, voice and movement
> **cannot prove drug consumption**. VisoNarc never labels a person as a drug user; it reports an
> experimental, quality-aware *indicator* with explicit uncertainty and limitations.

## 1. Overview

```
 Browser (React + Vite + TS, Tailwind/shadcn)          FastAPI backend (Python 3.13)          MySQL 8
 ┌──────────────────────────────────────┐   /api/v1   ┌───────────────────────────────┐   ┌──────────────┐
 │ Login · Dashboard · Analysis pages   │ ──────────▶ │ routes → services → models    │──▶│ visonarc DB  │
 │ webcam / microphone capture (Phase 3)│  Bearer JWT │ auth (bcrypt + JWT + sessions)│   │ (utf8mb4)    │
 │ AuthContext · ProtectedRoute · Axios │ ◀────────── │ AI modules (Phase 3):          │   └──────────────┘
 └──────────────────────────────────────┘    JSON     │  face · motion · voice · fusion│
         dev: Vite proxy /api → :8000                 └───────────────────────────────┘
```

* **Frontend** talks only to `/api/v1`. In development Vite proxies `/api` to `127.0.0.1:8000`,
  so the browser never needs CORS and never sees database credentials.
* **Backend** is layered: `api/routes` (HTTP) → `services` (business rules, audit) →
  `models` (SQLAlchemy). Pydantic schemas in `schemas/` define every request/response and are
  mirrored in `frontend/src/lib/types.ts`.
* **Database** schema is owned by Alembic migrations (`backend/alembic/versions`). A test
  (`tests/test_migrations.py`) fails if models and migrations ever diverge.

## 2. Directory structure

```
VisioNarc/
├─ scripts/                  PowerShell: check_env, bootstrap, setup_mysql, run_*, run_tests
├─ docs/                     ARCHITECTURE.md, BUILD_STATUS.md
├─ backend/
│  ├─ app/
│  │  ├─ main.py             create_app(): CORS, security headers, DB-outage handler, routers
│  │  ├─ core/               config.py (env settings), security.py (bcrypt, JWT, password policy)
│  │  ├─ db/                 base.py (Base, naming convention, utcnow), session.py (lazy engine)
│  │  ├─ models/             admin, audit, model_version, analysis, setting
│  │  ├─ schemas/            Pydantic request/response models
│  │  ├─ services/           auth_service.py, audit.py   (+ ai/ modules in Phase 3)
│  │  └─ api/                deps.py (auth dependencies), routes/ (auth, health, …)
│  ├─ alembic/               env.py + versions/0001_initial_schema.py
│  ├─ scripts/               create_admin, reset_admin_password, verify_db
│  ├─ tests/                 pytest suite (SQLite in-memory) + opt-in MySQL checks
│  └─ requirements*.txt      exact pins; requirements.lock.txt = full transitive lock
└─ frontend/
   ├─ src/
   │  ├─ auth/               AuthContext (session state), ProtectedRoute
   │  ├─ components/ui/      shadcn-style primitives (button, card, input, alert, label)
   │  ├─ lib/                api.ts (Axios + token handling), types.ts, brand.ts, utils.ts
   │  └─ pages/              LoginPage, DashboardPage (+ 10 more pages in Phase 2)
   └─ vite.config.ts         @ alias, Tailwind v4 plugin, /api proxy
```

## 3. Authentication design

| Concern | Implementation |
|---|---|
| Role model | Single role: administrator (`admins` table). No public sign-up. |
| Password storage | bcrypt (cost 12 by default), 12–72 byte policy, letter + digit required. |
| Token | HS256 JWT (`sub`, `jti`, `iss`, `iat`, `exp`), default 60-minute lifetime. |
| Revocation | Every token has an `admin_sessions` row; logout sets `revoked_at`, and the API rejects any token whose row is missing, revoked or expired. |
| Brute force | 5 failed attempts → 15-minute lock (configurable). Identical 401 message and dummy bcrypt check for unknown users, wrong passwords and locked accounts. |
| Password change | Requires current password; other sessions are revoked. |
| Reset | Server-side CLI only: `python -m scripts.reset_admin_password` (requires machine + `.env` access). |
| Token storage (browser) | `sessionStorage` (cleared when the tab closes) + Bearer header. Trade-off: simpler than cookie + CSRF; mitigated by short expiry, server-side revocation and no third-party scripts. |
| Audit | `audit_logs`: login, failed login, lock, logout, password change/reset, admin creation. |

## 4. Database schema (migration 0001)

| Table | Purpose | Key constraints |
|---|---|---|
| `admins` | Administrator accounts | `username` unique |
| `admin_sessions` | Issued tokens (revocation) | FK admins (CASCADE), `jti` unique, index `expires_at` |
| `audit_logs` | Security/activity trail | FK admins (SET NULL), indexes `action`, `created_at` |
| `model_versions` | Scoring method + evaluation metrics | unique (`name`,`version`), check `model_type` |
| `analysis_sessions` | One analysis of one pseudonymous subject | unique `reference_code`, check `status`, index `status`, `retain_until` |
| `consent_records` | Per-modality consent, raw-media consent, withdrawal | FK session (CASCADE), one per session |
| `facial_measurements` | Extracted face features + quality | FK session (CASCADE), checks `source`, `quality_score ∈ [0,1]` |
| `motion_measurements` | Extracted pose/motion features + tracking quality | same |
| `voice_measurements` | Extracted audio features + SNR | same |
| `combined_results` | Fused experimental indicator | checks `mode`, `indicator_level`, scores ∈ [0,1] |
| `app_settings` | Admin-editable settings (key → JSON) | FK admins (SET NULL) |

All timestamps are stored as UTC (`DATETIME`, naive) and returned by the API with an explicit
UTC offset. Measurement features are JSON documents versioned by `feature_schema_version`, so
the feature set can evolve in Phase 3 without destructive migrations.

### Privacy by design
* Subjects are identified only by an admin-chosen pseudonymous `subject_label`.
* Raw images/audio/video are **discarded after feature extraction** unless `STORE_RAW_MEDIA=true`
  *and* the subject ticked raw-media consent.
* `retain_until` on each session drives retention-based deletion (Phase 4); deleting a session
  cascades to consent, measurements and results.

## 5. API

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/api/v1/health` | public | Liveness, app name/version |
| GET | `/api/v1/health/ready` | public | DB reachability (200 / 503), no details |
| GET | `/api/v1/health/details` | admin | Diagnostics: DB version, migration state, admin count, privacy settings |
| POST | `/api/v1/auth/login` | public | `{username, password}` → `{access_token, expires_at, admin}` |
| POST | `/api/v1/auth/logout` | admin | Revokes the current token |
| GET / PATCH | `/api/v1/auth/me` | admin | Current profile / update `full_name` |
| POST | `/api/v1/auth/change-password` | admin | `{current_password, new_password}` |
| POST | `/api/v1/sessions` | admin | Create session + consent (`consent_given` must be true, ≥ 1 modality) |
| GET | `/api/v1/sessions` | admin | `page`, `page_size ≤ 100`, repeated `status`, `q`, `date_from`, `date_to` |
| GET | `/api/v1/sessions/export.csv` | admin | CSV of filtered sessions (≤ 5000 rows, formula-injection safe) |
| GET | `/api/v1/sessions/{id}` | admin | Detail incl. consent, measurements, results |
| GET | `/api/v1/sessions/{id}/export` | admin | JSON session record with disclaimer |
| POST | `/api/v1/sessions/{id}/withdraw-consent` | admin | Cancels the session and deletes its measurements/results (409 if already withdrawn) |
| DELETE | `/api/v1/sessions/{id}` | admin | Permanent delete (cascades) |
| GET | `/api/v1/dashboard/summary` | admin | Real counts, per-status, per-day (`days` 7–90), recent audit events |
| GET | `/api/v1/audit-logs` | admin | Paginated; `action` (exact `a.b` or prefix `a`), date range |
| GET | `/api/v1/audit-logs/actions` | admin | Distinct actions for filters |
| GET | `/api/v1/settings` | admin | Effective read-only policy + `capabilities` flags |
| POST | `/api/v1/sessions/{id}/analysis/face` · `/motion` · `/voice` | admin | Phase 3 measurements (see 5b) |
| GET | `/api/v1/sessions/{id}/multimodal-summary` | admin | Live side-by-side summary (no score) |
| POST / GET | `/api/v1/sessions/{id}/integrations` | admin | Save / list score-free feature-integration records |
| POST | `/api/v1/sessions/{id}/complete` | admin | Mark an active session with ≥ 1 measurement complete |
| GET | `/api/v1/analysis/feature-schema` | admin | Feature catalogue, extractor versions, integration order |
| GET | `/api/v1/sessions/{id}/report.pdf` | admin | Server-generated PDF (ReportLab); audited without contents |
| DELETE | `/api/v1/sessions/{id}/measurements/{modality}/{mid}` | admin | Delete one measurement plus combined records that used it |
| GET | `/api/v1/retention/preview` | admin | Expired sessions with dependent-record counts |
| POST | `/api/v1/retention/purge` | admin | `{session_ids, confirm: true}`; deletes only still-expired ids, atomically |
| GET | `/api/v1/auth/sessions` | admin | Your active sign-ins |
| POST | `/api/v1/auth/sessions/{id}/revoke` · `/auth/sessions/revoke-others` | admin | Revoke one / all other sign-ins |

### Behaviour when the database is unavailable (tested in `tests/test_db_unavailable.py`)
| Route | Behaviour |
|---|---|
| `GET /health` | 200: liveness does not use the database |
| `GET /health/ready` | 503 `{"status":"degraded","database":"unavailable"}` |
| `POST /auth/login` | 503 "Database unavailable…" (never reported as a wrong password) |
| Any authenticated route, valid token | 503 "Database unavailable…" (the session lookup needs the DB) |
| Any authenticated route, missing/invalid token | 401, decided without the database |

The frontend treats only 401 as "signed out". Network errors, proxy 5xx and 503 show "Cannot reach
the VisoNarc server" with Retry, and the token is kept (`frontend/src/auth/sessionCheck.ts`).

### Retention, deletion and security (Phase 4)
* **Retention:** expired = `retain_until < now (UTC)`. Purges run through `retention_service.purge`:
  one transaction, the condition re-checked in the DELETE, rollback on mismatch, cascade to consent,
  measurements and combined records, audit `retention.purged`. Triggers: manual (Settings), CLI
  (`scripts/purge_expired.py`, dry-run default) and automatic (only if `RETENTION_AUTO_PURGE=true`).
* **Sign-in protection:** per-account lockout (Phase 1) plus a per-IP failure limiter keyed on the TCP
  peer address (forwarded headers ignored), in memory per process.
* **Revocation:** each token has an `admin_sessions` row checked on every request; listing and
  revoking sign-ins changes that row, so revocation takes effect on the next request.
* **Headers:** `/api/*` responses send `CSP default-src 'none'`, `Cache-Control: no-store`,
  Permissions-Policy, COOP and CORP. The frontend dev/preview servers send nosniff, DENY,
  no-referrer and a camera/microphone-self Permissions-Policy (no frontend CSP).
* **Logging:** the database engine uses `hide_parameters=True`, so SQL logs never contain bound values.

Every state-changing or exporting endpoint writes an audit entry.

### Frontend structure (Phase 2)
`App.tsx` uses a data router: `/login` is public, and everything else sits behind `ProtectedRoute`
inside `AppShell` (responsive sidebar plus mobile drawer). Pages read data only through
`lib/api.ts`, using the `useApi` hook for loading, error and reload. The capture pages share
`ModalityWorkspace`, which enables "Run analysis" only when `GET /settings` reports the engine
**and** the page supplies an upload handler. Until then, media stays in browser memory.

Interactive docs: `http://127.0.0.1:8000/docs` (disabled when `APP_ENV=production`).

## 5b. Phase 3 analysis architecture

```
 Browser                                           FastAPI (NumPy only)                 MySQL
 ┌────────────────────────────────────────┐        ┌─────────────────────────────┐      ┌──────────────────┐
 │ Face photo ─► MediaPipe FaceLandmarker │ JSON   │ face.py: EAR, symmetry,     │      │ facial_          │
 │   + faceStats.ts (pixel statistics)    │──────► │ iris size, quality gates    │────► │ measurements     │
 │ Video ─► MediaPipe PoseLandmarker 15fps│ JSON   │ motion.py: speed, frequency,│      │ motion_          │
 │                                        │──────► │ posture, tracking coverage  │────► │ measurements     │
 │ Audio ─► 16 kHz mono WAV (audio.ts)    │ WAV*   │ voice.py: YIN F0, spectral, │      │ voice_           │
 │   *only after per-upload confirmation  │──────► │ MFCC, pauses, SNR (in RAM)  │────► │ measurements     │
 └────────────────────────────────────────┘        └─────────────────────────────┘      └──────────────────┘
                     multimodal-summary: features side by side + quality + missing modalities (no score)
```

* **Raw media:** photos and videos never leave the browser. Audio is uploaded only after an
  explicit confirmation, held in memory for the request, and discarded; it is never written to
  disk, stored in the database or logged.
* **Provenance:** every stored feature is catalogued in `backend/app/analysis/feature_schema.py`
  with label, unit, description, method source and provenance (`server_audio`,
  `server_landmarks`, `browser_pixels`, `browser_model`). The UI shows the provenance next to each value.
* **Validation:** request schemas reject wrong landmark counts, out-of-range coordinates, NaN or
  infinite values, unknown fields, non-increasing timestamps and oversized audio. The extractors
  reject unusable input (silence, too short or long, no pose) with readable messages.
* **No inference:** there is no model, score, probability, confidence, reference range or
  classification.
* **Provenance (migration 0002):** every new measurement stores `feature_schema_version` and
  `extractor_version` (server extractor and expected browser pipeline). Rows created before 0002
  have `extractor_version = NULL` ("not recorded").
* **Saved combined records (`POST/GET /sessions/{id}/integrations`):** `combined_results` rows with
  `mode = 'feature_integration'`. Each holds the latest quality-checked measurement of each consented
  modality of *that session only*, placed in the fixed order `INTEGRATION_FEATURES` (face → motion →
  voice, catalogue order; also published by `GET /analysis/feature-schema`). Every slot carries a
  value or an explicit status (`missing`, `not_consented`, `excluded_low_quality`, `not_measured`).
  The record also stores `source_measurements` (ids, timestamps, versions) and `processing_status`
  (`complete`/`partial`); `indicator_*`, `confidence` and `data_quality` are always NULL. If no
  modality qualifies, the API returns 422 and stores nothing.
* **Server-side support checks:** browser eye-region colour/pupil values are replaced by `null`
  when server-computed geometry shows they cannot be supported (eyes nearly closed, eye < 20 px,
  iris < 30 px for pupil values).
* **Method sources** (definitions only): YIN pitch (de Cheveigné & Kawahara, 2002), MFCC (Davis &
  Mermelstein, 1980), eye aspect ratio (Soukupová & Čech, 2016), MediaPipe Face Mesh (Kartynnik et
  al., 2019), BlazePose (Bazarevsky et al., 2020). Full citations are in `feature_schema.py`.

## 6. Dependency compatibility (verified 2026-10-25)

Python 3.13.9 on Windows x64. Every pinned backend package installed from wheels. Planned Phase 3
packages were checked on PyPI: `mediapipe 1.1.1` (py3 win_amd64 wheel), `librosa 1.0.0`
(pure Python; needs `numba`, which has cp313 wheels), `numpy`, `scikit-learn` and
`opencv` all publish Python 3.13 wheels. Frontend: Node 24.14, Vite 6.4.5, React 19.3,
Tailwind 4.3, TypeScript 5.8; `npm audit` reports 0 vulnerabilities.
