from __future__ import annotations

from typing import Any


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def growth_score(analysis: dict[str, Any]) -> tuple[float, str]:
    monthly = analysis.get("time_analysis", {}).get("monthly", [])
    revenue_column = analysis.get("detected_roles", {}).get("revenue", "revenue")
    values = [float(row.get(revenue_column, 0) or 0) for row in monthly]
    if len(values) < 2 or values[0] <= 0:
        return 50.0, "Revenue growth has limited trend history."
    growth = (values[-1] - values[0]) / values[0]
    score = clamp(50 + growth * 100)
    return score, f"Revenue changed {growth:.1%} from the first to latest period."


def profitability_score(analysis: dict[str, Any]) -> tuple[float, str]:
    kpis = analysis.get("kpis", {})
    revenue = float(kpis.get("revenue") or 0)
    profit = float(kpis.get("profit") or 0)
    if revenue <= 0:
        return 50.0, "Profitability cannot be fully scored without revenue."
    margin = profit / revenue
    score = clamp(50 + margin * 200)
    return score, f"Profit margin is {margin:.1%}."


def retention_score(analysis: dict[str, Any]) -> tuple[float, str]:
    customer = analysis.get("customer_analysis", {})
    top_customers = customer.get("top_customers", [])
    repeat_customers = float(customer.get("repeat_customers") or 0)
    if not top_customers:
        return 50.0, "Customer retention needs customer-level history."
    rate = repeat_customers / len(top_customers)
    score = clamp(rate * 100)
    return score, f"{repeat_customers:.0f} of {len(top_customers)} top customers are repeat customers."


def product_score(analysis: dict[str, Any]) -> tuple[float, str]:
    products = analysis.get("product_analysis", {}).get("best_sellers", [])
    revenue_column = analysis.get("detected_roles", {}).get("revenue", "revenue")
    if len(products) < 2:
        return 50.0, "Product performance needs at least two product records."
    revenues = [float(row.get(revenue_column, 0) or 0) for row in products]
    total = sum(revenues)
    if total <= 0:
        return 50.0, "Product performance cannot be scored without product revenue."
    top_share = max(revenues) / total
    score = clamp(100 - max(0, top_share - 0.35) * 120)
    return score, f"Top product contributes {top_share:.1%} of ranked product revenue."


def regional_score(analysis: dict[str, Any]) -> tuple[float, str]:
    regions = analysis.get("regional_analysis", {}).get("performance", [])
    revenue_column = analysis.get("detected_roles", {}).get("revenue", "revenue")
    if len(regions) < 2:
        return 50.0, "Regional performance needs at least two regions."
    revenues = [float(row.get(revenue_column, 0) or 0) for row in regions]
    total = sum(revenues)
    if total <= 0:
        return 50.0, "Regional performance cannot be scored without regional revenue."
    top_share = max(revenues) / total
    score = clamp(100 - max(0, top_share - 0.45) * 110)
    return score, f"Top region contributes {top_share:.1%} of ranked regional revenue."


def calculate_business_health_score(analysis: dict[str, Any] | None) -> dict[str, Any]:
    if not analysis:
        return {
            "score": None,
            "status": "Business health scoring will activate after you upload and analyze a dataset.",
            "factors": [],
        }

    calculators = {
        "Revenue Growth": growth_score,
        "Profitability": profitability_score,
        "Customer Retention": retention_score,
        "Product Performance": product_score,
        "Regional Performance": regional_score,
    }
    weights = {
        "Revenue Growth": 0.25,
        "Profitability": 0.25,
        "Customer Retention": 0.20,
        "Product Performance": 0.15,
        "Regional Performance": 0.15,
    }
    factors = []
    weighted_score = 0.0
    for name, calculator in calculators.items():
        score, explanation = calculator(analysis)
        weighted_score += score * weights[name]
        factors.append({"name": name, "score": round(score), "weight": weights[name], "explanation": explanation})

    final_score = round(clamp(weighted_score))
    if final_score >= 75:
        status = "Healthy business performance with strong supporting analytics."
    elif final_score >= 55:
        status = "Mixed business performance with targeted improvement opportunities."
    else:
        status = "Business performance needs attention across multiple analytics areas."

    return {"score": final_score, "status": status, "factors": factors}
