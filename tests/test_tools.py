"""Tool-behavior tests for the field-ops-agent worker.

These import the worker module, which depends on the Microsoft Agent Framework
and the Azure agent-server packages (shipped as wheels in
``src/field-ops-agent/wheels/``). When those deps aren't installed, the whole
module is skipped — so the suite stays green offline and runs fully in CI where
the wheels are present.

Run:
    pip install -r requirements-dev.txt
    # plus the agent wheels for full coverage:
    pip install src/field-ops-agent/wheels/*.whl
    pytest tests/test_tools.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("agent_framework", reason="agent_framework not installed (install the agent wheels)")

FIELD_OPS = Path(__file__).resolve().parents[1] / "src" / "field-ops-agent"
if str(FIELD_OPS) not in sys.path:
    sys.path.insert(0, str(FIELD_OPS))

try:
    import worker_agent  # type: ignore
except Exception as exc:  # noqa: BLE001 — any missing transitive dep means skip
    pytest.skip(f"worker_agent dependencies unavailable: {exc}", allow_module_level=True)


def _raw_callable(fn):
    """Resolve the underlying Python function behind an ``@tool`` wrapper."""
    for attr in ("__wrapped__", "func", "_func", "fn", "callback"):
        inner = getattr(fn, attr, None)
        if callable(inner):
            return inner
    return fn


def test_document_analysis_has_supplier_and_default_keys():
    mock = worker_agent.MOCK_DOCUMENT_ANALYSIS
    assert "supplier_agreement" in mock, "supplier_agreement entry missing"
    assert "pacific_optolink" in mock, "pacific_optolink entry missing"
    assert "default" in mock, "default entry missing"
    supplier = mock["supplier_agreement"]["extracted_data"]
    assert supplier["agreement_id"] == "MSA-2026-CF-0417"
    assert supplier["after_hours_rate_usd_per_hour"] == 235.0
    pacific = mock["pacific_optolink"]["extracted_data"]
    assert pacific["after_hours_rate_usd_per_hour"] == 265.0


def test_quincy_north_connector_is_lc_upc_duplex():
    """Guards the on-stage voice punchline."""
    assert worker_agent.MOCK_SITE_SPECS["quincy_north_b"]["connector"] == "LC/UPC Duplex"


def test_analyze_document_routes_supplier_pdf_to_supplier_entry():
    fn = _raw_callable(worker_agent.analyze_document)
    result = fn("file:///sample_docs/supplier-agreement.pdf")
    if not isinstance(result, str):
        pytest.skip("analyze_document is wrapped and not directly callable in this env")
    payload = json.loads(result)
    assert payload["status"] == "success"
    assert payload["analysis"]["document_type"] == "Supplier Agreement (RALA)"


def test_analyze_document_routes_pacific_optolink_to_its_entry():
    fn = _raw_callable(worker_agent.analyze_document)
    result = fn("file:///sample_docs/pacific-optolink-agreement.pdf")
    if not isinstance(result, str):
        pytest.skip("analyze_document is wrapped and not directly callable in this env")
    payload = json.loads(result)
    assert payload["analysis"]["extracted_data"]["supplier"] == "Pacific OptoLink Networks, Inc."


def test_analyze_document_routes_spec_sheet_to_default_entry():
    fn = _raw_callable(worker_agent.analyze_document)
    result = fn("https://docs.contoso.com/specs/qsfp-dd-400g-sr8.pdf")
    if not isinstance(result, str):
        pytest.skip("analyze_document is wrapped and not directly callable in this env")
    payload = json.loads(result)
    assert payload["analysis"]["document_type"] == "Technical Specification"
