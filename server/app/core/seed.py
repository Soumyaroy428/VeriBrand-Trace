"""Development seed data for VeriBrand Trace.

Scaffolds initial brand workspace, users (Admin, Reviewer, Creator),
role memberships, Brand Vault guidelines, approved facts, terminology rules,
and tamper-evident initial audit event.
"""

from typing import Optional
from datetime import datetime, timezone
import hashlib
from app.models.documents import (
    User,
    Workspace,
    Membership,
    ApprovedFact,
    TerminologyRule,
    VisualRule,
    AuditEvent,
)


def mock_hash_password(password: str) -> str:
    """Generate SHA-256 hash for seed development passwords."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


async def seed_database() -> dict:
    """Seeds the database with foundational multi-tenant data."""
    # 1. Create or retrieve default Brand Workspace
    workspace = await Workspace.find_one(Workspace.slug == "acme-global")
    if not workspace:
        workspace = Workspace(
            name="Acme Global Corporation",
            slug="acme-global",
            status="ACTIVE",
        )
        await workspace.insert()

    # 2. Seed Users
    users_data = [
        {
            "email": "admin@veribrand.io",
            "password": "AdminPassword123!",
            "full_name": "Governance Admin",
            "role": "GOVERNANCE_ADMIN",
            "is_superuser": True,
        },
        {
            "email": "reviewer@veribrand.io",
            "password": "ReviewerPassword123!",
            "full_name": "Senior Brand Reviewer",
            "role": "REVIEWER",
            "is_superuser": False,
        },
        {
            "email": "creator@veribrand.io",
            "password": "CreatorPassword123!",
            "full_name": "Content Creator",
            "role": "CREATOR",
            "is_superuser": False,
        },
    ]

    created_users = {}
    for u in users_data:
        user = await User.find_one(User.email == u["email"])
        if not user:
            user = User(
                email=u["email"],
                hashed_password=mock_hash_password(u["password"]),
                full_name=u["full_name"],
                is_active=True,
                is_superuser=u["is_superuser"],
            )
            await user.insert()
        created_users[u["role"]] = user

        # Ensure Membership
        membership = await Membership.find_one(
            Membership.workspace_id == workspace.id,
            Membership.user_id == user.id,
        )
        if not membership:
            membership = Membership(
                workspace_id=workspace.id,
                user_id=user.id,
                role=u["role"],
            )
            await membership.insert()

    # 3. Seed Brand Vault Approved Facts
    facts = [
        {
            "key": "customer_count_2026",
            "statement": "Over 500 enterprise customers worldwide rely on Acme platform.",
            "value": {"metric": "enterprise_customers", "value": 500, "operator": "gte"},
            "source": "Corporate Factsheet Q1 2026, Section 2.1",
        },
        {
            "key": "uptime_sla",
            "statement": "99.99% service availability guarantee backed by enterprise SLA.",
            "value": {"metric": "uptime_percentage", "value": 99.99, "unit": "percent"},
            "source": "Master Services Agreement v4.2",
        },
        {
            "key": "security_certification",
            "statement": "Acme is SOC 2 Type II and ISO 27001 certified.",
            "value": {"certifications": ["SOC 2 Type II", "ISO 27001"]},
            "source": "Security Compliance Whitepaper 2026",
        },
    ]

    for f in facts:
        existing_fact = await ApprovedFact.find_one(
            ApprovedFact.workspace_id == workspace.id,
            ApprovedFact.fact_key == f["key"],
        )
        if not existing_fact:
            fact = ApprovedFact(
                workspace_id=workspace.id,
                fact_key=f["key"],
                statement=f["statement"],
                value_json=f["value"],
                source_reference=f["source"],
                status="ACTIVE",
                version=1,
                created_by=created_users["GOVERNANCE_ADMIN"].id,
            )
            await fact.insert()

    # 4. Seed Terminology Rules
    terms = [
        {
            "term": "cheap",
            "rule_type": "BANNED",
            "replacement": "cost-effective",
            "severity": "HIGH",
            "reference": "Brand Voice Guidelines 2026, Rule 3",
        },
        {
            "term": "unbreakable",
            "rule_type": "BANNED",
            "replacement": "highly resilient",
            "severity": "CRITICAL",
            "reference": "Legal Claim Substantiation Policy, Sec 1",
        },
        {
            "term": "AI-driven",
            "rule_type": "PREFERRED",
            "replacement": "AI-powered",
            "severity": "LOW",
            "reference": "Product Messaging Guide, Sec 4",
        },
    ]

    for t in terms:
        existing_rule = await TerminologyRule.find_one(
            TerminologyRule.workspace_id == workspace.id,
            TerminologyRule.term == t["term"],
        )
        if not existing_rule:
            rule = TerminologyRule(
                workspace_id=workspace.id,
                term=t["term"],
                rule_type=t["rule_type"],
                replacement=t["replacement"],
                case_sensitive=False,
                whole_word=True,
                severity=t["severity"],
                guideline_reference=t["reference"],
                active=True,
                version=1,
            )
            await rule.insert()

    # 5. Seed Visual Standards Rules
    visual_rules = [
        {
            "rule_type": "COLOR_PALETTE",
            "config": {
                "approved_colors": [
                    {"name": "Brand Blue", "hex": "#0c8ce9"},
                    {"name": "Deep Slate", "hex": "#0f172a"},
                    {"name": "Light Canvas", "hex": "#f8fafc"},
                ],
                "delta_e_threshold": 2.0,
            },
            "severity": "HIGH",
            "reference": "Visual Identity System 2026, Page 12",
        },
        {
            "rule_type": "CONTRAST_RATIO",
            "config": {
                "standard": "WCAG_2.1_AA",
                "normal_text_ratio": 4.5,
                "large_text_ratio": 3.0,
            },
            "severity": "CRITICAL",
            "reference": "Digital Accessibility Standard, Sec 5",
        },
    ]

    for vr in visual_rules:
        existing_vr = await VisualRule.find_one(
            VisualRule.workspace_id == workspace.id,
            VisualRule.rule_type == vr["rule_type"],
        )
        if not existing_vr:
            v_rule = VisualRule(
                workspace_id=workspace.id,
                rule_type=vr["rule_type"],
                rule_config=vr["config"],
                severity=vr["severity"],
                source_reference=vr["reference"],
                active=True,
                version=1,
            )
            await v_rule.insert()

    # 6. Seed Genesis Tamper-Evident Audit Event
    genesis_event = await AuditEvent.find_one(
        AuditEvent.workspace_id == workspace.id,
        AuditEvent.action == "WORKSPACE_SEEDED",
    )
    if not genesis_event:
        created_at_now = datetime.now(timezone.utc)
        created_at_iso = created_at_now.isoformat()
        event_hash = AuditEvent.calculate_hash(
            workspace_id=workspace.id,
            actor_user_id=created_users["GOVERNANCE_ADMIN"].id,
            entity_type="WORKSPACE",
            entity_id=workspace.id,
            action="WORKSPACE_SEEDED",
            metadata_json={"seed_version": "1.0.0", "entities_seeded": 18},
            previous_hash=None,
            created_at_iso=created_at_iso,
        )
        genesis_event = AuditEvent(
            workspace_id=workspace.id,
            actor_user_id=created_users["GOVERNANCE_ADMIN"].id,
            entity_type="WORKSPACE",
            entity_id=workspace.id,
            action="WORKSPACE_SEEDED",
            metadata_json={"seed_version": "1.0.0", "entities_seeded": 18},
            previous_hash=None,
            event_hash=event_hash,
            created_at=created_at_now,
        )
        await genesis_event.insert()

    return {
        "workspace_id": workspace.id,
        "workspace_slug": workspace.slug,
        "admin_id": created_users["GOVERNANCE_ADMIN"].id,
        "reviewer_id": created_users["REVIEWER"].id,
        "creator_id": created_users["CREATOR"].id,
        "genesis_hash": genesis_event.event_hash,
    }
