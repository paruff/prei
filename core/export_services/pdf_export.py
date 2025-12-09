"""PDF export service for property analysis reports."""

from __future__ import annotations

import io
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import matplotlib
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Use non-interactive backend for matplotlib
matplotlib.use("Agg")


class PDFExportService:
    """Service for generating professional PDF reports."""

    def __init__(self):
        """Initialize PDF export service with custom styles."""
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()

    def _create_custom_styles(self):
        """Create custom paragraph styles."""
        self.styles.add(
            ParagraphStyle(
                name="CustomTitle",
                parent=self.styles["Title"],
                fontSize=24,
                textColor=colors.HexColor("#1a1a1a"),
                spaceAfter=30,
            )
        )

        self.styles.add(
            ParagraphStyle(
                name="SectionHeader",
                parent=self.styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#2563eb"),
                spaceAfter=12,
                spaceBefore=12,
            )
        )

    def generate_property_analysis_report(
        self,
        property_data: Dict[str, Any],
        analysis_results: Dict[str, Any],
        user_branding: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """
        Generate comprehensive property analysis PDF.

        Args:
            property_data: Property information dictionary
            analysis_results: Financial analysis results
            user_branding: Optional user branding configuration

        Returns:
            PDF content as bytes
        """
        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # Build document content
        story = []

        # Cover page
        story.extend(self._build_cover_page(property_data, user_branding))
        story.append(PageBreak())

        # Executive summary
        story.extend(self._build_executive_summary(property_data, analysis_results))
        story.append(Spacer(1, 0.2 * inch))

        # Property details
        story.extend(self._build_property_details(property_data))
        story.append(Spacer(1, 0.2 * inch))

        # Financial analysis
        story.extend(self._build_financial_analysis(analysis_results))
        story.append(PageBreak())

        # Charts
        story.extend(self._build_charts(analysis_results))

        # Build PDF
        doc.build(story)

        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes

    def _build_cover_page(
        self, property_data: Dict[str, Any], branding: Optional[Dict[str, Any]]
    ) -> List:
        """Build cover page elements."""
        elements = []

        # Title
        address = property_data.get("address", "Property Analysis")
        title = Paragraph(
            f"Property Investment Analysis<br/>{address}", self.styles["CustomTitle"]
        )
        title.alignment = TA_CENTER
        elements.append(title)
        elements.append(Spacer(1, 0.3 * inch))

        # Generation date
        date_str = datetime.now().strftime("%B %d, %Y")
        date_para = Paragraph(f"Report Generated: {date_str}", self.styles["Normal"])
        date_para.alignment = TA_CENTER
        elements.append(Spacer(1, 0.5 * inch))
        elements.append(date_para)

        return elements

    def _build_executive_summary(
        self, property_data: Dict[str, Any], analysis: Dict[str, Any]
    ) -> List:
        """Build executive summary section."""
        elements = []

        # Section header
        elements.append(
            Paragraph("Executive Summary", self.styles["SectionHeader"])
        )

        # Key metrics
        metrics_text = f"""
        <b>Property Overview:</b><br/>
        Purchase Price: ${property_data.get('purchasePrice', 0):,.2f}<br/>
        Property Type: {property_data.get('propertyType', 'N/A')}<br/>
        """

        if "investmentMetrics" in analysis:
            metrics = analysis["investmentMetrics"]
            metrics_text += f"""
            <br/>
            <b>Investment Metrics:</b><br/>
            Cash-on-Cash Return: {metrics.get('cocReturn', 0):.1f}%<br/>
            Cap Rate: {metrics.get('capRate', 0):.1f}%<br/>
            """

        elements.append(Paragraph(metrics_text, self.styles["Normal"]))

        return elements

    def _build_property_details(self, property_data: Dict[str, Any]) -> List:
        """Build property details section."""
        elements = []

        # Section header
        elements.append(Paragraph("Property Details", self.styles["SectionHeader"]))

        # Property details text
        details_text = f"""
        <b>Address:</b> {property_data.get('address', 'N/A')}<br/>
        <b>Property Type:</b> {property_data.get('propertyType', 'N/A')}<br/>
        <b>Purchase Price:</b> ${property_data.get('purchasePrice', 0):,.2f}<br/>
        """

        if property_data.get("squareFeet"):
            details_text += (
                f"<b>Square Feet:</b> {property_data['squareFeet']:,}<br/>"
            )

        elements.append(Paragraph(details_text, self.styles["Normal"]))

        return elements

    def _build_financial_analysis(self, analysis: Dict[str, Any]) -> List:
        """Build financial analysis section."""
        elements = []

        # Section header
        elements.append(
            Paragraph("Financial Analysis", self.styles["SectionHeader"])
        )

        # Carrying costs table
        if "carryingCosts" in analysis:
            carrying_costs = analysis["carryingCosts"]
            monthly = carrying_costs.get("monthly", {})
            annual = carrying_costs.get("annual", {})

            data = [["Expense Category", "Monthly", "Annual"]]

            # Add rows for each category
            categories = [
                ("mortgage", "Mortgage (P&I)"),
                ("propertyTax", "Property Tax"),
                ("insurance", "Insurance"),
                ("maintenance", "Maintenance"),
            ]

            for key, label in categories:
                if key in monthly and key in annual:
                    data.append(
                        [
                            label,
                            f"${monthly[key]:,.2f}",
                            f"${annual[key]:,.2f}",
                        ]
                    )

            # Add total row
            if "total" in monthly and "total" in annual:
                data.append(
                    [
                        "Total",
                        f"${monthly['total']:,.2f}",
                        f"${annual['total']:,.2f}",
                    ]
                )

            table = Table(data, colWidths=[3 * inch, 1.5 * inch, 1.5 * inch])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e5e7eb")),
                        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )

            elements.append(table)

        return elements

    def _build_charts(self, analysis: Dict[str, Any]) -> List:
        """Build charts for visualization."""
        elements = []

        # Cash flow chart (if cash flow data is available)
        if "cashFlow" in analysis:
            elements.append(
                Paragraph(
                    "Cash Flow Analysis", self.styles["SectionHeader"]
                )
            )

            # Generate chart
            fig, ax = plt.subplots(figsize=(6, 4))

            cash_flow = analysis["cashFlow"]
            if "monthly" in cash_flow:
                monthly = cash_flow["monthly"]
                categories = []
                values = []

                # Add key cash flow items
                items = [
                    ("grossRentalIncome", "Gross Rental Income"),
                    ("operatingExpenses", "Operating Expenses"),
                    ("debtService", "Debt Service"),
                    ("netCashFlow", "Net Cash Flow"),
                ]

                for key, label in items:
                    if key in monthly:
                        categories.append(label)
                        values.append(monthly[key])

                if categories and values:
                    ax.bar(categories, values, color="#2563eb")
                    ax.set_ylabel("Monthly Amount ($)")
                    ax.set_title("Monthly Cash Flow Breakdown")
                    ax.grid(axis="y", alpha=0.3)
                    plt.xticks(rotation=45, ha="right")

                    # Save chart to buffer
                    img_buffer = io.BytesIO()
                    plt.savefig(
                        img_buffer, format="png", dpi=150, bbox_inches="tight"
                    )
                    img_buffer.seek(0)
                    plt.close()

                    # Add chart to PDF
                    chart_img = Image(img_buffer, width=6 * inch, height=4 * inch)
                    elements.append(chart_img)

        return elements

    def generate_filename(
        self, property_address: str, report_type: str = "property_analysis"
    ) -> str:
        """
        Generate descriptive filename for PDF export.

        Args:
            property_address: Property address string
            report_type: Type of report

        Returns:
            Generated filename with .pdf extension
        """
        # Clean address for filename
        address_clean = (
            property_address.replace(" ", "_")
            .replace(",", "")
            .replace("/", "_")
            .lower()
        )

        # Add date
        date_str = datetime.now().strftime("%Y-%m-%d")

        return f"{report_type}_{address_clean}_{date_str}.pdf"
