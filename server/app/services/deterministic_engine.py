"""Deterministic Brand Verification Engine.

Executes deterministic, mathematically reproducible compliance checks:
1. Banned terminology detection with case/boundary controls.
2. Preferred terminology checking and replacement suggestion generation.
3. Approved numeric fact verification and discrepancy detection.
4. Computer vision image color extraction and CIEDE2000 Delta-E tolerance checks.
5. WCAG 2.1 AA accessibility contrast ratio verification.
6. OCR-based image text extraction and multi-modal compliance auditing.
7. Brand Readiness Score computation and finding normalization.
"""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional

from app.models.documents import (
    Submission,
    SubmissionRevision,
    TerminologyRule,
    ApprovedFact,
    VisualRule,
    AuditRun,
    Finding,
    FindingEvidence,
)
from app.models.base import utc_now
from app.services.color_math import (
    hex_to_lab,
    delta_e_ciede2000,
    calculate_contrast_ratio,
    hex_to_rgb,
    normalize_hex,
)
from app.services.image_analysis import image_analysis_service
from app.services.storage import storage_service


def compute_readiness_score(findings: List[Finding]) -> int:
    """Computes transparent, admin-configured Brand Readiness Score (0-100).

    Formula:
    Score = max(0, 100 - (25 * N_crit) - (10 * N_high) - (5 * N_med) - (1 * N_low))
    Active findings (not RESOLVED, EXCEPTION_APPROVED, or ACCEPTED) deduct points.
    """
    active_findings = [
        f for f in findings
        if getattr(f, "status", "OPEN") not in ["RESOLVED", "EXCEPTION_APPROVED", "ACCEPTED"]
    ]
    crit_count = sum(1 for f in active_findings if f.severity == "CRITICAL")
    high_count = sum(1 for f in active_findings if f.severity == "HIGH")
    med_count = sum(1 for f in active_findings if f.severity == "MEDIUM")
    low_count = sum(1 for f in active_findings if f.severity == "LOW")

    deductions = (crit_count * 25) + (high_count * 10) + (med_count * 5) + (low_count * 1)
    score = max(0, 100 - deductions)
    return score


class DeterministicEngine:
    """Core deterministic compliance engine."""

    async def run_audit(
        self,
        submission: Submission,
        revision: SubmissionRevision,
    ) -> Tuple[AuditRun, List[Finding]]:
        """Executes full deterministic suite on submission revision."""
        audit_run = AuditRun(
            submission_id=submission.id,
            revision_id=revision.id,
            status="PROCESSING",
            deterministic_status="PROCESSING",
            ai_status="PENDING",
            started_at=datetime.now(timezone.utc),
            rule_set_version="1.0.0",
        )
        await audit_run.insert()

        findings: List[Finding] = []

        try:
            workspace_id = submission.workspace_id
            text_to_audit = revision.sanitized_text or revision.extracted_text or revision.raw_content or ""

            # Check if this is an image submission
            image_bytes: Optional[bytes] = None
            if submission.input_type in ["IMAGE_PNG", "IMAGE_JPG"] and revision.storage_key:
                try:
                    image_bytes = storage_service.get_file_bytes(revision.storage_key)
                except Exception:
                    image_bytes = None

            # 1. Terminology Scanner (Banned & Preferred)
            term_findings = await self.check_terminology(
                workspace_id=workspace_id,
                text=text_to_audit,
                audit_run_id=audit_run.id,
            )
            findings.extend(term_findings)

            # 2. Approved Numeric Fact Scanner
            fact_findings = await self.check_numeric_facts(
                workspace_id=workspace_id,
                text=text_to_audit,
                audit_run_id=audit_run.id,
            )
            findings.extend(fact_findings)

            # 3. Visual Checks (Colors, Delta-E & WCAG Contrast) if Image
            if image_bytes:
                visual_findings = await self.check_visual_standards(
                    workspace_id=workspace_id,
                    image_bytes=image_bytes,
                    audit_run_id=audit_run.id,
                )
                findings.extend(visual_findings)

                # 4. OCR text scan from visual asset
                ocr_result = image_analysis_service.ocr_extract_text(image_bytes)
                if ocr_result["text"] and ocr_result["is_confident"]:
                    ocr_term_findings = await self.check_terminology(
                        workspace_id=workspace_id,
                        text=ocr_result["text"],
                        audit_run_id=audit_run.id,
                        prefix="[Image OCR Text] ",
                    )
                    findings.extend(ocr_term_findings)

            # Calculate Brand Readiness Score
            readiness_score = compute_readiness_score(findings)

            # Update AuditRun
            audit_run.status = "COMPLETED"
            audit_run.deterministic_status = "COMPLETED"
            audit_run.readiness_score = readiness_score
            audit_run.completed_at = datetime.now(timezone.utc)
            await audit_run.save()

            # Update Submission Status
            has_blocking_violations = any(f.severity in ["CRITICAL", "HIGH"] for f in findings)
            if has_blocking_violations:
                submission.status = "NEEDS_CHANGES"
            elif readiness_score >= 85:
                submission.status = "PENDING_REVIEW"
            await submission.save()

            return audit_run, findings

        except Exception as e:
            audit_run.status = "FAILED"
            audit_run.deterministic_status = "FAILED"
            audit_run.error_code = str(e)
            audit_run.completed_at = datetime.now(timezone.utc)
            await audit_run.save()
            raise e

    async def check_terminology(
        self,
        workspace_id: str,
        text: str,
        audit_run_id: str,
        prefix: str = "",
    ) -> List[Finding]:
        """Scans text against workspace terminology rules."""
        findings = []
        rules = await TerminologyRule.find(
            TerminologyRule.workspace_id == workspace_id,
            TerminologyRule.active == True,
        ).to_list()

        for rule in rules:
            flags = 0 if rule.case_sensitive else re.IGNORECASE
            pattern_str = rf"\b{re.escape(rule.term)}\b" if rule.whole_word else re.escape(rule.term)
            pattern = re.compile(pattern_str, flags)

            for match in pattern.finditer(text):
                matched_snippet = match.group(0)
                start_offset = match.start()
                end_offset = match.end()

                # Calculate approximate line and column
                line_no = text[:start_offset].count("\n") + 1
                col_no = start_offset - text[:start_offset].rfind("\n")

                if rule.rule_type == "BANNED":
                    title = f"{prefix}Banned terminology detected: '{rule.term}'"
                    description = (
                        f"The term '{rule.term}' is prohibited under brand guidelines. "
                        f"Found '{matched_snippet}' at line {line_no}, col {col_no}."
                    )
                    suggestion = {
                        "action": "REMOVE_TERM",
                        "original": matched_snippet,
                        "replacement": rule.replacement or "",
                    }
                else:
                    # PREFERRED or REPLACEMENT rule
                    title = f"{prefix}Non-preferred terminology: '{rule.term}'"
                    description = (
                        f"Guidelines recommend replacing '{rule.term}' with '{rule.replacement}'. "
                        f"Found at line {line_no}, col {col_no}."
                    )
                    suggestion = {
                        "action": "REPLACE_TERM",
                        "original": matched_snippet,
                        "replacement": rule.replacement,
                    }

                finding = Finding(
                    audit_run_id=audit_run_id,
                    category="TERMINOLOGY",
                    severity=rule.severity,
                    source_engine="DETERMINISTIC",
                    title=title,
                    description=description,
                    location={
                        "start_offset": start_offset,
                        "end_offset": end_offset,
                        "line": line_no,
                        "column": col_no,
                        "matched_text": matched_snippet,
                    },
                    evidence={
                        "rule_id": rule.id,
                        "term": rule.term,
                        "rule_type": rule.rule_type,
                        "guideline_reference": rule.guideline_reference,
                    },
                    suggestion=suggestion,
                    status="OPEN",
                )
                await finding.insert()

                # Append traceable evidence passage
                evidence_doc = FindingEvidence(
                    finding_id=finding.id,
                    source_type="RULE",
                    source_id=rule.id,
                    source_version=rule.version,
                    quote=f"Rule: {rule.rule_type} term '{rule.term}' -> '{rule.replacement or ''}'",
                    location={"line": line_no, "col": col_no},
                )
                await evidence_doc.insert()

                findings.append(finding)

        return findings

    async def check_numeric_facts(
        self,
        workspace_id: str,
        text: str,
        audit_run_id: str,
    ) -> List[Finding]:
        """Compares numeric figures and percentages in text against Approved Fact Registry."""
        findings = []
        approved_facts = await ApprovedFact.find(
            ApprovedFact.workspace_id == workspace_id,
            ApprovedFact.status == "ACTIVE",
        ).to_list()

        # Regex to detect metrics: e.g. "99.99%", "40%", "$500M", "10,000 customers"
        metric_pattern = re.compile(
            r"(?P<prefix>\$)?\b(?P<num>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?P<suffix>%|percent|uptime|reduction|users|customers|million|billion)?",
            re.IGNORECASE,
        )

        for fact in approved_facts:
            fact_val = fact.value_json or {}
            metric_name = fact_val.get("metric", "").lower()
            expected_num = fact_val.get("value")
            expected_unit = fact_val.get("unit", "").lower()

            if expected_num is None:
                continue

            # Look for mentions of the metric context in the submission
            # e.g., if metric is "uptime", check lines discussing "uptime"
            for line_no, line in enumerate(text.splitlines(), start=1):
                if metric_name and metric_name in line.lower():
                    # Found relevant claim line! Now parse all numbers in this line
                    for m in metric_pattern.finditer(line):
                        num_str = m.group("num").replace(",", "")
                        try:
                            found_num = float(num_str)
                        except ValueError:
                            continue

                        # If number differs from approved fact
                        if abs(found_num - float(expected_num)) > 0.001:
                            col_no = m.start() + 1
                            prefix_str = m.group("prefix") or ""
                            suffix_str = m.group("suffix") or ""
                            claimed_snippet = f"{prefix_str}{m.group('num')}{suffix_str}".strip()

                            title = f"Unverified numeric claim: '{claimed_snippet}'"
                            description = (
                                f"Submission claims '{claimed_snippet}' for {metric_name}, "
                                f"which contradicts Approved Fact '{fact.fact_key}' ({fact.statement})."
                            )
                            suggestion = {
                                "action": "ALIGN_WITH_APPROVED_FACT",
                                "original": claimed_snippet,
                                "approved_value": f"{expected_num}{expected_unit}",
                                "fact_key": fact.fact_key,
                                "statement": fact.statement,
                            }

                            finding = Finding(
                                audit_run_id=audit_run_id,
                                category="FACT_CHECK",
                                severity="HIGH",
                                source_engine="DETERMINISTIC",
                                title=title,
                                description=description,
                                location={
                                    "line": line_no,
                                    "column": col_no,
                                    "matched_text": claimed_snippet,
                                },
                                evidence={
                                    "fact_id": fact.id,
                                    "fact_key": fact.fact_key,
                                    "expected_value": expected_num,
                                    "found_value": found_num,
                                    "source_reference": fact.source_reference,
                                },
                                suggestion=suggestion,
                                status="OPEN",
                            )
                            await finding.insert()

                            evidence_doc = FindingEvidence(
                                finding_id=finding.id,
                                source_type="APPROVED_FACT",
                                source_id=fact.id,
                                source_version=fact.version,
                                quote=fact.statement,
                                location={"line": line_no, "col": col_no},
                            )
                            await evidence_doc.insert()

                            findings.append(finding)

        return findings

    async def check_visual_standards(
        self,
        workspace_id: str,
        image_bytes: bytes,
        audit_run_id: str,
    ) -> List[Finding]:
        """Performs computer vision color compliance (Delta-E) and WCAG contrast checks."""
        findings = []

        # 1. Color Palette Rules & CIEDE2000 Delta-E Checks
        color_rules = await VisualRule.find(
            VisualRule.workspace_id == workspace_id,
            VisualRule.rule_type == "COLOR_PALETTE",
            VisualRule.active == True,
        ).to_list()

        if color_rules:
            extracted_colors = image_analysis_service.extract_dominant_colors(image_bytes, max_colors=4)

            # Check primary dominant color against approved brand colors
            for color_rule in color_rules:
                approved_hex = color_rule.rule_config.get("color_hex")
                tolerance_de = float(color_rule.rule_config.get("tolerance_delta_e", 2.0))

                if not approved_hex:
                    continue

                approved_lab = hex_to_lab(approved_hex)

                for ext_color in extracted_colors:
                    # Only check prominent colors (>15% of pixels)
                    if ext_color["percentage"] < 15.0:
                        continue

                    delta_e = delta_e_ciede2000(approved_lab, ext_color["lab"])

                    # If color is supposed to match this brand color but diverges beyond tolerance
                    # (e.g. slight off-brand shade with 2.0 < Delta-E < 15.0)
                    if tolerance_de < delta_e <= 15.0:
                        title = f"Off-brand color deviation detected (Delta-E: {delta_e})"
                        description = (
                            f"Dominant color {ext_color['hex']} ({ext_color['percentage']}% prominence) "
                            f"diverges from approved brand color {approved_hex} by CIEDE2000 Delta-E {delta_e}. "
                            f"Maximum permissible tolerance is {tolerance_de}."
                        )
                        suggestion = {
                            "action": "SNAP_TO_BRAND_PALETTE",
                            "original_hex": ext_color["hex"],
                            "approved_hex": approved_hex,
                            "measured_delta_e": delta_e,
                            "tolerance": tolerance_de,
                        }

                        finding = Finding(
                            audit_run_id=audit_run_id,
                            category="COLOR_COMPLIANCE",
                            severity=color_rule.severity,
                            source_engine="DETERMINISTIC",
                            title=title,
                            description=description,
                            location={
                                "percentage_prominence": ext_color["percentage"],
                                "hex": ext_color["hex"],
                            },
                            evidence={
                                "rule_id": color_rule.id,
                                "approved_hex": approved_hex,
                                "measured_hex": ext_color["hex"],
                                "delta_e_ciede2000": delta_e,
                                "tolerance_limit": tolerance_de,
                            },
                            suggestion=suggestion,
                            status="OPEN",
                        )
                        await finding.insert()

                        evidence_doc = FindingEvidence(
                            finding_id=finding.id,
                            source_type="RULE",
                            source_id=color_rule.id,
                            source_version=color_rule.version,
                            quote=f"Brand color palette rule requires {approved_hex} with Delta-E <= {tolerance_de}",
                        )
                        await evidence_doc.insert()
                        findings.append(finding)

        # 2. WCAG Contrast Ratio Check
        contrast_rules = await VisualRule.find(
            VisualRule.workspace_id == workspace_id,
            VisualRule.rule_type == "CONTRAST_RATIO",
            VisualRule.active == True,
        ).to_list()

        contrast_report = image_analysis_service.check_image_contrast(image_bytes)
        measured_ratio = contrast_report["contrast_ratio"]

        min_ratio = 4.5  # Standard WCAG 2.1 AA default
        severity = "HIGH"
        rule_ref = None

        if contrast_rules:
            contrast_rule = contrast_rules[0]
            min_ratio = float(contrast_rule.rule_config.get("min_contrast_ratio", 4.5))
            severity = contrast_rule.severity
            rule_ref = contrast_rule.id

        if measured_ratio < min_ratio:
            c1_hex = contrast_report.get("color_1", {}).get("hex", "#FFFFFF")
            c2_hex = contrast_report.get("color_2", {}).get("hex", "#CCCCCC")

            title = f"Insufficient visual contrast ratio ({measured_ratio}:1)"
            description = (
                f"Visual asset contrast between primary colors ({c1_hex} and {c2_hex}) is {measured_ratio}:1, "
                f"which fails the WCAG 2.1 AA minimum requirement of {min_ratio}:1."
            )
            suggestion = {
                "action": "INCREASE_CONTRAST",
                "measured_ratio": measured_ratio,
                "minimum_required": min_ratio,
                "color_1": c1_hex,
                "color_2": c2_hex,
            }

            finding = Finding(
                audit_run_id=audit_run_id,
                category="CONTRAST",
                severity=severity,
                source_engine="DETERMINISTIC",
                title=title,
                description=description,
                location={"measured_ratio": measured_ratio},
                evidence={
                    "measured_ratio": measured_ratio,
                    "required_ratio": min_ratio,
                    "contrast_report": contrast_report,
                },
                suggestion=suggestion,
                status="OPEN",
            )
            await finding.insert()

            if rule_ref:
                evidence_doc = FindingEvidence(
                    finding_id=finding.id,
                    source_type="RULE",
                    source_id=rule_ref,
                    source_version=1,
                    quote=f"Accessibility rule requires minimum contrast ratio of {min_ratio}:1",
                )
                await evidence_doc.insert()

            findings.append(finding)

        return findings


# Singleton instance
deterministic_engine = DeterministicEngine()
