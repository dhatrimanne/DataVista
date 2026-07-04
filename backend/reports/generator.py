from __future__ import annotations

import re
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from uuid import uuid4

from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from backend.config import resolve_app_path
from backend.dashboard.health_score import calculate_business_health_score


PAGE_WIDTH, PAGE_HEIGHT = letter
REPORT_MARGIN = 0.55 * inch
CONTENT_WIDTH = PAGE_WIDTH - (REPORT_MARGIN * 2)
CHART_WIDTH = CONTENT_WIDTH * 0.72
NAVY = colors.HexColor("#0f172a")
SLATE = colors.HexColor("#475569")
MUTED = colors.HexColor("#64748b")
BLUE = colors.HexColor("#2563eb")
GREEN = colors.HexColor("#16a34a")
AMBER = colors.HexColor("#d97706")
RED = colors.HexColor("#dc2626")
TABLE_HEADER = colors.HexColor("#1e293b")
TABLE_ALT = colors.HexColor("#f8fafc")
TABLE_BORDER = colors.HexColor("#cbd5e1")
CARD_BG = colors.HexColor("#f8fafc")


def report_user_dir(user_id: int) -> Path:
    path = resolve_app_path("./reports") / str(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def report_path(user_id: int, filename: str) -> Path:
    path = report_user_dir(user_id) / Path(filename).name
    if not path.exists():
        raise FileNotFoundError("Report file not found.")
    return path


def money(value: object) -> str:
    try:
        number = float(value or 0)
    except (TypeError, ValueError):
        return str(value)
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000:
        return f"{sign}${number / 1_000_000:.2f}M"
    if number >= 1_000:
        return f"{sign}${number / 1_000:.1f}K"
    return f"{sign}${number:,.2f}"


def number(value: object) -> str:
    try:
        return f"{float(value or 0):,.0f}"
    except (TypeError, ValueError):
        return str(value)


def styles() -> dict:
    base = getSampleStyleSheet()
    font = "Helvetica"
    bold = "Helvetica-Bold"
    base["Title"].fontName = bold
    base["Title"].fontSize = 27
    base["Title"].leading = 32
    base["Title"].textColor = NAVY
    base["Title"].alignment = TA_LEFT
    base["Heading2"].fontName = bold
    base["Heading2"].fontSize = 18
    base["Heading2"].leading = 23
    base["Heading2"].textColor = NAVY
    base["Heading3"].fontName = bold
    base["Heading3"].fontSize = 14
    base["Heading3"].leading = 18
    base["Heading3"].textColor = NAVY
    base["BodyText"].fontName = font
    base["BodyText"].fontSize = 10.5
    base["BodyText"].leading = 15
    base["BodyText"].textColor = colors.HexColor("#1f2937")
    base["BodyText"].spaceAfter = 10
    base["BodyText"].splitLongWords = False
    base.add(ParagraphStyle(name="CoverKicker", parent=base["BodyText"], fontName=bold, fontSize=10, leading=14, textColor=BLUE))
    base.add(ParagraphStyle(name="CoverMeta", parent=base["BodyText"], fontSize=10.5, leading=15, textColor=SLATE))
    base.add(ParagraphStyle(name="Section", parent=base["Heading2"], spaceBefore=18, spaceAfter=12))
    base.add(ParagraphStyle(name="Subheading", parent=base["Heading3"], spaceBefore=10, spaceAfter=8))
    base.add(ParagraphStyle(name="Small", parent=base["BodyText"], fontSize=8.5, leading=12, textColor=SLATE))
    base.add(ParagraphStyle(name="TableHeader", parent=base["BodyText"], fontName=bold, fontSize=9, leading=11, textColor=colors.white))
    base.add(ParagraphStyle(name="TableText", parent=base["BodyText"], fontSize=8.8, leading=11.5, textColor=NAVY, splitLongWords=False))
    base.add(ParagraphStyle(name="TableNumber", parent=base["TableText"], alignment=TA_RIGHT))
    base.add(ParagraphStyle(name="CardValue", parent=base["BodyText"], fontName=bold, fontSize=18, leading=22, textColor=NAVY, alignment=TA_CENTER))
    base.add(ParagraphStyle(name="CardLabel", parent=base["BodyText"], fontSize=8.5, leading=11, textColor=MUTED, alignment=TA_CENTER))
    base.add(ParagraphStyle(name="AIHeading", parent=base["Heading3"], fontName=bold, fontSize=13.5, leading=18, spaceBefore=10, spaceAfter=7, splitLongWords=False))
    base.add(ParagraphStyle(name="AIBody", parent=base["BodyText"], fontName=font, fontSize=10.2, leading=14.5, spaceBefore=2, spaceAfter=10, splitLongWords=False))
    base.add(
        ParagraphStyle(
            name="AIBullet",
            parent=base["AIBody"],
            leftIndent=18,
            firstLineIndent=0,
            bulletIndent=5,
            spaceBefore=2,
            spaceAfter=6,
        )
    )
    return base


def inline_markdown(text: str) -> str:
    formatted = escape(text)
    formatted = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", formatted)
    formatted = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", formatted)
    return formatted


def section_title(title: str, style_map: dict) -> list:
    return [Spacer(1, 8), Paragraph(title, style_map["Section"])]


def cover_rule(width: float = CONTENT_WIDTH) -> Drawing:
    drawing = Drawing(width, 18)
    drawing.add(Line(0, 9, width, 9, strokeColor=colors.HexColor("#dbeafe"), strokeWidth=1.4))
    drawing.add(Line(0, 9, width * 0.22, 9, strokeColor=BLUE, strokeWidth=3))
    return drawing


def page_header_footer(canvas, document) -> None:
    canvas.saveState()
    if document.page > 1:
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(SLATE)
        canvas.drawString(REPORT_MARGIN, PAGE_HEIGHT - 0.35 * inch, "DataVista")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_WIDTH - REPORT_MARGIN, 0.32 * inch, f"Page {document.page}")
        canvas.setStrokeColor(colors.HexColor("#e2e8f0"))
        canvas.line(REPORT_MARGIN, PAGE_HEIGHT - 0.45 * inch, PAGE_WIDTH - REPORT_MARGIN, PAGE_HEIGHT - 0.45 * inch)
    canvas.restoreState()


def paragraph_cell(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(inline_markdown(str(value)), style)


def styled_table(rows: list[list[str]], header: bool = True, widths: list[float] | None = None) -> Table:
    style_map = styles()
    if not rows:
        return Table([])
    col_count = len(rows[0])
    if widths is None:
        first_width = CONTENT_WIDTH * 0.72 if col_count == 2 else CONTENT_WIDTH * 0.46
        remaining = CONTENT_WIDTH - first_width
        widths = [first_width] + [remaining / max(1, col_count - 1)] * (col_count - 1)
    table_rows: list[list[Paragraph]] = []
    for row_index, row in enumerate(rows):
        output_row = []
        for col_index, cell in enumerate(row):
            if header and row_index == 0:
                output_row.append(paragraph_cell(cell, style_map["TableHeader"]))
            elif col_index > 0:
                output_row.append(paragraph_cell(cell, style_map["TableNumber"]))
            else:
                output_row.append(paragraph_cell(cell, style_map["TableText"]))
        table_rows.append(output_row)
    table = Table(table_rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="CENTER")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, TABLE_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]
    if header:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEADER),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ]
        )
    for row_index in range(1 if header else 0, len(rows)):
        if row_index % 2 == 0:
            commands.append(("BACKGROUND", (0, row_index), (-1, row_index), TABLE_ALT))
    table.setStyle(TableStyle(commands))
    return table


def metric_card(label: str, value: str, accent: colors.Color = BLUE) -> Table:
    drawing = Drawing(12, 8)
    drawing.add(Rect(0, 0, 12, 4, rx=2, ry=2, fillColor=accent, strokeColor=accent))
    style_map = styles()
    table = Table(
        [[drawing], [Paragraph(value, style_map["CardValue"])], [Paragraph(label, style_map["CardLabel"])]],
        colWidths=[CONTENT_WIDTH / 3 - 11],
        rowHeights=[12, 27, 18],
        hAlign="CENTER",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dbeafe")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def dashboard_cards(kpis: dict, dataset: dict, customers: object) -> Table:
    cards = [
        metric_card("Revenue", money(kpis.get("revenue")), BLUE),
        metric_card("Profit", money(kpis.get("profit")), GREEN),
        metric_card("Orders", number(kpis.get("orders")), AMBER),
        metric_card("Customers", number(customers), colors.HexColor("#7c3aed")),
        metric_card("Average Order Value", money(kpis.get("average_order_value")), colors.HexColor("#0891b2")),
        metric_card("Data Quality", f"{dataset.get('data_quality_score', 'N/A')}/100", RED),
    ]
    table = Table(
        [[cards[0], cards[1], cards[2]], [cards[3], cards[4], cards[5]]],
        colWidths=[CONTENT_WIDTH / 3] * 3,
        rowHeights=[92, 92],
        hAlign="CENTER",
    )
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6)]))
    return table


def kpi_rows(analysis: dict) -> list[list[str]]:
    kpis = analysis.get("kpis", {})
    return [
        ["Metric", "Value"],
        ["Revenue", money(kpis.get("revenue"))],
        ["Profit", money(kpis.get("profit"))],
        ["Orders", number(kpis.get("orders"))],
        ["Customers", number(customer_count(analysis))],
        ["Average Order Value", money(kpis.get("average_order_value"))],
    ]


def customer_count(analysis: dict) -> object:
    kpis = analysis.get("kpis", {})
    if kpis.get("customers") or kpis.get("unique_customers"):
        return kpis.get("customers") or kpis.get("unique_customers")
    segments = analysis.get("customer_analysis", {}).get("segments", [])
    if segments:
        return sum(float(segment.get("customers", 0) or 0) for segment in segments)
    return 0


def rows_for_ranking(rows: list[dict], label_key: str, metric_key: str, limit: int = 8) -> list[list[str]]:
    output = [["Item", "Value"]]
    for row in rows[:limit]:
        output.append([str(row.get(label_key) or "Unknown"), money(row.get(metric_key))])
    return output


def chart_title(drawing: Drawing, title: str, y: float) -> None:
    drawing.add(String(0, y, title, fontName="Helvetica-Bold", fontSize=13, fillColor=NAVY))
    drawing.add(Line(0, y - 7, CHART_WIDTH, y - 7, strokeColor=colors.HexColor("#e2e8f0"), strokeWidth=0.8))


def bar_chart(title: str, rows: list[dict], label_key: str, metric_key: str) -> Drawing | None:
    visible = rows[:8]
    values = [float(row.get(metric_key, 0) or 0) for row in visible]
    if not values:
        return None
    drawing = Drawing(CHART_WIDTH, 250)
    chart_title(drawing, title, 234)
    chart = HorizontalBarChart()
    chart.x = 135
    chart.y = 34
    chart.height = 165
    chart.width = CHART_WIDTH - 150
    chart.data = [values]
    chart.categoryAxis.categoryNames = [
        (str(row.get(label_key) or "Unknown")[:34] + ("..." if len(str(row.get(label_key) or "")) > 34 else ""))
        for row in visible
    ]
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7.8
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 8
    chart.valueAxis.valueMin = 0
    chart.valueAxis.visibleGrid = True
    chart.valueAxis.gridStrokeColor = colors.HexColor("#e5e7eb")
    chart.bars[0].fillColor = BLUE
    drawing.add(chart)
    return drawing


def line_chart(title: str, rows: list[dict], metric_key: str) -> Drawing | None:
    values = [float(row.get(metric_key, 0) or 0) for row in rows[:12]]
    if len(values) < 2:
        return None
    drawing = Drawing(CHART_WIDTH, 245)
    chart_title(drawing, title, 230)
    chart = LinePlot()
    chart.x = 50
    chart.y = 35
    chart.height = 155
    chart.width = CHART_WIDTH - 70
    chart.data = [list(enumerate(values))]
    chart.lines[0].strokeColor = GREEN
    chart.lines[0].strokeWidth = 2.2
    chart.yValueAxis.valueMin = 0
    chart.yValueAxis.labels.fontName = "Helvetica"
    chart.yValueAxis.labels.fontSize = 8
    chart.xValueAxis.labels.fontName = "Helvetica"
    chart.xValueAxis.labels.fontSize = 8
    drawing.add(chart)
    return drawing


def centered_chart(chart: Drawing) -> Table:
    return Table([[chart]], colWidths=[CONTENT_WIDTH], hAlign="CENTER", style=[("ALIGN", (0, 0), (-1, -1), "CENTER")])


def parse_ai_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = "Executive Summary"
    sections[current] = []
    for line in text.splitlines():
        stripped = line.strip()
        heading = re.match(r"^#{1,4}\s+(.+)$", stripped)
        if heading:
            current = heading.group(1).strip()
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(line)
    return sections


def ai_markdown_flowables(text: str, style_map: dict, max_items: int | None = None) -> list:
    elements: list = []
    paragraph_lines: list[str] = []
    emitted = 0

    def limit_reached() -> bool:
        return max_items is not None and emitted >= max_items

    def add_item(item) -> None:
        nonlocal emitted
        if limit_reached():
            return
        elements.append(item)
        emitted += 1

    def flush_paragraph() -> None:
        if not paragraph_lines:
            return
        paragraph = "<br/>".join(inline_markdown(line) for line in paragraph_lines)
        if paragraph:
            add_item(Paragraph(paragraph, style_map["AIBody"]))
        paragraph_lines.clear()

    for raw_line in text.splitlines():
        if limit_reached():
            break
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            continue
        heading = re.match(r"^(#{1,4})\s+(.+)$", stripped)
        if heading:
            flush_paragraph()
            add_item(Paragraph(inline_markdown(heading.group(2)), style_map["AIHeading"]))
            continue
        bullet = re.match(r"^[-*]\s+(.+)$", stripped)
        if bullet:
            flush_paragraph()
            add_item(Paragraph(inline_markdown(bullet.group(1)), style_map["AIBullet"], bulletText="-"))
            continue
        numbered = re.match(r"^(\d+)[.)]\s+(.+)$", stripped)
        if numbered:
            flush_paragraph()
            add_item(Paragraph(inline_markdown(numbered.group(2)), style_map["AIBullet"], bulletText=f"{numbered.group(1)}."))
            continue
        paragraph_lines.append(line)
    flush_paragraph()
    return elements


def executive_summary_page(insights: str, style_map: dict) -> list:
    target_sections = ["Executive Summary", "Key Findings", "Business Risks", "Risks", "Growth Opportunities", "Opportunities"]
    section_limits = {
        "Executive Summary": 1,
        "Key Findings": 2,
        "Business Risks": 2,
        "Risks": 2,
        "Growth Opportunities": 2,
        "Opportunities": 2,
    }
    sections = parse_ai_sections(insights)
    elements: list = [Paragraph("Executive Summary", style_map["Title"]), cover_rule(), Spacer(1, 14)]
    used_titles: set[str] = set()
    for title in target_sections:
        display_title = "Business Risks" if title == "Risks" else "Growth Opportunities" if title == "Opportunities" else title
        if display_title in used_titles or title not in sections:
            continue
        used_titles.add(display_title)
        section_text = "\n".join(sections[title]).strip()
        if display_title == "Executive Summary":
            lines = section_text.splitlines()
            if lines:
                first_line = re.sub(r"^[#\s*_]+|[\s*_]+$", "", lines[0]).strip()
                if first_line.lower() == "executive summary":
                    section_text = "\n".join(lines[1:]).strip()
        if not section_text:
            continue
        if display_title != "Executive Summary":
            elements.append(Paragraph(display_title, style_map["AIHeading"]))
        elements.extend(ai_markdown_flowables(section_text, style_map, max_items=section_limits[title]))
        elements.append(Spacer(1, 2))
        if len(used_titles) >= 4:
            break
    if len(elements) <= 3:
        elements.extend(ai_markdown_flowables(insights, style_map, max_items=10))
    return elements


def recommendation_blocks(recommendations: dict, style_map: dict) -> list:
    elements: list = [Paragraph("Strategic Recommendations", style_map["Section"])]
    items = recommendations.get("recommendations", [])
    if not items:
        return elements + [Paragraph("No recommendations could be generated from the available analytics.", style_map["BodyText"])]
    for item in items[:8]:
        elements.append(
            KeepTogether(
                [
                    Paragraph(f"Recommendation: {inline_markdown(str(item['title']))}", style_map["Subheading"]),
                    Paragraph(f"<b>Reason:</b> {inline_markdown(str(item['rationale']))}", style_map["BodyText"]),
                    Paragraph(f"<b>Expected Business Impact:</b> {impact_for_category(item['category'])}", style_map["Small"]),
                    Spacer(1, 10),
                ]
            )
        )
    return elements


def impact_for_category(category: str) -> str:
    impacts = {
        "Products to promote": "Increase revenue from proven high-performing products.",
        "Products to discontinue": "Reduce operational drag from low-performing products.",
        "Regions needing attention": "Improve regional balance and recover underperforming markets.",
        "Marketing opportunities": "Scale messaging where market response is strongest.",
        "Upselling opportunities": "Grow customer lifetime value.",
        "Cross-selling opportunities": "Increase average order value through bundles.",
        "Inventory improvements": "Reduce tied-up capital and stock inefficiency.",
        "Pricing recommendations": "Protect margin while preserving demand.",
        "Customer recommendations": "Improve retention and reactivation.",
    }
    return impacts.get(category, "Improve business performance using the supplied analytics.")


def generate_pdf_report(
    user_id: int,
    dataset: dict,
    analysis: dict,
    recommendations: dict,
    ml_results: dict,
    insights: str | None = None,
) -> tuple[str, Path]:
    filename = f"{uuid4().hex}.pdf"
    path = report_user_dir(user_id) / filename
    style_map = styles()
    document = SimpleDocTemplate(
        str(path),
        pagesize=letter,
        title=f"DataVista Executive Report - {dataset['name']}",
        rightMargin=REPORT_MARGIN,
        leftMargin=REPORT_MARGIN,
        topMargin=0.62 * inch,
        bottomMargin=0.55 * inch,
    )

    roles = analysis.get("detected_roles", {})
    revenue_key = roles.get("revenue", "revenue")
    product_key = roles.get("product", "product")
    region_key = roles.get("region", "region")
    kpis = analysis.get("kpis", {})
    health = calculate_business_health_score(analysis)
    quality = dataset.get("data_quality_score")
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    executive_summary = insights or (
        "This report summarizes the uploaded dataset using DataVista's cleaning, analytics, recommendation, "
        "and machine learning pipeline. Enable Gemini to include AI-generated executive narrative."
    )

    elements: list = [
        Spacer(1, 72),
        Paragraph("DataVista", style_map["CoverKicker"]),
        Paragraph("Business Intelligence Report", style_map["Title"]),
        cover_rule(),
        Spacer(1, 26),
        Paragraph(escape(str(dataset["name"])), style_map["Heading2"]),
        Spacer(1, 34),
        styled_table(
            [
                ["Report Detail", "Value"],
                ["Generated", generated_at],
                ["Rows", number(dataset.get("row_count"))],
                ["Columns", number(dataset.get("column_count"))],
                ["Data Quality Score", f"{quality}/100" if quality is not None else "Not available"],
                ["Prepared by", "DataVista"],
            ],
            widths=[CONTENT_WIDTH * 0.35, CONTENT_WIDTH * 0.65],
        ),
        Spacer(1, 90),
        Paragraph("Prepared for executive review, portfolio demonstration, and strategic business analysis.", style_map["CoverMeta"]),
        PageBreak(),
        Paragraph("Executive Dashboard", style_map["Title"]),
        cover_rule(),
        Spacer(1, 20),
        dashboard_cards(kpis, dataset, customer_count(analysis)),
        Spacer(1, 24),
        Paragraph("KPI Detail", style_map["Section"]),
        styled_table(kpi_rows(analysis), widths=[CONTENT_WIDTH * 0.72, CONTENT_WIDTH * 0.28]),
        Spacer(1, 18),
        styled_table(
            [
                ["Score", "Value"],
                ["Business Health Score", f"{health['score']}/100" if health["score"] is not None else "Not enough data"],
                ["Data Quality Score", f"{quality}/100" if quality is not None else "Not available"],
            ],
            widths=[CONTENT_WIDTH * 0.72, CONTENT_WIDTH * 0.28],
        ),
        PageBreak(),
        *executive_summary_page(executive_summary, style_map),
        PageBreak(),
        Paragraph("Analytics", style_map["Title"]),
        cover_rule(),
    ]

    trend = analysis.get("time_analysis", {}).get("monthly", [])
    trend_chart = line_chart("Revenue Trend", trend, revenue_key)
    if trend_chart:
        elements.extend([Spacer(1, 18), centered_chart(trend_chart), Spacer(1, 18)])

    products = analysis.get("product_analysis", {}).get("best_sellers", [])
    if products:
        elements.extend(section_title("Top Products", style_map))
        chart = bar_chart("Product Sales", products, product_key, revenue_key)
        if chart:
            elements.extend([centered_chart(chart), Spacer(1, 14)])
        elements.append(styled_table(rows_for_ranking(products, product_key, revenue_key), widths=[CONTENT_WIDTH * 0.74, CONTENT_WIDTH * 0.26]))

    regions = analysis.get("regional_analysis", {}).get("performance", [])
    if regions:
        elements.extend(section_title("Regional Performance", style_map))
        chart = bar_chart("Regional Revenue", regions, region_key, revenue_key)
        if chart:
            elements.extend([centered_chart(chart), Spacer(1, 14)])
        elements.append(styled_table(rows_for_ranking(regions, region_key, revenue_key), widths=[CONTENT_WIDTH * 0.74, CONTENT_WIDTH * 0.26]))

    forecast = ml_results.get("sales_forecast", {})
    if forecast.get("available"):
        forecast_rows = [["Period", "Predicted Sales"]] + [
            [row["date"], money(row["predicted_sales"])] for row in forecast.get("forecast", [])[:6]
        ]
        elements.extend(section_title("Forecast Outlook", style_map))
        forecast_chart = line_chart("Forecast", forecast.get("forecast", []), "predicted_sales")
        if forecast_chart:
            elements.extend([centered_chart(forecast_chart), Spacer(1, 14)])
        elements.append(styled_table(forecast_rows, widths=[CONTENT_WIDTH * 0.72, CONTENT_WIDTH * 0.28]))

    elements.extend([PageBreak(), *recommendation_blocks(recommendations, style_map)])
    elements.extend([PageBreak(), Paragraph("Appendix", style_map["Title"]), cover_rule(), Paragraph("Data Quality Notes", style_map["Section"])])
    cleaning_report = dataset.get("cleaning_report") or {}
    quality_recommendations = cleaning_report.get("quality_recommendations", [])
    if quality_recommendations:
        for recommendation in quality_recommendations:
            elements.append(Paragraph(inline_markdown(str(recommendation)), style_map["AIBullet"], bulletText="-"))
    else:
        elements.append(Paragraph("No major data quality recommendations were generated.", style_map["BodyText"]))

    document.build(elements, onFirstPage=page_header_footer, onLaterPages=page_header_footer)
    return filename, path
