#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.recommender import load_catalog


LIST_URL = "https://mall.epostbank.go.kr/fnIPDGDL00DMR01.do"
DETAIL_URL = "https://mall.epostbank.go.kr/fnIPPSIN0000R02.do"


def post_json(url: str, values: dict[str, object]) -> object:
    body = urllib.parse.urlencode(values).encode()
    request = urllib.request.Request(url, data=body)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def fetch_page(page: int) -> dict:
    return post_json(
        LIST_URL,
        {
            "depsGdsDvsnCd": "2",
            "orderFlag": "",
            "pageNum": str(page),
            "conditions": "",
            "joinChannals": "",
        },
    )


def parse_months(text: str) -> int | None:
    year = re.search(r"(\d+)년", text)
    month = re.search(r"(\d+)개월", text)
    if year:
        return int(year.group(1)) * 12 + (int(month.group(1)) if month else 0)
    if month:
        return int(month.group(1))
    if "30일" in text:
        return 1
    return None


def label_covers_term(label: str, term: int) -> bool:
    clean = label.replace(" ", "").replace("만기", "")
    if "~" not in clean:
        exact = parse_months(clean)
        return exact == term
    start, end = clean.split("~", 1)
    minimum = parse_months(start)
    maximum = parse_months(end)
    if minimum is None or maximum is None:
        return False
    return minimum <= term < maximum if "미만" in end else minimum <= term <= maximum


def official_term_rates(product_id: str) -> dict[int, float]:
    rows = post_json(
        DETAIL_URL,
        {"gdsCd": product_id, "date": date.today().strftime("%Y%m%d")},
    )
    result = {}
    for row in rows:
        if (
            row.get("RINT_KIND_CD") != "01"
            or row.get("INTR_GIVE_KIND_CD") != "02"
            or not row.get("BASS_RINT")
        ):
            continue
        for term in (6, 12, 24, 36):
            if label_covers_term(row["APLCN_TRGT_ETC_CN"], term):
                result[term] = float(row["BASS_RINT"])
    return result


def local_term_rate(product: dict, term: int) -> float | None:
    for item in product["rate_ranges"]:
        if item["min_months"] <= term <= item["max_months"]:
            return float(item["base_rate"])
    return None


def main() -> None:
    official_max = {}
    for page in (0, 1):
        for product in fetch_page(page)["DEP"]:
            official_max[product["GDS_CD"]] = float(product["APLCN_IRRT"])

    mismatches = []
    detailed_checks = 0
    for product in load_catalog()["products"]:
        remote_max = official_max.get(product["id"])
        twelve_month = local_term_rate(product, 12)
        local_max = (
            round(twelve_month + float(product["bonus_cap"]), 3)
            if twelve_month is not None
            else None
        )
        if remote_max is None:
            mismatches.append((product["name"], "공식 목록에서 찾을 수 없음"))
        elif local_max is not None and remote_max != local_max:
            mismatches.append(
                (product["name"], f"12개월 최고금리 로컬 {local_max} / 공식 {remote_max}")
            )

        remote_terms = official_term_rates(product["id"])
        for term, remote_rate in remote_terms.items():
            local_rate = local_term_rate(product, term)
            if local_rate is None:
                continue
            detailed_checks += 1
            if local_rate != remote_rate:
                mismatches.append(
                    (
                        product["name"],
                        f"{term}개월 기본금리 로컬 {local_rate} / 공식 {remote_rate}",
                    )
                )

    print(f"공식 상품 {len(official_max)}개, 기간별 기본금리 {detailed_checks}건 확인")
    if mismatches:
        for name, detail in mismatches:
            print(f"[불일치] {name}: {detail}")
        raise SystemExit(1)
    print("프로토타입 금리가 공식 목록·상세 API와 일치합니다.")


if __name__ == "__main__":
    main()
