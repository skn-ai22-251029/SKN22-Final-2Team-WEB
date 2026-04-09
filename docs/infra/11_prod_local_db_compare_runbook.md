# 운영 DB와 로컬 DB 비교 런북

> 이 문서는 이슈 `#234`, `#235` 대응용이다.
> 목적은 추천 장애가 났을 때 운영 DB와 로컬 DB의 핵심 테이블 상태를 빠르게 비교하고,
> 배포 전에 추천 검색 메타데이터 누락 여부와 복구 절차를 빠르게 확인하는 것이다.

---

## 1. 비교 대상

| 테이블 | 왜 보나 | row 수 확인 | fill rate 확인 |
|---|---|---|---|
| `product` | 추천 검색, 필터, 랭킹의 핵심 원천 | ✅ | `goods_name`, `pet_type`, `category`, `subcategory`, `health_concern_tags`, `main_ingredients`, `ingredient_text_ocr`, `popularity_score`, `sentiment_avg`, `repeat_rate`, `embedding`, `search_vector` |
| `product_category_tag` | 건강 태그 매핑 정합성 확인 | ✅ | `product_id`, `tag` |
| `review` | 랭킹 피처 생성 원천 확인 | ✅ | `content`, `written_at`, `sentiment_score`, `absa_result`, `pet_age_months`, `pet_weight_kg`, `pet_gender`, `pet_breed` |
| `user_interaction` | 추천 피드백 로그 유무 확인 | ✅ | `click`, `cart`, `purchase`, `reject` 유형별 건수 |

---

## 2. 사전 준비

1. 로컬 PostgreSQL이 떠 있어야 한다.
2. 운영 DB가 private 이면 먼저 SSH 터널을 연다.
3. 두 DB에 모두 읽기 권한으로 접속 가능해야 한다.

운영 DB가 private 인 경우:

```bash
bash scripts/aws/start_test_rds_dbeaver_tunnel.sh
```

기본값 기준으로 운영 DB는 `127.0.0.1:15432`, 로컬 DB는 `127.0.0.1:5432`로 비교하면 된다.

---

## 3. 실행 방법

### 3-1. 가장 단순한 실행

로컬 DB는 `deploy/local/.env`를 읽어 자동 구성할 수 있으므로, 운영 DB DSN만 넘기면 된다.

```bash
export PROD_DATABASE_URL='postgresql://tailtalk:<PASSWORD>@127.0.0.1:15432/tailtalk'
python scripts/compare_prod_local_db.py
```

### 3-2. 두 쪽 모두 DSN 명시

```bash
python scripts/compare_prod_local_db.py \
  --prod-dsn 'postgresql://tailtalk:<PASSWORD>@127.0.0.1:15432/tailtalk' \
  --local-dsn 'postgresql://mungnyang:<PASSWORD>@127.0.0.1:5432/tailtalk_db'
```

### 3-3. 특정 테이블만 빠르게 보기

```bash
python scripts/compare_prod_local_db.py --tables product,review
python scripts/compare_prod_local_db.py --tables user_interaction
```

---

## 4. 배포 전 검증 절차

추천 검색이나 랭킹에 영향을 주는 배포 전에는 아래 순서로 확인한다.

### 4-1. 최소 실행

```bash
export PROD_DATABASE_URL='postgresql://tailtalk:<PASSWORD>@127.0.0.1:15432/tailtalk'
python scripts/compare_prod_local_db.py --tables product
```

### 4-2. 차단 기준

| 항목 | 통과 기준 | 의미 | 실패 시 조치 |
|---|---|---|---|
| `product.row_count` | 운영/로컬 차이 없음 | 추천 검색 원천 데이터 수량 일치 | 로컬 복원 또는 상품 재적재 |
| `goods_name` | fill rate `100%` | 상품명 누락 시 검색/응답 품질 저하 | 상품 재적재 |
| `pet_type` | fill rate `100%` | 추천 필터 핵심 | 상품 재적재 후 재검증 |
| `category` | fill rate `100%` | 추천 필터 핵심 | 상품 재적재 후 재검증 |
| `subcategory` | fill rate `100%` | 추천 필터 핵심 | 상품 재적재 후 재검증 |
| `embedding` | 추천 검색 배포 시 fill rate `100%` | dense 검색 불가 여부 확인 | 벡터 재생성 |
| `search_vector` | 추천 검색 배포 시 fill rate `100%` | sparse 검색 불가 여부 확인 | 벡터 재생성 |

> `pet_type`, `category`, `subcategory`는 이슈 `#234` 기준의 배포 차단 항목이다.
> 셋 중 하나라도 비어 있으면 추천 검색 필터가 깨질 수 있으므로 배포하지 않는다.

### 4-3. 경고 기준

아래 항목은 추천 결과 품질 저하와 연결되지만, 배포 목적에 따라 해석한다.

| 항목 | 해석 | 권장 대응 |
|---|---|---|
| `health_concern_tags` | 건강 태그 기반 필터/보정 약화 | goods 재적재 또는 OCR/태깅 파이프라인 확인 |
| `main_ingredients` | 알러지/원재료 안전 필터 약화 | ingredients 파이프라인 확인 |
| `ingredient_text_ocr` | OCR 원문 기반 안전 필터 약화 | OCR 파이프라인 확인 |
| `popularity_score` | 랭킹 fallback 약화 | goods Gold 산출물 확인 |
| `sentiment_avg` | 리뷰 품질 기반 랭킹 약화 | review Gold / goods 집계 확인 |
| `repeat_rate` | 재구매 기반 랭킹 약화 | review Gold / goods 집계 확인 |

### 4-4. 배포 전 완료 조건

아래 3개를 모두 만족하면 이슈 `#234`의 완료 기준을 충족한 것으로 본다.

1. `product.pet_type/category/subcategory` fill rate가 모두 `100%`다.
2. 누락 시 실행할 복구 명령이 문서화되어 있다.
3. 비교 결과를 다시 확인하는 재검증 절차가 있다.

---

## 5. 추천 장애와 직접 연결되는 컬럼

| 구간 | 컬럼 | 영향 |
|---|---|---|
| 검색 필터 | `pet_type`, `category`, `subcategory` | 추천 자체가 비거나 엉뚱한 상품이 섞일 수 있다 |
| 검색 인덱스 | `embedding`, `search_vector` | dense/sparse/hybrid 검색이 비정상 동작할 수 있다 |
| 랭킹 | `popularity_score`, `sentiment_avg`, `repeat_rate`, `health_concern_tags` | 검색은 되지만 정렬 품질이 떨어질 수 있다 |
| 안전 필터 | `main_ingredients`, `ingredient_text_ocr` | 알러지/원재료 제외 로직이 약해질 수 있다 |
| 응답 카드 | `goods_name`, `brand_name`, `thumbnail_url`, `product_url` | 추천 패널 노출 품질과 클릭 경험이 깨질 수 있다 |

> 최신 로컬 스냅샷 수치는 [docs/data/recommendation_data_audit_2026-04-06.md](./../data/recommendation_data_audit_2026-04-06.md)에 정리되어 있다.

---

## 6. 결과 해석

### 6-1. `product.row_count`가 다르다

- 로컬 복원 시점이 오래됐거나 적재가 덜 된 상태일 가능성이 높다.
- 먼저 [02_data_restore.md](./02_data_restore.md) 기준으로 로컬 복원 상태를 다시 맞춘다.

### 6-2. `pet_type` / `category` / `subcategory` 차이가 난다

- 추천 검색 필터와 직접 연결되는 항목이라 우선순위가 가장 높다.
- 운영에서는 추천이 되는데 로컬에서 안 되면 이 3개 컬럼부터 확인한다.
- 차이가 있으면 ETL 산출물과 PostgreSQL 적재 시점을 함께 본다.

### 6-3. `embedding` / `search_vector`가 비어 있다

- 상품은 있어도 추천 검색이 비정상일 수 있다.
- 적재가 중간에 끝났거나 벡터/검색 인덱스 생성이 누락된 상태다.
- `scripts/ingest_postgres.py --only vectors` 또는 전체 적재 이력을 확인한다.

### 6-4. `sentiment_avg` / `repeat_rate`가 낮다

- 검색 자체보다 랭킹 품질 저하 쪽으로 보는 게 맞다.
- 리뷰 데이터 유입, 리뷰 Gold 생성, 적재 상태를 같이 본다.

### 6-5. `user_interaction`가 모두 0에 가깝다

- 온라인 피드백 루프가 비어 있는 상태다.
- 현재는 `purchase` 위주일 수 있으므로 `click/cart/reject`가 0이어도 코드 경로와 배포 시점을 함께 판단해야 한다.

---

## 7. 추천 장애 대응 순서

1. `product.row_count`와 `pet_type/category/subcategory`부터 비교한다.
2. 검색 이상이면 `embedding`, `search_vector`를 본다.
3. 랭킹 이상이면 `sentiment_avg`, `repeat_rate`, `health_concern_tags`를 본다.
4. 피드백 반영 이상이면 `user_interaction` 유형별 건수를 본다.
5. 로컬만 이상하면 복원 또는 재적재를 먼저 수행한다.

---

## 8. 복구 기준

### 8-1. 로컬 DB만 뒤처진 경우

- 로컬 DB를 덤프 기준으로 다시 맞춘다.
- 필요하면 아래 순서로 진행한다.

```bash
bash scripts/setup_db.sh
cd services/django
python manage.py migrate --fake
```

### 8-2. 메타데이터 컬럼만 비는 경우

- Gold 산출물과 적재 시점을 확인한다.
- 필요하면 상품 적재를 다시 수행한다.

```bash
POSTGRES_HOST=localhost python scripts/ingest_postgres.py --only goods
POSTGRES_HOST=localhost python scripts/ingest_postgres.py --only vectors
```

### 8-3. 재검증

복구 후에는 반드시 다시 비교한다.

```bash
python scripts/compare_prod_local_db.py --tables product
```

`pet_type`, `category`, `subcategory`가 모두 `100%`로 회복됐는지 확인한 뒤 배포 여부를 결정한다.

---

## 9. 주의

- 이 스크립트는 값을 수정하지 않고 읽기만 한다.
- 운영 DB가 아니라 테스트 RDS를 비교 대상으로 삼는 경우에도 같은 절차를 쓸 수 있다.
- 스키마가 어긋나면 누락 컬럼을 `skipped`로 출력하므로, 그 자체를 스키마 드리프트 신호로 본다.
