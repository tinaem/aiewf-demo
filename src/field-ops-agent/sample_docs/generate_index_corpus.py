"""Generate the uploadable supplier-doc corpus for Foundry IQ.

Reads every supplier JSON (the same files the PDF generator uses) and writes a
*selection of discrete, citation-friendly documents* into ``index_corpus/`` —
one Markdown file per topic, per supplier (MSA, COI, rate card, safety
attestation, dispatch quick-reference).

Why Markdown (not just the combined PDF)?
  - Azure AI Search agentic retrieval chunks/embeds text cleanly.
  - One file per topic gives the agent precise, citable filenames — the agent's
    instructions say "Cite filenames in your answer."
  - Small, diff-able, git-friendly (no binary bloat).

Upload the resulting folder to the data source behind ``supplier-docs-index``,
then build ``supplier-docs-ks`` (knowledge source) and ``supplier-docs-kb``
(knowledge base). See ``index_corpus/README.md``.

Usage:
    python generate_index_corpus.py        # regenerates index_corpus/ for all suppliers
"""

from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT_DIR = HERE / "index_corpus"

# Source JSONs to render (keep in sync with generate_supplier_agreement_pdf.py).
SOURCES = [
    HERE / "supplier_agreement.json",
    HERE / "pacific_optolink_agreement.json",
]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _front_matter(supplier: dict, doc: dict, doc_kind: str) -> str:
    """Citation metadata block — also useful as index field source data."""
    return (
        "---\n"
        f"supplier: {supplier['legal_name']}\n"
        f"supplier_short: {supplier['short_name']}\n"
        f"vendor_id: {supplier['vendor_id']}\n"
        f"agreement_id: {doc['agreement_id']}\n"
        f"document_type: {doc_kind}\n"
        f"classification: {doc['classification']}\n"
        f"effective_date: {doc['effective_date']}\n"
        f"expiry_date: {doc['expiry_date']}\n"
        "---\n\n"
    )


def _msa(data: dict) -> str:
    d, s = data["document"], data["supplier"]
    return (
        _front_matter(s, d, "Master Services Agreement")
        + f"# {d['title']} — {s['legal_name']}\n\n"
        + f"**Agreement ID:** {d['agreement_id']} &nbsp;|&nbsp; **Revision:** {d['revision']} "
        + f"&nbsp;|&nbsp; **Region:** {d['governing_region']}\n\n"
        + f"**Term:** {d['effective_date']} to {d['expiry_date']}\n\n"
        + "## Supplier\n\n"
        + f"- **Legal name:** {s['legal_name']} ({s['short_name']})\n"
        + f"- **Vendor ID:** {s['vendor_id']}\n"
        + f"- **Primary contact:** {s['primary_contact']}\n"
        + f"- **After-hours dispatch:** {s['after_hours_phone']} · {s['noc_email']}\n"
        + f"- **Service territory:** {', '.join(s['service_territory'])}\n"
        + f"- **Specialties:** {', '.join(s['specialties'])}\n\n"
        + "This Master Services Agreement governs field dispatch, labor rates, service levels, "
        + "insurance, and safety obligations between Microsoft Corporation and the supplier named "
        + "above. Refer to the companion rate card, certificate of insurance, safety attestation, "
        + "and dispatch quick-reference documents for the controlling details of each schedule.\n"
    )


def _coi(data: dict) -> str:
    d, s, ins = data["document"], data["supplier"], data["insurance_coi"]
    return (
        _front_matter(s, d, "Certificate of Insurance")
        + f"# Certificate of Insurance — {s['legal_name']}\n\n"
        + f"| Field | Value |\n| --- | --- |\n"
        + f"| Carrier | {ins['carrier']} |\n"
        + f"| Policy number | {ins['policy_number']} |\n"
        + f"| General liability | ${ins['general_liability_usd']:,} |\n"
        + f"| Professional liability | ${ins['professional_liability_usd']:,} |\n"
        + f"| Workers' comp | {ins['workers_comp']} |\n"
        + f"| Additional insured | {ins['additional_insured']} |\n"
        + f"| Expiration | {ins['expiration_date']} |\n"
    )


def _rate_card(data: dict) -> str:
    d, s = data["document"], data["supplier"]
    rows = "".join(
        f"| {r['code']} | {r['description']} | {r['unit']} | ${r['rate_usd']:,.2f} | {r['min_units']} |\n"
        for r in data["rate_card"]
    )
    return (
        _front_matter(s, d, "Rate Card")
        + f"# Rate Card — {s['legal_name']}\n\n"
        + f"Agreement {d['agreement_id']} ({d['revision']}). All rates in USD.\n\n"
        + "| Code | Description | Unit | Rate (USD) | Min units |\n"
        + "| --- | --- | --- | --- | --- |\n"
        + rows
    )


def _sla(data: dict) -> str:
    d, s, sla = data["document"], data["supplier"], data["sla"]
    rows = "".join(
        f"| {t['priority']} | {t['ack_minutes']} | {t['onsite_hours']} | {t['credit_if_missed_pct']}% |\n"
        for t in sla["response_targets"]
    )
    return (
        _front_matter(s, d, "Service Level Agreement")
        + f"# Service Level Agreement — {s['legal_name']}\n\n"
        + "| Priority | Ack (min) | On-site (hrs) | Credit if missed |\n"
        + "| --- | --- | --- | --- |\n"
        + rows
        + f"\n**Monthly availability target:** {sla['monthly_availability_target_pct']}%  \n"
        + f"**Max loss budget:** {sla['max_loss_budget_db']} dB\n"
    )


def _safety(data: dict) -> str:
    d, s, sa = data["document"], data["supplier"], data["safety_attestation"]
    return (
        _front_matter(s, d, "Safety Attestation")
        + f"# Safety Attestation — {s['legal_name']}\n\n"
        + f"- **OSHA 300A on file:** {'Yes' if sa['osha_300a_on_file'] else 'No'}\n"
        + f"- **EMR rating:** {sa['emr_rating']}\n"
        + f"- **Required PPE:** {', '.join(sa['ppe_required'])}\n"
        + f"- **Certifications:** {', '.join(sa['certifications'])}\n"
        + f"- **Last safety audit:** {sa['last_safety_audit']} — {sa['audit_result']}\n"
    )


def _dispatch(data: dict) -> str:
    d, s, dq = data["document"], data["supplier"], data["dispatch_quick_reference"]
    return (
        _front_matter(s, d, "Dispatch Quick Reference")
        + f"# Dispatch Quick Reference — {s['legal_name']}\n\n"
        + f"- **Site:** {dq['site']}\n"
        + f"- **Preferred connector:** {dq['preferred_connector']}\n"
        + f"- **Trunk type:** {dq['trunk_type']}\n"
        + f"- **Spare locker:** {dq['spare_locker']}\n"
        + f"- **Escalation path:** {' → '.join(dq['escalation_path'])}\n\n"
        + f"> {dq['notes']}\n"
    )


# (filename suffix, agreement-id flag, renderer)
TOPICS = [
    ("msa", True, _msa),
    ("certificate-of-insurance", False, _coi),
    ("rate-card", False, _rate_card),
    ("service-level-agreement", False, _sla),
    ("safety-attestation", False, _safety),
    ("dispatch-quick-reference", False, _dispatch),
]


def build_all() -> list[Path]:
    OUT_DIR.mkdir(exist_ok=True)
    written: list[Path] = []
    for src in SOURCES:
        data = json.loads(src.read_text(encoding="utf-8"))
        prefix = _slug(data["supplier"]["short_name"])
        agreement_id = data["document"]["agreement_id"]
        for suffix, include_id, render in TOPICS:
            name = (
                f"{prefix}-{_slug(agreement_id)}.md"
                if include_id
                else f"{prefix}-{suffix}.md"
            )
            path = OUT_DIR / name
            path.write_text(render(data), encoding="utf-8")
            written.append(path)
            print(f"Wrote {path.relative_to(HERE)}")
    return written


if __name__ == "__main__":
    build_all()
