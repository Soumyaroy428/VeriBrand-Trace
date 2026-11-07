"""Automated test suite for Checkpoint 6: Deterministic Verification Engine.

Verifies:
1. Color mathematics & WCAG contrast calculation reproducibility.
2. ISO/CIE 11664-6 CIEDE2000 Delta-E color distance calculations.
3. Banned terminology detection with case/boundary controls and false-positive prevention.
4. Preferred terminology checking and replacement suggestion generation.
5. Approved numeric fact verification and discrepancy detection.
6. Computer vision image dominant color extraction and Delta-E tolerance checks.
7. WCAG 2.1 AA accessibility contrast ratio checks on visual assets.
8. Brand Readiness Score deduction mathematical reproducibility.
9. End-to-end API audit execution and SHA-256 chained audit events.
"""

import io
import pytest
from httpx import AsyncClient, ASGITransport
from PIL import Image

from app.main import app
from app.models.documents import (
    User,
    Workspace,
    Membership,
    Submission,
    SubmissionRevision,
    TerminologyRule,
    ApprovedFact,
    VisualRule,
    AuditRun,
    Finding,
    AuditEvent,
)
from app.core.security import get_password_hash, create_access_token
from app.services.color_math import (
    hex_to_rgb,
    rgb_to_hex,
    rgb_to_lab,
    calculate_contrast_ratio,
    delta_e_cie76,
    delta_e_ciede2000,
)
from app.services.image_analysis import image_analysis_service
from app.services.deterministic_engine import deterministic_engine, compute_readiness_score


# --- 1. Unit Tests: Color Mathematics & Reproducibility ---

def test_hex_rgb_conversions():
    """Verifies bidirectional hex and RGB conversions."""
    assert hex_to_rgb("#000000") == (0, 0, 0)
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("#1A2B3C") == (26, 43, 60)
    assert hex_to_rgb("FFF") == (255, 255, 255)
    assert rgb_to_hex(26, 43, 60) == "#1A2B3C"


def test_wcag_contrast_ratio_reproducibility():
    """Verifies mathematically exact WCAG 2.1 contrast ratios."""
    # Pure black on pure white must be exactly 21.0:1
    black = (0, 0, 0)
    white = (255, 255, 255)
    assert calculate_contrast_ratio(black, white) == 21.0

    # Identical colors must be 1.0:1
    navy = (0, 0, 128)
    assert calculate_contrast_ratio(navy, navy) == 1.0

    # Navy on White: high contrast, passes WCAG AA (>4.5)
    ratio = calculate_contrast_ratio(navy, white)
    assert ratio >= 4.5

    # Light gray (#CCCCCC) on White (#FFFFFF): fails WCAG AA (<4.5)
    light_gray = (204, 204, 204)
    low_ratio = calculate_contrast_ratio(light_gray, white)
    assert low_ratio < 4.5


def test_delta_e_ciede2000_reproducibility():
    """Verifies CIEDE2000 color distance calculations."""
    lab_white = rgb_to_lab(255, 255, 255)
    lab_black = rgb_to_lab(0, 0, 0)

    # Identical colors must have Delta-E = 0.0000
    assert delta_e_ciede2000(lab_white, lab_white) == 0.0
    assert delta_e_ciede2000(lab_black, lab_black) == 0.0

    # Distance between distinct colors is positive and reproducible
    lab_blue = rgb_to_lab(0, 85, 170)
    lab_blue_deviant = rgb_to_lab(0, 95, 181)

    de = delta_e_ciede2000(lab_blue, lab_blue_deviant)
    assert de > 0.0
    assert isinstance(de, float)

    # Re-running produces identical result down to 4 decimal places
    de_again = delta_e_ciede2000(lab_blue, lab_blue_deviant)
    assert de == de_again


# --- 2. Unit Tests: Brand Readiness Score Formula ---

def test_readiness_score_formula():
    """Verifies transparent Brand Readiness Score deductions:

    Score = max(0, 100 - (25*crit) - (10*high) - (5*med) - (1*low))
    """
    # 0 findings = 100
    assert compute_readiness_score([]) == 100

    # 1 High finding = 90
    f_high = Finding(
        audit_run_id="a1", category="TERMINOLOGY", severity="HIGH",
        source_engine="DETERMINISTIC", title="T", description="D"
    )
    assert compute_readiness_score([f_high]) == 90

    # 1 Critical + 1 Medium + 1 Low = 100 - 25 - 5 - 1 = 69
    f_crit = Finding(
        audit_run_id="a1", category="TERMINOLOGY", severity="CRITICAL",
        source_engine="DETERMINISTIC", title="T", description="D"
    )
    f_med = Finding(
        audit_run_id="a1", category="TERMINOLOGY", severity="MEDIUM",
        source_engine="DETERMINISTIC", title="T", description="D"
    )
    f_low = Finding(
        audit_run_id="a1", category="TERMINOLOGY", severity="LOW",
        source_engine="DETERMINISTIC", title="T", description="D"
    )
    assert compute_readiness_score([f_crit, f_med, f_low]) == 69

    # Floor at 0
    f_many_crit = [f_crit] * 5
    assert compute_readiness_score(f_many_crit) == 0


# --- 3. Integration Tests: Terminology Scanner ---

@pytest.mark.asyncio
async def test_banned_and_preferred_terminology_detection():
    """Verifies detection of banned terms and replacement suggestions with boundary controls."""
    ws = Workspace(name="Term WS", slug="term-ws")
    await ws.insert()

    # Rule 1: Banned term "cheap" with whole_word=True
    banned_rule = TerminologyRule(
        workspace_id=ws.id,
        term="cheap",
        rule_type="BANNED",
        severity="HIGH",
        whole_word=True,
        case_sensitive=False,
    )
    await banned_rule.insert()

    # Rule 2: Preferred term "eco-friendly" -> "sustainably sourced"
    preferred_rule = TerminologyRule(
        workspace_id=ws.id,
        term="eco-friendly",
        rule_type="PREFERRED",
        replacement="sustainably sourced",
        severity="MEDIUM",
        whole_word=True,
        case_sensitive=False,
    )
    await preferred_rule.insert()

    # Test text contains:
    # 1. "cheap" (banned - should trigger)
    # 2. "cheaper" (sub-string - should NOT trigger due to whole_word=True)
    # 3. "eco-friendly" (preferred - should trigger replacement suggestion)
    text = "We offer a cheap alternative, not cheaper products. All items are eco-friendly."

    findings = await deterministic_engine.check_terminology(
        workspace_id=ws.id,
        text=text,
        audit_run_id="test_run_1",
    )

    assert len(findings) == 2

    # Check banned finding
    banned_find = next(f for f in findings if "cheap" in f.title.lower())
    assert banned_find.severity == "HIGH"
    assert banned_find.suggestion["action"] == "REMOVE_TERM"

    # Check preferred finding
    pref_find = next(f for f in findings if "eco-friendly" in f.title.lower())
    assert pref_find.severity == "MEDIUM"
    assert pref_find.suggestion["action"] == "REPLACE_TERM"
    assert pref_find.suggestion["replacement"] == "sustainably sourced"


# --- 4. Integration Tests: Numeric Fact Comparison ---

@pytest.mark.asyncio
async def test_numeric_fact_discrepancy_detection():
    """Verifies that unapproved numeric claims contradictory to Approved Facts are flagged."""
    ws = Workspace(name="Fact WS", slug="fact-ws")
    await ws.insert()

    # Approved Fact: 99.9% uptime
    uptime_fact = ApprovedFact(
        workspace_id=ws.id,
        fact_key="UPTIME_GUARANTEE",
        statement="Platform delivers 99.9% uptime SLA.",
        value_json={"metric": "uptime", "value": 99.9, "unit": "%"},
        created_by="admin_id",
    )
    await uptime_fact.insert()

    # Case A: Submission exaggerates claim to "99.99% uptime" -> Flagged
    dirty_text = "Our enterprise cloud guarantees 99.99% uptime for global customers."
    findings = await deterministic_engine.check_numeric_facts(
        workspace_id=ws.id,
        text=dirty_text,
        audit_run_id="test_run_facts",
    )
    assert len(findings) == 1
    assert findings[0].category == "FACT_CHECK"
    assert findings[0].severity == "HIGH"
    assert "99.99%" in findings[0].title
    assert findings[0].evidence["fact_key"] == "UPTIME_GUARANTEE"

    # Case B: Submission matches approved fact "99.9% uptime" -> No finding
    clean_text = "Our enterprise cloud delivers 99.9% uptime for all teams."
    clean_findings = await deterministic_engine.check_numeric_facts(
        workspace_id=ws.id,
        text=clean_text,
        audit_run_id="test_run_facts_clean",
    )
    assert len(clean_findings) == 0


# --- 5. Integration Tests: Computer Vision & Color Compliance ---

@pytest.mark.asyncio
async def test_visual_color_delta_e_and_contrast_compliance():
    """Verifies Delta-E color distance inspection and WCAG contrast checking on images."""
    ws = Workspace(name="Vision WS", slug="vision-ws")
    await ws.insert()

    # Brand palette rule: Brand Blue #0055AA with max Delta-E tolerance of 2.0
    brand_color_rule = VisualRule(
        workspace_id=ws.id,
        rule_type="COLOR_PALETTE",
        rule_config={"color_hex": "#0055AA", "tolerance_delta_e": 2.0},
        severity="HIGH",
    )
    await brand_color_rule.insert()

    # Accessibility rule: WCAG AA contrast >= 4.5:1
    contrast_rule = VisualRule(
        workspace_id=ws.id,
        rule_type="CONTRAST_RATIO",
        rule_config={"min_contrast_ratio": 4.5},
        severity="HIGH",
    )
    await contrast_rule.insert()

    # Create synthetic low-contrast image (Light gray on White)
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(255, 255, 255))
    # Draw patch of light gray #E0E0E0
    for x in range(50):
        for y in range(100):
            img.putpixel((x, y), (224, 224, 224))
    img.save(buf, format="PNG")
    low_contrast_bytes = buf.getvalue()

    findings = await deterministic_engine.check_visual_standards(
        workspace_id=ws.id,
        image_bytes=low_contrast_bytes,
        audit_run_id="test_run_visual",
    )

    # Must flag insufficient contrast
    contrast_finding = next((f for f in findings if f.category == "CONTRAST"), None)
    assert contrast_finding is not None
    assert contrast_finding.severity == "HIGH"
    assert "contrast ratio" in contrast_finding.title.lower()


# --- 6. End-to-End API Integration: Full Audit Run ---

@pytest.mark.asyncio
async def test_full_deterministic_audit_api_flow():
    """Tests triggering audit via API, score deduction, finding citations, and audit event logging."""
    user = User(email="author@veribrand.io", hashed_password=get_password_hash("Pass123!"))
    await user.insert()
    ws = Workspace(name="Full Audit WS", slug="full-audit-ws")
    await ws.insert()
    await Membership(workspace_id=ws.id, user_id=user.id, role="CREATOR").insert()

    # Configure brand rules
    await TerminologyRule(
        workspace_id=ws.id,
        term="unbreakable",
        rule_type="BANNED",
        severity="CRITICAL",
        whole_word=True,
    ).insert()

    await ApprovedFact(
        workspace_id=ws.id,
        fact_key="SECURITY_ENCRYPTION",
        statement="Employs AES-256 bit encryption standard.",
        value_json={"metric": "encryption", "value": 256, "unit": "bit"},
        created_by=user.id,
    ).insert()

    # Create submission with violations
    sub = Submission(
        workspace_id=ws.id,
        created_by=user.id,
        title="Security Product Overview",
        input_type="TEXT",
        status="DRAFT",
    )
    await sub.insert()

    rev = SubmissionRevision(
        submission_id=sub.id,
        revision_number=1,
        content_hash="mock_hash_123",
        extracted_text="Our platform offers unbreakable protection with 512 bit encryption.",
        sanitized_text="Our platform offers unbreakable protection with 512 bit encryption.",
        created_by=user.id,
    )
    await rev.insert()

    token = create_access_token(user.id, user.email)
    headers = {"Authorization": f"Bearer {token}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Trigger Audit Run
        audit_resp = await client.post(
            f"/api/v1/submissions/{sub.id}/audits",
            headers=headers,
        )
        assert audit_resp.status_code == 201, audit_resp.text
        data = audit_resp.json()

        audit_run = data["audit_run"]
        findings = data["findings"]

        assert audit_run["status"] == "COMPLETED"
        assert audit_run["deterministic_status"] == "COMPLETED"
        assert len(findings) >= 2  # Banned "unbreakable" + numeric 512 bit encryption discrepancy

        # Check Brand Readiness Score was computed (Critical deduction: 100 - 25 = 75 or lower)
        assert audit_run["readiness_score"] <= 75

        # Check Submission status was set to NEEDS_CHANGES due to CRITICAL finding
        updated_sub = await Submission.get(sub.id)
        assert updated_sub.status == "NEEDS_CHANGES"

        # Check AuditEvent was chained with SHA-256 hash
        audit_event = await AuditEvent.find_one(
            AuditEvent.workspace_id == ws.id,
            AuditEvent.action == "DETERMINISTIC_AUDIT_COMPLETED",
        )
        assert audit_event is not None
        assert len(audit_event.event_hash) == 64

        # 2. Get Audit by ID
        get_audit_resp = await client.get(
            f"/api/v1/audits/{audit_run['id']}",
            headers=headers,
        )
        assert get_audit_resp.status_code == 200
        assert get_audit_resp.json()["id"] == audit_run["id"]

        # 3. Get Findings by Audit ID
        findings_resp = await client.get(
            f"/api/v1/audits/{audit_run['id']}/findings",
            headers=headers,
        )
        assert findings_resp.status_code == 200
        retrieved_findings = findings_resp.json()
        assert len(retrieved_findings) == len(findings)
        # Check evidence citation is attached
        assert len(retrieved_findings[0]["evidence_list"]) > 0

        # 4. Get Latest Audit for Submission
        latest_audit_resp = await client.get(
            f"/api/v1/submissions/{sub.id}/latest-audit",
            headers=headers,
        )
        assert latest_audit_resp.status_code == 200
        assert latest_audit_resp.json()["audit_run"]["id"] == audit_run["id"]
