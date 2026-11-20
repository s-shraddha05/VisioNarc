# VisoNarc – Drug Detection Using Voice and Motion

Final-year B.Tech CSE project: an experimental multimodal behavioural-analysis dashboard that
extracts facial, body-motion and voice features and combines them into a transparent,
quality-aware indicator.

> **Scientific limitation.** Facial appearance, voice and movement cannot reliably prove drug
> consumption. VisoNarc is an experimental academic system, **not** a medical or forensic
> diagnostic tool, and never labels a person as a drug user.

**Status:** Phase 5 in progress (reliability fixes, guarded restore, synthetic screening demonstration).
There is no validated screening model – see [docs/BUILD_STATUS.md](docs/BUILD_STATUS.md).
Architecture, schema and API: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Stack

React 19 + Vite 6 + TypeScript · Tailwind CSS 4 + shadcn/ui · React Router · Axios · Recharts · Lucide
FastAPI · Pydantic 2 · SQLAlchemy 2.1 · Alembic · Uvicorn · MySQL 8 · bcrypt · PyJWT
Phase 3: OpenCV · MediaPipe · Librosa · NumPy/pandas · scikit-learn

## Requirements

Windows 10/11, Python ≥ 3.11 (tested 3.13.9), Node.js ≥ 20 (tested 24.14), MySQL 8 running as a
Windows service, ~1 GB free disk for Phase 1 (another ~1.5 GB for Phase 3 AI libraries).

## First-time setup

Run from the project root in PowerShell:

```powershell
# 1. Check the environment (read-only)
powershell -ExecutionPolicy Bypass -File .\scripts\check_env.ps1

# 2. Create .env files, Python venv and node_modules (idempotent)
powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1

# 3. Create the MySQL database + app user and run migrations (asks for the MySQL root password)
powershell -ExecutionPolicy Bypass -File .\scripts\setup_mysql.ps1

# 4. Create the first administrator (password typed at a hidden prompt)
cd backend
.\.venv\Scripts\python.exe -m scripts.create_admin --username admin --full-name "Project Admin"
cd ..

# 5. Install the browser-side MediaPipe runtime + models (~35 MB, checksums verified)
powershell -ExecutionPolicy Bypass -File .\scripts\setup_mediapipe.ps1
```

### Phase 3 analysis: what runs where

| Modality | In the browser | Sent to the server | Stored |
|---|---|---|---|
| Face | MediaPipe face landmarks; pixel statistics | Landmarks and numbers only (the photo never leaves the browser) | Numeric features |
| Motion | MediaPipe pose landmarks at 15 fps | Landmark coordinates only (the video never leaves the browser) | Numeric features |
| Voice | Conversion to 16 kHz mono WAV | The WAV, **only after an explicit per-upload confirmation**; processed in memory, never written to disk or logged | Numeric features |

VisoNarc reports measurements only. It never produces a score, probability or classification, and
the measurements cannot establish drug use.

## Running

Two terminals:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_backend.ps1    # http://127.0.0.1:8000  (API docs: /docs)
powershell -ExecutionPolicy Bypass -File .\scripts\run_frontend.ps1   # http://127.0.0.1:5173
```

Open http://127.0.0.1:5173 and sign in.

Both scripts check prerequisites and their port first, and stop with one `[FAIL]` line if something is
missing or the port is taken; `run_backend.ps1` also validates `backend\.env` without printing values.
Both parameters are optional (defaults: ports 8000 / 5173, backend address from `frontend\.env`). To
run a second copy without stopping the first, use other ports:
`run_backend.ps1 -Port 8001` and `run_frontend.ps1 -Port 5174 -BackendOrigin http://127.0.0.1:8001`.

## Tests

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_tests.ps1          # backend pytest + frontend build
powershell -ExecutionPolicy Bypass -File .\scripts\run_tests.ps1 -MySql   # + read-only checks on real MySQL
```

Backend tests use an in-memory SQLite database, so they never touch your MySQL data.

## Database backups and migrations

Before applying a new migration, back up the database (the output folder is git-ignored):

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.backup_db
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.verify_db
cd ..
```

**Downgrades refuse to delete data.** `alembic downgrade` stops with a message, and changes
nothing, when it would delete saved combined records (0002 → 0001) or synthetic demo sessions and
screening results (0003 → 0002). Only if that loss is intended: back up first, then add
`-x allow_data_loss=true` (for example `alembic -x allow_data_loss=true downgrade 0002`).

### Restoring a backup

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.restore_db backups\visonarc-<timestamp>.sql           # dry run
.\.venv\Scripts\python.exe -m scripts.restore_db backups\visonarc-<timestamp>.sql --apply   # restore
.\.venv\Scripts\python.exe -m alembic upgrade head   # if the backup is from an older migration
.\.venv\Scripts\python.exe -m scripts.verify_db
cd ..
```

The dry run shows the target database, the tables that will be replaced or dropped and the
migration revisions, and changes nothing. `--apply` asks you to type the database name and writes
a fresh backup of the current database before replacing anything. Restoring makes the database
match the backup, so tables that are not in the backup are dropped (they remain in that fresh
backup). Stop the backend first. MySQL cannot roll back table changes, so if a restore fails
part-way, restore the fresh pre-restore backup the same way.

## Synthetic screening demonstration

VisoNarc has **no trained or validated screening model**: no labelled dataset with independent
reference outcomes is available. Real sessions therefore always show *No reliable estimate
available*. For demonstrations only, a fixed, hand-set formula (`backend/app/analysis/screening.py`)
can score **synthetic** sessions. Its percentage and its "Addict" / "Non-Addict" labels are
illustrative outputs, not probabilities or findings about any person.

The demo runs on a **separate demo database**; the seed script refuses a database that contains
real sessions. Example with a throwaway SQLite file, in one PowerShell window (the variables only
affect that window and its child processes; `backend\.env` is not changed):

```powershell
cd backend
$env:DATABASE_URL = "sqlite:///$((Resolve-Path .).Path.Replace('\','/'))/demo.db"
$env:SCREENING_MODE = "synthetic_demo"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m scripts.create_admin --username demo --full-name "Demo Admin"
.\.venv\Scripts\python.exe -m scripts.seed_synthetic_demo --admin demo
cd ..
powershell -ExecutionPolicy Bypass -File .\scripts\run_backend.ps1 -Port 8001
# second window:
powershell -ExecutionPolicy Bypass -File .\scripts\run_frontend.ps1 -Port 5174 -BackendOrigin http://127.0.0.1:8001
```

Open http://127.0.0.1:5174, sign in as `demo`, open **Multimodal** for a "SYNTHETIC DEMO" session
and click **Run demo screening**. The result is stored once (with the model version, input record
and measurement IDs), and the website and the PDF report both show that saved result. Delete
`backend\demo.db` afterwards. `SCREENING_MODE` defaults to `off`.

## Retention purge and audits

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.purge_expired            # dry run: lists expired sessions
.\.venv\Scripts\python.exe -m scripts.backup_db                # back up before deleting
.\.venv\Scripts\python.exe -m scripts.purge_expired --apply    # delete after typing PURGE
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt --no-deps --disable-pip   # dependency audit
cd ..\frontend; npm audit; cd ..
```

Deleted sessions can only be recovered by restoring a backup. The same preview and purge are
available in Settings → Retention purge.

## Administrator password reset

There is no e-mail reset. Anyone with access to the server and `backend\.env` can reset a password:

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.reset_admin_password --username admin
```

This sets a new password, clears any lockout and signs out every session. Add `--reactivate` to
re-enable a disabled account. Signed-in admins can change their own password through
`POST /api/v1/auth/change-password` (UI arrives with System Settings in Phase 2).

## Configuration

`backend\.env` (created from `backend\.env.example`, never committed):

| Variable | Default | Meaning |
|---|---|---|
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | 127.0.0.1 / 3306 / visonarc / visonarc_app / – | MySQL connection |
| `DATABASE_URL` | – | Optional full SQLAlchemy URL; overrides `DB_*` |
| `JWT_SECRET_KEY` | generated | ≥ 32 random chars; the API refuses to start otherwise |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 60 | Session lifetime |
| `LOGIN_MAX_FAILED_ATTEMPTS` / `LOGIN_LOCKOUT_MINUTES` | 5 / 15 | Brute-force lockout |
| `STORE_RAW_MEDIA` | false | Keep raw images/audio (also needs subject consent) |
| `DATA_RETENTION_DAYS` | 90 | Default retention for analysis sessions |
| `RETENTION_AUTO_PURGE` / `RETENTION_PURGE_INTERVAL_HOURS` | false / 24 | Delete expired sessions automatically at startup and periodically |
| `LOGIN_IP_MAX_FAILURES` / `LOGIN_IP_WINDOW_SECONDS` | 20 / 300 | Failed sign-ins allowed per client address per window |
| `SCREENING_MODE` | off | `synthetic_demo` enables the hand-set demo formula for synthetic sessions only (see above) |

`frontend\.env` holds only non-secret `VITE_*` values.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `running scripts is disabled on this system` | Use `powershell -ExecutionPolicy Bypass -File …` as shown (changes nothing system-wide). |
| `JWT_SECRET_KEY is missing or too short` | Run `scripts\bootstrap.ps1`, or put a long random value in `backend\.env`. |
| `Access denied for user 'visonarc_app'` / API says "The database refused the sign-in" | Re-run `scripts\setup_mysql.ps1` (rotates the app password and updates `.env`). |
| API says "no access to the configured database" or "does not exist" | Check `DB_NAME` in `backend\.env`, or re-run `scripts\setup_mysql.ps1`. |
| `run_backend.ps1` prints `[FAIL] … is invalid` | Fix that setting (see Configuration below); the preflight check names it without printing its value. |
| `Can't connect to MySQL server` / API returns 503 | Start the `MySQL80` service (`services.msc`). `GET /api/v1/health/ready` shows DB status. |
| Login page says it cannot reach the server | The backend is not running on port 8000 – start `run_backend.ps1`. |
| Diagnostics: "schema is not at the latest migration" | `cd backend; .\.venv\Scripts\python.exe -m alembic upgrade head` |
| Account locked after failed logins | Wait 15 minutes or run `scripts.reset_admin_password`. |
| `EPERM`/`EBUSY` errors during `npm`/`pip` | OneDrive is syncing the folder – pause OneDrive sync, then retry. |
| Port 8000 or 5173 already in use | `check_env.ps1` shows the PID; close that program or stop the old server. |
| Face/Motion page: "MediaPipe files are not installed" | Run `scripts\setup_mediapipe.ps1` (needs `frontend\node_modules`). |
| Voice page: "audio could not be decoded" | Use WAV or MP3; some browsers cannot decode every format. |
| "No face was detected" / "person detected in fewer than 10 frames" | Use even front lighting, one person, head and shoulders fully in view. |
| Builds or tests crash with out-of-memory / StackOverflow errors | Drive C: is almost full. Free space (see BUILD_STATUS known issues). |
| "Cannot reach the VisoNarc server" after reloading | The backend or MySQL is down. Start it, then click Retry; you stay signed in. |
| Login says "Too many failed sign-in attempts from this computer" (429) | Wait for the time shown, or restart the backend (the limiter is in memory). |
| Reports: "PDF report" disabled | ReportLab is missing in `backend\.venv`: run `scripts\bootstrap.ps1` again. |
