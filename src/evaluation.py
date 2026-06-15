from __future__ import annotations

from statistics import mean
from typing import Any

from .recommender import Customer, legacy_age_only, load_catalog, recommend


PERSONAS = [
    {
        "name": "첫 예금 직장인",
        "customer": Customer(
            age=29,
            amount=10000000,
            term_months=12,
            salary_or_pension=True,
            first_term_deposit=True,
            auto_renew=True,
        ),
    },
    {
        "name": "비대면 카드 이용자",
        "customer": Customer(
            age=42,
            amount=30000000,
            term_months=12,
            card_spend=700000,
            checking_balance=1500000,
            automatic_transfers=2,
        ),
    },
    {
        "name": "연금 수령 시니어",
        "customer": Customer(
            age=63,
            amount=50000000,
            term_months=12,
            salary_or_pension=True,
            checking_balance=1000000,
            auto_renew=True,
        ),
    },
    {
        "name": "친환경 실천 고객",
        "customer": Customer(
            age=36,
            amount=20000000,
            term_months=12,
            eco_points=True,
            donation=True,
            eco_pledge=True,
        ),
    },
    {
        "name": "소상공인",
        "customer": Customer(
            age=47,
            amount=80000000,
            term_months=12,
            channel="branch",
            business_owner=True,
            yellow_umbrella=True,
            checking_balance=3000000,
        ),
    },
    {
        "name": "농어촌 취약계층",
        "customer": Customer(
            age=58,
            amount=5000000,
            term_months=12,
            channel="branch",
            vulnerable_or_rural=True,
            government_support=True,
        ),
    },
]


def evaluate() -> dict[str, Any]:
    catalog = load_catalog()
    rows = []
    for persona in PERSONAS:
        customer = persona["customer"]
        eligible = recommend(customer, limit=20, catalog=catalog)["recommendations"]
        improved = eligible[0]

        legacy_ids = set(legacy_age_only(customer, catalog))
        legacy = [item for item in eligible if item["id"] in legacy_ids]
        legacy.sort(key=lambda item: item["gross_interest"], reverse=True)
        legacy_best = legacy[0] if legacy else None
        legacy_interest = legacy_best["gross_interest"] if legacy_best else 0

        rows.append(
            {
                "persona": persona["name"],
                "legacy_product": legacy_best["name"] if legacy_best else "추천 없음",
                "improved_product": improved["name"],
                "legacy_interest": legacy_interest,
                "improved_interest": improved["gross_interest"],
                "uplift": improved["gross_interest"] - legacy_interest,
                "legacy_hit": bool(legacy_best and legacy_best["id"] == improved["id"]),
            }
        )

    return {
        "personas": rows,
        "summary": {
            "persona_count": len(rows),
            "legacy_top1_hit_rate": sum(row["legacy_hit"] for row in rows) / len(rows),
            "average_interest_uplift": round(mean(row["uplift"] for row in rows)),
            "total_interest_uplift": sum(row["uplift"] for row in rows),
        },
    }
