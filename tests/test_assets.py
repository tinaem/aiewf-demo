"""Offline asset-integrity tests for the BRK241 demo.

These tests require NO Azure access and NO agent_framework install — they only
validate that the data/config files the demo ships with are well-formed, so a
broken JSON edit is caught before you're on stage.

Run:
    pip install -r requirements-dev.txt
    pytest tests/test_assets.py
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FIELD_OPS = REPO_ROOT / "src" / "field-ops-agent"

JSON_FILES = [
    FIELD_OPS / "sample_docs" / "supplier_agreement.json",
    FIELD_OPS / "sample_docs" / "pacific_optolink_agreement.json",
    FIELD_OPS / "procedural_memory_seed.json",
    FIELD_OPS / ".agent_configs" / "baseline" / "tools.json",
    FIELD_OPS / "evaluators" / "field-ops-agent" / "rubric_dimensions.json",
]


@pytest.mark.parametrize("path", JSON_FILES, ids=lambda p: p.name)
def test_json_files_are_valid(path: Path):
    assert path.exists(), f"missing file: {path}"
    json.loads(path.read_text(encoding="utf-8"))  # raises on invalid JSON


def test_golden_eval_jsonl_is_valid():
    path = FIELD_OPS / "eval" / "field_ops_golden.jsonl"
    assert path.exists(), f"missing file: {path}"
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "golden eval dataset is empty"
    for i, line in enumerate(lines, start=1):
        row = json.loads(line)  # raises on invalid JSON
        assert "query" in row, f"row {i} missing 'query'"
        assert "ground_truth" in row, f"row {i} missing 'ground_truth'"


def test_supplier_agreement_json_shape():
    data = json.loads((FIELD_OPS / "sample_docs" / "supplier_agreement.json").read_text(encoding="utf-8"))
    for key in ("document", "supplier", "insurance_coi", "rate_card", "sla", "safety_attestation"):
        assert key in data, f"supplier_agreement.json missing '{key}'"
    assert isinstance(data["rate_card"], list) and data["rate_card"], "rate_card must be a non-empty list"
    assert data["dispatch_quick_reference"]["preferred_connector"] == "LC/UPC Duplex"


def test_rubric_dimensions_have_weights():
    data = json.loads((FIELD_OPS / "evaluators" / "field-ops-agent" / "rubric_dimensions.json").read_text(encoding="utf-8"))
    # Accept either a list of dimensions or a dict wrapping one.
    dims = data if isinstance(data, list) else data.get("dimensions", data)
    assert dims, "rubric has no dimensions"
    for dim in dims:
        assert "weight" in dim, f"rubric dimension missing 'weight': {dim}"
        assert isinstance(dim["weight"], (int, float)), "weight must be numeric"


def test_supplier_agreement_pdf_generates(tmp_path: Path):
    """Run the PDF generator and confirm it produces non-empty PDFs for every supplier."""
    pytest.importorskip("reportlab")
    script = FIELD_OPS / "sample_docs" / "generate_supplier_agreement_pdf.py"
    assert script.exists(), f"missing generator: {script}"

    spec = importlib.util.spec_from_file_location("gen_supplier_pdf", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.build_all()
    assert len(module.SUPPLIERS) >= 2, "expected at least two supplier sets"
    for _src_json, out_pdf in module.SUPPLIERS:
        assert out_pdf.exists(), f"generator did not write {out_pdf.name}"
        assert out_pdf.stat().st_size > 1024, f"{out_pdf.name} is suspiciously small"
        assert out_pdf.read_bytes().startswith(b"%PDF"), f"{out_pdf.name} is not a valid PDF"


def test_index_corpus_generates():
    """Run the Foundry IQ corpus generator and confirm it writes citable Markdown."""
    script = FIELD_OPS / "sample_docs" / "generate_index_corpus.py"
    assert script.exists(), f"missing generator: {script}"

    spec = importlib.util.spec_from_file_location("gen_index_corpus", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    written = module.build_all()
    assert len(written) >= 12, "expected at least 12 corpus files (6 topics x 2 suppliers)"
    for path in written:
        assert path.exists(), f"generator did not write {path.name}"
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---"), f"{path.name} missing YAML front matter"
        assert "supplier:" in text, f"{path.name} missing supplier field"
        assert len(text) > 200, f"{path.name} is suspiciously short"

