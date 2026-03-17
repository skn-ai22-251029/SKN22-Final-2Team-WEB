"""
Gold parquet → PostgreSQL 적재

대상 테이블:
  - product           : gold/goods parquet
  - product_category_tag : health_concern_tags 배열 → 1행씩
  - review            : gold/reviews parquet

실행:
  # Docker (권장) — output/, scripts/ 마운트
  docker compose -f infra/docker-compose.yml run --rm \
      -v $(pwd)/output:/app/output \
      -v $(pwd)/scripts:/app/scripts \
      django python scripts/ingest_postgres.py

  # 로컬 conda (POSTGRES_HOST를 localhost로 오버라이드)
  POSTGRES_HOST=localhost conda run -n final-project python scripts/ingest_postgres.py

  # 옵션
  ... --only goods      # 상품만
  ... --only reviews    # 리뷰만
  ... --truncate        # 기존 데이터 삭제 후 재적재
"""

import argparse
import json
import os
import sys
from datetime import datetime
from glob import glob
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# ── 환경변수 로드 ──────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent.parent / "infra" / ".env")

DB_CONFIG = {
    "dbname":   os.getenv("POSTGRES_DB",       "tailtalk_db"),
    "user":     os.getenv("POSTGRES_USER",     "mungnyang"),
    "password": os.getenv("POSTGRES_PASSWORD", "final1234"),
    "host":     os.getenv("POSTGRES_HOST",     "postgres"),
    "port":     os.getenv("POSTGRES_PORT",     "5432"),
}

GOODS_GLOB   = "output/gold/goods/*_goods_gold.parquet"
REVIEWS_GLOB = "output/gold/reviews/*_reviews_gold.parquet"

BATCH_SIZE = 500


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def latest(glob_pattern: str) -> str:
    files = sorted(glob(glob_pattern))
    if not files:
        raise FileNotFoundError(f"파일 없음: {glob_pattern}")
    return files[-1]


def to_json(val):
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return json.dumps(val, ensure_ascii=False)
    return val


def clean_str(val) -> str | None:
    """NUL 문자 제거"""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return str(val).replace("\x00", "")


def to_list(val):
    """numpy array / list → Python list. null → []"""
    if val is None:
        return []
    try:
        return list(val)
    except TypeError:
        return []


def batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


# ── 상품 적재 ─────────────────────────────────────────────────────────────────

PRODUCT_UPSERT = """
INSERT INTO product (
    goods_id, goods_name, brand_name, price, discount_price,
    rating, review_count, thumbnail_url, product_url, soldout_yn,
    soldout_reliable, pet_type, category, subcategory, health_concern_tags,
    popularity_score, sentiment_avg, repeat_rate,
    main_ingredients, ingredient_composition, nutrition_info, ingredient_text_ocr,
    crawled_at
) VALUES %s
ON CONFLICT (goods_id) DO UPDATE SET
    goods_name            = EXCLUDED.goods_name,
    brand_name            = EXCLUDED.brand_name,
    price                 = EXCLUDED.price,
    discount_price        = EXCLUDED.discount_price,
    rating                = EXCLUDED.rating,
    review_count          = EXCLUDED.review_count,
    thumbnail_url         = EXCLUDED.thumbnail_url,
    product_url           = EXCLUDED.product_url,
    soldout_yn            = EXCLUDED.soldout_yn,
    soldout_reliable      = EXCLUDED.soldout_reliable,
    pet_type              = EXCLUDED.pet_type,
    category              = EXCLUDED.category,
    subcategory           = EXCLUDED.subcategory,
    health_concern_tags   = EXCLUDED.health_concern_tags,
    popularity_score      = EXCLUDED.popularity_score,
    sentiment_avg         = EXCLUDED.sentiment_avg,
    repeat_rate           = EXCLUDED.repeat_rate,
    main_ingredients      = EXCLUDED.main_ingredients,
    ingredient_composition = EXCLUDED.ingredient_composition,
    nutrition_info        = EXCLUDED.nutrition_info,
    ingredient_text_ocr   = EXCLUDED.ingredient_text_ocr
"""

TAG_UPSERT = """
INSERT INTO product_category_tag (id, product_id, tag)
VALUES %s
ON CONFLICT (product_id, tag) DO NOTHING
"""


def ingest_goods(conn, truncate: bool) -> None:
    path = latest(GOODS_GLOB)
    print(f"[goods] 로드: {path}")
    df = pd.read_parquet(path)
    print(f"  행 수: {len(df):,}")

    with conn.cursor() as cur:
        if truncate:
            print("  [truncate] product_category_tag, product 삭제...")
            cur.execute("TRUNCATE TABLE product_category_tag, product RESTART IDENTITY CASCADE")

        # product
        from tqdm import tqdm
        print("  product 적재 중...")
        rows = []
        for _, r in tqdm(df.iterrows(), total=len(df), desc="  rows 변환", unit="행"):
            rows.append((
                r["goods_id"],
                r["product_name"],
                r["brand_name"],
                int(r["price"]),
                int(r["discount_price"]),
                float(r["rating"]) if pd.notna(r.get("rating")) else None,
                int(r["review_count"]) if pd.notna(r.get("review_count")) else 0,
                r["thumbnail_url"],
                r.get("product_url"),
                bool(r["sold_out"]) if pd.notna(r.get("sold_out")) else False,
                bool(r["soldout_reliable"]) if pd.notna(r.get("soldout_reliable")) else True,
                to_list(r.get("pet_type")),
                to_list(r.get("category")),
                to_list(r.get("subcategory")),
                to_list(r.get("health_concern_tags")),
                float(r["popularity_score"]) if pd.notna(r.get("popularity_score")) else None,
                float(r["sentiment_avg"]) if pd.notna(r.get("sentiment_avg")) else None,
                float(r["repeat_rate"]) if pd.notna(r.get("repeat_rate")) else None,
                psycopg2.extras.Json(to_list(r.get("main_ingredients"))) if r.get("main_ingredients") is not None else None,
                psycopg2.extras.Json(r["ingredient_composition"]) if pd.notna(r.get("ingredient_composition")) else None,
                psycopg2.extras.Json(r["nutrition_info"]) if pd.notna(r.get("nutrition_info")) else None,
                r.get("ingredient_text_ocr") if pd.notna(r.get("ingredient_text_ocr")) else None,
                r["crawled_at"].to_pydatetime() if hasattr(r["crawled_at"], "to_pydatetime") else r["crawled_at"],
            ))

        batches = list(batched(rows, BATCH_SIZE))
        for batch in tqdm(batches, desc="  product upsert", unit="batch"):
            psycopg2.extras.execute_values(cur, PRODUCT_UPSERT, batch)
        print(f"  product {len(rows):,}행 완료")

        # product_category_tag
        print("  product_category_tag 적재 중...")
        import uuid
        tag_rows = []
        for _, r in df.iterrows():
            for tag in to_list(r.get("health_concern_tags")):
                tag_rows.append((str(uuid.uuid4()), r["goods_id"], tag))

        for batch in tqdm(list(batched(tag_rows, BATCH_SIZE)), desc="  tag upsert", unit="batch"):
            psycopg2.extras.execute_values(cur, TAG_UPSERT, batch)
        print(f"  product_category_tag {len(tag_rows):,}행 완료")

    conn.commit()


# ── 리뷰 적재 ─────────────────────────────────────────────────────────────────

REVIEW_UPSERT = """
INSERT INTO review (
    review_id, product_id, score, content, author_nickname, written_at,
    purchase_label, sentiment_score, sentiment_label, absa_result,
    pet_age_months, pet_weight_kg, pet_gender, pet_breed
) VALUES %s
ON CONFLICT (review_id) DO UPDATE SET
    sentiment_score  = EXCLUDED.sentiment_score,
    sentiment_label  = EXCLUDED.sentiment_label,
    absa_result      = EXCLUDED.absa_result
"""


def ingest_reviews(conn, truncate: bool) -> None:
    path = latest(REVIEWS_GLOB)
    print(f"[reviews] 로드: {path}")
    df = pd.read_parquet(path)
    print(f"  행 수: {len(df):,}")

    # 적재된 goods_id 목록 (FK 제약 — product 테이블에 없는 리뷰 skip)
    with conn.cursor() as cur:
        if truncate:
            print("  [truncate] review 삭제...")
            cur.execute("TRUNCATE TABLE review RESTART IDENTITY CASCADE")

        cur.execute("SELECT goods_id FROM product")
        valid_goods = {row[0] for row in cur.fetchall()}
    print(f"  유효 goods_id: {len(valid_goods):,}개")

    df = df[df["goods_id"].isin(valid_goods)].copy()
    print(f"  FK 필터 후: {len(df):,}행")

    with conn.cursor() as cur:
        from tqdm import tqdm
        rows = []
        for _, r in tqdm(df.iterrows(), total=len(df), desc="  rows 변환", unit="행"):
            rows.append((
                r["review_id"],
                r["goods_id"],
                float(r["rating_5pt"]) if pd.notna(r.get("rating_5pt")) else None,
                clean_str(r.get("review_text")) or "",
                clean_str(r.get("nickname")) or "",
                r["review_date"] if pd.notna(r.get("review_date")) else None,
                r.get("purchase_label") if pd.notna(r.get("purchase_label")) else None,
                float(r["sentiment_score"]) if pd.notna(r.get("sentiment_score")) else None,
                r.get("sentiment_label") if pd.notna(r.get("sentiment_label")) else None,
                psycopg2.extras.Json(r["absa_result"]) if r.get("absa_result") is not None else None,
                int(r["pet_age_months"]) if pd.notna(r.get("pet_age_months")) else None,
                float(r["pet_weight_kg"]) if pd.notna(r.get("pet_weight_kg")) else None,
                clean_str(r.get("pet_gender")),
                clean_str(r.get("pet_breed")),
            ))

        for batch in tqdm(list(batched(rows, BATCH_SIZE)), desc="  review upsert", unit="batch"):
            psycopg2.extras.execute_values(cur, REVIEW_UPSERT, batch)
        print(f"  review {len(rows):,}행 완료")

    conn.commit()


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(only: str | None, truncate: bool) -> None:
    print(f"[ingest_postgres] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        if only != "reviews":
            ingest_goods(conn, truncate)
        if only != "goods":
            ingest_reviews(conn, truncate)
    finally:
        conn.close()

    print(f"\n완료 — {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gold parquet → PostgreSQL 적재")
    parser.add_argument("--only", choices=["goods", "reviews"], default=None)
    parser.add_argument("--truncate", action="store_true", help="기존 데이터 삭제 후 재적재")
    args = parser.parse_args()
    main(only=args.only, truncate=args.truncate)
