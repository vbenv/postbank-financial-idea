#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from src.recommender import Customer, recommend


def main() -> None:
    parser = argparse.ArgumentParser(description="우체국 정기예금 추천")
    parser.add_argument("--age", type=int, required=True)
    parser.add_argument("--amount", type=int, required=True)
    parser.add_argument("--term", type=int, default=12)
    parser.add_argument("--channel", choices=["online", "branch"], default="online")
    parser.add_argument(
        "--priority",
        choices=["highest_interest", "easy_conditions", "liquidity", "inclusive"],
        default="highest_interest",
    )
    parser.add_argument("--salary", action="store_true")
    parser.add_argument("--card-spend", type=int, default=0)
    parser.add_argument("--checking-balance", type=int, default=0)
    parser.add_argument("--first-deposit", action="store_true")
    parser.add_argument("--auto-renew", action="store_true")
    args = parser.parse_args()
    customer = Customer(
        age=args.age,
        amount=args.amount,
        term_months=args.term,
        channel=args.channel,
        priority=args.priority,
        salary_or_pension=args.salary,
        card_spend=args.card_spend,
        checking_balance=args.checking_balance,
        first_term_deposit=args.first_deposit,
        auto_renew=args.auto_renew,
    )
    print(json.dumps(recommend(customer), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
