# 피처 엔지니어링 및 추천 시스템 아키텍처

> **연계 문서**
> - `07_gold_eda.md`: Gold 데이터 현황
> - `03_medallion_schema.md`: ETL 파이프라인 스키마
> - `docs/planning/04_data_model_detail.md`: DB 스키마

---

## 1. 피처 정의

### 1-1. 원본 필드

**상품 (goods)**

| 필드 | 타입 | 설명 | 활용 |
|---|---|---|---|
| `goods_id` | str | 상품 고유 ID | 키 |
| `prefix` | str | GI/GP/GO/GS/PI | 상품 유형 분류 |
| `product_name` | str | 상품명 | 임베딩, 검색 |
| `brand_name` | str | 브랜드명 | 필터링, 임베딩 |
| `price` / `discount_price` | int | 정가 / 할인가 | 예산 필터링 |
| `rating` / `rating_5pt` | float | 10점 / 5점 평점 | popularity_score |
| `review_count` | int | 리뷰 수 (GP: aggregated) | popularity_score |
| `review_count_source` | str | direct / aggregated | GP 보정 구분 |
| `sold_out` | bool | 품절 여부 | 추천 필터링 |
| `soldout_reliable` | bool | GO 상품 False | 필터 신뢰도 판단 |
| `subcategory_names` | list[str] | 소분류 태그 | 카테고리 필터, 임베딩 |
| `health_concern_tags` | list[str] | 건강 관심사 태그 | 펫 프로필 매핑 필터 |
| `ingredient_text_ocr` | str | OCR 추출 성분 원문 | 알레르기 필터, 임베딩 |
| `main_ingredients` | list | 주요 성분 구조화 | 알레르기 필터 (미완) |
| `ingredient_composition` | dict | 성분별 함량 | 상세 성분 정보 (미완) |
| `nutrition_info` | dict | 영양소 정보 | 영양 기반 추천 (미완) |
| `popularity_score` | float | log(review+1)×rating | 재랭킹 |
| `trend_score` | float | 최근 30일 기반 | 재랭킹 |
| `thumbnail_url` | str | 상품 이미지 URL | 상품 카드 표시 |
| `product_url` | str | 상품 상세 페이지 URL | 상품 카드 링크 |

**리뷰 (reviews)**

| 필드 | 타입 | 설명 | 활용 |
|---|---|---|---|
| `review_id` | str | 리뷰 고유 ID | 키 |
| `goods_id` | str | 상품 ID | 상품-리뷰 조인 |
| `review_date` | datetime | 작성일 (2014~2026) | trend_score 계산 |
| `rating_5pt` | float | 별점 (0~5) | popularity_score |
| `purchase_label` | str | first / repeat | 재구매 implicit signal |
| `review_text` | str | 리뷰 본문 | 감성 분석 입력 |
| `pet_name` | str | 펫 이름 | — |
| `pet_gender` | str | 수컷 / 암컷 | 펫 프로필 필터 |
| `pet_age_months` | int | 펫 나이(월) | 연령 필터 |
| `pet_weight_kg` | float | 펫 체중 (이상값 주의) | 체중 기반 추천 |
| `pet_breed` | str | 품종 | 품종 기반 추천 |
| `review_info` | dict | 체크박스 항목 (현재 null) | Phase 2 활용 |
| `sentiment_label` | str | positive / negative | 품질 지표 |
| `sentiment_score` | float | 감성 확신도 0~1 | sentiment_avg 계산 |
| `absa_result` | dict | ABSA 속성별 결과 | 속성 기반 필터/추천 |

### 1-2. 파생 피처

#### popularity_score
```
popularity_score = log(review_count + 1) × rating_5pt
```
- `review_count_source = aggregated` (GP)인 경우: goods 목록 API의 `review_count` 그대로 사용
- review_count = 0이면 popularity_score = 0

#### trend_score
```
trend_score = log(최근 30일 리뷰 수 + 1) × 최근 30일 평균 rating_5pt
```
- non-null: 2,314개 (최근 리뷰 있는 상품)
- null 상품은 재랭킹 시 가중치 δ = 0 처리

#### sentiment_avg (상품 단위 집계)
```
sentiment_avg = mean(sentiment_score per goods_id)
```
- rating 편향(5점 77%) 보완용 실질 품질 지표
- GP 리뷰 sentiment 미처리 상품은 null → 재랭킹 시 제외

#### absa_aspect_score (속성 단위 집계)
```
absa_aspect_score[aspect] = (긍정 수 - 부정 수) / (긍정 + 부정 + 1)
```
- 속성: 기호성, 가격/구매, 배송/포장, 제품 성상, 냄새, 소화/배변, 성분/원료, 생체반응
- 사용자 질문 의도에서 특정 속성이 추출된 경우 해당 속성 score로 재랭킹 가중

#### repeat_rate (상품 단위)
```
repeat_rate = repeat 리뷰 수 / 전체 리뷰 수
```
- `purchase_label = repeat` 비율 — 재구매 implicit signal

---

## 2. Implicit / Explicit 데이터

### 2-1. Explicit 데이터

사용자가 명시적으로 제공하는 선호 신호.

| 데이터 | 수집 시점 | DB 저장 위치 | 활용 방식 |
|---|---|---|---|
| 펫 품종 / 나이 / 체중 | 회원가입 / 펫 등록 | `PET` | 품종 메타 연계 → health_concern_tags 자동 매핑 |
| PET_HEALTH_CONCERN | 펫 등록 / 설정 | `PET_HEALTH_CONCERN` | health_concern_tags 필터링 |
| PET_ALLERGY | 펫 등록 / 설정 | `PET_ALLERGY` | 알레르기 성분 제외 필터 |
| PET_FOOD_PREFERENCE | 펫 등록 / 설정 | `PET_FOOD_PREFERENCE` | 사료 형태(dry/wet) 필터 |
| 별점 / 리뷰 | 구매 후 | `REVIEW` | sentiment_avg, absa_aspect_score 갱신 |
| 챗봇 직접 요청 | 대화 중 | `CHAT_MESSAGE` | 의도 분류 → 검색 쿼리 생성 |

### 2-2. Implicit 데이터

사용자 행동에서 간접 추출하는 선호 신호.

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

CF 방식 후보:

| 방식 | 특징 | 적용 조건 |
|---|---|---|
| ALS (Implicit) | 암시적 피드백 Matrix Factorization | ORDER / INTERACTION 10K+ |
| BPR | 구매 vs 미구매 쌍 학습 | ORDER 1K+ |
| Item2Vec | 구매 시퀀스 기반 상품 임베딩 | 사용자당 평균 구매 3회+ |
| LightGCN | 그래프 기반, 고성능 | 대규모 데이터 (50K+ interaction) |

---

## 3. 추천 시스템 아키텍처

### 3-1. 전체 흐름 (LangGraph)

```
사용자 메시지
    │
    ▼
[의도 분류 노드]
    상품 추천 / 건강 상담 / 일반 질문 / 기타
    │
    ├─ 건강 상담 / 일반 질문
    │       └─ [RAG 노드]
    │               └─ Qdrant domain_qna / breed_meta 검색
    │               └─ LLM 응답 생성 → 스트리밍
    │
    └─ 상품 추천
            ├─ [펫 프로필 로드]
            │       펫 품종 → breed_meta → health_concern_tags 매핑
            │
            ├─ [쿼리 생성 노드]
            │       사용자 의도 + 펫 프로필 → 검색 쿼리 + 필터 조건 생성
            │
            ├─ [Qdrant Hybrid Search 노드]
            │       Dense + Sparse + RRF
            │
            ├─ [재랭킹 노드]
            │       final_score 계산 + 필터 적용
            │
            └─ [응답 생성 노드]
                    LLM 추천 이유 생성 → 스트리밍 출력 + 상품 카드 반환
```

### 3-2. Qdrant Hybrid Search

#### 컬렉션 설계

| 컬렉션 | 임베딩 텍스트 | payload 필드 |
|---|---|---|
| `products` | `product_name + subcategory_names + health_concern_tags + ingredient_text_ocr` | goods_id, brand_name, price, sold_out, soldout_reliable, health_concern_tags, sentiment_avg, popularity_score, trend_score, repeat_rate |
| `domain_qna` | `질문 + 답변` | species, category, source |
| `breed_meta` | `품종명 + 수의 영양학적 메타 디스크립션` | species, breed_name, group, health_keywords |

#### 검색 방식

```
Dense:  multilingual-e5-large (또는 bge-m3) — 의미 유사도
Sparse: BM25 (Qdrant 내장) — 키워드 정밀 매칭
융합:   RRF (Reciprocal Rank Fusion) — Dense + Sparse 점수 통합
```

#### 필터링 조건 (Qdrant payload filter)

```python
# 우선순위 순
1. sold_out = False  AND  (soldout_reliable = True)
2. health_concern_tags ⊇ PET_HEALTH_CONCERN      # 펫 건강 관심사
3. allergen_exclude: ingredient_text_ocr ∩ PET_ALLERGY = ∅
4. subcategory_names 매칭 PET_FOOD_PREFERENCE      # 사료 형태 (dry/wet)
5. price ≤ 예산 상한                               # 챗봇에서 언급 시만 적용
```

### 3-3. 재랭킹 수식

```
final_score = α × rrf_score
            + β × normalize(popularity_score)
            + γ × sentiment_avg
            + δ × normalize(trend_score)
            + ε × absa_aspect_score[detected_aspect]  # 의도 분류에서 속성 추출 시

기본 가중치 (Phase 1):
  α = 0.5   검색 적합도
  β = 0.2   인기도
  γ = 0.2   감성 품질
  δ = 0.1   트렌드
  ε = 0.1   ABSA 속성 (속성 감지 시만 적용, 미감지 시 ε = 0)
```

> - `sentiment_avg` null 상품 (GP 리뷰 미처리): γ = 0
> - `trend_score` null 상품: δ = 0
> - 가중치는 A/B 테스트로 튜닝 예정

### 3-4. Cold-start 처리

| 케이스 | 전략 |
|---|---|
| 게스트 / 펫 프로필 없음 | 카테고리 인기 기반 추천 (popularity_score 상위) |
| 펫 프로필 있음, 구매 이력 없음 | 품종 메타 → health_concern_tags 자동 매핑 → Qdrant 필터 검색 |
| 신규 상품 (리뷰 0건) | popularity_score = 0 → rrf_score(α)만으로 랭킹 |
| GP 리뷰 미처리 상품 | sentiment_avg = null → γ = 0, popularity_score(β)로 보완 |
