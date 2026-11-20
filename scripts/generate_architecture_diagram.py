"""Generate high-resolution PNG and vector SVG system architecture diagrams for VisoNarc.
Produces docs/system_architecture.png and docs/system_architecture.svg.
"""

import os
from PIL import Image, ImageDraw, ImageFont

OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
PNG_PATH = os.path.join(OUTPUT_DIR, "system_architecture.png")
SVG_PATH = os.path.join(OUTPUT_DIR, "system_architecture.svg")

# --- 1. SVG Generation ---
def generate_svg():
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1000" width="100%" height="100%" style="background:#0b1120; font-family:'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b1120" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
    <linearGradient id="clientGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
    <linearGradient id="serverGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
    <linearGradient id="dbGrad" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="#1e293b" />
      <stop offset="100%" stop-color="#0f172a" />
    </linearGradient>
    
    <!-- Modality gradients -->
    <linearGradient id="faceGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0284c7" />
      <stop offset="100%" stop-color="#38bdf8" />
    </linearGradient>
    <linearGradient id="motionGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#0d9488" />
      <stop offset="100%" stop-color="#2dd4bf" />
    </linearGradient>
    <linearGradient id="voiceGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#7c3aed" />
      <stop offset="100%" stop-color="#a855f7" />
    </linearGradient>
    <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#3b82f6" />
      <stop offset="100%" stop-color="#8b5cf6" />
    </linearGradient>

    <!-- Filters -->
    <filter id="cardShadow" x="-10%" y="-5%" width="120%" height="115%" filterUnits="userSpaceOnUse">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.5"/>
    </filter>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="4" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>

    <marker id="arrowBlue" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 1 1 L 7 4 L 1 7 Z" fill="#38bdf8" />
    </marker>
    <marker id="arrowGreen" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 1 1 L 7 4 L 1 7 Z" fill="#34d399" />
    </marker>
    <marker id="arrowPurple" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto">
      <path d="M 1 1 L 7 4 L 1 7 Z" fill="#c084fc" />
    </marker>
  </defs>

  <!-- Background -->
  <rect width="1600" height="1000" fill="url(#bgGrad)"/>
  
  <!-- Subtle Grid Pattern -->
  <g opacity="0.04" stroke="#ffffff" stroke-width="1">
    <path d="M0,100 H1600 M0,200 H1600 M0,300 H1600 M0,400 H1600 M0,500 H1600 M0,600 H1600 M0,700 H1600 M0,800 H1600 M0,900 H1600" />
    <path d="M100,0 V1000 M200,0 V1000 M300,0 V1000 M400,0 V1000 M500,0 V1000 M600,0 V1000 M700,0 V1000 M800,0 V1000 M900,0 V1000 M1000,0 V1000 M1100,0 V1000 M1200,0 V1000 M1300,0 V1000 M1400,0 V1000 M1500,0 V1000" />
  </g>

  <!-- ==================== HEADER ==================== -->
  <g transform="translate(60, 45)">
    <rect x="0" y="0" width="1480" height="75" rx="12" fill="#1e293b" opacity="0.6" stroke="#334155" stroke-width="1" />
    <circle cx="35" cy="37" r="18" fill="url(#accentGrad)" />
    <text x="35" y="43" fill="#ffffff" font-size="18" font-weight="bold" text-anchor="middle">VN</text>
    <text x="70" y="34" fill="#f8fafc" font-size="22" font-weight="700" letter-spacing="0.5">VisoNarc – System Architecture</text>
    <text x="70" y="55" fill="#94a3b8" font-size="13">Multimodal Behavioural Analysis Platform · Privacy-Preserving Edge AI · Full-Stack Research Architecture</text>
    <rect x="1310" y="22" width="145" height="30" rx="15" fill="#0369a1" opacity="0.4" stroke="#0ea5e9" stroke-width="1"/>
    <text x="1382" y="42" fill="#38bdf8" font-size="12" font-weight="600" text-anchor="middle">Academic B.Tech Final</text>
  </g>

  <!-- ==================== TIER 1: CLIENT (EDGE AI) ==================== -->
  <g transform="translate(60, 145)">
    <!-- Main Box -->
    <rect width="430" height="700" rx="16" fill="url(#clientGrad)" stroke="#38bdf8" stroke-width="1.5" stroke-opacity="0.4" filter="url(#cardShadow)"/>
    
    <!-- Header Badge -->
    <rect x="20" y="20" width="390" height="42" rx="8" fill="#0369a1" opacity="0.25" stroke="#0284c7" stroke-width="1"/>
    <text x="35" y="46" fill="#38bdf8" font-size="15" font-weight="700">TIER 1: CLIENT BROWSER (EDGE AI)</text>
    <text x="395" y="45" fill="#94a3b8" font-size="12" text-anchor="end">React 19 + TypeScript</text>

    <!-- Sub-block: UI Layer -->
    <rect x="20" y="80" width="390" height="110" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="35" y="105" fill="#e2e8f0" font-size="13" font-weight="600">Frontend Presentation &amp; Workspace</text>
    <text x="35" y="128" fill="#94a3b8" font-size="11.5">• Tailwind CSS v4 + shadcn/ui Component Primitives</text>
    <text x="35" y="148" fill="#94a3b8" font-size="11.5">• Live WebCam &amp; Audio Input Capture via MediaStream API</text>
    <text x="35" y="168" fill="#94a3b8" font-size="11.5">• Interactive Analytics (Recharts), PDF viewer, Audit pages</text>

    <!-- Sub-block: MediaPipe Edge Inference -->
    <rect x="20" y="205" width="390" height="340" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="35" y="230" fill="#38bdf8" font-size="13" font-weight="700">Client-Side Edge AI (WASM / Tasks-Vision)</text>
    <text x="35" y="248" fill="#64748b" font-size="11">Models run locally in browser memory — no raw video leaves device</text>

    <!-- Modality 1: Face -->
    <rect x="35" y="262" width="360" height="75" rx="6" fill="#1e293b" stroke="#0284c7" stroke-width="1" stroke-opacity="0.5"/>
    <rect x="45" y="272" width="60" height="20" rx="4" fill="#0284c7" opacity="0.3"/>
    <text x="75" y="286" fill="#38bdf8" font-size="10.5" font-weight="700" text-anchor="middle">FACE</text>
    <text x="115" y="286" fill="#f1f5f9" font-size="11.5" font-weight="600">MediaPipe Face Landmarker</text>
    <text x="45" y="310" fill="#cbd5e1" font-size="11">• 478 3D mesh points · Eye contour extraction</text>
    <text x="45" y="326" fill="#cbd5e1" font-size="11">• Iris tracking (10 pts) · Pixel stats (brightness/sharpness)</text>

    <!-- Modality 2: Motion -->
    <rect x="35" y="347" width="360" height="75" rx="6" fill="#1e293b" stroke="#0d9488" stroke-width="1" stroke-opacity="0.5"/>
    <rect x="45" y="357" width="60" height="20" rx="4" fill="#0d9488" opacity="0.3"/>
    <text x="75" y="371" fill="#2dd4bf" font-size="10.5" font-weight="700" text-anchor="middle">MOTION</text>
    <text x="115" y="371" fill="#f1f5f9" font-size="11.5" font-weight="600">MediaPipe BlazePose (Pose Lite)</text>
    <text x="45" y="395" fill="#cbd5e1" font-size="11">• 33 body landmarks tracked at 15 FPS</text>
    <text x="45" y="411" fill="#cbd5e1" font-size="11">• Real decoded timestamp synchronization</text>

    <!-- Modality 3: Voice -->
    <rect x="35" y="432" width="360" height="75" rx="6" fill="#1e293b" stroke="#7c3aed" stroke-width="1" stroke-opacity="0.5"/>
    <rect x="45" y="442" width="60" height="20" rx="4" fill="#7c3aed" opacity="0.3"/>
    <text x="75" y="456" fill="#c084fc" font-size="10.5" font-weight="700" text-anchor="middle">VOICE</text>
    <text x="115" y="456" fill="#f1f5f9" font-size="11.5" font-weight="600">Audio Pre-Processing (Browser)</text>
    <text x="45" y="480" fill="#cbd5e1" font-size="11">• Web Audio API mono channel capture</text>
    <text x="45" y="496" fill="#cbd5e1" font-size="11">• Resampled to 16 kHz 16-bit PCM WAV in memory</text>

    <!-- Privacy Banner -->
    <rect x="20" y="560" width="390" height="115" rx="10" fill="#064e3b" opacity="0.3" stroke="#059669" stroke-width="1.2"/>
    <text x="35" y="585" fill="#34d399" font-size="12.5" font-weight="700">🔒 PRIVACY-BY-DESIGN SAFEGUARD</text>
    <text x="35" y="608" fill="#a7f3d0" font-size="11">• Raw photos &amp; pose video NEVER leave the browser.</text>
    <text x="35" y="626" fill="#a7f3d0" font-size="11">• Only numeric landmark coordinates are sent.</text>
    <text x="35" y="644" fill="#a7f3d0" font-size="11">• Audio uploaded ONLY after explicit subject confirmation.</text>
    <text x="35" y="662" fill="#a7f3d0" font-size="11">• Audio processed in RAM only, zero disk storage.</text>
  </g>

  <!-- ==================== FLOW CONNECTIONS (CLIENT TO SERVER) ==================== -->
  <g>
    <!-- Landmarks arrow -->
    <path d="M 490, 435 L 575, 435" stroke="#38bdf8" stroke-width="2" stroke-dasharray="4,4" marker-end="url(#arrowBlue)" />
    <rect x="500" y="405" width="68" height="22" rx="4" fill="#0f172a" stroke="#0284c7" stroke-width="1"/>
    <text x="534" y="420" fill="#38bdf8" font-size="9.5" font-weight="600" text-anchor="middle">JSON Data</text>

    <!-- Audio arrow -->
    <path d="M 490, 610 L 575, 610" stroke="#c084fc" stroke-width="2" stroke-dasharray="4,4" marker-end="url(#arrowPurple)" />
    <rect x="500" y="580" width="68" height="22" rx="4" fill="#0f172a" stroke="#7c3aed" stroke-width="1"/>
    <text x="534" y="595" fill="#c084fc" font-size="9.5" font-weight="600" text-anchor="middle">WAV bytes</text>
  </g>

  <!-- ==================== TIER 2: GATEWAY & BACKEND ==================== -->
  <g transform="translate(585, 145)">
    <!-- Main Box -->
    <rect width="520" height="700" rx="16" fill="url(#serverGrad)" stroke="#a855f7" stroke-width="1.5" stroke-opacity="0.4" filter="url(#cardShadow)"/>
    
    <!-- Header Badge -->
    <rect x="20" y="20" width="480" height="42" rx="8" fill="#581c87" opacity="0.3" stroke="#9333ea" stroke-width="1"/>
    <text x="35" y="46" fill="#d8b4fe" font-size="15" font-weight="700">TIER 2: BACKEND &amp; SIGNAL PIPELINE</text>
    <text x="485" y="45" fill="#94a3b8" font-size="12" text-anchor="end">FastAPI + Python 3.13</text>

    <!-- Core Security & Gateway -->
    <rect x="20" y="80" width="480" height="95" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="35" y="103" fill="#e2e8f0" font-size="12.5" font-weight="600">REST API Gateway &amp; Defensive Security</text>
    <text x="35" y="123" fill="#94a3b8" font-size="11">• HS256 JWT Authentication with Database Session Revocation (JTI table)</text>
    <text x="35" y="141" fill="#94a3b8" font-size="11">• Bcrypt password hashing (cost 12) · Brute-force lockout &amp; IP limiter</text>
    <text x="35" y="159" fill="#94a3b8" font-size="11">• Strict Pydantic v2 validation · CORS &amp; CSP headers (`default-src none`)</text>

    <!-- Signal Processing Modules -->
    <rect x="20" y="190" width="480" height="235" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="35" y="213" fill="#a855f7" font-size="13" font-weight="700">Acoustic &amp; Mathematical Feature Extractors</text>

    <!-- Face Extractor Detail -->
    <rect x="35" y="225" width="450" height="55" rx="6" fill="#1e293b" stroke="#0284c7" stroke-width="1" stroke-opacity="0.4"/>
    <text x="45" y="244" fill="#38bdf8" font-size="11.5" font-weight="700">face.py (Geometry &amp; Quality Gates)</text>
    <text x="45" y="263" fill="#cbd5e1" font-size="10.5">Eye Aspect Ratio (EAR, Soukupová &amp; Čech) · Landmark midline symmetry index · Iris/pupil ratio</text>

    <!-- Motion Extractor Detail -->
    <rect x="35" y="287" width="450" height="55" rx="6" fill="#1e293b" stroke="#0d9488" stroke-width="1" stroke-opacity="0.4"/>
    <text x="45" y="306" fill="#2dd4bf" font-size="11.5" font-weight="700">motion.py (Kinematic Analysis)</text>
    <text x="45" y="325" fill="#cbd5e1" font-size="10.5">Speed normalized by shoulder-width (BW/s) · Velocity CV · FFT Tremor frequency (0.25–7.5 Hz)</text>

    <!-- Voice Extractor Detail -->
    <rect x="35" y="349" width="450" height="65" rx="6" fill="#1e293b" stroke="#7c3aed" stroke-width="1" stroke-opacity="0.4"/>
    <text x="45" y="368" fill="#c084fc" font-size="11.5" font-weight="700">voice.py (YIN Algorithm &amp; Spectral Analysis)</text>
    <text x="45" y="387" fill="#cbd5e1" font-size="10.5">YIN pitch tracking (F0 median/std in semitones) · 13 MFCC coefficients (26 mel-filterbanks)</text>
    <text x="45" y="403" fill="#cbd5e1" font-size="10.5">Spectral centroid, rolloff &amp; flatness · SNR estimate · Speech pause duration segmentation</text>

    <!-- Integration & Demo Engine -->
    <rect x="20" y="440" width="480" height="135" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="35" y="463" fill="#f59e0b" font-size="13" font-weight="700">Multimodal Integration &amp; Synthetic Screening Engine</text>
    <text x="35" y="485" fill="#cbd5e1" font-size="11.5"><tspan font-weight="700" fill="#fde68a">14-Feature Matrix:</tspan> Deterministic feature integration (Face + Motion + Voice)</text>
    <text x="35" y="504" fill="#cbd5e1" font-size="11.5"><tspan font-weight="700" fill="#fde68a">Missing Modality Handler:</tspan> Native missing states — NO zero-fill/imputation bias</text>
    <text x="35" y="523" fill="#cbd5e1" font-size="11.5"><tspan font-weight="700" fill="#fde68a">Real Sessions:</tspan> Unbiased reporting ("No reliable estimate available" — honest science)</text>
    <text x="35" y="542" fill="#cbd5e1" font-size="11.5"><tspan font-weight="700" fill="#fde68a">Synthetic Demo:</tspan> Hand-set weighted sigmoid classifier for synthetic testing sessions</text>
    <text x="35" y="561" fill="#cbd5e1" font-size="11.5"><tspan font-weight="700" fill="#fde68a">ReportLab Engine:</tspan> High-fidelity, tamper-evident PDF export with legal disclaimers</text>

    <!-- Quality & Compliance Footer -->
    <rect x="20" y="590" width="480" height="85" rx="10" fill="#1e293b" stroke="#475569" stroke-width="1"/>
    <text x="35" y="613" fill="#38bdf8" font-size="12" font-weight="700">Software Engineering Rigor</text>
    <text x="35" y="633" fill="#94a3b8" font-size="11">• 201 Backend Automated Pytest tests (in-memory SQLite + MySQL)</text>
    <text x="35" y="650" fill="#94a3b8" font-size="11">• SQL Query Parameter hiding (`hide_parameters=True`) preventing log leaks</text>
    <text x="35" y="667" fill="#94a3b8" font-size="11">• CSV injection sanitization (=, +, -, @ escaped) &amp; Alembic Downgrade guards</text>
  </g>

  <!-- ==================== FLOW CONNECTIONS (SERVER TO DB) ==================== -->
  <g>
    <path d="M 1105, 480 L 1180, 480" stroke="#34d399" stroke-width="2" stroke-dasharray="4,4" marker-end="url(#arrowGreen)" />
    <rect x="1115" y="450" width="60" height="22" rx="4" fill="#0f172a" stroke="#059669" stroke-width="1"/>
    <text x="1145" y="465" fill="#34d399" font-size="9" font-weight="600" text-anchor="middle">SQLAlchemy</text>
  </g>

  <!-- ==================== TIER 3: PERSISTENCE & GOVERNANCE ==================== -->
  <g transform="translate(1190, 145)">
    <!-- Main Box -->
    <rect width="350" height="700" rx="16" fill="url(#dbGrad)" stroke="#34d399" stroke-width="1.5" stroke-opacity="0.4" filter="url(#cardShadow)"/>
    
    <!-- Header Badge -->
    <rect x="20" y="20" width="310" height="42" rx="8" fill="#064e3b" opacity="0.3" stroke="#059669" stroke-width="1"/>
    <text x="35" y="46" fill="#6ee7b7" font-size="14" font-weight="700">TIER 3: DATA PERSISTENCE</text>
    <text x="315" y="45" fill="#94a3b8" font-size="12" text-anchor="end">MySQL 8</text>

    <!-- Schema Tables List -->
    <rect x="20" y="80" width="310" height="340" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="35" y="105" fill="#e2e8f0" font-size="13" font-weight="700">Relational Database Schema</text>
    <text x="35" y="125" fill="#64748b" font-size="11">12 Tables Managed by Alembic Migrations</text>

    <g transform="translate(35, 140)">
      <!-- Table pills -->
      <rect x="0" y="0" width="280" height="24" rx="4" fill="#1e293b"/>
      <text x="10" y="16" fill="#cbd5e1" font-size="11" font-weight="600">admins · admin_sessions (tokens)</text>

      <rect x="0" y="30" width="280" height="24" rx="4" fill="#1e293b"/>
      <text x="10" y="46" fill="#cbd5e1" font-size="11" font-weight="600">audit_logs (immutable trail)</text>

      <rect x="0" y="60" width="280" height="24" rx="4" fill="#1e293b"/>
      <text x="10" y="76" fill="#cbd5e1" font-size="11" font-weight="600">analysis_sessions (anonymized)</text>

      <rect x="0" y="90" width="280" height="24" rx="4" fill="#1e293b"/>
      <text x="10" y="106" fill="#cbd5e1" font-size="11" font-weight="600">consent_records (per-modality)</text>

      <rect x="0" y="120" width="280" height="24" rx="4" fill="#1e293b"/>
      <text x="10" y="136" fill="#38bdf8" font-size="11" font-weight="600">facial_measurements (JSON features)</text>

      <rect x="0" y="150" width="280" height="24" rx="4" fill="#1e293b"/>
      <text x="10" y="166" fill="#2dd4bf" font-size="11" font-weight="600">motion_measurements (kinematics)</text>

      <rect x="0" y="180" width="280" height="24" rx="4" fill="#1e293b"/>
      <text x="10" y="196" fill="#c084fc" font-size="11" font-weight="600">voice_measurements (acoustics)</text>

      <rect x="0" y="210" width="280" height="24" rx="4" fill="#1e293b"/>
      <text x="10" y="226" fill="#fde68a" font-size="11" font-weight="600">combined_results (14-features)</text>

      <rect x="0" y="240" width="280" height="24" rx="4" fill="#1e293b"/>
      <text x="10" y="256" fill="#cbd5e1" font-size="11" font-weight="600">screening_results · app_settings</text>
    </g>

    <!-- Data Retention & Governance -->
    <rect x="20" y="440" width="310" height="235" rx="10" fill="#0f172a" stroke="#334155" stroke-width="1"/>
    <text x="35" y="465" fill="#34d399" font-size="13" font-weight="700">Data Lifecycle &amp; Governance</text>
    
    <text x="35" y="490" fill="#cbd5e1" font-size="11.5">• <tspan font-weight="600" fill="#f1f5f9">Cascading Deletion:</tspan></text>
    <text x="45" y="508" fill="#94a3b8" font-size="11">Withdrawing consent automatically purges all linked records.</text>

    <text x="35" y="532" fill="#cbd5e1" font-size="11.5">• <tspan font-weight="600" fill="#f1f5f9">Retention Auto-Purge:</tspan></text>
    <text x="45" y="550" fill="#94a3b8" font-size="11">Automated atomic purge of sessions past `retain_until` date.</text>

    <text x="35" y="574" fill="#cbd5e1" font-size="11.5">• <tspan font-weight="600" fill="#f1f5f9">Safety Downgrade Guard:</tspan></text>
    <text x="45" y="592" fill="#94a3b8" font-size="11">Alembic blocks downgrades that would cause silent data loss.</text>

    <text x="35" y="616" fill="#cbd5e1" font-size="11.5">• <tspan font-weight="600" fill="#f1f5f9">Guarded Backup &amp; Restore:</tspan></text>
    <text x="45" y="634" fill="#94a3b8" font-size="11">`backup_db.py` &amp; dry-run verified `restore_db.py` scripts.</text>
  </g>

  <!-- ==================== FOOTER BADGES ==================== -->
  <g transform="translate(60, 870)">
    <rect width="1480" height="75" rx="12" fill="#1e293b" opacity="0.6" stroke="#334155" stroke-width="1"/>
    
    <g transform="translate(30, 25)">
      <circle cx="12" cy="12" r="10" fill="#0284c7" />
      <text x="12" y="16" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">1</text>
      <text x="32" y="16" fill="#e2e8f0" font-size="12" font-weight="600">Zero Raw Media Uploaded (Browser Edge AI)</text>
    </g>

    <g transform="translate(370, 25)">
      <circle cx="12" cy="12" r="10" fill="#0d9488" />
      <text x="12" y="16" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">2</text>
      <text x="32" y="16" fill="#e2e8f0" font-size="12" font-weight="600">In-Memory Audio (Zero Disk Persistence)</text>
    </g>

    <g transform="translate(710, 25)">
      <circle cx="12" cy="12" r="10" fill="#7c3aed" />
      <text x="12" y="16" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">3</text>
      <text x="32" y="16" fill="#e2e8f0" font-size="12" font-weight="600">Peer-Reviewed Algorithms (EAR, YIN, MFCC, BlazePose)</text>
    </g>

    <g transform="translate(1180, 25)">
      <circle cx="12" cy="12" r="10" fill="#059669" />
      <text x="12" y="16" fill="#ffffff" font-size="10" font-weight="bold" text-anchor="middle">4</text>
      <text x="32" y="16" fill="#e2e8f0" font-size="12" font-weight="600">201 Automated Tests Passing</text>
    </g>
  </g>
</svg>'''
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated SVG: {SVG_PATH}")


# --- 2. High-Resolution PNG Generation via Pillow ---
def generate_png():
    # Render at 2400 x 1500 (super crisp high-DPI)
    width = 2400
    height = 1500
    img = Image.new("RGBA", (width, height), (11, 17, 32, 255))
    draw = ImageDraw.Draw(img)

    # Fonts
    font_dir = "C:/Windows/Fonts"
    f_title = ImageFont.truetype(f"{font_dir}/segoeuib.ttf", 36)
    f_sub = ImageFont.truetype(f"{font_dir}/segoeui.ttf", 20)
    f_badge = ImageFont.truetype(f"{font_dir}/segoeuib.ttf", 18)
    f_header = ImageFont.truetype(f"{font_dir}/segoeuib.ttf", 24)
    f_box_title = ImageFont.truetype(f"{font_dir}/segoeuib.ttf", 20)
    f_body = ImageFont.truetype(f"{font_dir}/segoeui.ttf", 17)
    f_body_bold = ImageFont.truetype(f"{font_dir}/segoeuib.ttf", 17)
    f_small = ImageFont.truetype(f"{font_dir}/segoeui.ttf", 15)
    f_tag = ImageFont.truetype(f"{font_dir}/segoeuib.ttf", 14)

    # Colors
    c_card_bg = (24, 34, 53, 255)
    c_card_border = (51, 65, 85, 255)
    c_inner_bg = (15, 23, 42, 255)
    c_inner_border = (40, 53, 73, 255)
    c_text_bright = (248, 250, 252, 255)
    c_text_sub = (148, 163, 184, 255)
    c_text_dark = (100, 116, 139, 255)
    c_blue = (56, 189, 248, 255)
    c_blue_dark = (2, 132, 199, 255)
    c_teal = (45, 212, 191, 255)
    c_purple = (192, 132, 252, 255)
    c_purple_dark = (124, 58, 237, 255)
    c_green = (52, 211, 153, 255)
    c_amber = (251, 191, 36, 255)

    # Header Card
    draw.rounded_rectangle([90, 60, 2310, 170], radius=16, fill=(30, 41, 59, 200), outline=c_card_border, width=2)
    # Icon circle
    draw.ellipse([120, 85, 175, 140], fill=c_blue_dark)
    draw.text((147, 95), "VN", fill=c_text_bright, font=f_badge, anchor="mm")
    draw.text((195, 85), "VisoNarc – System Architecture & Dataflow", fill=c_text_bright, font=f_title)
    draw.text((195, 130), "Multimodal Behavioural Analysis Platform · Privacy-Preserving Edge AI · Full-Stack Research Architecture", fill=c_text_sub, font=f_sub)
    draw.rounded_rectangle([2050, 90, 2275, 140], radius=25, fill=(3, 105, 161, 80), outline=c_blue, width=2)
    draw.text((2162, 115), "Academic B.Tech Final", fill=c_blue, font=f_badge, anchor="mm")

    # Tier Dimensions
    y_top = 210
    card_h = 1060

    # ==================== TIER 1: CLIENT (EDGE AI) ====================
    x1, w1 = 90, 640
    draw.rounded_rectangle([x1, y_top, x1 + w1, y_top + card_h], radius=20, fill=c_card_bg, outline=c_blue, width=2)
    # Header bar
    draw.rounded_rectangle([x1 + 25, y_top + 25, x1 + w1 - 25, y_top + 85], radius=12, fill=(3, 105, 161, 60), outline=c_blue_dark, width=1)
    draw.text((x1 + 45, y_top + 40), "TIER 1: CLIENT BROWSER (EDGE AI)", fill=c_blue, font=f_header)
    draw.text((x1 + w1 - 45, y_top + 45), "React 19 + TypeScript", fill=c_text_sub, font=f_body, anchor="ra")

    # Box 1A: UI Presentation
    y_curr = y_top + 105
    draw.rounded_rectangle([x1 + 25, y_curr, x1 + w1 - 25, y_curr + 155], radius=14, fill=c_inner_bg, outline=c_inner_border, width=1)
    draw.text((x1 + 45, y_curr + 20), "Frontend Presentation & Workspace", fill=c_text_bright, font=f_box_title)
    draw.text((x1 + 45, y_curr + 55), "• React 19 + Vite + Tailwind CSS v4 + shadcn/ui primitives", fill=c_text_sub, font=f_body)
    draw.text((x1 + 45, y_curr + 85), "• Real-time Camera & Microphone streaming via MediaStream API", fill=c_text_sub, font=f_body)
    draw.text((x1 + 45, y_curr + 115), "• Dashboard Analytics (Recharts), Reports & Audit Trails", fill=c_text_sub, font=f_body)

    # Box 1B: Edge Models
    y_curr = y_curr + 175
    draw.rounded_rectangle([x1 + 25, y_curr, x1 + w1 - 25, y_curr + 520], radius=14, fill=c_inner_bg, outline=c_inner_border, width=1)
    draw.text((x1 + 45, y_curr + 20), "MediaPipe Edge Computer Vision (WASM)", fill=c_blue, font=f_box_title)
    draw.text((x1 + 45, y_curr + 50), "Client-side inference — zero video frames sent over the network", fill=c_text_dark, font=f_small)

    # Modality: Face
    y_mod = y_curr + 80
    draw.rounded_rectangle([x1 + 45, y_mod, x1 + w1 - 45, y_mod + 120], radius=10, fill=(30, 41, 59, 255), outline=c_blue_dark, width=1)
    draw.rounded_rectangle([x1 + 60, y_mod + 15, x1 + 130, y_mod + 45], radius=6, fill=(2, 132, 199, 80))
    draw.text((x1 + 95, y_mod + 30), "FACE", fill=c_blue, font=f_tag, anchor="mm")
    draw.text((x1 + 145, y_mod + 18), "MediaPipe Face Landmarker (Mesh)", fill=c_text_bright, font=f_body_bold)
    draw.text((x1 + 60, y_mod + 55), "• 478 3D landmark tracking (Kartynnik et al., 2019)", fill=c_text_sub, font=f_small)
    draw.text((x1 + 60, y_mod + 80), "• 10 iris keypoints & browser pixel statistics (brightness/sharpness)", fill=c_text_sub, font=f_small)

    # Modality: Motion
    y_mod = y_mod + 135
    draw.rounded_rectangle([x1 + 45, y_mod, x1 + w1 - 45, y_mod + 120], radius=10, fill=(30, 41, 59, 255), outline=(13, 148, 136, 255), width=1)
    draw.rounded_rectangle([x1 + 60, y_mod + 15, x1 + 150, y_mod + 45], radius=6, fill=(13, 148, 136, 80))
    draw.text((x1 + 105, y_mod + 30), "MOTION", fill=c_teal, font=f_tag, anchor="mm")
    draw.text((x1 + 165, y_mod + 18), "MediaPipe BlazePose (Pose Lite)", fill=c_text_bright, font=f_body_bold)
    draw.text((x1 + 60, y_mod + 55), "• 33 skeletal joint landmarks captured at 15 FPS", fill=c_text_sub, font=f_small)
    draw.text((x1 + 60, y_mod + 80), "• Decoded video timestamp synchronization & coverage tracking", fill=c_text_sub, font=f_small)

    # Modality: Voice
    y_mod = y_mod + 135
    draw.rounded_rectangle([x1 + 45, y_mod, x1 + w1 - 45, y_mod + 120], radius=10, fill=(30, 41, 59, 255), outline=c_purple_dark, width=1)
    draw.rounded_rectangle([x1 + 60, y_mod + 15, x1 + 140, y_mod + 45], radius=6, fill=(124, 58, 237, 80))
    draw.text((x1 + 100, y_mod + 30), "VOICE", fill=c_purple, font=f_tag, anchor="mm")
    draw.text((x1 + 155, y_mod + 18), "Web Audio In-Memory Capture", fill=c_text_bright, font=f_body_bold)
    draw.text((x1 + 60, y_mod + 55), "• Web Audio API conversion to 16 kHz Mono 16-bit PCM WAV", fill=c_text_sub, font=f_small)
    draw.text((x1 + 60, y_mod + 80), "• Uploaded strictly on explicit user confirmation; RAM only", fill=c_text_sub, font=f_small)

    # Privacy Box Bottom
    y_curr = y_curr + 540
    draw.rounded_rectangle([x1 + 25, y_curr, x1 + w1 - 25, y_curr + 180], radius=14, fill=(6, 78, 59, 80), outline=(5, 150, 105, 255), width=2)
    draw.text((x1 + 45, y_curr + 22), "🔒 PRIVACY-BY-DESIGN COMPLIANCE", fill=c_green, font=f_box_title)
    draw.text((x1 + 45, y_curr + 60), "1. Camera images & videos never touch the network or disk.", fill=(167, 243, 208, 255), font=f_body)
    draw.text((x1 + 45, y_curr + 90), "2. Only mathematical float coordinates (landmarks) are transmitted.", fill=(167, 243, 208, 255), font=f_body)
    draw.text((x1 + 45, y_curr + 120), "3. Raw audio is processed in RAM and discarded immediately.", fill=(167, 243, 208, 255), font=f_body)
    draw.text((x1 + 45, y_curr + 150), "4. Strict subject pseudonymity (e.g. SUB-XXXXXX) enforced.", fill=(167, 243, 208, 255), font=f_body)

    # ==================== TIER 2: SERVER / SIGNAL PIPELINE ====================
    x2, w2 = 780, 880
    draw.rounded_rectangle([x2, y_top, x2 + w2, y_top + card_h], radius=20, fill=c_card_bg, outline=c_purple, width=2)
    # Header bar
    draw.rounded_rectangle([x2 + 25, y_top + 25, x2 + w2 - 25, y_top + 85], radius=12, fill=(88, 28, 135, 60), outline=c_purple_dark, width=1)
    draw.text((x2 + 45, y_top + 40), "TIER 2: BACKEND & SIGNAL PIPELINE", fill=c_purple, font=f_header)
    draw.text((x2 + w2 - 45, y_top + 45), "FastAPI + Python 3.13", fill=c_text_sub, font=f_body, anchor="ra")

    # Box 2A: REST API & Security
    y_curr = y_top + 105
    draw.rounded_rectangle([x2 + 25, y_curr, x2 + w2 - 25, y_curr + 155], radius=14, fill=c_inner_bg, outline=c_inner_border, width=1)
    draw.text((x2 + 45, y_curr + 20), "REST API Layer & Security Architecture", fill=c_text_bright, font=f_box_title)
    draw.text((x2 + 45, y_curr + 55), "• Bearer JWT authentication linked to database token revocation table (admin_sessions)", fill=c_text_sub, font=f_body)
    draw.text((x2 + 45, y_curr + 85), "• Bcrypt password hashing (cost 12) · Brute-force lockout (5 attempts / 15 mins) & IP Limiter", fill=c_text_sub, font=f_body)
    draw.text((x2 + 45, y_curr + 115), "• Pydantic v2 schemas reject invalid landmarks, NaN/infinite coordinates, and malformed audio", fill=c_text_sub, font=f_body)

    # Box 2B: Signal Analysis Modules
    y_curr = y_curr + 175
    draw.rounded_rectangle([x2 + 25, y_curr, x2 + w2 - 25, y_curr + 375], radius=14, fill=c_inner_bg, outline=c_inner_border, width=1)
    draw.text((x2 + 45, y_curr + 20), "Algorithmic Signal Extraction (NumPy)", fill=c_purple, font=f_box_title)

    # Face Extractor Box
    y_ext = y_curr + 60
    draw.rounded_rectangle([x2 + 45, y_ext, x2 + w2 - 45, y_ext + 90], radius=10, fill=(30, 41, 59, 255), outline=c_blue_dark, width=1)
    draw.text((x2 + 65, y_ext + 15), "face.py – Geometric Analysis & Quality Gates", fill=c_blue, font=f_body_bold)
    draw.text((x2 + 65, y_ext + 40), "• Eye Aspect Ratio (EAR, Soukupová & Čech, 2016) from 6 eyelid points per eye", fill=c_text_sub, font=f_small)
    draw.text((x2 + 65, y_ext + 63), "• Midline Facial Symmetry Index (Kartynnik et al.) · Iris-to-eye width ratio · Quality gates", fill=c_text_sub, font=f_small)

    # Motion Extractor Box
    y_ext = y_ext + 102
    draw.rounded_rectangle([x2 + 45, y_ext, x2 + w2 - 45, y_ext + 90], radius=10, fill=(30, 41, 59, 255), outline=(13, 148, 136, 255), width=1)
    draw.text((x2 + 65, y_ext + 15), "motion.py – Kinematic & Tremor Analysis", fill=c_teal, font=f_body_bold)
    draw.text((x2 + 65, y_ext + 40), "• Upper-body speed normalized by shoulder width (invariant to camera distance)", fill=c_text_sub, font=f_small)
    draw.text((x2 + 65, y_ext + 63), "• Velocity Coefficient of Variation (CV) · FFT Tremor frequency (0.25–7.5 Hz) & Posture tilt", fill=c_text_sub, font=f_small)

    # Voice Extractor Box
    y_ext = y_ext + 102
    draw.rounded_rectangle([x2 + 45, y_ext, x2 + w2 - 45, y_ext + 105], radius=10, fill=(30, 41, 59, 255), outline=c_purple_dark, width=1)
    draw.text((x2 + 65, y_ext + 15), "voice.py – YIN Algorithm & Spectral Acoustics", fill=c_purple, font=f_body_bold)
    draw.text((x2 + 65, y_ext + 40), "• YIN Pitch Algorithm (de Cheveigné & Kawahara, 2002): F0 median, mean & variability in semitones", fill=c_text_sub, font=f_small)
    draw.text((x2 + 65, y_ext + 63), "• 13 MFCC Coefficients (Davis & Mermelstein, 1980) · Spectral centroid, roll-off & flatness", fill=c_text_sub, font=f_small)
    draw.text((x2 + 65, y_ext + 86), "• Speech-pause segmentation (quiet stretches ≥ 250 ms) · SNR signal-to-noise ratio estimate", fill=c_text_sub, font=f_small)

    # Box 2C: Integration & Demo Screening
    y_curr = y_curr + 395
    draw.rounded_rectangle([x2 + 25, y_curr, x2 + w2 - 25, y_curr + 220], radius=14, fill=c_inner_bg, outline=c_inner_border, width=1)
    draw.text((x2 + 45, y_curr + 20), "Multimodal Feature Integration & Demonstration Engine", fill=c_amber, font=f_box_title)
    draw.text((x2 + 45, y_curr + 55), "• 14-Feature Unified Schema: Fixed deterministic order (Face → Motion → Voice summary features)", fill=c_text_sub, font=f_body)
    draw.text((x2 + 45, y_curr + 85), "• Missing Modality Handling: Preserves true missing state — never zero-filled or imputed", fill=c_text_sub, font=f_body)
    draw.text((x2 + 45, y_curr + 115), "• Real Sessions: Reports objective physical measurements ('No reliable estimate available')", fill=c_text_sub, font=f_body)
    draw.text((x2 + 45, y_curr + 145), "• Synthetic Demo Formula: Fixed weighted sigmoid classifier for synthetic testing sessions only", fill=c_text_sub, font=f_body)
    draw.text((x2 + 45, y_curr + 175), "• ReportLab Engine: Generates tamper-evident clinical PDF reports with cryptographic timestamps", fill=c_text_sub, font=f_body)

    # Box 2D: Software Engineering Badge
    y_curr = y_curr + 240
    draw.rounded_rectangle([x2 + 25, y_curr, x2 + w2 - 25, y_curr + 85], radius=14, fill=(30, 41, 59, 255), outline=c_card_border, width=1)
    draw.text((x2 + 45, y_curr + 18), "Production-Grade Engineering & Testing Gateways", fill=c_blue, font=f_body_bold)
    draw.text((x2 + 45, y_curr + 45), "• 201 backend tests passing (Pytest) · 18 frontend tests passing · 0 vulnerabilities in pip/npm audit", fill=c_text_sub, font=f_small)
    draw.text((x2 + 45, y_curr + 65), "• SQL query parameter hiding (hide_parameters=True) prevents accidental data leaks in terminal logs", fill=c_text_sub, font=f_small)

    # ==================== TIER 3: DATA PERSISTENCE ====================
    x3, w3 = 1715, 595
    draw.rounded_rectangle([x3, y_top, x3 + w3, y_top + card_h], radius=20, fill=c_card_bg, outline=c_green, width=2)
    # Header bar
    draw.rounded_rectangle([x3 + 25, y_top + 25, x3 + w3 - 25, y_top + 85], radius=12, fill=(6, 78, 59, 60), outline=(5, 150, 105, 255), width=1)
    draw.text((x3 + 45, y_top + 40), "TIER 3: DATA PERSISTENCE", fill=c_green, font=f_header)
    draw.text((x3 + w3 - 45, y_top + 45), "MySQL 8 (utf8mb4)", fill=c_text_sub, font=f_body, anchor="ra")

    # Box 3A: Relational Tables
    y_curr = y_top + 105
    draw.rounded_rectangle([x3 + 25, y_curr, x3 + w3 - 25, y_curr + 520], radius=14, fill=c_inner_bg, outline=c_inner_border, width=1)
    draw.text((x3 + 45, y_curr + 20), "12 Relational Tables (Alembic Migrations)", fill=c_text_bright, font=f_box_title)
    
    tables = [
        ("admins", "Administrator credentials & lockout states"),
        ("admin_sessions", "Active JWT tokens for real-time revocation"),
        ("audit_logs", "Immutable append-only administrative trail"),
        ("analysis_sessions", "Subject reference code, dates, retention"),
        ("consent_records", "Granular per-modality consent states"),
        ("facial_measurements", "Extracted face features & quality gates"),
        ("motion_measurements", "Kinematic metrics & tracking coverage"),
        ("voice_measurements", "Acoustic parameters, pitch & SNR values"),
        ("combined_results", "Saved 14-feature integration records"),
        ("screening_results", "Synthetic demo outcome & contributions"),
        ("model_versions", "Catalogue of analytical extractor versions"),
        ("app_settings", "Runtime system configurations & policies")
    ]
    t_y = y_curr + 60
    for t_name, t_desc in tables:
        draw.rounded_rectangle([x3 + 45, t_y, x3 + w3 - 45, t_y + 32], radius=6, fill=(30, 41, 59, 255))
        draw.text((x3 + 55, t_y + 7), t_name, fill=c_green, font=f_tag)
        draw.text((x3 + 215, t_y + 8), t_desc, fill=c_text_sub, font=f_small)
        t_y += 37

    # Box 3B: Governance & Lifecycle
    y_curr = y_curr + 540
    draw.rounded_rectangle([x3 + 25, y_curr, x3 + w3 - 25, y_curr + 370], radius=14, fill=c_inner_bg, outline=c_inner_border, width=1)
    draw.text((x3 + 45, y_curr + 20), "Data Governance & Lifecycle Controls", fill=c_green, font=f_box_title)
    
    draw.text((x3 + 45, y_curr + 60), "• Cascading Deletion (ON DELETE CASCADE):", fill=c_text_bright, font=f_body_bold)
    draw.text((x3 + 45, y_curr + 85), "  Subject consent withdrawal immediately purges all linked", fill=c_text_sub, font=f_small)
    draw.text((x3 + 45, y_curr + 105), "  measurements, integrations and results atomically.", fill=c_text_sub, font=f_small)

    draw.text((x3 + 45, y_curr + 140), "• Automated Data Retention Purge:", fill=c_text_bright, font=f_body_bold)
    draw.text((x3 + 45, y_curr + 165), "  Periodic purge script cleans sessions past retain_until window.", fill=c_text_sub, font=f_small)

    draw.text((x3 + 45, y_curr + 200), "• Alembic Migration Downgrade Guards:", fill=c_text_bright, font=f_body_bold)
    draw.text((x3 + 45, y_curr + 225), "  Migrations refuse downgrades that would delete records", fill=c_text_sub, font=f_small)
    draw.text((x3 + 45, y_curr + 245), "  without explicit flag: -x allow_data_loss=true.", fill=c_text_sub, font=f_small)

    draw.text((x3 + 45, y_curr + 280), "• Backup & Dry-Run Restore Scripts:", fill=c_text_bright, font=f_body_bold)
    draw.text((x3 + 45, y_curr + 305), "  Guarded restore_db.py creates pre-restore snapshot before", fill=c_text_sub, font=f_small)
    draw.text((x3 + 45, y_curr + 325), "  applying any changes; dry-run preview mode supported.", fill=c_text_sub, font=f_small)

    # ==================== BOTTOM FOOTER ====================
    draw.rounded_rectangle([90, 1330, 2310, 1430], radius=16, fill=(30, 41, 59, 200), outline=c_card_border, width=2)
    badges = [
        ("1. Edge AI Privacy", "Photos & video never leave browser memory"),
        ("2. RAM-Only Audio", "Processed in memory, never written to disk"),
        ("3. Published Science", "EAR, YIN, MFCC & BlazePose algorithms"),
        ("4. Automated Testing", "201 backend tests + 18 frontend tests passing")
    ]
    b_x = 120
    for b_title, b_sub in badges:
        draw.ellipse([b_x, 1360, b_x + 36, 1396], fill=c_blue_dark)
        draw.text((b_x + 18, 1378), "✓", fill=c_text_bright, font=f_badge, anchor="mm")
        draw.text((b_x + 50, 1362), b_title, fill=c_text_bright, font=f_body_bold)
        draw.text((b_x + 50, 1388), b_sub, fill=c_text_sub, font=f_small)
        b_x += 540

    # Save PNG
    img.save(PNG_PATH, "PNG", dpi=(300, 300))
    print(f"Generated High-Res PNG: {PNG_PATH}")

if __name__ == "__main__":
    generate_svg()
    generate_png()
