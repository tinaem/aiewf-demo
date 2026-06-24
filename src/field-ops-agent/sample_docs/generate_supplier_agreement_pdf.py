"""Generate supplier-agreement.pdf from supplier_agreement.json.

Demo helper for BRK241 Step 3 (Content Understanding). Produces a PDF with
tabular data (rate card, SLA matrix) that is intentionally *not* trivially
agent-readable — exactly the kind of document Content Understanding converts
into markdown / JSON.

Usage:
    pip install reportlab
    python generate_supplier_agreement_pdf.py

Reads:  supplier_agreement.json   (same folder)
Writes: supplier-agreement.pdf    (same folder)
"""

from __future__ import annotations

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
SRC_JSON = HERE / "supplier_agreement.json"
OUT_PDF = HERE / "supplier-agreement.pdf"

ACCENT = colors.HexColor("#0F6CBD")
LIGHT = colors.HexColor("#EAF2FB")
GREY = colors.HexColor("#5A5A5A")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("DocTitle", parent=styles["Title"], textColor=ACCENT, fontSize=20, spaceAfter=4))
    styles.add(ParagraphStyle("Sub", parent=styles["Normal"], textColor=GREY, fontSize=9, spaceAfter=12))
    styles.add(ParagraphStyle("H2", parent=styles["Heading2"], textColor=ACCENT, fontSize=13, spaceBefore=14, spaceAfter=6))
    styles.add(ParagraphStyle("Body", parent=styles["Normal"], fontSize=9.5, leading=13, alignment=TA_LEFT))
    return styles


def _kv_table(rows: list[tuple[str, str]], col0=1.9 * inch, col1=4.4 * inch) -> Table:
    data = [[Paragraph(f"<b>{k}</b>", _BODY), Paragraph(v, _BODY)] for k, v in rows]
    t = Table(data, colWidths=[col0, col1])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _grid_table(header: list[str], rows: list[list[str]], widths: list[float]) -> Table:
    data = [[Paragraph(f"<b>{h}</b>", _HEAD) for h in header]]
    data += [[Paragraph(str(c), _BODY) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#C8D6E5")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def build() -> None:
    data = json.loads(SRC_JSON.read_text(encoding="utf-8"))
    styles = _styles()

    global _BODY, _HEAD
    _BODY = styles["Body"]
    _HEAD = ParagraphStyle("HeadCell", parent=styles["Body"], textColor=colors.white)

    doc = SimpleDocTemplate(
        str(OUT_PDF), pagesize=LETTER,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
        topMargin=0.8 * inch, bottomMargin=0.8 * inch,
        title=data["document"]["title"], author="Microsoft Azure Networking Operations",
    )

    el = []
    d = data["document"]
    s = data["supplier"]

    el.append(Paragraph(d["title"], styles["DocTitle"]))
    el.append(Paragraph(
        f'{d["classification"]} &nbsp;|&nbsp; {d["agreement_id"]} &nbsp;|&nbsp; '
        f'{d["revision"]} &nbsp;|&nbsp; Effective {d["effective_date"]} – {d["expiry_date"]}',
        styles["Sub"]))

    # Parties / supplier overview
    el.append(Paragraph("1. Parties &amp; Supplier Overview", styles["H2"]))
    el.append(_kv_table([
        ("Supplier (legal name)", s["legal_name"]),
        ("Vendor ID", s["vendor_id"]),
        ("Service territory", ", ".join(s["service_territory"])),
        ("Specialties", ", ".join(s["specialties"])),
        ("After-hours dispatch", f'{s["after_hours_phone"]} &nbsp;·&nbsp; {s["noc_email"]}'),
        ("Governing region", d["governing_region"]),
    ]))

    # Insurance / COI
    ins = data["insurance_coi"]
    el.append(Paragraph("2. Certificate of Insurance (COI)", styles["H2"]))
    el.append(_kv_table([
        ("Carrier", ins["carrier"]),
        ("Policy number", ins["policy_number"]),
        ("General liability", f'${ins["general_liability_usd"]:,}'),
        ("Professional liability", f'${ins["professional_liability_usd"]:,}'),
        ("Workers' comp", ins["workers_comp"]),
        ("Additional insured", ins["additional_insured"]),
        ("Expiration", ins["expiration_date"]),
    ]))

    # Rate card (tabular)
    el.append(Paragraph("3. Rate Card", styles["H2"]))
    el.append(_grid_table(
        ["Code", "Description", "Unit", "Rate (USD)", "Min"],
        [[r["code"], r["description"], r["unit"], f'${r["rate_usd"]:,.2f}', r["min_units"]]
         for r in data["rate_card"]],
        widths=[0.85 * inch, 2.95 * inch, 1.0 * inch, 1.0 * inch, 0.5 * inch],
    ))

    # SLA matrix (tabular)
    sla = data["sla"]
    el.append(Paragraph("4. Service Level Agreement", styles["H2"]))
    el.append(_grid_table(
        ["Priority", "Ack (min)", "On-site (hrs)", "Credit if missed"],
        [[t["priority"], t["ack_minutes"], t["onsite_hours"], f'{t["credit_if_missed_pct"]}%']
         for t in sla["response_targets"]],
        widths=[1.8 * inch, 1.2 * inch, 1.5 * inch, 1.8 * inch],
    ))
    el.append(Spacer(1, 6))
    el.append(Paragraph(
        f'Monthly availability target: <b>{sla["monthly_availability_target_pct"]}%</b> &nbsp;·&nbsp; '
        f'Max loss budget: <b>{sla["max_loss_budget_db"]} dB</b>', styles["Body"]))

    # Safety attestation
    sa = data["safety_attestation"]
    el.append(Paragraph("5. Safety Attestation", styles["H2"]))
    el.append(_kv_table([
        ("OSHA 300A on file", "Yes" if sa["osha_300a_on_file"] else "No"),
        ("EMR rating", str(sa["emr_rating"])),
        ("Required PPE", ", ".join(sa["ppe_required"])),
        ("Certifications", ", ".join(sa["certifications"])),
        ("Last safety audit", f'{sa["last_safety_audit"]} — {sa["audit_result"]}'),
    ]))

    # Dispatch quick reference
    dq = data["dispatch_quick_reference"]
    el.append(Paragraph("6. Dispatch Quick Reference", styles["H2"]))
    el.append(_kv_table([
        ("Site", dq["site"]),
        ("Preferred connector", dq["preferred_connector"]),
        ("Trunk type", dq["trunk_type"]),
        ("Spare locker", dq["spare_locker"]),
        ("Escalation path", " → ".join(dq["escalation_path"])),
        ("Notes", dq["notes"]),
    ]))

    doc.build(el)
    print(f"Wrote {OUT_PDF}")


if __name__ == "__main__":
    build()
