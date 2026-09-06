"""
Automated quote draft generator: produces a client-ready email response and
an HTML + PDF rate confirmation sheet from parsed tender + rate engine data.
"""
import os
from datetime import datetime

from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from . import models

TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
PDF_OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rate_confirmations"
)
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html"]),
)


def build_email_draft(tender: models.Tender, final_rate: float) -> str:
    origin = tender.origin or "origin"
    destination = tender.destination or "destination"
    equipment = tender.equipment_type or "the requested equipment"
    pickup = tender.pickup_date or "your requested pickup date"

    return f"""Subject: Rate Confirmation - {origin} to {destination} ({equipment})

Hi there,

Thanks for sending over the load details. Based on current lane rates and market
conditions, here is our quote for this shipment:

  Lane:            {origin} -> {destination}
  Equipment:       {equipment}
  Weight:          {tender.weight_lbs or "N/A"} lbs
  Pickup Date:     {pickup}
  Estimated Miles: {tender.miles or "N/A"}

  Quoted Rate:     ${final_rate:,.2f}

This rate is all-in and includes current fuel surcharge. A full rate confirmation
sheet is attached (PDF). Please reply to confirm and we will proceed with carrier
dispatch and tracking setup.

Let us know if you have any questions or need adjustments to the pickup window.

Best regards,
FreightFlow AI Brokerage Team
"""


def build_rate_confirmation_html(tender: models.Tender, final_rate: float) -> str:
    template = _env.get_template("rate_confirmation.html")
    return template.render(
        tender=tender,
        final_rate=final_rate,
        generated_at=datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
    )


def build_rate_confirmation_pdf(tender: models.Tender, final_rate: float) -> str:
    path = os.path.join(PDF_OUTPUT_DIR, f"tender_{tender.id}_rate_confirmation.pdf")
    doc = SimpleDocTemplate(path, pagesize=letter, topMargin=0.6 * inch, bottomMargin=0.6 * inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleBlue", parent=styles["Heading1"], textColor=colors.HexColor("#0f172a"), fontSize=18
    )
    meta_style = ParagraphStyle("Meta", parent=styles["Normal"], textColor=colors.HexColor("#64748b"), fontSize=9)
    footer_style = ParagraphStyle("Footer", parent=styles["Normal"], textColor=colors.HexColor("#94a3b8"), fontSize=8)

    elements = [
        Paragraph("FreightFlow AI &mdash; Rate Confirmation", title_style),
        Paragraph(
            f"Tender #{tender.id} &bull; Generated {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')} "
            f"&bull; Status: {tender.status}",
            meta_style,
        ),
        Spacer(1, 16),
    ]

    load_data = [
        ["Origin", tender.origin or "N/A"],
        ["Destination", tender.destination or "N/A"],
        ["Equipment Type", tender.equipment_type or "N/A"],
        ["Weight", f"{tender.weight_lbs or 'N/A'} lbs"],
        ["Pickup Date", tender.pickup_date or "TBD"],
        ["Commodity", tender.commodity or "General Freight"],
        ["Estimated Miles", str(tender.miles or "N/A")],
    ]
    load_table = Table(load_data, colWidths=[2.2 * inch, 3.8 * inch])
    load_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#334155")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(load_table)
    elements.append(Spacer(1, 18))

    pricing_data = [
        ["Carrier Cost Estimate", f"${tender.carrier_cost_estimate or 0:,.2f}"],
        ["Fuel Surcharge", f"${tender.fuel_surcharge_amount or 0:,.2f}"],
        ["Quoted Customer Rate", f"${final_rate:,.2f}"],
        ["Estimated Broker Margin", f"{(tender.estimated_margin_pct or 0) * 100:.1f}%"],
    ]
    pricing_table = Table(pricing_data, colWidths=[2.2 * inch, 3.8 * inch])
    pricing_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                ("LINEABOVE", (0, 2), (-1, 2), 1.2, colors.HexColor("#2563eb")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(pricing_table)
    elements.append(Spacer(1, 24))
    elements.append(
        Paragraph(
            "This rate confirmation was generated automatically by FreightFlow AI based on parsed "
            "tender data and historical lane rate analysis. Please review before dispatch.",
            footer_style,
        )
    )

    doc.build(elements)
    return path
