import unittest

from src.advisor import QUESTION_OPTIONS, advise
from src.evaluation import evaluate
from src.recommender import Customer, recommend


class RecommenderTest(unittest.TestCase):
    def test_first_time_customer_finds_omitted_product(self) -> None:
        result = recommend(
            Customer(
                age=29,
                amount=10000000,
                term_months=12,
                salary_or_pension=True,
                first_term_deposit=True,
                auto_renew=True,
            )
        )
        top = result["recommendations"][0]
        self.assertEqual(top["name"], "우체국편리한e정기예금")
        self.assertEqual(top["achievable_rate"], 3.25)
        self.assertFalse(top["legacy_recommended"])
        self.assertEqual(top["net_interest"], 274950)

    def test_term_specific_rate_is_used(self) -> None:
        result = recommend(
            Customer(age=29, amount=10000000, term_months=24, channel="online")
        )
        product = next(
            item
            for item in result["recommendations"]
            if item["name"] == "2040+α정기예금"
        )
        self.assertEqual(product["base_rate"], 2.45)

    def test_exact_term_product_rejects_unsupported_month(self) -> None:
        result = recommend(
            Customer(age=60, amount=10000000, term_months=18, channel="online")
        )
        excluded = {item["name"]: item["reason"] for item in result["excluded"]}
        self.assertIn("시니어싱글벙글정기예금", excluded)
        self.assertIn("12·24·36개월", excluded["시니어싱글벙글정기예금"])

    def test_age_does_not_hide_better_general_product(self) -> None:
        result = recommend(
            Customer(
                age=63,
                amount=10000000,
                term_months=12,
                card_spend=700000,
                checking_balance=1500000,
            )
        )
        names = [item["name"] for item in result["recommendations"]]
        self.assertIn("우체국파트너든든정기예금", names)

    def test_audience_is_tie_breaker_not_filter(self) -> None:
        result = recommend(
            Customer(
                age=42,
                amount=30000000,
                term_months=12,
                card_spend=700000,
                checking_balance=1500000,
            )
        )
        names = [item["name"] for item in result["recommendations"]]
        self.assertLess(
            names.index("2040+α정기예금"),
            names.index("시니어싱글벙글정기예금"),
        )

    def test_interest_priority_never_places_lower_interest_above_higher(self) -> None:
        result = recommend(
            Customer(age=29, amount=10000000, term_months=12, channel="online")
        )
        interests = [
            item["gross_interest"] for item in result["recommendations"]
        ]
        self.assertEqual(interests, sorted(interests, reverse=True))

    def test_hard_constraints_exclude_ineligible_products(self) -> None:
        result = recommend(
            Customer(age=30, amount=500000, term_months=12, channel="online")
        )
        names = [item["name"] for item in result["recommendations"]]
        self.assertNotIn("우체국편리한e정기예금", names)
        self.assertNotIn("시니어싱글벙글정기예금", names)

    def test_special_segment_is_not_recommended_without_qualification(self) -> None:
        result = recommend(
            Customer(age=45, amount=10000000, term_months=12, channel="branch")
        )
        names = [item["name"] for item in result["recommendations"]]
        self.assertNotIn("우체국소상공인정기예금", names)
        self.assertNotIn("이웃사랑정기예금", names)

    def test_inclusive_priority_uses_verified_qualification(self) -> None:
        result = recommend(
            Customer(
                age=47,
                amount=80000000,
                term_months=12,
                channel="branch",
                priority="inclusive",
                business_owner=True,
                yellow_umbrella=True,
                checking_balance=3000000,
            )
        )
        top = result["recommendations"][0]
        self.assertEqual(top["name"], "우체국소상공인정기예금")
        self.assertTrue(top["inclusion"]["matched"])

    def test_advisor_only_accepts_fixed_questions_and_returns_sources(self) -> None:
        customer = Customer(age=29, amount=10000000, term_months=12)
        answer = advise(QUESTION_OPTIONS[0]["id"], customer)
        self.assertTrue(answer["citations"])
        self.assertEqual(
            answer["method"], "structured-retrieval-plus-template-generation"
        )
        with self.assertRaises(ValueError):
            advise("free_text_question", customer)

    def test_evaluation_shows_legacy_misses(self) -> None:
        summary = evaluate()["summary"]
        self.assertLess(summary["legacy_top1_hit_rate"], 1.0)
        self.assertGreater(summary["total_interest_uplift"], 0)


if __name__ == "__main__":
    unittest.main()
