# 피처 엔지니어링

> **연계 문서**
> - `docs/eda/01_gold_eda.md`: Gold 데이터 현황 및 null 비율
> - `02_medallion_schema.md`: ETL 파이프라인 스키마
> - `docs/planning/04_data_model_detail.md`: DB 스키마
> - `docs/planning/07_recommendation_architecture.md`: 추천 시스템 아키텍처 (LangGraph, 재랭킹 수식, Fallback 전략)

---

## 1. 피처 정의

### 1-1. 원본 필드

**상품 (goods)**

| 필드 | 타입 | 설명 | 활용 |
|---|---|---|---|
| `goods_id` | str | 상품 고유 ID | 키 |
| `prefix` | str | GI/GP/GO/GS/PI | GP = 기획전 전용, Qdrant 미적재 |
| `product_name` | str | 상품명 | 임베딩 |
| `brand_name` | str | 브랜드명 | 임베딩, 필터링 |
| `price` / `discount_price` | int | 정가 / 할인가 | 예산 필터링, payload |
| `rating` / `rating_5pt` | float | 10점 / 5점 평점 | popularity_score 계산 입력 (단독 사용 금지) |
| `review_count` | int | 리뷰 수 | popularity_score |
| `review_count_source` | str | direct / aggregated | GO 상품 집계 구분 |
| `sold_out` | bool | 품절 여부 | Qdrant 필터링 |
| `soldout_reliable` | bool | GO 상품 False | 필터 신뢰도 판단 |
| `subcategory_names` | list[str] | `{pet_type}_{category}_{subcategory}` 태그 | 임베딩 |
| `pet_type` | list[str] | 강아지/고양이 (Silver 파싱) | Qdrant 필터, payload |
| `category` | list[str] | 사료/간식/용품/... (Silver 파싱) | Qdrant 필터, payload |
| `subcategory` | list[str] | 전연령/퍼피/시니어/... (Silver 파싱) | Qdrant 필터, payload |
| `health_concern_tags` | list[str] | 건강 관심사 태그 (Gold LLM 분류) | 임베딩, Qdrant 필터 |
| `main_ingredients` | list[str] | 주요 원료 키워드 배열 (OCR 추출) | 임베딩, 알레르기 필터 |
| `ingredient_composition` | dict\|null | `{원료명: 함량%}` (OCR LLM 파싱) | 임베딩 직렬화, 상품 상세 표시 (PostgreSQL) |
| `nutrition_info` | dict\|null | `{영양성분명: 수치}` (OCR LLM 파싱) | 임베딩 직렬화, 상품 상세 표시 (PostgreSQL) |
| `ingredient_text_ocr` | str\|null | OCR 원문 (식품류만) | Qdrant payload 저장 (알레르기 키워드 매칭). 임베딩 제외 |
| `popularity_score` | float | log(review+1)×rating_5pt | 재랭킹 — null 7.2% (259/3,618) |
| `sentiment_avg` | float | 상품별 sentiment_score 평균 (Gold 집계) | 재랭킹 품질 지표 — null 52.6% (1,903/3,618) |
| `repeat_rate` | float | 재구매 리뷰 비율 (Gold 집계) | 재랭킹 implicit signal — null 52.6% (1,903/3,618) |
| `thumbnail_url` | str | 상품 이미지 URL | 상품 카드 |
| `product_url` | str | 상품 상세 페이지 URL | 상품 카드 링크 |

**리뷰 (reviews)**

| 필드 | 타입 | 설명 | 활용 |
|---|---|---|---|
| `review_id` | str | 리뷰 고유 ID | 키 |
| `goods_id` | str | 상품 ID | 상품-리뷰 조인 |
| `review_date` | date | 작성일 (2014~2026) | — |
| `rating_5pt` | float | 별점 (0~5) | popularity_score |
| `purchase_label` | str | first / repeat | repeat_rate 계산 |
| `review_text` | str | 리뷰 본문 | 감성 분석 입력 |
| `pet_gender` | str | 수컷 / 암컷 | 펫 프로필 필터 |
| `pet_age_months` | int | 펫 나이(월) | 연령 필터 |
| `pet_weight_kg` | float | 펫 체중 (이상값 주의) | 체중 기반 추천 |
| `pet_breed` | str | 품종 | 품종 기반 추천 |
| `review_info` | dict | 체크박스 항목 (현재 null) | Phase 2 활용 |
| `sentiment_label` | str | positive / negative | 품질 지표 |
| `sentiment_score` | float | 감성 확신도 0~1 | sentiment_avg 집계 입력 |
| `absa_result` | dict | ABSA 속성별 결과 | 속성 기반 필터/추천 |

### 1-2. 파생 피처

#### popularity_score

```
popularity_score = log(review_count + 1) × rating_5pt
```

- `review_count_source = aggregated` (GO)인 경우 goods API의 `review_count` 그대로 사용
- review_count = 0이면 popularity_score = 0
- **null 비율**: Qdrant 7.2% (259/3,618) — 신상품 또는 rating 미수집 상품
- **rating 단독 사용 금지**: 5점 편향 77.4%, 평균 4.73 → 품질 식별력 없음. `popularity_score` 형태(리뷰 수로 편향 보정)로만 활용.

#### sentiment_avg (상품 단위 집계)

```
sentiment_avg = mean(sentiment_score per goods_id)
```

- rating 편향(5점 77%) 보완용 실질 품질 지표
- `gold/goods.py`에서 sentiment basic.parquet + silver reviews 조인으로 집계
- **null 비율**: Qdrant 52.6% (1,903/3,618) — 리뷰 없는 상품(신상품, 저인기 등)
- null 시 재랭킹에서 제외, `popularity_score`로 대체. 상세 fallback: `docs/planning/07_recommendation_architecture.md` 2-4절.

#### repeat_rate (상품 단위)

```
repeat_rate = repeat 리뷰 수 / 전체 리뷰 수
```

- `purchase_label = repeat` 비율 — 재구매 implicit signal
- `gold/goods.py`에서 silver reviews `purchase_label` 집계
- **null 비율**: Qdrant 52.6% (1,903/3,618) — `sentiment_avg` null 상품과 동일 집합

#### absa_aspect_score (속성 단위 집계)

```
absa_aspect_score[aspect] = (긍정 수 - 부정 수) / (긍정 + 부정 + 1)
```

- 속성: 기호성, 가격/구매, 배송/포장, 제품 성상, 냄새, 소화/배변, 성분/원료, 생체반응
- 의도 분류에서 특정 속성 감지 시 해당 score로 재랭킹 가중

---

## 2. Implicit / Explicit 데이터

### 2-1. Explicit 데이터

| 데이터 | 수집 시점 | DB 저장 위치 | 활용 방식 |
|---|---|---|---|
| 펫 품종 / 나이 / 체중 | 회원가입 / 펫 등록 | `PET` | 품종 메타 연계 → health_concern_tags 자동 매핑 |
| PET_HEALTH_CONCERN | 펫 등록 / 설정 | `PET_HEALTH_CONCERN` | health_concern_tags 필터링 |
| PET_ALLERGY | 펫 등록 / 설정 | `PET_ALLERGY` | main_ingredients / ingredient_text_ocr 키워드 제외 필터 |
| PET_FOOD_PREFERENCE | 펫 등록 / 설정 | `PET_FOOD_PREFERENCE` | 사료 형태(dry/wet) 필터 |
| 챗봇 직접 요청 | 대화 중 | `CHAT_MESSAGE` | 의도 분류 → 검색 쿼리 생성 |

### 2-2. Implicit 데이터

| 데이터 | 수집 시점 | DB 저장 위치 | 활용 방식 |
|---|---|---|---|
| 상품 카드 클릭 | 챗봇 응답 후 | `USER_INTERACTION` | CTR 기반 선호 추정 |
| 장바구니 담기 | 상품 카드 → 장바구니 | `CART` | 구매 의향 신호 |
| 구매 완료 | 결제 | `ORDER` | 가장 강한 implicit 신호 |
| 재구매 (`purchase_label=repeat`) | 리뷰 작성 | `REVIEW` | `repeat_rate` 파생 피처 |
| 대화 히스토리 | 챗봇 세션 | `CHAT_MESSAGE` | 관심 카테고리/속성 추출 |

### 2-3. Phase 2 — CF 확장

Phase 1에서 implicit 데이터가 충분히 축적된 후 협업 필터링(CF) 레이어를 추가한다.

```
축적 목표:
  USER_INTERACTION: 10,000건 이상
  ORDER: 1,000건 이상
  → 사용자-상품 행렬 sparsity 허용 수준 확인 후 CF 적용
```

| 방식 | 특징 | 적용 조건 |
|---|---|---|
| ALS (Implicit) | 암시적 피드백 Matrix Factorization | ORDER / INTERACTION 10K+ |
| BPR | 구매 vs 미구매 쌍 학습 | ORDER 1K+ |
| Item2Vec | 구매 시퀀스 기반 상품 임베딩 | 사용자당 평균 구매 3회+ |
| LightGCN | 그래프 기반, 고성능 | 대규모 데이터 (50K+ interaction) |

> CF 모델 선택 및 랭킹 수식 통합 방식: `docs/planning/07_recommendation_architecture.md` 3절.
