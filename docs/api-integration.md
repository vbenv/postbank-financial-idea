# 실제 API 연동 명세

## 1. 필요한 입력

추천 엔진은 주민번호나 상세 거래내역 원문이 필요하지 않습니다. 아래처럼 추천에 필요한 파생값만 전달하면 됩니다.

```json
{
  "customer_id": "익명화 식별자",
  "age": 29,
  "amount": 10000000,
  "term_months": 12,
  "channel": "online",
  "salary_or_pension": true,
  "checking_balance": 1200000,
  "card_spend": 350000,
  "first_term_deposit": true,
  "auto_renew": true,
  "business_owner": false,
  "vulnerable_or_rural": false
}
```

민감한 자격정보는 원문 대신 `true/false` 형태로 전달하고, 추천 응답과 로그에는 자격 사유를 저장하지 않는 방식을 권장합니다.

## 2. 상품 API

상품별로 다음 필드가 필요합니다.

```json
{
  "product_id": "200108000101",
  "name": "우체국편리한e정기예금",
  "sale_status": "active",
  "min_amount": 1000000,
  "max_amount": 50000000,
  "min_term_months": 6,
  "max_term_months": 12,
  "channels": ["online"],
  "base_rates_by_term": {"12": 2.5},
  "max_rate": 3.1,
  "bonus_rules": [
    {
      "condition_code": "FIRST_TERM_DEPOSIT",
      "rate": 0.3,
      "cap_group": "PRODUCT_BONUS",
      "description": "온라인 정기예금 첫 거래"
    }
  ],
  "product_bonus_cap": 0.5,
  "effective_from": "2026-03-30"
}
```

운영 환경에서는 상품설명 문자열을 자연어로 파싱하지 않고, 우대조건 코드와 금리·상한을 구조화해 받아야 계산 오류를 줄일 수 있습니다.

## 3. 추천 API

`POST /api/v1/deposit-recommendations`

응답 예시:

```json
{
  "recommendation_id": "rec_...",
  "products": [
    {
      "rank": 1,
      "product_id": "200108000101",
      "achievable_rate": 3.1,
      "estimated_gross_interest": 310000,
      "matched_conditions": ["비대면 가입", "정기예금 첫 거래", "급여 이체"],
      "next_actions": [],
      "calculation_version": "deposit-reco-v1"
    }
  ]
}
```

## 3-1. 선택형 상담 API

`GET /api/advice/questions`에서 허용된 질문 목록을 조회하고, `POST /api/advice`에 질문 ID와 추천 입력값을 전달한다.

```json
{
  "question_id": "inclusive_support",
  "customer": {
    "age": 47,
    "amount": 80000000,
    "term_months": 12,
    "channel": "branch",
    "priority": "inclusive",
    "business_owner": true
  }
}
```

응답은 구조화된 상품정보에서 검색한 답변과 공식 상품상세 근거를 포함한다. 자유입력 질문은 받지 않는다.

## 4. 운영 로그

최소 로그:

- 추천 요청 시각과 알고리즘 버전
- 노출 상품 ID와 순위
- 상품 상세보기, 가입 시작, 가입 완료
- 예상금리와 가입 시 확정금리의 차이
- 중도해지 여부와 만기 유지 여부

고객 속성 원문 대신 조건 충족 코드만 저장하고 보존기간을 제한합니다.

## 5. 도입 단계

1. 현재 추천 결과를 변경하지 않는 그림자 모드로 2~4주 계산합니다.
2. 현행 추천 대비 `eligible recall`, 예상이자 후회값, 금리 오차를 검증합니다.
3. 트래픽 5%에서 A/B 테스트를 시작합니다.
4. 가입전환율뿐 아니라 민원율, 중도해지율, 취약계층 노출 형평성을 함께 확인합니다.
5. 품질 기준을 충족하면 트래픽을 단계적으로 확대합니다.

실제 우체국은행 API를 제공받으면 상품·고객 필드 매핑 어댑터만 추가하면 현재 엔진과 화면을 그대로 연결할 수 있습니다.
