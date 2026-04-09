# pgvector 마이그레이션 — DB 테이블 변경사항

> Qdrant 벡터 DB를 제거하고 PostgreSQL pgvector로 통합
> 변경 대상: `product` 테이블

---

## 1. 변경 배경

| 항목 | Before | After |
|------|--------|-------|
| 벡터 검색 | Qdrant (별도 서비스) | PostgreSQL pgvector (동일 DB) |
| Sparse 검색 | Qdrant BM25 (내장) | Kiwi + tsvector (PostgreSQL 내장) |
| Hybrid Search | Qdrant Dense + Sparse + RRF | pgvector Cosine + ts_rank + RRF |
| 메타데이터 필터 | Qdrant payload 필드 | SQL WHERE (기존 컬럼 그대로) |
| 인프라 | PostgreSQL + Qdrant 2개 서비스 | PostgreSQL 1개로 통합 |

---

## 2. 필수 확장

```sql
CREATE EXTENSION IF NOT EXISTS vector;   -- pgvector
```

> PostgreSQL 15+ 권장. `tsvector`는 내장이므로 별도 확장 불필요.

---

## 3. `product` 테이블 변경

### 3-1. 추가 컬럼

| 컬럼 | 타입 | Nullable | 설명 |
|------|------|:--------:|------|
| `prefix` | `VARCHAR(5)` | NOT NULL | 상품 ID 접두사 (`GI`/`GP`/`GO`/`GS`/`PI`). Silver에서 파싱. GP 상품 벡터 제외 판단용 |
| `embedding` | `vector(1024)` | NULL | Dense 벡터. `intfloat/multilingual-e5-large` 1024d. GP 상품은 NULL |
| `embedding_text` | `TEXT` | NULL | 임베딩 생성에 사용한 원본 텍스트. 디버깅/재생성용 |
| `search_vector` | `tsvector` | NULL | Kiwi 형태소 분석 결과. 한국어 전문검색용 |

### 3-2. 추가 인덱스

| 인덱스명 | 타입 | 대상 | 용도 |
|----------|------|------|------|
| `idx_product_embedding` | HNSW | `embedding vector_cosine_ops` | 벡터 유사도 검색 |
| `idx_product_search_vector` | GIN | `search_vector` | 전문검색 |
| `idx_product_prefix` | BTREE | `prefix` | GP 제외 필터링 |

### 3-3. DDL

```sql
-- 컬럼 추가
ALTER TABLE product ADD COLUMN prefix         VARCHAR(5);
ALTER TABLE product ADD COLUMN embedding      vector(1024);
ALTER TABLE product ADD COLUMN embedding_text  TEXT;
ALTER TABLE product ADD COLUMN search_vector   tsvector;

-- prefix 채우기 (기존 데이터)
UPDATE product SET prefix = LEFT(goods_id, 2);

-- NOT NULL 제약 (prefix만)
ALTER TABLE product ALTER COLUMN prefix SET NOT NULL;

-- 인덱스 생성
CREATE INDEX idx_product_embedding      ON product USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_product_search_vector  ON product USING gin (search_vector);
CREATE INDEX idx_product_prefix         ON product USING btree (prefix);
```

### 3-4. 변경 후 전체 컬럼 목록

```
product
├── goods_id               VARCHAR(20)    PK
├── prefix                 VARCHAR(5)     NOT NULL        ← NEW
├── goods_name             TEXT
├── brand_name             VARCHAR(200)
├── price                  INTEGER
├── discount_price         INTEGER
├── rating                 NUMERIC(3,1)   NULLABLE
├── review_count           INTEGER        DEFAULT 0
├── thumbnail_url          TEXT
├── product_url            TEXT
├── soldout_yn             BOOLEAN        DEFAULT FALSE
├── soldout_reliable       BOOLEAN        DEFAULT TRUE
├── pet_type               TEXT[]
├── category               TEXT[]
├── subcategory            TEXT[]
├── health_concern_tags    TEXT[]
├── popularity_score       NUMERIC(10,4)  NULLABLE
├── sentiment_avg          NUMERIC(5,4)   NULLABLE
├── repeat_rate            NUMERIC(5,4)   NULLABLE
├── main_ingredients       JSONB          NULLABLE
├── ingredient_composition JSONB          NULLABLE
├── nutrition_info         JSONB          NULLABLE
├── ingredient_text_ocr    TEXT           NULLABLE
├── embedding              vector(1024)   NULLABLE        ← NEW
├── embedding_text         TEXT           NULLABLE        ← NEW
├── search_vector          tsvector       NULLABLE        ← NEW
└── crawled_at             TIMESTAMP
```

---

## 4. 삭제 대상

| 항목 | 설명 |
|------|------|
| Qdrant `products` 컬렉션 | pgvector로 대체됨 |
| `scripts/ingest_qdrant.py` | `ingest_postgres.py`에 벡터 적재 로직 통합 |
| `services/fastapi/core/qdrant_setup.py` | Qdrant 연결 설정 불필요 |
| `deploy/local/.env`의 `QDRANT_URL`, `QDRANT_API_KEY` | 환경변수 제거 |
| `docker-compose.yml`의 qdrant 서비스 | 컨테이너 제거 |

---

## 5. 다른 테이블 변경

**변경 없음.** `product_category_tag`, `review`, 기타 테이블은 그대로 유지.

---

## 6. Django 모델 변경 (예정)

`services/django/products/models.py`의 `Product` 모델에 반영 필요:

```python
# 추가 필요 (pgvector django 통합)
from pgvector.django import VectorField

class Product(models.Model):
    # ... 기존 필드 ...
    prefix          = models.CharField(max_length=5)
    embedding       = VectorField(dimensions=1024, null=True, blank=True)
    embedding_text  = models.TextField(null=True, blank=True)
    search_vector   = SearchVectorField(null=True)  # django.contrib.postgres.search
```

**pip 의존성 추가**: `pgvector` (Django pgvector 통합 패키지)

---

## 7. 영향받는 문서

| 문서 | 반영 상태 |
|------|:---------:|
| `docs/data/02_medallion_schema.md` | 완료 |
| `docs/data/03_ingest_pipeline.md` | 완료 |
| `docs/data/04_feature_engineering.md` | 완료 |
| `docs/planning/04_data_model_detail.md` | 완료 |
| `docs/infra/03_django_models.md` | 완료 |
| `docs/planning/07_recommendation_architecture.md` | 완료 |
| `docs/domain/02_domain_rag_pipeline.md` | 완료 |
