from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS_PATH = ROOT / "data" / "products.json"
FLEXIBILITY_WEIGHTS = {
    "emergency_withdrawal": 4,
    "split_withdrawal": 3,
    "additional_deposit": 2,
    "flexible_term": 2,
    "auto_renew": 1,
    "rotating_rate": 1,
}
PRIORITY_WEIGHTS = {
    "highest_interest": {"financial": 0.85, "simplicity": 0.1, "audience": 0.05},
    "easy_conditions": {"financial": 0.6, "simplicity": 0.35, "audience": 0.05},
    "liquidity": {"financial": 0.55, "liquidity": 0.4, "audience": 0.05},
    "inclusive": {
        "financial": 0.6,
        "inclusion": 0.25,
        "simplicity": 0.1,
        "audience": 0.05,
    },
}


@dataclass(frozen=True)
class Customer:
    age: int
    amount: int
    term_months: int
    channel: str = "online"
    priority: str = "highest_interest"
    salary_or_pension: bool = False
    checking_balance: int = 0
    card_spend: int = 0
    first_term_deposit: bool = False
    auto_renew: bool = False
    eco_points: bool = False
    donation: bool = False
    paperless: bool = True
    eco_pledge: bool = False
    referral_count: int = 0
    daily_savings: bool = False
    postal_contract: bool = False
    vip: bool = False
    business_owner: bool = False
    yellow_umbrella: bool = False
    vulnerable_or_rural: bool = False
    government_support: bool = False
    disability_card: bool = False
    online_product_new: bool = False
    automatic_transfers: int = 0

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> "Customer":
        fields = cls.__dataclass_fields__
        clean = {key: values[key] for key in fields if key in values}
        customer = cls(**clean)
        if customer.priority not in PRIORITY_WEIGHTS:
            raise ValueError("지원하지 않는 추천 목표입니다.")
        if customer.amount <= 0 or customer.term_months <= 0:
            raise ValueError("예치금액과 가입기간은 0보다 커야 합니다.")
        if customer.channel not in {"online", "branch"}:
            raise ValueError("가입채널은 online 또는 branch여야 합니다.")
        return customer


def load_catalog(path: Path = DEFAULT_PRODUCTS_PATH) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _rule_matches(rule: dict[str, Any], customer: Customer) -> bool:
    actual = getattr(customer, rule["field"])
    op = rule["op"]
    if op == "truthy":
        return bool(actual)
    if op == "eq":
        return actual == rule["value"]
    if op == "gte":
        return actual >= rule["value"]
    raise ValueError(f"지원하지 않는 비교 연산자: {op}")


def _base_rate_for_term(product: dict[str, Any], term_months: int) -> float | None:
    for item in product["rate_ranges"]:
        if item["min_months"] <= term_months <= item["max_months"]:
            return float(item["base_rate"])
    return None


def _eligibility_reason(product: dict[str, Any], customer: Customer) -> str | None:
    if customer.amount < product["min_amount"]:
        return f"최소 가입금액 {product['min_amount']:,}원 미달"
    maximum = product["max_amount"]
    if maximum is not None and customer.amount > maximum:
        return f"최대 가입금액 {maximum:,}원 초과"
    allowed_terms = product.get("allowed_terms")
    if allowed_terms and customer.term_months not in allowed_terms:
        terms = "·".join(str(term) for term in allowed_terms)
        return f"가입기간은 {terms}개월만 가능"
    if not product["min_term"] <= customer.term_months <= product["max_term"]:
        return f"가입기간 {product['min_term']}~{product['max_term']}개월 불일치"
    if _base_rate_for_term(product, customer.term_months) is None:
        return "선택한 가입기간의 고시금리 없음"
    if customer.channel not in product["channels"]:
        return "선택한 가입채널에서 가입 불가"
    if product["segment"] == "business_owner" and not customer.business_owner:
        return "소상공인·소기업 대표 전용"
    if product["segment"] == "vulnerable_or_rural" and not customer.vulnerable_or_rural:
        return "취약계층·나눔고객·농어촌 주민 전용"
    return None


def _inclusion_match(product: dict[str, Any], customer: Customer) -> dict[str, Any]:
    tags = set(product.get("inclusive_tags", []))
    reasons = []
    level = 0
    if "small_business" in tags and customer.business_owner:
        reasons.append("소상공인·소기업 대표의 금융비용 절감과 자산형성 지원")
        level = 100
    if {"vulnerable", "rural"}.intersection(tags) and customer.vulnerable_or_rural:
        reasons.append("취약계층·나눔고객·농어촌 주민의 금융 접근성 지원")
        level = 100
    if "senior_access" in tags and customer.age >= 65:
        reasons.append("고령 고객의 목돈 관리와 금융 편의 지원")
        level = max(level, 60)
    return {"matched": bool(reasons), "level": level, "reasons": reasons}


def _apply_bonus_rules(
    product: dict[str, Any], customer: Customer
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], float]:
    matched = []
    unmatched = []
    for rule in product["bonus_rules"]:
        (matched if _rule_matches(rule, customer) else unmatched).append(rule)

    remaining = float(product["bonus_cap"])
    applied = []
    for rule in matched:
        if remaining <= 0:
            break
        applied_rate = min(float(rule["rate"]), remaining)
        applied.append({"label": rule["label"], "rate": round(applied_rate, 3)})
        remaining = round(remaining - applied_rate, 4)
    return applied, unmatched, round(float(product["bonus_cap"]) - remaining, 4)


def score_product(product: dict[str, Any], customer: Customer) -> dict[str, Any]:
    reason = _eligibility_reason(product, customer)
    if reason:
        return {
            "id": product["id"],
            "name": product["name"],
            "eligible": False,
            "reason": reason,
        }

    base_rate = _base_rate_for_term(product, customer.term_months)
    assert base_rate is not None
    applied, unmatched, applied_bonus = _apply_bonus_rules(product, customer)
    rate = round(base_rate + applied_bonus, 3)
    max_rate = round(base_rate + float(product["bonus_cap"]), 3)
    gross_interest = round(
        customer.amount * (rate / 100) * (customer.term_months / 12)
    )
    net_interest = round(gross_interest * (1 - 0.154))

    remaining_bonus = round(float(product["bonus_cap"]) - applied_bonus, 4)
    next_actions = []
    if remaining_bonus > 0:
        actionable = [item for item in unmatched if item.get("actionable", True)]
        actionable.sort(key=lambda item: item["rate"], reverse=True)
        for item in actionable:
            if remaining_bonus <= 0:
                break
            additional_rate = min(float(item["rate"]), remaining_bonus)
            next_actions.append(
                {"label": item["label"], "additional_rate": additional_rate}
            )
            remaining_bonus = round(remaining_bonus - additional_rate, 4)

    liquidity_raw = sum(
        FLEXIBILITY_WEIGHTS.get(feature, 0) for feature in product["features"]
    )
    liquidity_score = min(100.0, liquidity_raw / 9 * 100)
    simplicity_score = max(0.0, 100.0 - len(next_actions) * 22)
    inclusion = _inclusion_match(product, customer)
    audience_match = True
    if "audience_min_age" in product and customer.age < product["audience_min_age"]:
        audience_match = False
    if "audience_max_age" in product and customer.age > product["audience_max_age"]:
        audience_match = False
    return {
        "id": product["id"],
        "name": product["name"],
        "description": product["description"],
        "eligible": True,
        "base_rate": base_rate,
        "applied_bonus": applied_bonus,
        "achievable_rate": rate,
        "max_rate": max_rate,
        "gross_interest": gross_interest,
        "net_interest": net_interest,
        "applied_conditions": applied,
        "matched_conditions": [item["label"] for item in applied],
        "next_actions": next_actions[:3],
        "features": product["features"],
        "channels": product["channels"],
        "liquidity_score": round(liquidity_score, 1),
        "simplicity_score": round(simplicity_score, 1),
        "inclusion": inclusion,
        "audience_match": audience_match,
        "source_url": product["source_url"],
        "legacy_recommended": False,
    }


def _rank_products(products: list[dict[str, Any]], priority: str) -> None:
    if not products:
        return
    max_interest = max(item["gross_interest"] for item in products) or 1
    weights = PRIORITY_WEIGHTS[priority]
    for item in products:
        components = {
            "financial": item["gross_interest"] / max_interest * 100,
            "simplicity": item["simplicity_score"],
            "liquidity": item["liquidity_score"],
            "inclusion": item["inclusion"]["level"],
            "audience": 100.0 if item["audience_match"] else 0.0,
        }
        item["score_breakdown"] = {
            key: round(value, 1) for key, value in components.items()
        }
        item["recommendation_score"] = round(
            sum(components[key] * weight for key, weight in weights.items()), 2
        )
    if priority == "highest_interest":
        products.sort(
            key=lambda item: (
                item["gross_interest"],
                item["audience_match"],
                item["simplicity_score"],
                item["liquidity_score"],
            ),
            reverse=True,
        )
    else:
        products.sort(
            key=lambda item: (
                item["recommendation_score"],
                item["gross_interest"],
                item["achievable_rate"],
            ),
            reverse=True,
        )


def recommend(
    customer: Customer,
    limit: int = 5,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    catalog = catalog or load_catalog()
    scored = [score_product(product, customer) for product in catalog["products"]]
    eligible = [item for item in scored if item["eligible"]]
    excluded = [item for item in scored if not item["eligible"]]
    _rank_products(eligible, customer.priority)
    for index, item in enumerate(eligible, start=1):
        item["rank"] = index

    legacy_ids = set(legacy_age_only(customer, catalog))
    for item in eligible:
        item["legacy_recommended"] = item["id"] in legacy_ids
    legacy = [item for item in eligible if item["legacy_recommended"]]
    legacy.sort(key=lambda item: item["gross_interest"], reverse=True)
    best = eligible[0] if eligible else None
    legacy_best = legacy[0] if legacy else None
    uplift = 0
    if best and legacy_best:
        uplift = best["gross_interest"] - legacy_best["gross_interest"]

    reference_date = date.fromisoformat(catalog["rate_reference_date"])
    data_age_days = max(0, (date.today() - reference_date).days)
    return {
        "as_of": catalog["as_of"],
        "rate_reference_date": catalog["rate_reference_date"],
        "data_freshness": {
            "age_days": data_age_days,
            "status": (
                "fresh"
                if data_age_days <= 3
                else "warning"
                if data_age_days <= 7
                else "stale"
            ),
        },
        "priority": customer.priority,
        "customer": customer.__dict__,
        "recommendations": eligible[:limit],
        "excluded": excluded,
        "comparison": {
            "legacy_candidate_count": len(legacy),
            "full_candidate_count": len(eligible),
            "best_legacy_product": legacy_best["name"] if legacy_best else None,
            "best_product": best["name"] if best else None,
            "interest_difference": uplift,
        },
    }


def legacy_age_only(customer: Customer, catalog: dict[str, Any] | None = None) -> list[str]:
    """연령 태그와 전략추천 상품만 노출하는 단순 기준선."""
    catalog = catalog or load_catalog()
    candidates = {"200109200101"}
    if customer.age >= 50:
        candidates.add("200108800101")
    elif 20 <= customer.age <= 49:
        candidates.add("200100200101")
    return [
        product["id"]
        for product in catalog["products"]
        if product["id"] in candidates
        and _eligibility_reason(product, customer) is None
    ]
