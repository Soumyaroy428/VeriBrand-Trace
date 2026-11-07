"""Privacy Gate & PII Redaction Service.

Ensures no Personally Identifiable Information (PII) or confidential
project codenames are sent to external AI providers or downstream LLMs.

Core Philosophy:
- Protect privacy at the gateway before LLM inference.
- Immutably preserve raw text in database revisions for human reviewers.
- Produce clean, sanitized text with deterministic tokens for AI verification.
"""

import re
from typing import List, Dict, Any, Tuple, Optional


# High-precision PII regex patterns
PII_PATTERNS = {
    "EMAIL": re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE,
    ),
    "PHONE": re.compile(
        r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"
    ),
    "SSN": re.compile(
        r"\b\d{3}-\d{2}-\d{4}\b"
    ),
    "CREDIT_CARD": re.compile(
        r"\b(?:\d{4}[-\s]?){3}\d{4}\b|\b3[47]\d{2}[-\s]?\d{6}[-\s]?\d{5}\b"
    ),
    "IP_ADDRESS": re.compile(
        r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
    ),
}

PII_MASKS = {
    "EMAIL": "[REDACTED_EMAIL]",
    "PHONE": "[REDACTED_PHONE]",
    "SSN": "[REDACTED_SSN]",
    "CREDIT_CARD": "[REDACTED_CREDIT_CARD]",
    "IP_ADDRESS": "[REDACTED_IP_ADDRESS]",
}


class PrivacyGateService:
    """Scans and redacts PII and confidential project terms."""

    def redact_pii(self, text: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Scans and replaces PII instances with sanitized token masks."""
        sanitized = text
        pii_findings = []

        # Find all matches across patterns
        matches_to_replace = []
        for pii_type, pattern in PII_PATTERNS.items():
            for m in pattern.finditer(text):
                # Basic sanity filters to prevent false positives
                matched_str = m.group(0)
                if pii_type == "IP_ADDRESS" and matched_str.startswith("0.0.0.0"):
                    continue
                matches_to_replace.append({
                    "type": pii_type,
                    "start": m.start(),
                    "end": m.end(),
                    "snippet": matched_str,
                    "mask": PII_MASKS[pii_type],
                })

        # Sort matches by start position descending to replace without offset drift
        matches_to_replace.sort(key=lambda x: x["start"], reverse=True)

        for match in matches_to_replace:
            s_start = match["start"]
            s_end = match["end"]
            mask = match["mask"]
            sanitized = sanitized[:s_start] + mask + sanitized[s_end:]
            pii_findings.append({
                "type": match["type"],
                "snippet_masked": f"{match['snippet'][:2]}***{match['snippet'][-2:]}" if len(match['snippet']) > 4 else "***",
                "mask_applied": mask,
                "start": s_start,
                "end": s_end,
            })

        # Reverse back to ascending order for natural reading
        pii_findings.reverse()
        return sanitized, pii_findings

    def mask_confidential_terms(
        self,
        text: str,
        confidential_terms: Optional[List[str]] = None,
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, str]]:
        """Replaces confidential project terms with indexed tokens [CONFIDENTIAL_PROJECT_N].

        Returns:
            (sanitized_text, masked_terms_report, token_to_original_mapping)
        """
        if not confidential_terms:
            return text, [], {}

        # Filter out empty or whitespace terms
        clean_terms = [t.strip() for t in confidential_terms if t and t.strip()]
        if not clean_terms:
            return text, [], {}

        # Sort terms by length descending to match longest phrases first
        clean_terms.sort(key=len, reverse=True)

        sanitized = text
        report = []
        token_map = {}

        for idx, term in enumerate(clean_terms, start=1):
            token = f"[CONFIDENTIAL_PROJECT_{idx}]"
            pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
            matches = list(pattern.finditer(sanitized))
            if matches:
                occurrences = len(matches)
                sanitized = pattern.sub(token, sanitized)
                token_map[token] = term
                report.append({
                    "term": term,
                    "token": token,
                    "occurrences": occurrences,
                })

        return sanitized, report, token_map

    def process(
        self,
        raw_text: str,
        confidential_terms: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Full Privacy Gate pipeline:

        1. Redact PII (emails, phones, SSNs, credit cards, IPs).
        2. Mask confidential project terms.
        3. Assemble cryptographic status and audit metadata.
        """
        if not raw_text:
            return {
                "original_text": "",
                "sanitized_text": "",
                "status": "PASSED",
                "pii_detected": [],
                "confidential_terms_masked": [],
                "token_map": {},
                "original_char_count": 0,
                "sanitized_char_count": 0,
            }

        # Step 1: PII Redaction
        pii_sanitized, pii_findings = self.redact_pii(raw_text)

        # Step 2: Confidential Terms Masking
        final_sanitized, terms_report, token_map = self.mask_confidential_terms(
            pii_sanitized, confidential_terms
        )

        has_modifications = bool(pii_findings or terms_report)
        status = "SANITIZED" if has_modifications else "PASSED"

        return {
            "original_text": raw_text,
            "sanitized_text": final_sanitized,
            "status": status,
            "pii_detected": pii_findings,
            "confidential_terms_masked": terms_report,
            "token_map": token_map,
            "original_char_count": len(raw_text),
            "sanitized_char_count": len(final_sanitized),
        }


# Singleton instance
privacy_service = PrivacyGateService()

