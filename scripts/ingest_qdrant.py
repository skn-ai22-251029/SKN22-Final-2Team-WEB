"""
Gold goods parquet → Qdrant products 컬렉션 적재

- GP 상품 (prefix=GP) 제외
- Dense: BAAI/bge-m3 (1024d, fastembed)
- Sparse: Qdrant/bm25 (fastembed)
- 임베딩 텍스트: product_name + brand_name + subcategory_names +
                 health_concern_tags + main_ingredients +
                 ingredient_composition(직렬화) + nutrition_info(직렬화)

실행:
  docker compose -f infra/docker-compose.yml run --rm \\
      -v $(pwd)/output:/app/output \\
      -v $(pwd)/scripts:/app/scripts \\
      fastapi python scripts/ingest_qdrant.py

  # 옵션
  ... --recreate    # 컬렉션 재생성 후 적재
  ... --batch 64    # 배치 크기 (기본 64)
"""

import argparse
import os
import sys
from datetime import datetime
from glob import glob
from pathlib import Path

import pandas as pd
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    HnswConfigDiff,
    Modifier,
    PointStruct,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

# ── 환경변수 ───────────────────────────────────────────────────────────────────

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_KEY = os.getenv("QDRANT_API_KEY", None)
COLLECTION  = "products"

GOODS_GLOB  = "output/gold/goods/*_goods_gold.parquet"


# ── 텍스트 직렬화 ──────────────────────────────────────────────────────────────

def serialize_dict(d) -> str:
    if not isinstance(d, dict) or not d:
        return ""
    return " ".join(f"{k} {v}" for k, v in d.items())


def to_list(val) -> list:
    if val is None:
        return []
    try:
        lst = list(val)
        return [x for x in lst if x is not None]
    except TypeError:
        return []


def build_product_text(row) -> str:
    parts = [
        str(row.get("product_name") or ""),
        str(row.get("brand_name") or ""),
        " ".join(to_list(row.get("subcategory_names"))),
        " ".join(to_list(row.get("health_concern_tags"))),
        " ".join(to_list(row.get("main_ingredients"))),
        serialize_dict(row.get("ingredient_composition")),
        serialize_dict(row.get("nutrition_info")),
    ]
    return " ".join(p for p in parts if p).strip()


# ── payload 빌더 ───────────────────────────────────────────────────────────────

def build_payload(row) -> dict:
    def safe_float(v):
        try:
            f = float(v)
            return None if f != f else f  # NaN 체크
        except (TypeError, ValueError):
            return None

    return {
        "goods_id":          row["goods_id"],
        "product_name":      row.get("product_name"),
        "brand_name":        row.get("brand_name"),
        "prefix":            row.get("prefix"),
        "price":             int(row["price"]) if pd.notna(row.get("price")) else None,
        "discount_price":    int(row["discount_price"]) if pd.notna(row.get("discount_price")) else None,
        "sold_out":          bool(row["sold_out"]) if pd.notna(row.get("sold_out")) else False,
        "soldout_reliable":  bool(row["soldout_reliable"]) if pd.notna(row.get("soldout_reliable")) else True,
        "pet_type":          to_list(row.get("pet_type")),
        "category":          to_list(row.get("category")),
        "subcategory":       to_list(row.get("subcategory")),
        "health_concern_tags": to_list(row.get("health_concern_tags")),
        "main_ingredients":  to_list(row.get("main_ingredients")),
        "ingredient_text_ocr": row.get("ingredient_text_ocr") if pd.notna(row.get("ingredient_text_ocr")) else None,
        "popularity_score":  safe_float(row.get("popularity_score")),
        "sentiment_avg":     safe_float(row.get("sentiment_avg")),
        "repeat_rate":       safe_float(row.get("repeat_rate")),
        "thumbnail_url":     row.get("thumbnail_url"),
        "product_url":       row.get("product_url"),
    }


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(recreate: bool, batch_size: int) -> None:
    print(f"[ingest_qdrant] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Qdrant: {QDRANT_URL}")

    # 1. 데이터 로드
    files = sorted(glob(GOODS_GLOB))
    if not files:
        raise FileNotFoundError(f"파일 없음: {GOODS_GLOB}")
    path = files[-1]
    print(f"  로드: {path}")
    df = pd.read_parquet(path)
    print(f"  전체: {len(df):,}행")

    # 2. GP 제외
    df = df[df["prefix"] != "GP"].copy()
    print(f"  GP 제외 후: {len(df):,}행")

    # 3. 임베딩 텍스트 생성
    print("  임베딩 텍스트 생성 중...")
    texts = [build_product_text(row) for _, row in df.iterrows()]

    # 4. 모델 로드
    print("  모델 로드 중 (fastembed)...")
    from fastembed import SparseTextEmbedding, TextEmbedding
    dense_model  = TextEmbedding("intfloat/multilingual-e5-large")
    sparse_model = SparseTextEmbedding("Qdrant/bm25")
    print("  모델 로드 완료")

    # 5. Qdrant 클라이언트 / 컬렉션
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY)
    existing = {c.name for c in client.get_collections().collections}
    if recreate and COLLECTION in existing:
        print(f"  [{COLLECTION}] 삭제 후 재생성...")
        client.delete_collection(COLLECTION)
        existing.discard(COLLECTION)
    if COLLECTION not in existing:
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config={
                "dense": VectorParams(
                    size=1024,
                    distance=Distance.COSINE,
                    hnsw_config=HnswConfigDiff(m=16, ef_construct=100),
                )
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams(
                    index=SparseIndexParams(on_disk=False),
                    modifier=Modifier.IDF,
                )
            },
        )
        print(f"  [{COLLECTION}] 컬렉션 생성 완료")

    # 6. 배치 임베딩 + 적재
    print(f"  임베딩 + 적재 (batch={batch_size})...")
    goods_ids = df["goods_id"].tolist()
    rows      = df.to_dict("records")
    total     = len(texts)
    upserted  = 0

    from tqdm import tqdm

    batches = range(0, total, batch_size)
    pbar = tqdm(batches, total=len(batches), unit="batch",
                desc="임베딩+적재", dynamic_ncols=True)

    for start in pbar:
        end        = min(start + batch_size, total)
        batch_text = texts[start:end]
        batch_rows = rows[start:end]
        batch_ids  = goods_ids[start:end]

        dense_vecs  = list(dense_model.embed(batch_text))
        sparse_vecs = list(sparse_model.embed(batch_text))

        points = []
        for gid, row, dv, sv in zip(batch_ids, batch_rows, dense_vecs, sparse_vecs):
            points.append(PointStruct(
                id      = abs(hash(gid)) % (2 ** 63),
                vector  = {
                    "dense":  dv.tolist(),
                    "sparse": SparseVector(
                        indices=sv.indices.tolist(),
                        values=sv.values.tolist(),
                    ),
                },
                payload = build_payload(row),
            ))

        client.upsert(collection_name=COLLECTION, points=points)
        upserted += len(points)
        pbar.set_postfix({"적재": f"{upserted:,}/{total:,}"})

    print(f"\n적재 완료: {upserted:,}개 — {datetime.now().strftime('%H:%M:%S')}")
    info = client.get_collection(COLLECTION)
    print(f"  컬렉션 points: {info.points_count:,}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gold goods → Qdrant products 적재")
    parser.add_argument("--recreate", action="store_true", help="컬렉션 재생성 후 적재")
    parser.add_argument("--batch", type=int, default=64, metavar="N", help="배치 크기 (기본 64)")
    args = parser.parse_args()
    main(recreate=args.recreate, batch_size=args.batch)
