from __future__ import annotations

from dataclasses import replace
from typing import Any

from .recommender import Customer, load_catalog, recommend, score_product


QUESTION_OPTIONS = [
    {"id": "why_top", "label": "왜 이 상품이 1위인가요?"},
    {"id": "compare_top", "label": "1위와 2위를 비교해 주세요"},
    {"id": "easier_bonus", "label": "우대금리를 쉽게 더 받는 방법은?"},
    {"id": "liquidity", "label": "급하게 돈이 필요할 때 유리한 상품은?"},
    {"id": "inclusive_support", "label": "저에게 맞는 포용금융 상품이 있나요?"},
    {"id": "branch_help", "label": "창구 상담이 필요한 상품이 있나요?"}
]
QUESTION_IDS = {item["id"] for item in QUESTION_OPTIONS}

FEATURE_LABELS = {
    "additional_deposit": "추가입금",
    "emergency_withdrawal": "비상금 출금",
    "split_withdrawal": "분할해지",
    "flexible_term": "자유로운 가입기간",
    "auto_renew": "자동 재예치",
    "rotating_rate": "회전주기 금리",
    "public_interest": "공익형 지원",
    "esg": "친환경 활동 연계"
}


def _product_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {product["id"]: product for product in catalog["products"]}


def _citation(product: dict[str, Any], detail: str) -> dict[str, str]:
    return {
        "product_id": product["id"],
        "title": product["name"],
        "detail": detail,
        "url": product["source_url"]
    }


def _features(item: dict[str, Any]) -> str:
    labels = [FEATURE_LABELS.get(feature, feature) for feature in item["features"]]
    return ", ".join(labels) if labels else "별도 편의기능 없음"


def _money(value: int) -> str:
    return f"{value:,}원"


def _retrieve(
    question_id: str,
    result: dict[str, Any],
    catalog: dict[str, Any],
) -> list[dict[str, Any]]:
    candidates = result["recommendations"]
    if question_id == "liquidity":
        candidates = sorted(
            candidates, key=lambda item: item["liquidity_score"], reverse=True
        )
    elif question_id == "inclusive_support":
        candidates = sorted(
            candidates, key=lambda item: item["inclusion"]["level"], reverse=True
        )
    return candidates[:2]


def advise(
    question_id: str,
    customer: Customer,
    catalog: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if question_id not in QUESTION_IDS:
        raise ValueError("제공된 상담 질문 중 하나를 선택해 주세요.")

    catalog = catalog or load_catalog()
    result = recommend(customer, limit=10, catalog=catalog)
    recommendations = result["recommendations"]
    if not recommendations:
        return {
            "question_id": question_id,
            "answer": "현재 입력 조건으로 가입 가능한 상품을 찾지 못했습니다. 금액, 기간 또는 가입채널을 다시 확인해 주세요.",
            "citations": [],
            "retrieved_product_ids": []
        }

    products = _product_map(catalog)
    top = recommendations[0]
    citations = []

    if question_id == "why_top":
        applied = ", ".join(top["matched_conditions"]) or "기본금리"
        answer = (
            f"{top['name']}은 현재 추천 목표에서 {top['recommendation_score']:.1f}점을 받아 1위입니다. "
            f"{customer.term_months}개월 기본금리 연 {top['base_rate']:.2f}%에 "
            f"{applied} 조건이 반영되어 실현 가능 금리는 연 {top['achievable_rate']:.2f}%입니다. "
            f"예상 세전이자는 {_money(top['gross_interest'])}, 일반과세 가정 세후이자는 "
            f"약 {_money(top['net_interest'])}입니다."
        )
        citations.append(_citation(products[top["id"]], "기간별 기본금리와 우대조건"))

    elif question_id == "compare_top":
        if len(recommendations) < 2:
            answer = "현재 조건에서는 비교할 수 있는 추천상품이 한 개뿐입니다."
        else:
            second = recommendations[1]
            difference = top["gross_interest"] - second["gross_interest"]
            answer = (
                f"1위 {top['name']}은 연 {top['achievable_rate']:.2f}%, "
                f"2위 {second['name']}은 연 {second['achievable_rate']:.2f}%입니다. "
                f"예상 세전이자 차이는 {_money(abs(difference))}이며, "
                f"1위 편의기능은 {_features(top)}, 2위는 {_features(second)}입니다. "
                "금리 차이가 작다면 중도자금 필요 가능성과 충족하기 쉬운 조건을 함께 확인하는 편이 좋습니다."
            )
            citations.extend(
                [
                    _citation(products[top["id"]], "1위 상품의 금리·편의기능"),
                    _citation(products[second["id"]], "2위 상품의 금리·편의기능")
                ]
            )

    elif question_id == "easier_bonus":
        actions = top["next_actions"]
        if not actions:
            answer = (
                f"{top['name']}은 현재 확인된 조건으로 상품 우대상한을 모두 반영했습니다. "
                "추가 조건을 만들기보다 가입 시 최종 적용금리를 확인하는 것이 좋습니다."
            )
        else:
            action_text = ", ".join(
                f"{item['label']}(최대 +{item['additional_rate']:.2f}%p)"
                for item in actions
            )
            answer = (
                f"{top['name']}에서 추가로 확인할 조건은 {action_text}입니다. "
                "새 카드 사용이나 불필요한 거래를 늘리기 전에, 추가 이자가 비용보다 큰지 먼저 비교하세요."
            )
        citations.append(_citation(products[top["id"]], "상품별 우대금리 조건"))

    elif question_id == "liquidity":
        retrieved = _retrieve(question_id, result, catalog)
        liquid = retrieved[0]
        answer = (
            f"현재 가입 가능한 상품 중 자금 활용 편의가 가장 높은 상품은 {liquid['name']}입니다. "
            f"지원 기능은 {_features(liquid)}입니다. 다만 분할해지나 중도해지 금액에는 "
            "약정금리보다 낮은 중도해지이율이 적용될 수 있으므로 상품설명서를 확인해야 합니다."
        )
        citations.append(_citation(products[liquid["id"]], "분할해지·추가입금 등 금융서비스"))

    elif question_id == "inclusive_support":
        matched = [item for item in recommendations if item["inclusion"]["matched"]]
        if matched:
            inclusive = matched[0]
            reasons = " ".join(inclusive["inclusion"]["reasons"])
            answer = (
                f"입력하신 자격과 직접 연결되는 포용금융 상품은 {inclusive['name']}입니다. "
                f"{reasons} 상품이며, 현재 실현 가능 금리는 연 {inclusive['achievable_rate']:.2f}%입니다. "
                "포용금융 배지는 실제 자격이 확인된 경우에만 표시되며 최종 가입 시 증빙이 필요할 수 있습니다."
            )
            citations.append(_citation(products[inclusive["id"]], "가입대상과 공익 지원 목적"))
        else:
            answer = (
                "현재 입력에서는 소상공인 또는 취약계층·농어촌 전용 자격과 직접 연결되는 상품이 없습니다. "
                "그렇더라도 전체 상품을 동일하게 비교해 연령이나 인기순 때문에 유리한 상품이 누락되지 않도록 했습니다. "
                "민감한 자격정보는 필요한 항목만 직접 선택하도록 설계했습니다."
            )

    else:
        branch_customer = replace(customer, channel="branch")
        branch_only = []
        for product in catalog["products"]:
            if product["channels"] != ["branch"]:
                continue
            scored = score_product(product, branch_customer)
            if scored["eligible"]:
                branch_only.append(scored)
        if branch_only:
            names = ", ".join(item["name"] for item in branch_only)
            answer = (
                f"입력하신 금액·기간·자격에서 창구로만 가입 가능한 상품은 {names}입니다. "
                "온라인 추천 결과와 금리·이동시간·증빙 필요 여부를 비교한 뒤 가까운 우체국에서 상담하세요."
            )
            citations.extend(
                _citation(products[item["id"]], "창구 전용 가입채널과 가입대상")
                for item in branch_only[:2]
            )
        else:
            answer = (
                "현재 입력 조건에서 별도로 안내할 창구 전용 상품은 없습니다. "
                "비대면 가입이 어렵다면 추천상품명을 가지고 우체국 창구에서 가입 가능 여부를 확인할 수 있습니다."
            )

    retrieved = _retrieve(question_id, result, catalog)
    return {
        "question_id": question_id,
        "answer": answer,
        "citations": citations,
        "retrieved_product_ids": [item["id"] for item in retrieved],
        "method": "structured-retrieval-plus-template-generation"
    }
