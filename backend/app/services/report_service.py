"""Server-generated PDF session report (ReportLab).

Contains only data the requesting administrator can already see through the API: session and
consent metadata, measured features with quality warnings and provenance, saved combined records,
limitations and generation metadata. Never raw media, secrets, scores or diagnoses.
"""

import io
from datetime import UTC, datetime
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.analysis.feature_schema import (
    FEATURE_SCHEMA_VERSION,
    FEATURES,
    LIMITATIONS,
    MIXED_SCHEMAS,
    PROVENANCE_LABELS,
    SOURCES,
)
from app.core.config import APP_FULL_NAME
from app.schemas.sessions import SessionDetail

REPORT_VERSION = "report/1.0.0"
DISCLAIMER = (
    "Experimental academic behavioural-analysis record. Facial appearance, eye redness, pupil-region size, "
    "voice and movement cannot establish drug use or identify any substance. This report contains measurements "
    "only: no score, probability, classification or diagnosis, and it is not medical, forensic or legal evidence."
)
PROVENANCE_SHORT = {
    "server_audio": "Server (audio)",
    "server_landmarks": "Server (landmarks)",
    "browser_pixels": "Browser (pixels)",
    "browser_model": "Browser (model)",
}
FEATURE_STATUS_LABELS = {
    "measured": "Measured",
    "not_measured": "Not measured",
    "missing": "Modality missing",
    "not_consented": "Not consented",
    "excluded_low_quality": "Excluded (quality)",
}
# Characters outside the standard PDF fonts' WinAnsi set that appear in our texts.
_REPLACEMENTS = {"≥": ">=", "≤": "<=", "→": "->", "−": "-", "√": "sqrt", "≈": "~"}


def _text(value: Any) -> str:
    """Escape for ReportLab's mini-markup and keep to characters the built-in fonts can draw."""
    s = "" if value is None else str(value)
    for bad, good in _REPLACEMENTS.items():
        s = s.replace(bad, good)
    s = s.encode("cp1252", errors="replace").decode("cp1252")
    return escape(s)


def _fmt(value: Any, unit: str = "") -> str:
    if value is None:
        return "not measured"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, list):
        return f"{len(value)} values"
    if isinstance(value, dict):
        return ", ".join(f"{k} {_fmt(v)}" for k, v in value.items()) or "none"
    if isinstance(value, float):
        text = f"{value:.4g}"
    else:
        text = str(value)
    plain_units = {"", "count", "ratio", "fraction", "0-1", "0–1", "CV", "per sample", "13 values", "0–1 each"}
    return text if unit in plain_units else f"{text} {unit}"


def _dt(value: datetime | None) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC") if value else "-"


class _Styles:
    def __init__(self):
        base = getSampleStyleSheet()
        self.title = ParagraphStyle("t", parent=base["Title"], fontSize=17, leading=21, spaceAfter=2)
        self.subtitle = ParagraphStyle("st", parent=base["Normal"], fontSize=10, textColor=colors.HexColor("#475569"))
        self.h2 = ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, spaceBefore=10, spaceAfter=4,
                                 textColor=colors.HexColor("#0f766e"))
        self.h3 = ParagraphStyle("h3", parent=base["Heading3"], fontSize=10.5, spaceBefore=6, spaceAfter=3)
        self.body = ParagraphStyle("b", parent=base["Normal"], fontSize=9, leading=12)
        self.small = ParagraphStyle("s", parent=base["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#475569"))
        self.cell = ParagraphStyle("c", parent=base["Normal"], fontSize=8, leading=10)
        self.disclaimer = ParagraphStyle("d", parent=self.body, backColor=colors.HexColor("#f0fdfa"),
                                         borderColor=colors.HexColor("#99f6e4"), borderWidth=0.6, borderPadding=6,
                                         spaceBefore=6, spaceAfter=10)


def _table(rows: list[list[Any]], styles: _Styles, widths: list[float], header: bool = False) -> Table:
    data = [[Paragraph(c if isinstance(c, str) else _text(c), styles.cell) for c in row] for row in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")))
    t.setStyle(TableStyle(style))
    return t


def _kv(pairs: list[tuple[str, Any]], styles: _Styles) -> Table:
    return _table([[f"<b>{_text(k)}</b>", _text(v)] for k, v in pairs], styles, [45 * mm, 125 * mm])


SYNTHETIC_BANNER = (
    "SYNTHETIC DEMONSTRATION RECORD - generated from synthetic signals, not a real person. "
    "Any score below comes from a hand-set demo formula and is not a probability about anyone."
)
NO_ESTIMATE = (
    "No validated model exists, so no estimate or classification is produced for real sessions. "
    "No reliable estimate is available."
)


def _screening_section(detail: SessionDetail, st: _Styles) -> list:
    """Experimental screening, printed from the saved rows only (the website reads the same rows)."""
    out: list = [Paragraph("Experimental screening", st.h2)]
    if not detail.is_synthetic:
        return out + [Paragraph(NO_ESTIMATE, st.body)]
    if not detail.screening_results:
        return out + [Paragraph("No screening result has been saved for this synthetic session.", st.body)]
    for r in sorted(detail.screening_results, key=lambda r: (r.created_at, r.id), reverse=True):
        out.append(Paragraph(f"Screening result #{r.id} - {_dt(r.created_at)} - SYNTHETIC DEMONSTRATION", st.h3))
        pairs = [
            ("Model", f"{r.model_name} {r.model_version}"),
            ("Status", r.model_status.replace("_", " ")),
            ("Input record", f"combined record #{r.combined_result_id}, schema {r.feature_schema_version or '-'}"),
            ("Inputs", ", ".join(f"{m} #{i}" for m, i in r.input_measurement_ids.items()) or "-"),
            ("Missing modalities", ", ".join(r.missing_modalities) or "none"),
        ]
        if r.estimate is None:
            pairs.append(("Demo score", "No estimate: " + (" ".join(r.explanation.get("reasons", [])) or "insufficient input")))
        else:
            pairs += [
                ("Demo score", f"{r.estimate * 100:.1f} % (synthetic demo formula - not a probability about a person)"),
                ("Demo label", f"{r.classification} (synthetic demonstration label, threshold {r.decision_threshold:.2f})"),
                ("Feature coverage", f"{(r.coverage or 0) * 100:.0f} % of scored features measured"),
            ]
        pairs.append(("Target", r.target_definition))
        out.append(_kv(pairs, st))
        for item in r.limitations:
            out.append(Paragraph(f"- {_text(item)}", st.small))
    return out


def build_session_report(detail: SessionDetail, generated_by: str, generated_at: datetime | None = None) -> bytes:
    generated_at = generated_at or datetime.now(UTC)
    st = _Styles()
    story: list = []

    story += [
        Paragraph(_text(APP_FULL_NAME), st.title),
        Paragraph(f"Session record report - {_text(detail.reference_code)}", st.subtitle),
        *([Paragraph(f"<b>{SYNTHETIC_BANNER}</b>", st.disclaimer)] if detail.is_synthetic else []),
        Paragraph(_text(DISCLAIMER), st.disclaimer),
        Paragraph("Report", st.h2),
        _kv([
            ("Generated", _dt(generated_at)),
            ("Generated by", generated_by),
            ("Report version", REPORT_VERSION),
            ("Current feature schema", FEATURE_SCHEMA_VERSION),
        ], st),
        Paragraph("Session", st.h2),
        _kv([
            ("Reference", detail.reference_code),
            ("Subject label (pseudonym)", detail.subject_label),
            ("Status", detail.status.replace("_", " ")),
            ("Created", _dt(detail.created_at)),
            ("Created by", detail.created_by or "deleted administrator"),
            ("Completed", _dt(detail.completed_at)),
            ("Retain until", _dt(detail.retain_until)),
            ("Notes", detail.notes or "-"),
        ], st),
        Paragraph("Consent", st.h2),
    ]
    c = detail.consent
    if c is None:
        story.append(Paragraph("No consent record.", st.body))
    else:
        story.append(_kv([
            ("Consent text version", c.consent_text_version),
            ("Given by", c.consented_by_label),
            ("Recorded", _dt(c.consented_at)),
            ("Face / motion / voice", " / ".join("yes" if x else "no" for x in (c.allow_face, c.allow_motion, c.allow_voice))),
            ("Raw media storage", "yes" if c.allow_raw_media_storage else "no"),
            ("Withdrawn", _dt(c.withdrawn_at) if c.withdrawn_at else "no"),
        ], st))

    for modality, items in (
        ("face", detail.facial_measurements),
        ("motion", detail.motion_measurements),
        ("voice", detail.voice_measurements),
    ):
        story.append(Paragraph(f"{modality.capitalize()} measurements", st.h2))
        if not items:
            story.append(Paragraph("No measurements recorded for this modality.", st.body))
            continue
        specs = [f for f in FEATURES if f.modality == modality]
        for m in items:
            block = [
                Paragraph(f"Measurement #{m.id} - {_dt(m.captured_at)} - {_text(m.source)}", st.h3),
                _kv([
                    ("Quality checks", "passed" if m.is_reliable else "failed one or more"),
                    ("Quality score", f"{m.quality_score:.2f} (engineering check, not confidence)" if m.quality_score is not None else "-"),
                    ("Feature schema", m.feature_schema_version),
                    ("Extractor", m.extractor_version or "not recorded (before migration 0002)"),
                ], st),
            ]
            if m.warnings:
                block.append(Paragraph("Warnings: " + "; ".join(_text(w) for w in m.warnings), st.small))
            rows = [["<b>Feature</b>", "<b>Value</b>", "<b>Computed</b>"]]
            rows += [
                [_text(s.label), _text(_fmt(m.features.get(s.key), s.unit)), _text(PROVENANCE_SHORT[s.provenance])]
                for s in specs
                if s.key in m.features
            ]
            block.append(Spacer(1, 3))
            block.append(_table(rows, st, [80 * mm, 55 * mm, 35 * mm], header=True))
            story.append(KeepTogether(block[:2]))
            story += block[2:]

    story.append(Paragraph("Saved combined records", st.h2))
    records = [r for r in detail.combined_results if r.mode == "feature_integration"]
    if not records:
        story.append(Paragraph("No combined records saved for this session.", st.body))
    for r in records:
        story.append(Paragraph(
            f"Record #{r.id} - {_dt(r.created_at)} - {_text(r.processing_status or '-')} - "
            f"modalities: {_text(', '.join(r.modalities_used) or 'none')}", st.h3))
        schema = (
            "mixed feature schemas (see sources)" if r.feature_schema_version == MIXED_SCHEMAS
            else f"schema {_text(r.feature_schema_version or '-')}"
        )
        story.append(Paragraph(
            f"Integration {_text(r.extractor_version or '-')} - {schema}. "
            "Values are copied as measured; nothing is weighted, combined or scored.", st.small))
        rows = [["<b>#</b>", "<b>Feature</b>", "<b>Value</b>", "<b>Status</b>"]]
        for f in r.features or []:
            rows.append([
                _text(f.get("index")),
                _text(f"{f.get('modality', '')} - {f.get('label', '')}"),
                "-" if f.get("value") is None else _text(_fmt(f.get("value"), f.get("unit", ""))),
                _text(FEATURE_STATUS_LABELS.get(f.get("status"), f.get("status"))),
            ])
        story.append(_table(rows, st, [10 * mm, 82 * mm, 38 * mm, 40 * mm], header=True))
        for s in r.source_measurements or []:
            story.append(Paragraph(
                f"Input: {_text(s.get('modality'))} measurement #{_text(s.get('measurement_id'))}, "
                f"{_text(s.get('captured_at'))}, schema {_text(s.get('feature_schema_version'))}, "
                f"{_text(s.get('extractor_version') or 'extractor not recorded')}", st.small))

    story += _screening_section(detail, st)

    story.append(Paragraph("Provenance", st.h2))
    for key, label in PROVENANCE_LABELS.items():
        story.append(Paragraph(f"<b>{_text(PROVENANCE_SHORT[key])}</b>: {_text(label)}", st.small))
    story.append(Paragraph("Limitations", st.h2))
    for item in LIMITATIONS:
        story.append(Paragraph(f"- {_text(item)}", st.body))
    story.append(Paragraph("Method sources (definitions of how values are computed, not reference values)", st.h3))
    for src in SOURCES.values():
        story.append(Paragraph(_text(src), st.small))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#64748b"))
        kind = "SYNTHETIC DEMONSTRATION record" if detail.is_synthetic else "experimental research record"
        canvas.drawString(15 * mm, 10 * mm, f"VisoNarc - {detail.reference_code} - {kind}, not a diagnosis")
        canvas.drawRightString(195 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=18 * mm,
        title=f"VisoNarc session report {detail.reference_code}", author="VisoNarc", subject="Session record report",
        pageCompression=0,  # uncompressed text keeps tests able to inspect content; reports are small
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
