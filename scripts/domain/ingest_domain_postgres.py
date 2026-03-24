"""
output/domain/ Parquet → PostgreSQL domain_qna / breed_meta 테이블 적재
(pgvector Dense + Kiwi tsvector)

- Dense:  intfloat/multilingual-e5-large (1024d, fastembed)
- Sparse: Kiwi 형태소 분석 → tsvector('simple', tokens)
- 청크 텍스트 설계: docs/domain/02_domain_rag_pipeline.md

실행:
  # Docker (권장)
  docker compose -f infra/docker-compose.yml run --rm \
      -v $(pwd)/output:/app/output \
      -v $(pwd)/scripts:/app/scripts \
      django python scripts/domain/ingest_domain_postgres.py --table all

  # 로컬 conda
  POSTGRES_HOST=localhost conda run -n web_server_env python scripts/domain/ingest_domain_postgres.py --table all

  # 개별 테이블
  ... --table qna
  ... --table breed

  # 기존 데이터 삭제 후 재적재
  ... --table all --truncate

  # 배치 크기 조정
  ... --table all --batch 32
"""

import argparse
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# -- 환경변수 로드 ----------------------------------------------------------------

load_dotenv(Path(__file__).resolve().parents[2] / "infra" / ".env")

DB_CONFIG = {
    "dbname":   os.getenv("POSTGRES_DB",       "tailtalk_db"),
    "user":     os.getenv("POSTGRES_USER",     "mungnyang"),
    "password": os.getenv("POSTGRES_PASSWORD", "final1234"),
    "host":     os.getenv("POSTGRES_HOST",     "postgres"),
    "port":     os.getenv("POSTGRES_PORT",     "5432"),
}

BASE_DIR     = Path(__file__).resolve().parents[2]
DOMAIN_DIR   = BASE_DIR / "output" / "domain"
QNA_PARQUET  = DOMAIN_DIR / "qna.parquet"
BREED_PARQUET = DOMAIN_DIR / "breed_meta.parquet"

BATCH_SIZE = 500


# -- DDL -----------------------------------------------------------------------

DDL_DOMAIN_QNA = """
CREATE TABLE IF NOT EXISTS domain_qna (
    id            SERIAL PRIMARY KEY,
    no            INTEGER NOT NULL,
    species       VARCHAR(10),
    category      VARCHAR(50),
    source        VARCHAR(20),
    chunk_text    TEXT,
    embedding     vector(1024),
    search_vector tsvector
)
"""

DDL_BREED_META = """
CREATE TABLE IF NOT EXISTS breed_meta (
    id              SERIAL PRIMARY KEY,
    species         VARCHAR(10),
    breed_name      VARCHAR(100),
    breed_name_en   VARCHAR(100),
    group_name      VARCHAR(50),
    size_class      TEXT[],
    age_group       VARCHAR(20),
    care_difficulty  INTEGER,
    preferred_food   TEXT,
    health_products  TEXT,
    chunk_text      TEXT,
    embedding       vector(1024),
    search_vector   tsvector
)
"""

IDX_DOMAIN_QNA = [
    "CREATE INDEX IF NOT EXISTS idx_domain_qna_embedding ON domain_qna USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)",
    "CREATE INDEX IF NOT EXISTS idx_domain_qna_search_vector ON domain_qna USING gin (search_vector)",
    "CREATE INDEX IF NOT EXISTS idx_domain_qna_species ON domain_qna (species)",
]

IDX_BREED_META = [
    "CREATE INDEX IF NOT EXISTS idx_breed_meta_embedding ON breed_meta USING hnsw (embedding vector_cosine_ops) WITH (m=16, ef_construction=64)",
    "CREATE INDEX IF NOT EXISTS idx_breed_meta_search_vector ON breed_meta USING gin (search_vector)",
    "CREATE INDEX IF NOT EXISTS idx_breed_meta_species ON breed_meta (species)",
    "CREATE INDEX IF NOT EXISTS idx_breed_meta_breed_age ON breed_meta (breed_name, age_group)",
]


# -- 청크 텍스트 빌더 -------------------------------------------------------------

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


# -- Kiwi 토큰화 ----------------------------------------------------------------

def tokenize_korean(kiwi, text: str) -> str:
    tokens = []
    for token in kiwi.tokenize(text):
        if token.tag.startswith(("NN", "VV", "VA")):
            tokens.append(token.form)
    return " ".join(tokens)


# -- 헬퍼 ---------------------------------------------------------------------

def batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def clean_str(val) -> str | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    return str(val).replace("\x00", "").strip() or None


def to_list(val) -> list:
    if val is None:
        return []
    try:
        return list(val)
    except TypeError:
        return []


# -- QnA 적재 ------------------------------------------------------------------

def ingest_qna(conn, kiwi, dense_model, embed_batch_size: int, truncate: bool) -> None:
    print(f"\n=== domain_qna 적재 ===")
    if not QNA_PARQUET.exists():
        raise FileNotFoundError(f"파일 없음: {QNA_PARQUET}  (convert_domain_data.py 먼저 실행)")
    df = pd.read_parquet(QNA_PARQUET)
    print(f"  로드: {QNA_PARQUET}  ({len(df):,}행)")

    with conn.cursor() as cur:
        cur.execute(DDL_DOMAIN_QNA)
        for idx_sql in IDX_DOMAIN_QNA:
            cur.execute(idx_sql)
        if truncate:
            print("  [truncate] domain_qna 삭제...")
            cur.execute("TRUNCATE TABLE domain_qna RESTART IDENTITY CASCADE")
    conn.commit()

    # 청크 텍스트 조합
    from tqdm import tqdm
    print("  청크 텍스트 조합 중...")
    texts = []
    rows_data = []
    for _, r in tqdm(df.iterrows(), total=len(df), desc="  텍스트 조합", unit="행"):
        text = build_qna_text(r)
        texts.append(text)
        rows_data.append({
            "no":       int(r["no"]),
            "species":  r.get("species"),
            "category": r.get("category"),
            "source":   r.get("source"),
        })

    # Kiwi 토큰화
    print("  Kiwi 형태소 분석 중...")
    tokenized = [tokenize_korean(kiwi, t) for t in tqdm(texts, desc="  토큰화", unit="행")]

    # Dense 임베딩
    print("  Dense 임베딩 생성 중...")
    embeddings = list(dense_model.embed(texts, batch_size=embed_batch_size))
    print(f"  임베딩 {len(embeddings):,}개 생성 완료")

    # INSERT
    print("  DB 적재 중...")
    insert_sql = """
    INSERT INTO domain_qna (no, species, category, source, chunk_text, embedding, search_vector)
    VALUES (%s, %s, %s, %s, %s, %s::vector, to_tsvector('simple', %s))
    """
    with conn.cursor() as cur:
        for batch_start in tqdm(range(0, len(texts), BATCH_SIZE), desc="  qna insert", unit="batch"):
            batch_end = min(batch_start + BATCH_SIZE, len(texts))
            for i in range(batch_start, batch_end):
                vec_str = "[" + ",".join(str(float(v)) for v in embeddings[i]) + "]"
                rd = rows_data[i]
                cur.execute(insert_sql, (
                    rd["no"], rd["species"], rd["category"], rd["source"],
                    texts[i], vec_str, tokenized[i],
                ))
            conn.commit()

    print(f"  domain_qna {len(texts):,}행 적재 완료")


# -- breed_meta 적재 -----------------------------------------------------------

def ingest_breed(conn, kiwi, dense_model, embed_batch_size: int, truncate: bool) -> None:
    print(f"\n=== breed_meta 적재 ===")
    if not BREED_PARQUET.exists():
        raise FileNotFoundError(f"파일 없음: {BREED_PARQUET}  (convert_domain_data.py 먼저 실행)")
    df = pd.read_parquet(BREED_PARQUET)
    print(f"  로드: {BREED_PARQUET}  ({len(df):,}행)")

    with conn.cursor() as cur:
        cur.execute(DDL_BREED_META)
        for idx_sql in IDX_BREED_META:
            cur.execute(idx_sql)
        if truncate:
            print("  [truncate] breed_meta 삭제...")
            cur.execute("TRUNCATE TABLE breed_meta RESTART IDENTITY CASCADE")
    conn.commit()

    # 청크 텍스트 조합
    from tqdm import tqdm
    print("  청크 텍스트 조합 중...")
    texts = []
    rows_data = []
    for _, r in tqdm(df.iterrows(), total=len(df), desc="  텍스트 조합", unit="행"):
        text = build_breed_text(r)
        texts.append(text)
        rows_data.append({
            "species":         r.get("species"),
            "breed_name":      r.get("breed_name"),
            "breed_name_en":   r.get("breed_name_en"),
            "group_name":      r.get("group"),
            "size_class":      to_list(r.get("size_class")),
            "age_group":       r.get("age_group"),
            "care_difficulty":  int(r["care_difficulty"]) if pd.notna(r.get("care_difficulty")) else None,
            "preferred_food":   clean_str(r.get("preferred_food")),
            "health_products":  clean_str(r.get("health_products")),
        })

    # Kiwi 토큰화
    print("  Kiwi 형태소 분석 중...")
    tokenized = [tokenize_korean(kiwi, t) for t in tqdm(texts, desc="  토큰화", unit="행")]

    # Dense 임베딩
    print("  Dense 임베딩 생성 중...")
    embeddings = list(dense_model.embed(texts, batch_size=embed_batch_size))
    print(f"  임베딩 {len(embeddings):,}개 생성 완료")

    # INSERT
    print("  DB 적재 중...")
    insert_sql = """
    INSERT INTO breed_meta (
        species, breed_name, breed_name_en, group_name, size_class, age_group,
        care_difficulty, preferred_food, health_products,
        chunk_text, embedding, search_vector
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::vector, to_tsvector('simple', %s))
    """
    with conn.cursor() as cur:
        for batch_start in tqdm(range(0, len(texts), BATCH_SIZE), desc="  breed insert", unit="batch"):
            batch_end = min(batch_start + BATCH_SIZE, len(texts))
            for i in range(batch_start, batch_end):
                vec_str = "[" + ",".join(str(float(v)) for v in embeddings[i]) + "]"
                rd = rows_data[i]
                cur.execute(insert_sql, (
                    rd["species"], rd["breed_name"], rd["breed_name_en"],
                    rd["group_name"], rd["size_class"], rd["age_group"],
                    rd["care_difficulty"], rd["preferred_food"], rd["health_products"],
                    texts[i], vec_str, tokenized[i],
                ))
            conn.commit()

    print(f"  breed_meta {len(texts):,}행 적재 완료")


# -- 메인 ---------------------------------------------------------------------

def main(table: str, truncate: bool, embed_batch_size: int) -> None:
    print(f"[ingest_domain_postgres] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  DB: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}")
    print(f"  table: {table}  truncate: {truncate}  batch: {embed_batch_size}")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()

        # 모델 로드
        print("\n  모델 로드 중...")
        from fastembed import TextEmbedding
        from kiwipiepy import Kiwi
        dense_model = TextEmbedding("intfloat/multilingual-e5-large")
        kiwi = Kiwi()
        print("  모델 로드 완료")

        if table in ("qna", "all"):
            ingest_qna(conn, kiwi, dense_model, embed_batch_size, truncate)
        if table in ("breed", "all"):
            ingest_breed(conn, kiwi, dense_model, embed_batch_size, truncate)
    finally:
        conn.close()

    print(f"\n[완료] {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="domain Parquet → PostgreSQL 적재 (pgvector + tsvector)")
    parser.add_argument("--table", choices=["qna", "breed", "all"], default="all", help="적재할 테이블 (기본: all)")
    parser.add_argument("--truncate", action="store_true", help="기존 데이터 삭제 후 재적재")
    parser.add_argument("--batch", type=int, default=64, metavar="N", help="임베딩 배치 크기 (기본 64)")
    args = parser.parse_args()
    main(table=args.table, truncate=args.truncate, embed_batch_size=args.batch)
