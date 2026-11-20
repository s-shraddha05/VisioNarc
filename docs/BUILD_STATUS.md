# VisoNarc – Build Status

Resume point for future sessions. Update after every batch of work.

| Phase | Scope | Status |
|---|---|---|
| 1 | Environment, setup, database, authentication | **Done**. User confirmed: MySQL set up, admin created, 37 tests passing on MySQL, browser login OK |
| 2 | Complete frontend and dashboard (12 pages) | **Done**. User confirmed working |
| 3 | Face, motion, voice measurements + multimodal summary | **Done**. User verified face, motion and voice with a real webcam and microphone (2026-10-25). Gap pass (provenance, saved records) approved by the user after saving a combined record on a real session |
| 4 | Complete workflows, reports, security, deletion | **Approved by user and committed** (2026-10-25): automated gate re-run before the commit, plus user manual verification |
| 5 | Final testing, documentation, delivery | **In progress**. Dataset audit done (no usable labelled dataset). D1–D4 fixed and committed (`fe8965f`). Verification pass and port options committed (`f10dd35`). Part 2 (downgrade guards, guarded restore, synthetic screening demo, migration 0003) implemented and tested, **uncommitted, awaiting review**. No validated model; numeric output is a synthetic demonstration only |

## Phase 5 – dataset audit, integration defects, verification (2026-10-25/26)

### Status: part 1 committed (`fe8965f`, `f10dd35`); part 2 below is uncommitted and awaiting review

- Baseline: Phase 4 commit `a9bca711926f18e323c68f8fd40fd96cfbfe485f`.
- D1–D4 commit: `fe8965f358bce9e0a8db6ca6488f9c45dcb20d0c` ("Fix Phase 5 integration defects D1-D4"), approved by the user. Not pushed.
- Follow-up commit after `fe8965f` (approved by the user, not pushed): an optional `-Port` parameter for `run_backend.ps1`, and `-Port` / `-BackendOrigin` for `run_frontend.ps1` (defaults unchanged: 8000 / 5173 and the backend address from `frontend\.env`; `-BackendOrigin` accepts only `http(s)://host[:port]`, and the previous `VITE_BACKEND_ORIGIN` is restored on exit), plus the README notes and this record.
- No screening model has been trained or connected. No score or probability is shown anywhere. `RETENTION_AUTO_PURGE` is still off, and `backend\.env` was not modified.

### Dataset audit (read-only)

- The VisoNarc project and its MySQL database have no labels or reference outcomes. The `model_versions` table is empty.
- Old prototype (`Desktop\finalproject`, its backups and the three `Downloads\visionarc*.zip` files). Inspected read-only: database schemas and counts, archive file lists, scripts. No images were opened and no archives extracted.
  - The SQLite databases hold only that prototype's own outputs ("Addict" / "Non-Addict" / "Potential Addict"). They are not independent reference labels, so training on them would be circular.
  - There are no participant IDs and no feature table. `extract_features.py` sets every label to `"baseline"`.
  - `model.h5` is a 224×224 image model with no recorded training data. It doesn't fit the 14-feature schema.
- The project report (`.docx`) mentions an unnamed "Dataset of Facial Images (Abuser vs. Non-Abuser)". It gives no source, no consent and no toxicology confirmation.
- **Conclusion: not ready.** Consent and provenance are unclear. A screening model needs a new, consented dataset with independent reference labels (for example toxicology) and participant IDs, captured with VisoNarc's own extractors.

### D1–D4 fixes (existing defects, committed in `fe8965f`)

| ID | Defect | Fix |
|---|---|---|
| D1 | A combined record's `feature_schema_version` was the current constant, not its inputs' version | Taken from the inputs, or `mixed` when they differ. The website and PDF show "mixed feature schemas (see sources)". Existing records are not rewritten: real record #3 still says 1.1 although its inputs are 1.0 |
| D2 | Every database error said "Check that MySQL is running" | MySQL errors 1045, 1044 and 1049 get their own messages, naming the setting to check (`app/db/errors.py`). Driver text and credentials are never returned |
| D3 | A bad `.env` value printed a long traceback | `scripts/preflight.py`, run by `run_backend.ps1`: one line per problem, naming the setting and where it came from (env var or `.env`), never the value. A malformed `DATABASE_URL` blocks startup. Both run scripts check ports and prerequisites |
| D4 | `latest_indicator_level` was always empty | Removed from the session list API, the CSV export (last column dropped) and frontend types. The database column is unchanged; no migration |

### Automated results (final run, 2026-10-26, working tree as described above)

- `scripts\run_tests.ps1 -MySql`: **163 backend tests passed**, including the read-only MySQL tests. **18/18 frontend tests passed**, none skipped. The production build succeeded.
- `npx tsc -b`: exit 0.
- `pip-audit -r requirements.txt --no-deps --disable-pip`: no known vulnerabilities (it warns that hashes aren't pinned).
- `npm audit`: 0 vulnerabilities.
- Flaky test fixed (test-only). `test_logs_never_contain_media_or_feature_values` failed about 3 times in 11 runs. SQLAlchemy timing notes such as `[cached since 0.2543s ago]` contained short feature values such as `0.25` by chance. Parameters were hidden all along (`hide_parameters`), so this was never a real leak. The test now removes those timing notes from SQLAlchemy log lines before searching, and a simulated real parameter leak is still detected. Afterwards: 0 failures in 15 focused runs, and two full `run_tests.ps1 -MySql` gates passed (163 backend, 18 frontend, build).

### Manual checks completed (by Claude; not yet repeated by the user)

- **Run scripts.**
  - Port conflict: with the user's servers on 8000 and 5173, both scripts stopped with `[FAIL] Port … in use by PID …` and left those servers untouched.
  - Invalid configuration, tested through environment variables in child processes only: a bad `ACCESS_TOKEN_EXPIRE_MINUTES`, a weak JWT secret and a malformed `DATABASE_URL` each gave a single `[FAIL]` line and exit 1. No values were printed.
  - `-Port 80` was rejected with exit 1.
  - Normal startup: the backend on 8001 against the real `.env` returned `ready` `{"status":"ok","database":"ok"}`. The frontend on 5174 served the app and proxied `/api` to 8001. Both were stopped afterwards.
- **D1 website and PDF**, in a disposable environment (a SQLite file in the scratchpad, synthetic data, backend on 8001, frontend on 5174):
  - The mixed record showed "mixed feature schemas (see sources)", with its sources showing v1.0 and v1.1.
  - The current-schema record showed "schema v1.1".
  - The PDFs matched.
  - Nothing was created in the real database.
- **Responsive layout** in the same environment: 12 pages at 375 px and 4 pages at 768 px had no horizontal scroll. The only console error came from a deliberate framing test (X-Frame-Options DENY working).
- **Migration recovery drill.** This used a throwaway MySQL 8.0.44 server (`--no-defaults`, its own data folder, port 3307, synthetic data) and was deleted afterwards. The MySQL80 service was not touched.
  - `alembic upgrade head` and `verify_db`: OK.
  - `backup_db`: OK.
  - A simulated half-applied 0002 (one column already present) made `alembic upgrade` fail with MySQL error 1060. The revision stayed at 0001, and `verify_db` reported FAIL.
  - Recovery by recreating the database and restoring the backup brought every row back and the schema to head. `verify_db`, sign-in and readiness were OK afterwards.
- **Security review.**
  - Only health, readiness and login are public; the other 31 operations require the Bearer token.
  - JWT: algorithm pinned, issuer and claims required, revocation table checked.
  - No secrets or `.env` files in git history; `.env`, backups and `*.db` are git-ignored.
  - No raw SQL built from strings, no `shell=True`, `eval` or unsafe HTML in the frontend.
  - The token is kept in `sessionStorage`.
- **Real database check (read-only).**
  - Row counts are unchanged since the dataset audit, except for one new `auth.login` audit entry at 18:38 UTC, before these checks started.
  - The database is at revision 0002.
  - No purge or deletion entries.

### Findings not yet fixed (no critical or high findings; awaiting user decision)

| Severity | Finding | Proposed action |
|---|---|---|
| Medium (**fixed in part 2**) | `alembic downgrade 0001` deleted all saved combined records without warning | The downgrade now refuses unless `-x allow_data_loss=true` is passed (see part 2) |
| Medium (**fixed in part 2**) | There was no restore script or documented restore procedure | Guarded `scripts/restore_db.py` and README steps (see part 2) |
| Low | Two backend processes were listening on port 8000 at the same time (started hours before these checks). Windows allows it | Stop the older one. The new port check prevents this when using `run_backend.ps1` |
| Low | The unauthenticated login endpoint now says which database setting is wrong. The server only listens on 127.0.0.1 | Acceptable for local use. Keep the generic message if the API is ever exposed beyond this computer |

### Outstanding checks

- The user's own run of `run_backend.ps1` / `run_frontend.ps1`, and the website wording on the user's own data. Real data has no mixed record, and none was created.
- A restore drill on the real MySQL service. Not done, because that would replace the user's data.
- Camera and microphone capture were not re-tested in Phase 5; the D1–D4 changes don't touch capture.

## Phase 5 part 2 – downgrade guards, guarded restore, synthetic screening demo (2026-10-26)

### Status: IMPLEMENTED AND TESTED, UNCOMMITTED, AWAITING USER REVIEW

- Approved by the user: A (downgrade guard and guarded restore, tested on a throwaway MySQL only), B (synthetic demo with migration 0003, off by default, synthetic sessions only), and C (do not integrate the VisionArc model).
- **The numeric estimate is a synthetic demonstration only.** No model was trained, and the VisionArc `model.h5` is not used. Real sessions always show "No reliable estimate available". `SCREENING_MODE` defaults to `off`.

### VisionArc inspection (read-only)

- `model.h5` (12 identical copies): a MobileNetV2 image network on 224×224 RGB images, with Dense(128), Dropout(0.5) and Dense(1, sigmoid), trained with `binary_crossentropy`, saved by Keras 3.13.2. It has no class names, no training-data record and no evaluation record. The correct input preparation is unresolved (`test_model_inference.py` tries three). It doesn't match the report's "DCNN 4096 features + SVM" description.
- The served prototype never loads `model.h5`. Its "Addict / Not Addict" results come from:
  - the uploaded file name (`addict`, `positive`, `symptom`);
  - hand-set thresholds (for example strain > 0.32, sway > 2.5, silence > 0.45, more than 5 pauses);
  - hard-coded confidence values (86.5 / 92.0 %, ranges 76–97.5 %, or 88.0).
- **Conclusion:** the prototype's outputs aren't model predictions and can't serve as labels. The model can't be used without independent provenance and an evaluation. Nothing was reused except the participant-split idea.
- A new search for datasets by file name found no labelled data. The only CSV, `vacant_posts_2026-02-05.csv`, looks unrelated by its name and wasn't opened.

### A. Reliability

| Change | Files |
|---|---|
| 0002 downgrade refuses while saved combined records exist. It names the backup command and the override, and needs exactly `-x allow_data_loss=true` | `alembic/versions/0002_…py` |
| `scripts/restore_db.py`. Dry run by default. `--apply` requires typing the database name and writes a pre-restore backup first, aborting if that fails. It refuses non-mysqldump files, backups of another database and incomplete backups. It drops tables that aren't in the backup and strips `LOCK TABLES` (the app user deliberately lacks that privilege). Credentials go only through a temporary option file | `scripts/restore_db.py`, `scripts/backup_db.py` (shared option-file helper; new backups use `--skip-add-locks`) |
| README: downgrade guard, restore steps, demo instructions, `SCREENING_MODE` | `README.md`, `backend/.env.example` |

### B. Synthetic screening demonstration

- **Migration 0003 (additive)** adds:
  - `analysis_sessions.is_synthetic`, default 0. Only `scripts.seed_synthetic_demo` sets it; the API can't.
  - The new table `screening_results`, which stores: session, combined record, admin, model name and version, status, synthetic flag, target definition, schema version, input measurement IDs, modality status, missing modalities, coverage, estimate, classification, threshold, explanation and limitations.
  - A downgrade that refuses while synthetic data exists; with the override it deletes only synthetic sessions, so they can never become "real".
- **Formula** (`app/analysis/screening.py`): fixed, documented and not learned.
  - It validates feature names, order and schema version (1.1 only), plus numeric and plausible-range checks.
  - Missing modalities stay missing (no zero-filling), and at least 2 of 3 modalities are required.
  - Otherwise the status is `insufficient_input` and no score is produced.
  - Score = sigmoid of a weighted sum; label "Addict" at or above 0.50, otherwise "Non-Addict". Both are shown only as synthetic demo labels.
- **Service and API:** `GET /sessions/{id}/screening` (overview) and `POST /sessions/{id}/screening` (run and save). Running needs `SCREENING_MODE=synthetic_demo`, a synthetic session, consent and a saved combined record. Real sessions get 409 and nothing is stored. The audit log records the result ID and status only.
- **Website:** an "Experimental screening" panel on the Multimodal page, and "Synthetic demo" badges in History and Session detail. **PDF:** a synthetic banner and footer, and an "Experimental screening" section printed from the saved rows. Real sessions show "No reliable estimate is available".
- **Seed script:** `scripts.seed_synthetic_demo --admin <name>` creates three profiles from deterministic synthetic signals through the real extractors. A gives 16.8 % "Non-Addict", B 59.9 % "Addict", and C (face only) "insufficient input". It refuses any database that contains real sessions.
- **Deletion:** consent withdrawal, measurement deletion, session deletion and purge all remove screening results. The SQLite engine now enforces foreign keys, which matters for demo databases.
- Migration 0003's downgrade was first written with explicit `DROP INDEX` statements, which fail on MySQL (error 1553). The throwaway-MySQL drill caught this, and it was fixed before the real upgrade.

### Real database (user data)

- Backup `backend/backups/visonarc-20261025-194253.sql` (46,079 bytes) was taken first, and the restore dry run read it successfully. Then `alembic upgrade head` ran 0002 → 0003, and `verify_db` passed.
- Row counts are identical before and after: admins 1, sessions 3, consent 3, face 3, motion 3, voice 4, combined 2, audit 41. That includes one sign-in at 19:40 UTC that isn't from Claude's tests.
- After the upgrade: 0 synthetic sessions and 0 screening rows. No data was deleted or restored.
- While the new code was in place before the upgrade (about 20 minutes), the user's auto-reloading backend on :8000 returned "database unavailable" for session pages, because the `is_synthetic` column didn't exist yet. It was healthy again after the upgrade.

### Automated results (2026-10-26)

- `scripts\run_tests.ps1 -MySql`: **201 backend tests passed** (MySQL tests included), **18/18 frontend**, build succeeded.
- New tests:
  - 10 migration tests: both guards, overrides, exact-value check, and 0003 upgrade and downgrade;
  - 8 restore tests;
  - 20 screening tests: formula, missing and invalid input, schema versions, off by default, real sessions refused, provenance, consent, withdrawal and deletion cascades, PDF matches the saved row, real-session PDF, and seed refusal.
- `npx tsc -b`: exit 0. `npm audit`: 0 vulnerabilities. `pip-audit -r requirements.txt --no-deps --disable-pip`: exit 0, no known vulnerabilities.

### Manual checks (by Claude)

- **Throwaway MySQL 8.0.44 drill** (port 3307, `--no-defaults`, synthetic rows, deleted afterwards; MySQL80 untouched). All 12 steps passed:
  1. upgrade 0002 → 0003 keeps every row;
  2. the seed script refuses a database with real sessions;
  3. screening is refused for a real session even with demo mode on;
  4. the 0003 guard blocks the downgrade, and its override removes only the synthetic session;
  5. the 0002 guard blocks the downgrade;
  6. the restore dry run is correct;
  7. a wrong typed name means nothing is restored;
  8. a correct name gives a pre-restore backup, rows equal to the backup, and the newer table dropped;
  9. the database upgrades again afterwards.
  The first runs found the `DROP INDEX` and `LOCK TABLES` problems; both were fixed and re-drilled.
- **Demo walkthrough** following the README (SQLite demo DB in the scratchpad, backend :8001, frontend :5174, deleted afterwards):
  - A showed "Non-Addict", B "Addict" (59.9 %), and C "Insufficient evidence: At least 2 of 3 modalities…". The synthetic banner, badges, model version and inputs were all shown.
  - For all three sessions, the PDF showed the same result ID, score, label and model version as the saved result.
  - Layout: no horizontal overflow at 375 px and 768 px.

### Known limitations and remaining risks

- The demo formula's weights are arbitrary. The demo shows the software workflow only and is **not evidence of any predictive ability**.
- A restore that fails part-way can leave the database partly restored, because MySQL can't roll back schema changes. The pre-restore backup is the recovery path. A real-database restore was not exercised.
- Running the seed script twice creates duplicate synthetic profiles (allowed, since everything there is synthetic).
- Not re-tested: camera and microphone capture, and the user's own walkthrough of the demo and of the real-session screening panel.
## Phase 4 – workflows, PDF reports, retention, security (2026-10-25)

### Approval status: APPROVED (user approved committing the completed Phase 4 work)
Evidence is kept in two separate categories.

**Automated results** (run by Claude). The full gate was **re-run immediately before the commit**,
after two cosmetic fixes found during the pre-commit diff review (import order in
`routes/analysis.py`; blank line and final newline in `services/analysis_service.py`). Results of that
re-run: backend 146 passed, 0 skipped (7 MySQL), 1 known warning; frontend 18 passed; typecheck and build
passed; `pip_audit -r requirements.txt` and `-r requirements.lock.txt`: no known vulnerabilities;
`npm audit`: 0. MySQL counts identical before and after the run (sessions 3, consent 3, face 3, motion 3,
voice 4, combined 2, audit 39, including the user's manual-check data); 0 purge or measurement-delete audit
entries; effective `RETENTION_AUTO_PURGE = False`. The table below is the earlier post-implementation run:
| Check | Result |
|---|---|
| `scripts\run_tests.ps1 -MySql`: backend pytest | 146 passed, 0 skipped (7 database-backed against the real MySQL: read-only or always rolled back), 1 known warning (Starlette httpx deprecation) |
| `npm test` (node --test) | 18 passed |
| `tsc -b && vite build` | Passed |
| pip-audit (production pins, full lock) / npm audit (prod, all) | No known vulnerabilities / 0 vulnerabilities. Installed-venv finding limited to the pip 25.2 tool itself |
| Browser checks on throwaway SQLite (Claude) | All pages render; no overflow at 1024/375 px; purge, measurement delete, PDF endpoint and outage/Retry verified |
| MySQL data before/after | Identical counts; 0 purge or measurement-delete audit entries |

**Manual verification by the user** (real browser, real installation, reported 2026-10-25):
| Behaviour | Result reported by user |
|---|---|
| PDF report download and layout | Verified |
| Retention preview (Settings) | Verified |
| Active sign-in revocation | Verified |
| Backend-unavailable recovery (reload → "Cannot reach…" → Retry) | Verified |
| Camera and microphone permission denied messages | Verified |

**Not covered by either:** an actual purge, which was never run on the real database by design, and
automatic purging, which stays off: `RETENTION_AUTO_PURGE` is not set in `backend/.env`, so the code
default `false` applies (confirmed by loading the settings; `.env` not modified).

Approved decisions: ReportLab server PDFs; pytest API workflows plus manual camera/microphone
checks (no Playwright); pip-audit as a development-only tool; no automatic dependency upgrades.
**No commits were made** (user instruction): all Phase 4 changes are uncommitted in the working tree.

### Baseline (before any edit)
Clean tree at `6a461d7` (the Phase 3 approval commit, confirmed as an ancestor of HEAD).
`scripts\run_tests.ps1 -MySql`: 110 backend passed (5 MySQL), 12 frontend passed, build passed;
1 known warning (Starlette httpx deprecation). No baseline failures. MySQL backup
`backend/backups/visonarc-20261025-144222.sql` (34,220 bytes). Baseline counts: admins 1, analysis
sessions 2, consent 2, face 2, motion 2, voice 3, combined 1. No session expired (earliest
retain_until 2027-01-23).

### A. Reliability
* A failed session check on page load is classified by `auth/sessionCheck.ts`: only HTTP 401 signs out.
  Network errors, proxy 5xx and database 503 show "Cannot reach the VisoNarc server" with Retry
  (the token is kept).
* Development hot-reload error fixed at the root: the context object moved to `auth/context.ts` and the
  hook to `auth/useAuth.ts`, so `AuthContext.tsx` exports only a component (React Fast Refresh
  requirement). Verified: editing AuthContext.tsx while the app was open gave
  `[vite] hot updated: /src/auth/AuthContext.tsx` and no "useAuth must be used inside <AuthProvider>".
* Stale state: the capture pages now clear the previous result when the selected session changes.

### B. PDF reports
* `reportlab==5.1.0` (pure-Python wheel, BSD; pulls in pillow 13.0.0 and charset-normalizer 3.5.2,
  all with Python 3.13 Windows wheels; dry-run verified; `pip check` clean).
* `GET /sessions/{id}/report.pdf` (single admin role: any signed-in admin). Contents: title,
  disclaimer, generation metadata, session, consent, every measurement with quality checks, warnings,
  schema and extractor versions and features with provenance, saved combined records with slot statuses and
  inputs, provenance legend, limitations, method sources. No raw media, secrets, score or diagnosis.
  Empty, partial and withdrawn sessions render with explicit "No measurements…" text. Audit
  `session.report_pdf` stores only reference_code and byte size.
* PDF buttons on the Reports rows and the Session page (loading and error states). Capability
  `pdf_reports` is true when ReportLab is importable.

### C. Retention and deletion
* Policy (unchanged): expired = `retain_until < now (UTC)`; NULL is never purged.
* `GET /retention/preview` lists the exact sessions and dependent-record counts. `POST /retention/purge`
  requires `confirm: true` plus the previewed ids, deletes only those still expired, re-checks the
  condition inside the DELETE and rolls back on any mismatch (409). Dependents are removed through
  `ON DELETE CASCADE`. Audit `retention.purged` holds trigger, count and reference codes.
* Automatic purge (startup + every `RETENTION_PURGE_INTERVAL_HOURS`) runs only when
  `RETENTION_AUTO_PURGE=true`; **default off; `backend/.env` was not changed**. Settings shows the
  real state and the last automatic run.
* CLI: `python -m scripts.purge_expired` (dry run) / `--apply` (type PURGE) / `--apply --yes`.
* Individual measurement deletion: `DELETE /sessions/{id}/measurements/{modality}/{mid}` (session-scoped).
  It also deletes saved combined records that used that measurement (they would no longer match stored data);
  the confirmation dialog states how many. Audit `measurement.deleted`.
* Recovery: deletions are permanent; the only recovery is restoring a mysqldump backup
  (`python -m scripts.backup_db`), which restores the whole database to that point in time.

### D. Security and privacy
* Per-IP limit on failed sign-ins (`LOGIN_IP_MAX_FAILURES` within `LOGIN_IP_WINDOW_SECONDS`, default
  20 / 300 s), on top of the per-account lockout. Keyed on the TCP peer address only (X-Forwarded-For
  ignored; a test proves spoofing does not bypass it). Returns 429 with Retry-After before any password check.
  In memory, per process.
* API headers on `/api/*`: `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'`,
  `Cache-Control: no-store`, `Permissions-Policy`, COOP, CORP (plus the existing nosniff, DENY,
  no-referrer). Vite dev/preview send nosniff, DENY, no-referrer and a Permissions-Policy that
  allows camera/microphone for this origin only. No frontend CSP (documented limitation).
* Active sign-ins: the architecture already supports real revocation (each token's `admin_sessions`
  row is checked on every request). Added `GET /auth/sessions`, `POST /auth/sessions/{id}/revoke`,
  `POST /auth/sessions/revoke-others` (own sign-ins only) and an Active sign-ins card in Settings.
* Logs: `create_engine(..., hide_parameters=True)`. Negative control: with SQL logging switched on
  and without this flag a feature value appeared in the log; with it, no value appeared. The test
  enables SQL logging, asserts that SQL statements are logged, and asserts that no raw audio,
  landmarks or feature values appear.
* Audits (development tool `pip-audit==2.10.1`):

| Scope | Command | Result |
|---|---|---|
| Production pins | `pip_audit -r requirements.txt --no-deps --disable-pip` | No known vulnerabilities |
| Full lock (prod + dev) | `pip_audit -r requirements.lock.txt --no-deps --disable-pip` | No known vulnerabilities |
| Installed venv | `pip_audit` | 6 advisories, all in **pip 25.2** itself (installer tool; crafted-archive/path issues during installs; not used at runtime). Fix: upgrade pip to ≥ 26.2. **Not upgraded automatically** |
| Frontend production | `npm audit --omit=dev` | 0 vulnerabilities |
| Frontend all | `npm audit` | 0 vulnerabilities |

### E. Workflow and failure tests
* `tests/test_workflow_e2e.py`: sign-in → session and consent → face, motion and voice (synthetic
  fixtures) → detail → combined record (14 slots) → summary → history, JSON, CSV and PDF → consent
  withdrawal → ordered audit trail → sign-out (token rejected) → sign-in again.
* `tests/test_db_unavailable.py` uses a real connection failure. Route behaviour: `/health` 200 (no DB);
  `/health/ready` 503; login 503 (not "wrong password"); every authenticated route 503 with a
  signature-valid token; invalid or missing token 401 without touching the database.
* Frontend `node --test`: session-check classification (3), camera/microphone error messages (3).
* MySQL (real DB, safe): retention preview finds an expired **test** row inserted inside a transaction
  that is always rolled back; PDF built in memory from an existing session (read-only). Purge is never
  called against MySQL. Side effect: InnoDB does not reuse auto-increment ids, so the rolled-back
  insert leaves a harmless gap in future session ids.
* Browser (throwaway SQLite on :8010, frontend on :5180; generated test admin): sign-in via the
  form; all 12 pages plus not-found render without errors. **Fixed two overflow bugs found here:**
  /history (screen-reader-only header escaping the scroll container, from Phase 2) and /settings (long
  user-agent strings stretching the grid). After the fix: no overflow at 1024 px or 375 px. Retention preview
  listed exactly the expired smoke session; purge needed typed PURGE and deleted only it.
  Measurement delete confirmed its dependent-record count and removed both. The PDF endpoint
  returned a 29.6 KB `application/pdf`. Backend stopped plus a real reload showed "Cannot reach the VisoNarc
  server" with the token kept; Retry after restart returned to the page without signing in again.
* Not verified here: visual layout of the PDF (no renderer available; a synthetic sample PDF is provided
  for review), real camera and microphone permission prompts (manual check listed below).

### Final gate (after all changes)
`scripts\run_tests.ps1 -MySql`: **146 backend passed, 0 skipped** (including 7 MySQL), 1 known warning;
**18 frontend passed**; TypeScript and production build passed. Encoding scan: 0 garbled characters.
MySQL after: admins 1, sessions 2, consent 2, face 2, motion 2, voice 3, combined 1, revision 0002;
0 purge or measurement-delete audit entries. **Identical to the baseline.**

### Known issues / limitations
* pip 25.2 advisories (tooling only); upgrade pip when convenient: `python -m pip install --upgrade pip`.
* The rate limiter is in memory: it resets on backend restart and is not shared across multiple workers.
* No frontend Content-Security-Policy (MediaPipe WebAssembly and Vite dev need careful allowances).
* Sign-out while the backend is down clears the tab's token, but the server-side token stays valid
  until it expires (60 min).
* PDF visual layout is only checked by content tests; please review the sample.

### Manual verification steps for the user
1. Restart the backend so it loads the Phase 4 code (`scripts\run_backend.ps1`); no migration is needed.
2. Session page → **PDF report** on a real session; open the PDF and check the layout.
3. Settings → **Preview expired sessions** (expect none: your sessions retain until 2027) and
   **Active sign-ins** (revoke another tab's sign-in and confirm that tab is signed out).
4. Stop the backend, reload a page: expect "Cannot reach the VisoNarc server"; start it, click Retry.
5. In Chrome/Edge, block camera access for 127.0.0.1:5173 in site settings, open Face analysis → Webcam
   → Start camera: expect "Permission was denied…". Repeat for the microphone on Voice analysis.
6. Optional: `python -m scripts.purge_expired` (dry run; lists nothing to purge today).

## Phase 3 gap pass – provenance and saved combined records (2026-10-25)

### Audit (before changes)
Clean tree at `9d705be`. `scripts\run_tests.ps1 -MySql` gave 99 backend + 9 frontend tests passing
and the build passing. Versions: NumPy 2.5.4, FastAPI 0.162.0, SQLAlchemy 2.1.6, Alembic 1.20.1,
@mediapipe/tasks-vision 1.1.0 (unchanged; nothing installed). MySQL had 2 sessions,
7 measurements (2 face, 2 motion, 3 voice) and 0 combined results, at revision 0001.

Verified gaps: (G1) no extractor/algorithm version stored with measurements; (G2) combined analysis
not persisted, and `combined_results` could not hold a score-free record; (G3) the server accepted
browser eye-region values that its own geometry shows are unsupported; (G4) motion frames used the
requested seek time instead of the decoded frame time; (G5) no defined integration feature order and
no session-isolation or reproducibility tests.

### Changes
* **Migration `0002`** (additive): `extractor_version` on the three measurement tables (existing rows
  stay NULL = "not recorded"; nothing back-filled). `combined_results` gains `processing_status`,
  `feature_schema_version`, `extractor_version`, `features`, `source_measurements`; `indicator_level`
  becomes nullable; mode `feature_integration` is allowed. The downgrade removes feature-integration rows.
* **Extractor versions:** `face/1.1.0+mp-tasks-vision-1.1.0+face_landmarker-f16v1`,
  `motion/1.1.0+mp-tasks-vision-1.1.0+pose_lite-f16v1@15fps`, `voice/1.0.0+numpy-yin-mfcc@16kHz-mono-pcm16`.
  Feature schema `1.1` (same keys and units; see changelog in `feature_schema.py`).
* **Face (server):** withholds browser eye-region colour and pupil values when the eyes are nearly
  closed or the eye is < 20 px wide; withholds pupil values when the server-computed iris is < 30 px.
  A warning explains each case.
* **Motion (browser):** frame timestamps come from the decoded frame (`video.currentTime`), and
  repeated frames are skipped (`lib/frameTimes.ts`).
* **Saved combined records:** `POST/GET /sessions/{id}/integrations`. The record holds the latest
  quality-checked measurement per consented modality, in the fixed order `INTEGRATION_FEATURES`
  (face → motion → voice, catalogue order). Every slot is always present with its value or status
  (`measured`, `not_measured`, `missing`, `not_consented`, `excluded_low_quality`); absent values are
  `null`, never zero. `processing_status` is `complete` or `partial`. `indicator_*`, `confidence` and
  `data_quality` are always NULL. If no modality qualifies, the API returns 422 "Insufficient data…"
  and nothing is saved. Audit: `analysis.integration_recorded` (ids and status only).
* **Frontend:** a "Saved combined records" card on the Multimodal page (save, list, per-slot status,
  input versions); extractor version shown next to each measurement; types updated.
* **Ops:** `python -m scripts.backup_db` (mysqldump via a temporary option file; output in git-ignored
  `backend/backups/`).

### Commands run and results
| Command | Result |
|---|---|
| `python -m scripts.backup_db` | 27,944-byte dump; data present for sessions, all 3 measurement tables and alembic_version |
| `alembic upgrade head` (MySQL) | 0001 → 0002 applied. Afterwards: same counts (2 / 2 / 2 / 3 / 0), the 7 old measurements have `extractor_version` NULL, new columns and CHECK constraints present; `scripts.verify_db` all OK |
| `scripts\run_tests.ps1 -MySql` | **110 backend passed** (5 MySQL, including a rolled-back insert that MySQL accepts for a feature-integration row and rejects for an invalid mode; 0 rows left), **12 frontend passed**, build passed |
| Browser (throwaway SQLite on :8010 and frontend on :5180) | Voice upload saved with extractor + schema 1.1. "Save combined record" created a Partial record: 14 slots in order, face "Modality missing" with "—", voice measured, input versions listed. A session with no measurements shows the "Insufficient data…" message, nothing saved, and the button usable again. The motion pipeline with the new frame times runs to the expected "person detected in fewer than 10 frames" message on a synthetic clip |

New tests: migration data preservation; server eye-value withholding (closed eyes, 19 px iris, tiny
face); face determinism; extractor versions persisted; 7 integration tests (auth, complete/ordered/
reproducible, partial keeps missing as null, low-quality exclusion and insufficient-data 422,
cross-session isolation, consent withdrawal and lifecycle, schema exposes versions and order); MySQL
constraint test; 3 frame-time tests.

### Known issues / limitations
* Development only: after a hot reload (HMR) of modules imported by `AuthContext.tsx`, React can raise
  "useAuth must be used inside <AuthProvider>" until the page is reloaded. Normal page loads are not
  affected. Splitting the context into its own module would remove it (not done: the auth code works).
* Existing measurements from before 0002 show "extractor version not recorded".
* Saved records copy measured values only; there is still no model, training data, score or reference range.
* Reloading a page while the backend is down still signs you out (pre-existing).

### Next step
User reviews this gap pass (restart the backend so it uses schema 0002, then try "Save combined record"
on a session with real measurements). Phase 4 starts only after explicit approval.

## Fix – "Run voice analysis does nothing" (2026-10-25)

**Symptom:** after recording and ticking the upload confirmation, clicking the button did nothing:
no progress, no network request, and a temporary `console.log` in the click handler never printed.

**Investigation:**
* `git diff` showed the diagnostic was saved in the correct file (`ModalityWorkspace.tsx`), and a
  disk search found no other copy of the project, so the dev server was serving this code.
* Reproduced the microphone path in the browser (synthetic microphone stream → real MediaRecorder →
  preview → tick → click). With a session selected, the handler ran, the diagnostic printed and
  `POST /sessions/1/analysis/voice` returned **201**. The conversion, API call and backend all work.
* Reproduced the symptom: with **no session selected** (opening Voice from the sidebar drops
  `?session=`), the button was `disabled` (opacity 0.5, `pointer-events: none`). A disabled button
  fires no click handler, hence no log and no request.

**Root cause:** `canAnalyze` silently required six conditions (capabilities loaded, engine
available, session selected, session active with voice consent, media captured, confirmation
ticked), but only "capture first" was explained near the button. A missing session had no message at
all; an inactive or unconsented session showed only in step 1; capabilities that failed to load
while the backend was down stayed failed with no retry. Separately, when the backend is stopped the
Vite dev proxy answers with an **empty-bodied HTTP 500** (the `ECONNREFUSED` in the Vite log), which
the UI showed as "Request failed (HTTP 500)" instead of "cannot reach server".

**Fix (minimal):**
* `frontend/src/lib/analyzeReadiness.ts` (new, pure): lists every reason analysis cannot start.
* `ModalityWorkspace.tsx`: `canAnalyze` comes from that list, and the reasons appear under the button
  ("Not ready yet: …"). Retry button when server capabilities fail to load. The temporary
  `console.log` is replaced by a development-only trace that never logs media or feature values.
* `lib/api.ts`: an empty-bodied 5xx or a 502/504 is reported as "Cannot reach the VisoNarc server…
  (scripts\run_backend.ps1)".
* `lib/audio.ts`: readable errors for empty or unconvertible recordings; `encodeWav` exported for tests.
* The consent requirement is unchanged: the box must be ticked before every upload, and the server still
  requires `upload_consent=true`. Face/Motion behaviour is unchanged apart from the same explanations.

**Tests:** `npm test` (new, Node built-in runner, no new dependencies): 7 readiness tests + WAV
header test + an end-to-end test that feeds the frontend encoder's WAV into the real backend
extractor (F0 220 Hz, reliable). `scripts\run_tests.ps1 -MySql`: 99 backend passed, 9 frontend passed,
build passed. Browser: the reasons update live (no session → select → tick); success shows progress
immediately and saves a measurement; with the backend stopped mid-session the message is "Cannot reach the
VisoNarc server…" and the button is usable again.

**Not fixed (pre-existing, out of scope):** reloading any page while the backend is down signs you
out, because the startup session check treats an unreachable server as an invalid token.

## Phase 3 – 2026-10-25

### Decisions (approved by user)
* Hybrid architecture: MediaPipe Tasks Vision runs **in the browser** for face and pose landmarks;
  the backend computes measurements with **NumPy only**.
* **No combined score, index, probability, classification or diagnosis.** The multimodal page is a
  side-by-side summary of measured features, data quality, missing modalities and limitations.
  The `combined_results` table stays unused (schema unchanged).
* No population reference ranges. Quality gates are labelled as unvalidated engineering thresholds.

### Dependency and disk checks (run before installing)
| Item | Verified | Disk |
|---|---|---|
| `numpy==2.5.4` | Python 3.13 Windows x64 wheel (`cp313-cp313-win_amd64`), no extra dependencies (pip dry run) | +51 MB (installed with `--no-cache-dir`) |
| `@mediapipe/tasks-vision@1.1.0` | Apache-2.0, no dependencies, released 2026-10-06 | +40 MB `node_modules` |
| WebAssembly runtime copied to `frontend/public/mediapipe/wasm` | SIMD and non-SIMD builds only | +25 MB |
| `face_landmarker.task`, `pose_landmarker_lite.task` | Official MediaPipe storage, sizes match the HEAD check (3.6 / 5.5 MB), SHA-256 pinned in `scripts/setup_mediapipe.ps1` | +9 MB |
| Full Python stack (rejected) | MediaPipe + OpenCV-contrib + librosa + SciPy would need about 555 MB installed (measured from wheel listings) | not installed |

Free space was 0.838 GB before installing. The project grew by about 160 MB, but free space fell
to **0.24 GB**, because something outside the project keeps growing (OneDrive's local log folder is
861 MB). See Known issues.

### Implemented
Backend (new): `app/analysis/{common,feature_schema,voice,face,motion}.py`,
`app/schemas/analysis.py`, `app/services/analysis_service.py`, `app/api/routes/analysis.py`;
tests `tests/{analysis_fixtures,test_voice_features,test_face_motion_features,test_analysis_api}.py`.
Backend (modified): `app/main.py` (routers), `app/api/routes/settings.py` (capabilities depend on
whether NumPy is installed), `requirements.txt` / `requirements.lock.txt` (NumPy),
`tests/test_dashboard_audit_settings.py` (capability expectations updated for Phase 3).
Frontend (new): `lib/{vision,faceStats,audio,pose}.ts`, `components/analysis/FeatureTable.tsx`.
Frontend (modified): `components/capture/ModalityWorkspace.tsx`, the Face/Motion/Voice pages,
`pages/analysis/MultimodalPage.tsx`, `pages/records/SessionDetailPage.tsx`,
`pages/system/SettingsPage.tsx` (label), `lib/{api,types}.ts`, `package.json`.
Scripts and config: `scripts/setup_mediapipe.ps1`, `.gitignore` (`frontend/public/mediapipe/`).

### API endpoints added
| Method | Path | Notes |
|---|---|---|
| POST | `/sessions/{id}/analysis/face` | JSON: 478 landmarks, browser pixel stats, expression coefficients; strict range validation |
| POST | `/sessions/{id}/analysis/motion` | JSON: ≤ 1200 frames × 33 pose landmarks; timestamps must increase; 5–60 s |
| POST | `/sessions/{id}/analysis/voice?source=…&upload_consent=true` | Raw `audio/wav` body, 16 kHz mono 16-bit, ≤ 4 MB. Read into memory, never written to disk, stored or logged. `upload_consent=true` required |
| GET | `/sessions/{id}/multimodal-summary` | Key features per modality, status, quality, warnings, limitations, method sources. **No score fields** (enforced by test) |
| POST | `/sessions/{id}/complete` | Requires an active session with ≥ 1 measurement |
| GET | `/analysis/feature-schema` | Feature catalogue: label, unit, provenance, description, method source |

Every capture endpoint checks: session exists (404), consent recorded and not withdrawn (403/409),
consent covers the modality (403), and the session is active (409). Audit entries
`analysis.{face,motion,voice}_measured` contain only the measurement id and the quality-check result.

### Verification (commands run, results observed)
| Check | Result |
|---|---|
| `scripts\run_tests.ps1 -MySql` | **99 passed** (41 new for Phase 3; 4 are read-only MySQL checks). One Phase 2 test changed: the expected capabilities are now available |
| Unit tests with synthetic signals | Pitch matches 110/220/330 Hz tones within 2 %. Pause count and length are correct. Clipping, noise, silence, wrong format, too short/long and oversized inputs are rejected. Eye aspect ratio 0.25, symmetry 1.0, and 0.9556 for a known offset (matches the hand calculation). Motion frequency matches 0.5/2/4 Hz, shoulder tilt 10° is measured, patchy tracking is flagged |
| `npm run build` | Passed. MediaPipe is a separate on-demand chunk (156 kB) |
| Browser test (throwaway SQLite on :8010 and frontend on :5180; MySQL not touched) | **Voice:** generated 44.1 kHz stereo test tone, converted in the browser, uploaded only after the confirmation tick, measured pitch 180 Hz (generated at 180 Hz), 1 pause of 0.58 s (0.6 s inserted). The confirmation resets after each upload. **Face:** MediaPipe loaded and ran in the browser. A gradient image gives "No face was detected". A drawn cartoon face gave landmarks, symmetry 0.969 and a head-turn proxy of 0.02, and pupil "not measured" (iris 29 px < 30 px threshold). **Motion:** a synthetic 6 s WebM (no person) was tracked frame by frame with progress, and the clear "person detected in fewer than 10 frames" message appeared. **Summary:** face and voice measured, motion excluded, limitations and sources shown, no score. Mark complete set the status to Completed and removed capture links. Audit details contain only the id and the quality-check result. No horizontal overflow at 375 px |
| User verification | Face and motion analysis confirmed working by the user with a real webcam. Voice confirmed with a real microphone after the disabled-button fix (see "Fix" section) |

### Known issues and limitations
* **Disk space is critical: 0.24 GB free on C: and still falling** from activity outside the
  project (OneDrive's local logs are 861 MB). Builds crashed at 0.18 GB in Phase 2. Free space before
  Phase 4: move the project out of OneDrive (for example `C:\dev\VisoNarc`) or pause OneDrive, and
  clear OneDrive logs/temp files.
* Face pixel statistics and expression coefficients are computed in the browser. The server checks
  their ranges but cannot verify them (they are labelled "Browser · pixels/model").
* Pupil-region measurements need the iris to be at least 30 px wide; webcam photos often fall short.
* The motion clip is sampled by seeking, so long recorded WebM files can take about as long as the clip to process.
* No trained model and no reference ranges, by design (see limitations in the app and in `feature_schema.py`).
* An encoding bug introduced during this phase (PowerShell 5.1 reading UTF-8 as ANSI) garbled
  characters in two frontend files. It was found in the browser test and fixed, and a repository-wide
  search now finds no garbled characters.

### Next steps
1. User restarts the backend and frontend, runs `scripts\setup_mediapipe.ps1` if
   `frontend\public\mediapipe` is missing, and tests the face, motion and voice pages with a real
   webcam and microphone.
2. After the user verifies Phase 3 → Phase 4 (reports, retention enforcement, final security
   review). Free disk space first.

## Phase 2 – 2026-10-25

### Result
All in-scope work is implemented and verified (see "Verification" below). Git commits:
`14f276b` (Phase 1 baseline), `76b7b9c` (Phase 2 backend), plus the Phase 2 frontend commit.

### Routes and real API integrations
| Route | Page | Backend endpoints used |
|---|---|---|
| `/login` | Admin login (unchanged from Phase 1) | `POST /auth/login` |
| `/` | Dashboard: totals, 14-day trend, status breakdown, recent activity, health | `GET /dashboard/summary`, `/health/ready`, `/health/details` |
| `/analysis/new` | New analysis and consent form (consent v1.0) | `GET /settings`, `POST /sessions` |
| `/analysis/face` | Upload or webcam photo, validation, preview, stored measurements | `GET /sessions`, `GET /sessions/{id}`, `GET /settings` |
| `/analysis/motion` | Webcam recording or video upload, validation, preview | same as face |
| `/analysis/voice` | Microphone recording with live level meter or audio upload, playback | same as face |
| `/analysis/combined` | Per-session modality readiness from real measurements | `GET /sessions`, `GET /sessions/{id}`, `GET /settings` |
| `/history` | Search, status/date filters (kept in the URL), pagination, CSV export | `GET /sessions`, `GET /sessions/export.csv` |
| `/history/:id` | Session detail, consent, measurements, results, JSON export, withdraw, delete | `GET /sessions/{id}`, `/export`, `POST /withdraw-consent`, `DELETE` |
| `/reports` | CSV export and per-session JSON records; PDF shown as unavailable | `GET /sessions`, export endpoints, `GET /settings` |
| `/audit` | Paginated audit log with event-type and date filters, expandable details | `GET /audit-logs`, `GET /audit-logs/actions` |
| `/diagnostics` | API, database, migration and browser capture capability checks | `GET /health`, `/health/ready`, `/health/details` |
| `/settings` | Profile name, password change, read-only privacy/security/capabilities | `PATCH /auth/me`, `POST /auth/change-password`, `GET /settings` |
| `*` | Not-found page inside the shell; `RouteErrorPage` for render errors | — |

### Files
Backend (new): `app/api/routes/{sessions,dashboard,audit_logs,settings}.py`,
`app/schemas/{sessions,dashboard}.py`, `app/services/session_service.py`,
`tests/test_sessions.py`, `tests/test_dashboard_audit_settings.py`.
Backend (modified): `app/main.py` (routers), `app/api/routes/auth.py` + `app/schemas/auth.py`
(`PATCH /auth/me`), `app/schemas/common.py` (`Page[T]`), `tests/test_mysql_integration.py`
(read-only MySQL run of the new queries).
Frontend (new): `components/layout/{AppShell,nav}`, `components/common/*`,
`components/capture/*`, `components/sessions/*`, `components/ui/{badge,form-controls,skeleton,confirm-dialog}`,
`hooks/{useApi,useMediaStream,useDocumentTitle}`, `lib/{format,consent,media}.ts`, and every page
under `pages/analysis`, `pages/records` and `pages/system`, plus `NotFoundPage` and `RouteErrorPage`.
Frontend (modified): `App.tsx` (data router), `lib/api.ts`, `lib/types.ts`, `index.css`,
`auth/AuthContext.tsx` (adds `setAdmin` only; login/logout unchanged), `pages/DashboardPage.tsx`,
`vite.config.ts` (vendor chunks).

### Verification (commands run and observed results)
| Check | Result |
|---|---|
| `scripts\run_tests.ps1 -MySql` | **58 passed** (20 new). Includes 4 read-only MySQL checks against the real `visonarc` DB that execute the new list/search/dashboard/audit queries |
| `npm run build` (tsc + vite) | Passed. Main bundle 374 kB (110 kB gzip); charts and vendor code are split into separate chunks |
| Browser test (throwaway SQLite backend on :8010 and frontend on :5180, generated test admin; MySQL not touched) | Unauthenticated visit redirects to login. Login opens the dashboard with real zero counts. The new-session form shows every validation message, and a valid submit creates the session and opens its detail page. On the face page, uploads of a 100×100 image and of a .txt file are rejected with clear messages, a 640×480 image shows a preview, and Analyse stays disabled with an explanation. The motion page warns when the session has no motion consent. History search updates the URL and shows the empty state. The CSV endpoint returns the expected header. Consent withdrawal through the dialog cancels the session and disables capture. Delete stays disabled until the reference code is typed, then deletes. A deleted session URL shows "not found". The audit page lists the real events. A token revoked on the server redirects to login. Every page has no horizontal overflow at 375 px, and the mobile drawer opens and navigates. The console showed only the expected 401/404 network responses from these tests. |
| Not verified | Live webcam and microphone capture: the test browser blocks camera/mic permission (the Diagnostics page reports "Blocked"). Please test them in Chrome or Edge on localhost. |

### Known limitations
* Analysis engines are not implemented (Phase 3), so all "Run analysis" buttons are disabled and
  explain why. Captured media is never uploaded or stored.
* Retention dates are recorded, but automatic deletion is not enforced yet (Phase 4). Delete
  manually from the session page.
* Settings are read-only in the UI. Values come from `backend/.env`.
* **Disk space:** C: had dropped to 0.18 GB free, which made builds crash (Node out of memory /
  page file). With the user's approval the npm and pip caches were cleared (now 0.87 GB free).
  Phase 3 needs about 1.5 GB for the AI libraries, so more space must be freed first.

### Next steps
1. User restarts the backend and frontend and checks the new pages, especially webcam and
   microphone capture in a normal browser.
2. After the user confirms → Phase 3: free disk space, install the AI requirements, implement
   face/motion/voice feature extraction and upload endpoints with server-side validation, then
   enable the `capabilities` flags and wire `onAnalyze` in `ModalityWorkspace`.

### Findings from inspection (before any Phase 2 edits)
* Git baseline commit `14f276b` was created (local repository; `.env` files are git-ignored).
* Frontend routes: `/login` and `/` (the Phase 1 status dashboard) only.
* Backend endpoints: `/health`, `/health/ready`, `/health/details`, `/auth/login`, `/auth/logout`,
  `/auth/me` and `/auth/change-password`.
* The schema already has every Phase 2 table (sessions, consent, measurements, results, audit
  logs, settings), so **no migration is needed**. But there were **no endpoints** to create, list,
  view, export or delete analysis sessions, read audit logs, get dashboard statistics or read
  settings. Without them the History, Dashboard and Audit pages would have no real data.

### Scope (as planned before implementation)
Backend additions (authenticated, audited, tested; no schema change):
* `POST/GET /sessions`, `GET /sessions/{id}`, `GET /sessions/{id}/export`,
  `GET /sessions/export.csv`, `POST /sessions/{id}/withdraw-consent`, `DELETE /sessions/{id}`
* `GET /dashboard/summary` (real counts and per-day trend), `GET /audit-logs`,
  `GET /audit-logs/actions`, `GET /settings` (effective policy + capability flags),
  `PATCH /auth/me` (profile name)

Frontend: app shell with responsive sidebar, plus Dashboard, New Analysis & Consent, Face, Motion,
Voice, Multimodal, History, Session Detail, Reports, Settings, Diagnostics, Audit, Not Found and
route-error pages.

Out of scope (Phase 3): the face, motion and voice analysis engines and fusion. Capture pages
collect media only in the browser, and the Analyse buttons stay disabled until the
`capabilities` flags in `GET /settings` report the engines as available.

## Phase 1 – 2026-10-25

### Environment (verified)
Windows 11 · Python 3.13.9 · Node 24.14.0 · npm 11.10.1 · Git 2.49.0 · MySQL 8.0.44 (service
`MySQL80` running). Project at `C:\Users\Shraddha\OneDrive\Desktop\VisioNarc` (the master prompt
named `C:\Users\hp\Desktop\DrugSenseAI`, but the user chose to build in this folder).

### Completed
* `scripts/`: `check_env.ps1`, `bootstrap.ps1`, `setup_mysql.ps1`, `run_backend.ps1`,
  `run_frontend.ps1`, `run_tests.ps1`.
* Backend: FastAPI app factory, env-based settings, bcrypt + JWT auth with server-side session
  revocation, lockout, audit logging, health/readiness/diagnostics endpoints, DB-outage handler
  (503), security headers.
* Database: full relational schema (11 tables) and Alembic migration `0001_initial_schema`
  (autogenerated from the models, then verified by a test against them).
* CLI: `scripts.create_admin`, `scripts.reset_admin_password`, `scripts.verify_db`.
* Frontend: Vite + React + TS + Tailwind 4 + shadcn-style UI, Axios client with token handling,
  AuthContext, ProtectedRoute, branded login page, Phase 1 dashboard showing live diagnostics.
* Docs: `README.md`, `docs/ARCHITECTURE.md`, this file.

### Commands executed and results
| Command | Result |
|---|---|
| `scripts\check_env.ps1` | All tools OK. **FAIL: 1.9 GB free on C:**; WARN: project is inside OneDrive |
| `scripts\bootstrap.ps1` | Succeeded: created `backend\.env` with a random JWT secret, venv, npm ci |
| `pytest` (backend) | **34 passed**, 3 skipped (the MySQL checks are opt-in) |
| `npm run build` | tsc + vite build succeeded (366 kB JS, 119 kB gzip) |
| `npm audit` | 0 vulnerabilities (after moving to react-router-dom 7.18.4 and vite 6.4.5) |
| Browser smoke test (throwaway SQLite DB, generated test admin) | Login page renders. Wrong password shows the generic error. Correct login opens the dashboard with live diagnostics. Sign-out clears the token, and `/` redirects to `/login`. No horizontal scroll at 375 px. Smoke data was deleted afterwards. |
| `scripts\setup_mysql.ps1` | **Not run yet**: it needs the MySQL root password, which only the user can enter |

### Known issues / notes
* **Disk space:** only 1.9 GB is free on C:. The Phase 3 AI libraries need about 1.5 GB more.
  Free some space first. Clearing the pip and npm download caches (`pip cache purge`,
  `npm cache clean --force`) is a safe start.
* The project is inside OneDrive. Pause syncing if npm or pip hit `EPERM`/`EBUSY` errors.
* Starlette prints a deprecation warning about `httpx` in the TestClient. It is harmless, and the
  tests pass.
* Recharts 3, lucide-react 0.511 and TypeScript 5.8 are pinned on purpose. Vite 7/8 and TS 7
  are newer major versions and were not adopted.

### Next action
1. User runs `scripts\setup_mysql.ps1`, `scripts.create_admin` and
   `scripts\run_tests.ps1 -MySql`, then signs in at http://127.0.0.1:5173.
2. After the user confirms → Phase 2 (all 12 pages, sidebar layout, real dashboard stats,
   System Settings with change password, Health & Diagnostics page).
