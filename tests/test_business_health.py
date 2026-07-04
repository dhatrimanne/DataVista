from backend.dashboard.health_score import calculate_business_health_score


def test_business_health_score_uses_analysis_factors():
    analysis = {
        "detected_roles": {"revenue": "revenue"},
        "kpis": {"revenue": 1000, "profit": 250},
        "customer_analysis": {"repeat_customers": 2, "top_customers": [{"customer": "A"}, {"customer": "B"}]},
        "product_analysis": {"best_sellers": [{"product": "A", "revenue": 550}, {"product": "B", "revenue": 450}]},
        "regional_analysis": {"performance": [{"region": "North", "revenue": 600}, {"region": "South", "revenue": 400}]},
        "time_analysis": {"monthly": [{"date": "2026-01", "revenue": 100}, {"date": "2026-02", "revenue": 140}]},
    }

    result = calculate_business_health_score(analysis)

    assert result["score"] >= 70
    assert len(result["factors"]) == 5
    assert result["factors"][0]["name"] == "Revenue Growth"


def test_business_health_score_waits_for_analysis():
    result = calculate_business_health_score(None)

    assert result["score"] is None
    assert result["factors"] == []
