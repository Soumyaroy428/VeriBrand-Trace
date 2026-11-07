"""Official Compliance Certificate PDF Generator.

Generates high-resolution, vector-crisp PDF certificates with embedded QR codes,
golden verification seals, and tamper-evident cryptographic digests.
Adheres to the core philosophy: 'Suggest, Never Override'.
"""

import io
from typing import Optional, Dict, Any
from datetime import datetime
import qrcode
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader


def generate_compliance_certificate_pdf(
    certificate_number: str,
    certificate_hash: str,
    submission_title: str,
    workspace_name: str,
    readiness_score: int,
    approver_name: str,
    approver_email: str,
    issued_at: datetime,
    verification_url: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> bytes:
    """Generates an official branded PDF compliance certificate with embedded QR proof."""
    buf = io.BytesIO()
    
    # Page setup: Landscape Letter (792 x 612 pt)
    page_width, page_height = landscape(letter)
    pdf = canvas.Canvas(buf, pagesize=(page_width, page_height))
    pdf.setTitle(f"VeriBrand Trace Compliance Certificate - {certificate_number}")
    pdf.setAuthor("VeriBrand Trace Sovereign Governance Platform")
    pdf.setSubject("Proof of Brand Compliance and Human-in-the-Loop Sign-off")

    # Color Palette (Tailwind & Governance tokens)
    c_navy_bg = colors.HexColor("#0f172a")       # Deep slate 900
    c_gold = colors.HexColor("#d97706")          # Amber 600
    c_gold_light = colors.HexColor("#fef3c7")    # Amber 100
    c_dark_text = colors.HexColor("#0f172a")     # Slate 900
    c_muted_text = colors.HexColor("#64748b")    # Slate 500
    c_emerald = colors.HexColor("#059669")       # Emerald 600
    c_emerald_bg = colors.HexColor("#ecfdf5")    # Emerald 50
    c_border_gray = colors.HexColor("#e2e8f0")   # Slate 200

    # 1. Background Outer Frame
    pdf.setFillColor(colors.HexColor("#f8fafc"))
    pdf.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # 2. Certificate Paper Card (with shadow margin)
    margin = 24
    card_x = margin
    card_y = margin
    card_w = page_width - (margin * 2)
    card_h = page_height - (margin * 2)

    pdf.setFillColor(colors.white)
    pdf.setStrokeColor(c_gold)
    pdf.setLineWidth(3)
    pdf.roundRect(card_x, card_y, card_w, card_h, radius=8, fill=1, stroke=1)

    # Inner decorative thin border
    inner_margin = 8
    pdf.setStrokeColor(c_border_gray)
    pdf.setLineWidth(1)
    pdf.roundRect(
        card_x + inner_margin,
        card_y + inner_margin,
        card_w - (inner_margin * 2),
        card_h - (inner_margin * 2),
        radius=6,
        fill=0,
        stroke=1,
    )

    # Corner gold flourishes / squares
    corner_size = 14
    pdf.setFillColor(c_gold)
    for cx in [card_x + 12, card_x + card_w - 12 - corner_size]:
        for cy in [card_y + 12, card_y + card_h - 12 - corner_size]:
            pdf.rect(cx, cy, corner_size, corner_size, fill=1, stroke=0)

    # 3. Header Section
    content_top = card_y + card_h - 45

    # Brand Pill
    pdf.setFont("Helvetica-Bold", 10)
    pdf.setFillColor(c_gold)
    header_tag = "VERIBRAND TRACE  •  SOVEREIGN BRAND GOVERNANCE"
    tag_width = pdf.stringWidth(header_tag, "Helvetica-Bold", 10)
    pdf.drawString((page_width - tag_width) / 2, content_top, header_tag)

    # Main Certificate Title
    pdf.setFont("Helvetica-Bold", 24)
    pdf.setFillColor(c_dark_text)
    cert_title = "OFFICIAL CERTIFICATE OF BRAND COMPLIANCE"
    title_width = pdf.stringWidth(cert_title, "Helvetica-Bold", 24)
    pdf.drawString((page_width - title_width) / 2, content_top - 32, cert_title)

    # Decorative divider under title
    div_y = content_top - 44
    pdf.setStrokeColor(c_gold)
    pdf.setLineWidth(1.5)
    pdf.line(page_width / 2 - 120, div_y, page_width / 2 + 120, div_y)

    # Preamble text
    pdf.setFont("Helvetica", 10.5)
    pdf.setFillColor(c_muted_text)
    preamble = (
        "This certifies that the content submission referenced below has successfully satisfied all brand integrity rules, "
        "deterministic factual constraints, and formal sovereign human reviewer sign-off."
    )
    # Wrap preamble to fit cleanly
    words = preamble.split()
    line1 = " ".join(words[:14])
    line2 = " ".join(words[14:])
    w1 = pdf.stringWidth(line1, "Helvetica", 10.5)
    w2 = pdf.stringWidth(line2, "Helvetica", 10.5)
    pdf.drawString((page_width - w1) / 2, div_y - 20, line1)
    pdf.drawString((page_width - w2) / 2, div_y - 35, line2)

    # 4. Details Section (Structured Grid)
    grid_top = div_y - 65
    left_x = card_x + 40
    right_x = page_width / 2 + 10
    col_w = (card_w / 2) - 50

    # Submission Title Box (Full Width Accent Box)
    pdf.setFillColor(colors.HexColor("#f1f5f9"))
    pdf.roundRect(left_x, grid_top - 46, card_w - 80, 46, radius=6, fill=1, stroke=0)
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(c_muted_text)
    pdf.drawString(left_x + 14, grid_top - 16, "VERIFIED SUBMISSION TITLE")
    pdf.setFont("Helvetica-Bold", 13)
    pdf.setFillColor(c_dark_text)
    # Truncate title if too long
    display_title = submission_title if len(submission_title) <= 75 else submission_title[:72] + "..."
    pdf.drawString(left_x + 14, grid_top - 35, display_title)

    # Grid Details
    fields_y = grid_top - 68

    def draw_field(x: float, y: float, label: str, value: str, is_highlight: bool = False):
        pdf.setFont("Helvetica-Bold", 8)
        pdf.setFillColor(c_muted_text)
        pdf.drawString(x, y, label.upper())
        if is_highlight:
            pdf.setFont("Helvetica-Bold", 12)
            pdf.setFillColor(c_emerald)
        else:
            pdf.setFont("Helvetica-Bold", 10.5)
            pdf.setFillColor(c_dark_text)
        pdf.drawString(x, y - 16, value)

    # Left Column Fields
    draw_field(left_x, fields_y, "Certificate Number", certificate_number)
    draw_field(left_x, fields_y - 42, "Brand Workspace", workspace_name)
    grade = "GRADE A+ (EXEMPLARY)" if readiness_score >= 95 else "GRADE A (PASSED)"
    draw_field(left_x, fields_y - 84, "Brand Readiness Score", f"{readiness_score}%  •  {grade}", is_highlight=True)

    # Right Column Fields
    formatted_date = issued_at.strftime("%B %d, %Y  •  %H:%M:%S UTC")
    draw_field(right_x, fields_y, "Date of Approval & Issuance", formatted_date)
    draw_field(right_x, fields_y - 42, "Authorized Reviewer", f"{approver_name} ({approver_email})")
    draw_field(right_x, fields_y - 84, "Governance Threshold", ">= 85% Passing  •  Zero Unresolved Critical Violations")

    # 5. Cryptographic Proof & QR Section (Bottom Section)
    proof_box_y = card_y + 45
    proof_box_h = 105
    proof_box_w = card_w - 80

    pdf.setFillColor(colors.HexColor("#fafafa"))
    pdf.setStrokeColor(c_border_gray)
    pdf.setLineWidth(1)
    pdf.roundRect(left_x, proof_box_y, proof_box_w, proof_box_h, radius=6, fill=1, stroke=1)

    # QR Code Generation
    qr_target = verification_url or f"https://veribrand-trace.vercel.app/verify/{certificate_number}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=1,
    )
    qr.add_data(qr_target)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")

    qr_io = io.BytesIO()
    qr_img.save(qr_io, format="PNG")
    qr_io.seek(0)
    qr_reader = ImageReader(qr_io)

    # Draw QR code in bottom right of proof box
    qr_size = 85
    qr_x = left_x + proof_box_w - qr_size - 10
    qr_y = proof_box_y + 10
    pdf.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

    # Cryptographic Hash text
    hash_x = left_x + 16
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(c_gold)
    pdf.drawString(hash_x, proof_box_y + proof_box_h - 20, "TAMPER-EVIDENT CRYPTOGRAPHIC SEAL  •  SHA-256")

    pdf.setFont("Courier-Bold", 9)
    pdf.setFillColor(c_dark_text)
    # Draw hash in mono
    pdf.drawString(hash_x, proof_box_y + proof_box_h - 38, certificate_hash)

    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(c_muted_text)
    pdf.drawString(
        hash_x,
        proof_box_y + proof_box_h - 56,
        "This digest is permanently chained to the workspace audit ledger. Any post-approval alteration invalidates this proof.",
    )

    # Verification URL text
    pdf.setFont("Helvetica-Bold", 8)
    pdf.setFillColor(c_dark_text)
    pdf.drawString(hash_x, proof_box_y + 18, f"Scan QR code or verify online at: {qr_target}")

    # 6. Golden Seal / Stamp in Center Left
    # Draw a gold circle badge
    seal_x = left_x + proof_box_w - qr_size - 90
    seal_y = proof_box_y + 52
    pdf.setFillColor(c_gold_light)
    pdf.setStrokeColor(c_gold)
    pdf.setLineWidth(1.5)
    pdf.circle(seal_x, seal_y, 30, fill=1, stroke=1)

    pdf.setFont("Helvetica-Bold", 7)
    pdf.setFillColor(c_gold)
    s1 = "VERIFIED"
    s2 = "COMPLIANT"
    s3 = "2026"
    pdf.drawString(seal_x - (pdf.stringWidth(s1, "Helvetica-Bold", 7) / 2), seal_y + 8, s1)
    pdf.drawString(seal_x - (pdf.stringWidth(s2, "Helvetica-Bold", 7) / 2), seal_y - 2, s2)
    pdf.drawString(seal_x - (pdf.stringWidth(s3, "Helvetica-Bold", 7) / 2), seal_y - 12, s3)

    # 7. Bottom Philosophy Line
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.setFillColor(c_muted_text)
    phil_text = "Suggest, Never Override  •  Formal publishing governance authority retained exclusively by authorized human reviewers."
    phil_w = pdf.stringWidth(phil_text, "Helvetica-Oblique", 8)
    pdf.drawString((page_width - phil_w) / 2, card_y + 16, phil_text)

    # Save and output bytes
    pdf.showPage()
    pdf.save()

    return buf.getvalue()
