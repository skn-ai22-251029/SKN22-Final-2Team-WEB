# DB 적재 데이터 EDA

> **분석 기준일**: 2026-03-18
> **적재 기준 파일**
> - `output/gold/goods/20260318_goods_gold.parquet`
> - `output/gold/reviews/20260316_reviews_gold.parquet` ※ Silver ETL 개선 미반영 상태

---

## 1. PostgreSQL

### 1-1. 테이블 행 수

| 테이블 | 행 수 |
|---|---|
| `product` | 4,902 |
| `product_category_tag` | 2,856 |
| `review` | 349,277 |

### 1-2. product — 기본 통계

| 항목 | 수치 |
|---|---|
| 총 상품 수 | 4,902 |
| 품절 (soldout_yn=true) | 281 (5.7%) |
| soldout 신뢰 불가 (soldout_reliable=false, GO) | 621 (12.7%) |
| review_count = 0 | 1,746 (35.6%) |
| rating NULL | 261 (5.3%) |

### 1-3. product — 배열 컬럼

| 컬럼 | 값 있음 | 비고 |
|---|---|---|
| `pet_type` | 4,902 (100%) | ✅ |
| `category` | 4,902 (100%) | ✅ |
| `subcategory` | 4,902 (100%) | ✅ |
| `health_concern_tags` | 1,379 (28.1% / ocr_target 기준 45.3%) | ✅ LLM 분류 적용 (이전 12.1%) |

**pet_type 분포:**

| pet_type | 상품 수 |
|---|---|
| 강아지 | 2,918 |
| 고양이 | 2,519 |

> 다중 pet_type 상품 포함 (합계 > 4,902)

**category 분포:**

| category | 상품 수 |
|---|---|
| 용품 | 1,621 |
| 사료 | 1,384 |
| 간식 | 1,337 |
| 배변용품 | 312 |
| 모래 | 241 |
| 습식관 | 204 |
| 덴탈관 | 187 |

> 다중 category 상품 포함 (합계 > 4,902)

### 1-4. product — 추천 피처

| 피처 | non-null | min | median | avg | max |
|---|---|---|---|---|---|
| `popularity_score` | 4,641 (94.7%) | 0.00 | 6.93 | 10.32 | 48.51 |
| `sentiment_avg` | 1,715 (35.0%) | 0.001 | 0.906 | 0.859 | 0.995 |
| `repeat_rate` | 2,314 (47.2%) | 0.000 | 0.205 | 0.230 | 1.000 |

> `sentiment_avg`(1,715) vs `repeat_rate`(2,314) 불일치: repeat_rate는 GP 포함 일부 상품에도 산출됨

### 1-5. product — OCR/성분 필드

| 필드 | non-null/non-empty | 비율 |
|---|---|---|
| `ingredient_text_ocr` | 2,419 | 49.3% |
| `main_ingredients` | 1,912 | 39.0% |
| `ingredient_composition` | 1,134 | 23.1% |
| `nutrition_info` | 848 | 17.3% |

> PG `main_ingredients` 1,912에는 GP 상품(1,284개) 포함. GP 제외 기준 1,221건 — Qdrant와 일치

### 1-6. product — health_concern_tags 분포

| 태그 | 상품 수 |
|---|---|
| 소화 | 508 |
| 치아 | 486 |
| 피부 | 473 |
| 면역 | 414 |
| 관절 | 394 |
| 체중 | 316 |
| 요로 | 115 |
| 헤어볼 | 86 |
| 눈물 | 64 |

> `product_category_tag` 2,856행과 배열 unnest 합계 일치 → 정합성 정상
> LLM 분류(`scripts/gold/health_tags.py`) 적용 — ocr_target(식품류) 3,041개 기준 **45.3%** 커버리지 (전체 4,902 기준 28.1%)

### 1-7. review — 기본 통계

> GP 상품(1,284개) 리뷰 232,821건은 sentiment/ABSA 미처리 상태로 DB에 포함되어 있음.
> 유효한 분석 기준은 **GP 제외** 수치. 이하 통계는 GP 제외 기준으로 작성.

| 항목 | 전체 (GP 포함) | **GP 제외** |
|---|---|---|
| 총 리뷰 수 | 349,277 | **116,456** |
| 리뷰 보유 상품 수 | 2,314 | **1,715** |
| 리뷰 없는 상품 수 | 2,588 (52.8%) | **2,587** |

### 1-8. review — 필드 현황 (GP 제외 기준)

| 필드 | NULL | 빈값/비고 |
|---|---|---|
| `content` | 0 | 빈문자열 487건 (0.4%) ⚠️ Silver ETL 개선 미반영 |
| `score` | 0 | — |
| `written_at` | 0 | — |
| `sentiment_score` | 0 | **100% 처리 완료** ✅ |
| `absa_result` | 4건 | 사실상 100% ✅ |

**sentiment_label 분포:**

| 레이블 | 건수 | 비율 |
|---|---|---|
| positive | 107,668 | 92.4% |
| negative | 8,788 | 7.6% |

**sentiment_score 통계**: min=0.001, median=0.978, avg=0.890, max=0.996

### 1-9. review — 구매/평점 분포 (GP 제외 기준)

**purchase_label:**

| 레이블 | 건수 | 비율 |
|---|---|---|
| first | 66,782 | 57.3% |
| repeat | 49,674 | 42.7% |

**score 분포:**

| score | 건수 | 비율 |
|---|---|---|
| 5.0 | 90,125 | 77.4% |
| 4.5 | 10,659 | 9.2% |
| 4.0 | 7,806 | 6.7% |
| 3.5 | 2,722 | 2.3% |
| 3.0 | 2,163 | 1.9% |
| 기타 | 2,981 | 2.6% |

> 평균 4.73, 중앙값 5.0 — 5점 편향 77.4%. rating 단독 품질 지표 사용 부적합

**연도별 분포:**

| 연도 | 건수 |
|---|---|
| ~2020 | 6,404 |
| 2021 | 8,684 |
| 2022 | 23,929 |
| 2023 | 35,921 |
| 2024 | 18,280 |
| 2025 | 20,477 |
| 2026 (1~3월) | 2,761 |

### 1-10. review — 펫 프로필 기록률 (GP 제외 기준)

| 필드 | non-null | 비율 |
|---|---|---|
| `pet_age_months` | 44,680 | 38.4% |
| `pet_weight_kg` | 41,266 | 35.4% |
| `pet_gender` | 41,643 | 35.8% |
| `pet_breed` | 40,443 | 34.7% |
| `pet_weight_kg > 100` 이상값 | 258건 | — ⚠️ Silver ETL 개선 미반영 |

### 1-11. FK 정합성

| 검사 | 불일치 |
|---|---|
| `review.product_id` → `product` | **0** ✅ |
| `product_category_tag.product_id` → `product` | **0** ✅ |

---

## 2. Qdrant

### 2-1. 컬렉션 기본 정보

| 항목 | 값 |
|---|---|
| 컬렉션명 | `products` |
| points_count | **3,618** |
| status | green |
| 벡터 구성 | Dense (multilingual-e5-large, 1024d) + Sparse (BM25) |

> 3,618 = 전체 4,902 − GP 1,284 (GP 제외 적재)

### 2-2. payload 필드 목록

```
goods_id, product_name, brand_name, prefix, price, discount_price,
sold_out, soldout_reliable, pet_type, category, subcategory,
health_concern_tags, main_ingredients, ingredient_text_ocr,
popularity_score, sentiment_avg, repeat_rate, thumbnail_url, product_url
```

### 2-3. payload null/empty 현황

| 필드 | null/empty | non-null |
|---|---|---|
| `product_name` | 0 (0%) | 3,618 ✅ |
| `brand_name` | 0 (0%) | 3,618 ✅ |
| `price` | 0 (0%) | 3,618 ✅ |
| `discount_price` | 0 (0%) | 3,618 ✅ |
| `thumbnail_url` | 0 (0%) | 3,618 ✅ |
| `product_url` | 0 (0%) | 3,618 ✅ |
| `popularity_score` | 259 (7.2%) | 3,359 ✅ |
| `sentiment_avg` | 1,903 (52.6%) | 1,715 ⚠️ |
| `repeat_rate` | 1,903 (52.6%) | 1,715 ⚠️ |

> `sentiment_avg`/`repeat_rate` null 1,903건: 해당 상품에 리뷰가 없는 경우 (신상품, 저인기 등)

### 2-4. prefix 분포

| prefix | 수 | 비율 |
|---|---|---|
| GI | 2,280 | 63.0% |
| GO | 621 | 17.2% |
| GS | 508 | 14.0% |
| PI | 209 | 5.8% |
| GP | 0 | — (제외됨) |

### 2-5. sold_out / soldout_reliable

| 항목 | 수 | 비율 |
|---|---|---|
| sold_out=True | 200 | 5.5% |
| sold_out=False | 3,418 | 94.5% |
| soldout_reliable=True | 2,997 | 82.8% |
| soldout_reliable=False | 621 | 17.2% |

### 2-6. pet_type / category 분포

**pet_type** (포함 기준):

| pet_type | 수 | 비율 |
|---|---|---|
| 강아지 포함 | 2,291 | 63.3% |
| 고양이 포함 | 1,748 | 48.3% |
| empty | 0 | ✅ |

**category** (포함 기준):

| category | 수 |
|---|---|
| 용품 | 1,479 |
| 사료 | 912 |
| 간식 | 845 |
| 배변용품 | 248 |
| 모래 | 155 |
| 덴탈관 | 145 |
| 습식관 | 58 |
| empty | 0 ✅ |

### 2-7. health_concern_tags / main_ingredients

| 필드 | 값 있는 상품 | 비율 |
|---|---|---|
| `health_concern_tags` | 940 | 26.0% |
| `main_ingredients` | 1,221 | 33.7% |

> PG non-GP 기준 hct 940, main_ingredients 1,221 — Qdrant와 정합 ✅

---

## 3. 주요 이슈

| # | 이슈 | 영향 | 현황 |
|---|---|---|---|
| 1 | `sentiment_avg`/`repeat_rate` null 52.6% (Qdrant), 35~47% (PG) | 리뷰 없는 상품 추천 피처 부재 | 리뷰 없는 상품 자체의 한계. popularity_score로 대체 |
| 2 | `health_concern_tags` 12.1%만 보유 | 건강 관심사 필터링 제한 | ✅ 해결 — LLM 분류 전환, ocr_target 기준 **45.3%** 커버리지 (`scripts/gold/health_tags.py`) |
| 3 | GP 리뷰 sentiment/ABSA 미처리 (232,821건) | 추천 품질 저하 | GP 추천 완전 제외 결정. GP 리뷰 수집 시 별도 적재 가능 |
| 4 | `review content` 빈문자열 487건 (0.4%) | 감성 분석 노이즈 | 미해결 — Silver ETL 코드 수정 완료, DB 재적재 미실행 |
| 5 | `pet_weight_kg > 100` 이상값 258건 | 체중 기반 필터 오작동 | 미해결 — Silver ETL 코드 수정 완료, DB 재적재 미실행 |
| 6 | 5점 rating 편향 (77.5%) | 평점 단독 품질 지표 부적합 | 추천 로직에서 `rating` 단독 사용 금지, `sentiment_avg` 우선 / `popularity_score` fallback |
| 7 | `main_ingredients` PG(1,912) vs Qdrant(1,221) 불일치 | — | ✅ 해결 — GP 제외 기준 PG(1,221) = Qdrant(1,221) 정합 확인 |
