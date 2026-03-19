"""
output/domain/ Parquet → Qdrant domain_qna / breed_meta 컬렉션 적재

- Dense:  intfloat/multilingual-e5-large (1024d, fastembed)
- Sparse: Qdrant/bm25 (fastembed)
- 청크 텍스트 설계: docs/domain/02_domain_rag_pipeline.md

실행:
  conda run -n final-project python scripts/domain/ingest_domain_qdrant.py --collection all

  # 개별 컬렉션
  conda run -n final-project python scripts/domain/ingest_domain_qdrant.py --collection qna
  conda run -n final-project python scripts/domain/ingest_domain_qdrant.py --collection breed

  # 컬렉션 재생성 (기존 데이터 삭제 후 재적재)
  conda run -n final-project python scripts/domain/ingest_domain_qdrant.py --collection all --recreate

  # 배치 크기 조정
  conda run -n final-project python scripts/domain/ingest_domain_qdrant.py --collection all --batch 32
"""

import argparse
import os
from datetime import datetime
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

BASE_DIR   = Path(__file__).resolve().parents[2]
DOMAIN_DIR = BASE_DIR / "output" / "domain"

QNA_PARQUET   = DOMAIN_DIR / "qna.parquet"
BREED_PARQUET = DOMAIN_DIR / "breed_meta.parquet"

COL_QNA   = "domain_qna"
COL_BREED = "breed_meta"


# ── 청크 텍스트 빌더 ──────────────────────────────────────────────────────────

def build_qna_text(row) -> str:
    parts = [
        f"[카테고리] {row.get('category') or ''}",
        f"[질문] {row.get('question') or ''}",
        f"[답변] {row.get('answer') or ''}",
    ]
    notes = row.get("notes")
    if notes and str(notes).strip() and str(notes).strip().lower() != "nan":
        parts.append(f"[참고] {notes}")
    return "\n".join(parts).strip()


def build_breed_text(row) -> str:
    species_kr = "강아지" if row.get("species") == "dog" else "고양이"
    parts = [
        f"[품종] {row.get('breed_name') or ''} ({row.get('breed_name_en') or ''}) — {species_kr} / {row.get('group') or ''}",
        f"[연령대] {row.get('age_group') or ''}",
        f"[일반 특징] {row.get('general_traits') or ''}",
        f"[건강 특징] {row.get('health_traits') or ''}",
        f"[좋아하는 사료] {row.get('preferred_food') or ''}",
        f"[건강제품] {row.get('health_products') or ''}",
        f"[수의 영양학적 메타] {row.get('vet_nutrition_desc') or ''}",
    ]
    return "\n".join(p for p in parts if not p.endswith("— /") and not p.endswith("] ")).strip()


# ── payload 빌더 ──────────────────────────────────────────────────────────────

def build_qna_payload(row) -> dict:
    return {
        "no":       int(row["no"]),
        "species":  row.get("species"),
        "category": row.get("category"),
        "source":   row.get("source"),
    }


def build_breed_payload(row) -> dict:
    def safe_int(v):
        try:
            iv = int(v)
            return iv
        except (TypeError, ValueError):
            return None

    def safe_str(v):
        if v is None or (isinstance(v, float) and v != v):
            return None
        return str(v).strip() or None

    return {
        "species":       row.get("species"),
        "breed_name":    row.get("breed_name"),
        "breed_name_en": row.get("breed_name_en"),
        "group":         row.get("group"),
        "size_class":    list(row["size_class"]) if row.get("size_class") is not None else [],
        "age_group":     row.get("age_group"),
        "care_difficulty": safe_int(row.get("care_difficulty")),
        "preferred_food":  safe_str(row.get("preferred_food")),
        "health_products": safe_str(row.get("health_products")),
    }


# ── Qdrant 컬렉션 생성 ────────────────────────────────────────────────────────

def ensure_collection(client: QdrantClient, name: str, recreate: bool) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if recreate and name in existing:
        print(f"  [{name}] 삭제 후 재생성...")
        client.delete_collection(name)
        existing.discard(name)
    if name not in existing:
        client.create_collection(
            collection_name=name,
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
        print(f"  [{name}] 컬렉션 생성 완료")
    else:
        print(f"  [{name}] 기존 컬렉션 사용 (upsert)")


# ── 배치 적재 ─────────────────────────────────────────────────────────────────

def ingest(
    client: QdrantClient,
    collection: str,
    texts: list[str],
    payloads: list[dict],
    point_ids: list[int],
    dense_model,
    sparse_model,
    batch_size: int,
) -> None:
    from tqdm import tqdm

    total    = len(texts)
    upserted = 0
    batches  = range(0, total, batch_size)
    pbar     = tqdm(batches, total=len(batches), unit="batch",
                    desc=f"{collection} 임베딩+적재", dynamic_ncols=True)

    for start in pbar:
        end         = min(start + batch_size, total)
        batch_text  = texts[start:end]
        batch_pay   = payloads[start:end]
        batch_ids   = point_ids[start:end]

        dense_vecs  = list(dense_model.embed(batch_text))
        sparse_vecs = list(sparse_model.embed(batch_text))

        points = [
            PointStruct(
                id=pid,
                vector={
                    "dense":  dv.tolist(),
                    "sparse": SparseVector(
                        indices=sv.indices.tolist(),
                        values=sv.values.tolist(),
                    ),
                },
                payload=pay,
            )
            for pid, pay, dv, sv in zip(batch_ids, batch_pay, dense_vecs, sparse_vecs)
        ]

        client.upsert(collection_name=collection, points=points)
        upserted += len(points)
        pbar.set_postfix({"적재": f"{upserted:,}/{total:,}"})

    info = client.get_collection(collection)
    print(f"  [{collection}] 적재 완료: {upserted:,}개  (컬렉션 총 {info.points_count:,})")


# ── QnA 파이프라인 ────────────────────────────────────────────────────────────

def run_qna(client, dense_model, sparse_model, recreate: bool, batch_size: int) -> None:
    print(f"\n=== domain_qna 적재 ===")
    if not QNA_PARQUET.exists():
        raise FileNotFoundError(f"파일 없음: {QNA_PARQUET}  (convert_domain_data.py 먼저 실행)")
    df = pd.read_parquet(QNA_PARQUET)
    print(f"  로드: {QNA_PARQUET}  ({len(df):,}행)")

    ensure_collection(client, COL_QNA, recreate)

    texts    = [build_qna_text(row) for _, row in df.iterrows()]
    payloads = [build_qna_payload(row) for _, row in df.iterrows()]
    # point id: no 기반 (1-indexed sequential)
    ids      = [int(row["no"]) for _, row in df.iterrows()]

    ingest(client, COL_QNA, texts, payloads, ids, dense_model, sparse_model, batch_size)


# ── breed_meta 파이프라인 ─────────────────────────────────────────────────────

def run_breed(client, dense_model, sparse_model, recreate: bool, batch_size: int) -> None:
    print(f"\n=== breed_meta 적재 ===")
    if not BREED_PARQUET.exists():
        raise FileNotFoundError(f"파일 없음: {BREED_PARQUET}  (convert_domain_data.py 먼저 실행)")
    df = pd.read_parquet(BREED_PARQUET)
    print(f"  로드: {BREED_PARQUET}  ({len(df):,}행)")

    ensure_collection(client, COL_BREED, recreate)

    texts    = [build_breed_text(row) for _, row in df.iterrows()]
    payloads = [build_breed_payload(row) for _, row in df.iterrows()]
    # point id: 행 인덱스 기반 (0-indexed → 1-indexed)
    ids      = list(range(1, len(df) + 1))

    ingest(client, COL_BREED, texts, payloads, ids, dense_model, sparse_model, batch_size)


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(collection: str, recreate: bool, batch_size: int) -> None:
    print(f"[ingest_domain_qdrant] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Qdrant: {QDRANT_URL}")
    print(f"  collection: {collection}  recreate: {recreate}  batch: {batch_size}")

    print("\n  모델 로드 중 (fastembed)...")
    from fastembed import SparseTextEmbedding, TextEmbedding
    dense_model  = TextEmbedding("intfloat/multilingual-e5-large")
    sparse_model = SparseTextEmbedding("Qdrant/bm25")
    print("  모델 로드 완료")

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY)

    if collection in ("qna", "all"):
        run_qna(client, dense_model, sparse_model, recreate, batch_size)
    if collection in ("breed", "all"):
        run_breed(client, dense_model, sparse_model, recreate, batch_size)

    print(f"\n[완료] {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="domain Parquet → Qdrant 적재")
    parser.add_argument(
        "--collection",
        choices=["qna", "breed", "all"],
        default="all",
        help="적재할 컬렉션 (기본: all)",
    )
    parser.add_argument("--recreate", action="store_true", help="컬렉션 재생성 후 적재")
    parser.add_argument("--batch", type=int, default=64, metavar="N", help="배치 크기 (기본 64)")
    args = parser.parse_args()
    main(collection=args.collection, recreate=args.recreate, batch_size=args.batch)
