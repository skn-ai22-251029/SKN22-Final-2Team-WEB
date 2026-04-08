# 운영 DB와 로컬 DB 비교 런북

> 이 문서는 이슈 `#235` 대응용이다.
> 목적은 추천 장애가 났을 때 운영 DB와 로컬 DB의 핵심 테이블 상태를 빠르게 비교하는 것이다.

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

로컬 DB는 `infra/.env`를 읽어 자동 구성할 수 있으므로, 운영 DB DSN만 넘기면 된다.

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

## 4. 결과 해석

### 4-1. `product.row_count`가 다르다

- 로컬 복원 시점이 오래됐거나 적재가 덜 된 상태일 가능성이 높다.
- 먼저 [02_data_restore.md](./02_data_restore.md) 기준으로 로컬 복원 상태를 다시 맞춘다.

### 4-2. `pet_type` / `category` / `subcategory` 차이가 난다

- 추천 검색 필터와 직접 연결되는 항목이라 우선순위가 가장 높다.
- 운영에서는 추천이 되는데 로컬에서 안 되면 이 3개 컬럼부터 확인한다.
- 차이가 있으면 ETL 산출물과 PostgreSQL 적재 시점을 함께 본다.

### 4-3. `embedding` / `search_vector`가 비어 있다

- 상품은 있어도 추천 검색이 비정상일 수 있다.
- 적재가 중간에 끝났거나 벡터/검색 인덱스 생성이 누락된 상태다.
- `scripts/ingest_postgres.py --only vectors` 또는 전체 적재 이력을 확인한다.

### 4-4. `sentiment_avg` / `repeat_rate`가 낮다

- 검색 자체보다 랭킹 품질 저하 쪽으로 보는 게 맞다.
- 리뷰 데이터 유입, 리뷰 Gold 생성, 적재 상태를 같이 본다.

### 4-5. `user_interaction`가 모두 0에 가깝다

- 온라인 피드백 루프가 비어 있는 상태다.
- 현재는 `purchase` 위주일 수 있으므로 `click/cart/reject`가 0이어도 코드 경로와 배포 시점을 함께 판단해야 한다.

---

## 5. 추천 장애 대응 순서

1. `product.row_count`와 `pet_type/category/subcategory`부터 비교한다.
2. 검색 이상이면 `embedding`, `search_vector`를 본다.
3. 랭킹 이상이면 `sentiment_avg`, `repeat_rate`, `health_concern_tags`를 본다.
4. 피드백 반영 이상이면 `user_interaction` 유형별 건수를 본다.
5. 로컬만 이상하면 복원 또는 재적재를 먼저 수행한다.

---

## 6. 복구 기준

### 로컬 DB만 뒤처진 경우

- 로컬 DB를 덤프 기준으로 다시 맞춘다.
- 필요하면 아래 순서로 진행한다.

```bash
bash scripts/setup_db.sh
cd services/django
python manage.py migrate --fake
```

### 메타데이터 컬럼만 비는 경우

- Gold 산출물과 적재 시점을 확인한다.
- 필요하면 상품 적재를 다시 수행한다.

```bash
POSTGRES_HOST=localhost python scripts/ingest_postgres.py --only goods
POSTGRES_HOST=localhost python scripts/ingest_postgres.py --only vectors
```

---

## 7. 주의

- 이 스크립트는 값을 수정하지 않고 읽기만 한다.
- 운영 DB가 아니라 테스트 RDS를 비교 대상으로 삼는 경우에도 같은 절차를 쓸 수 있다.
- 스키마가 어긋나면 누락 컬럼을 `skipped`로 출력하므로, 그 자체를 스키마 드리프트 신호로 본다.
