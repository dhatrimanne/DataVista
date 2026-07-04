from __future__ import annotations

from typing import Any


def recommendation(category: str, title: str, rationale: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"category": category, "title": title, "rationale": rationale, "evidence": evidence}


def metric_value(row: dict[str, Any], metric: str | None) -> float:
    if not metric:
        return 0.0
    return float(row.get(metric, 0) or 0)


def build_recommendations(analysis: dict[str, Any]) -> dict[str, Any]:
    roles = analysis.get("detected_roles", {})
    revenue = roles.get("revenue", "revenue")
    product = roles.get("product", "product")
    region = roles.get("region", "region")
    recommendations: list[dict[str, Any]] = []

    products = analysis.get("product_analysis", {})
    best_sellers = products.get("best_sellers", [])
    worst_sellers = products.get("worst_sellers", [])
    profitable = products.get("most_profitable", [])
    least_profitable = products.get("least_profitable", [])

    if best_sellers:
        top = best_sellers[0]
        recommendations.append(
            recommendation(
                "Products to promote",
                f"Promote {top.get(product, 'the top product')}",
                "This product leads ranked revenue and is a strong candidate for campaigns or homepage placement.",
                top,
            )
        )
    if worst_sellers:
        weak = worst_sellers[0]
        recommendations.append(
            recommendation(
                "Products to discontinue",
                f"Review {weak.get(product, 'the weakest product')}",
                "This product has the lowest ranked revenue and should be reviewed for pricing, positioning, or retirement.",
                weak,
            )
        )
    if profitable:
        top_profit = profitable[0]
        recommendations.append(
            recommendation(
                "Pricing recommendations",
                f"Protect margin on {top_profit.get(product, 'the most profitable product')}",
                "The product ranks highest by profit, so discounting should be controlled.",
                top_profit,
            )
        )
    if least_profitable:
        low_profit = least_profitable[0]
        recommendations.append(
            recommendation(
                "Inventory improvements",
                f"Audit inventory for {low_profit.get(product, 'the least profitable product')}",
                "Low profit contribution can tie up working capital if inventory is overstocked.",
                low_profit,
            )
        )

    regions = analysis.get("regional_analysis", {}).get("performance", [])
    if len(regions) >= 2:
        weakest = regions[-1]
        recommendations.append(
            recommendation(
                "Regions needing attention",
                f"Investigate {weakest.get(region, 'the weakest region')}",
                "This region ranks lowest by revenue and may need localized sales or marketing support.",
                weakest,
            )
        )
    if regions:
        strongest = regions[0]
        recommendations.append(
            recommendation(
                "Marketing opportunities",
                f"Scale campaigns in {strongest.get(region, 'the strongest region')}",
                "The strongest region can provide proven messaging and channel patterns for expansion.",
                strongest,
            )
        )

    customers = analysis.get("customer_analysis", {})
    top_customers = customers.get("top_customers", [])
    rfm = customers.get("rfm", [])
    if top_customers:
        top_customer = top_customers[0]
        recommendations.append(
            recommendation(
                "Upselling opportunities",
                "Prioritize high-value customer expansion",
                "The highest-value customer cohort is the best starting point for premium offers or annual plans.",
                top_customer,
            )
        )
    if len(best_sellers) >= 2:
        recommendations.append(
            recommendation(
                "Cross-selling opportunities",
                "Bundle top products",
                "The two highest revenue products can be tested together in cross-sell offers.",
                {"primary": best_sellers[0], "secondary": best_sellers[1]},
            )
        )
    if rfm:
        stale = sorted(rfm, key=lambda row: row.get("recency", 0), reverse=True)[0]
        recommendations.append(
            recommendation(
                "Customer recommendations",
                "Launch a reactivation offer",
                "The RFM table shows customers with older recency values who may need re-engagement.",
                stale,
            )
        )

    return {
        "recommendations": recommendations,
        "summary": {
            "total": len(recommendations),
            "covered_categories": sorted({item["category"] for item in recommendations}),
            "unsupported": [] if recommendations else ["No recommendation categories could be generated from the available analytics."],
            "primary_metric": revenue,
        },
    }
