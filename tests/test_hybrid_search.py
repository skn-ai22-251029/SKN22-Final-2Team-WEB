"""
Hybrid Search 통합 테스트 (product / domain_qna / breed_meta)

Dense (pgvector cosine) + Sparse (Kiwi tsvector) + RRF 결합 검증.

실행:
  # docker compose 환경
  POSTGRES_HOST=localhost POSTGRES_DB=tailtalk_db POSTGRES_USER=mungnyang POSTGRES_PASSWORD=<pw> \
      python -m pytest tests/test_hybrid_search.py -v

  # pgvector-lab 테스트 환경
  POSTGRES_HOST=localhost POSTGRES_DB=tailtalk_test POSTGRES_USER=postgres POSTGRES_PASSWORD=1234 \
      python -m pytest tests/test_hybrid_search.py -v
"""

import os

import psycopg2
import pytest

DB_CONFIG = {
    "dbname":   os.getenv("POSTGRES_DB",       "tailtalk_db"),
    "user":     os.getenv("POSTGRES_USER",     "mungnyang"),
    "password": os.getenv("POSTGRES_PASSWORD", ""),
    "host":     os.getenv("POSTGRES_HOST",     "localhost"),
    "port":     os.getenv("POSTGRES_PORT",     "5432"),
}

# ── 공통 fixtures ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def conn():
    c = psycopg2.connect(**DB_CONFIG)
    yield c
    c.close()


@pytest.fixture(scope="session")
def embed_model():
    from fastembed import TextEmbedding
    return TextEmbedding("intfloat/multilingual-e5-large")


@pytest.fixture(scope="session")
def kiwi():
    from kiwipiepy import Kiwi
    return Kiwi()


def _embed(model, text: str) -> str:
    vec = list(model.embed([text]))[0]
    return "[" + ",".join(str(float(v)) for v in vec) + "]"


def _tokenize(kiwi, text: str) -> str:
    tokens = [t.form for t in kiwi.tokenize(text) if t.tag.startswith(("NN", "VV", "VA"))]
    return " & ".join(tokens) if tokens else text


# ── Hybrid Search SQL ──────────────────────────────────────────

HYBRID_SQL = """
WITH dense AS (
    SELECT {pk} AS id, 1 - (embedding <=> %s::vector) AS score
    FROM {table}
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> %s::vector
    LIMIT 20
),
sparse AS (
    SELECT {pk} AS id, ts_rank(search_vector, to_tsquery('simple', %s)) AS score
    FROM {table}
    WHERE search_vector @@ to_tsquery('simple', %s)
    ORDER BY score DESC
    LIMIT 20
),
rrf AS (
    SELECT COALESCE(d.id, s.id) AS id,
           COALESCE(1.0/(60+rank() OVER (ORDER BY d.score DESC NULLS LAST)),0) +
           COALESCE(1.0/(60+rank() OVER (ORDER BY s.score DESC NULLS LAST)),0) AS rrf_score
    FROM dense d FULL OUTER JOIN sparse s ON d.id = s.id
)
SELECT r.rrf_score, r.id
FROM rrf r
ORDER BY r.rrf_score DESC
LIMIT %s;
"""


def hybrid_search(conn, table: str, pk: str, query_vec: str, tsquery: str, limit: int = 5):
    sql = HYBRID_SQL.format(table=table, pk=pk)
    with conn.cursor() as cur:
        cur.execute(sql, (query_vec, query_vec, tsquery, tsquery, limit))
        return cur.fetchall()


# ── product 테스트 ─────────────────────────────────────────────

class TestProductHybridSearch:

    def test_keyword_match(self, conn, embed_model, kiwi):
        """'관절 영양제 소형견' 검색 → 결과 존재"""
        query = "관절 영양제 소형견"
        vec = _embed(embed_model, query)
        tsq = _tokenize(kiwi, query)
        results = hybrid_search(conn, "product", "goods_id", vec, tsq)
        assert len(results) > 0, "product 검색 결과가 없습니다"

    def test_rrf_score_descending(self, conn, embed_model, kiwi):
        """RRF 스코어가 내림차순"""
        query = "강아지 사료 추천"
        vec = _embed(embed_model, query)
        tsq = _tokenize(kiwi, query)
        results = hybrid_search(conn, "product", "goods_id", vec, tsq)
        scores = [r[0] for r in results]
        assert scores == sorted(scores, reverse=True), "RRF 스코어가 내림차순이 아닙니다"

    def test_gp_products_excluded(self, conn):
        """GP 상품은 embedding=NULL이므로 Dense 검색에서 제외"""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*) FROM product
                WHERE prefix = 'GP' AND embedding IS NOT NULL
            """)
            count = cur.fetchone()[0]
        assert count == 0, f"GP 상품 중 embedding이 있는 행: {count}"


# ── domain_qna 테스트 ──────────────────────────────────────────

class TestDomainQnaHybridSearch:

    def test_chocolate_dog(self, conn, embed_model, kiwi):
        """'강아지 초콜릿 중독' → 관련 QnA 검색"""
        query = "강아지가 초콜릿을 먹었어요"
        vec = _embed(embed_model, query)
        tsq = _tokenize(kiwi, query)
        results = hybrid_search(conn, "domain_qna", "id", vec, tsq)
        assert len(results) > 0, "domain_qna 검색 결과가 없습니다"

        # top-5 중 하나는 '초콜릿' 관련이어야 함
        ids = [r[1] for r in results]
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM domain_qna WHERE id = ANY(%s) AND chunk_text LIKE '%%초콜릿%%'",
                (ids,),
            )
            match_count = cur.fetchone()[0]
        assert match_count > 0, "초콜릿 관련 결과가 top-5에 없습니다"

    def test_cat_vomit(self, conn, embed_model, kiwi):
        """'고양이 구토' → species=cat 결과 포함"""
        query = "고양이 구토 원인"
        vec = _embed(embed_model, query)
        tsq = _tokenize(kiwi, query)
        results = hybrid_search(conn, "domain_qna", "id", vec, tsq)
        assert len(results) > 0

        ids = [r[1] for r in results]
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM domain_qna WHERE id = ANY(%s) AND species IN ('cat', 'both')",
                (ids,),
            )
            cat_count = cur.fetchone()[0]
        assert cat_count > 0, "고양이 관련 결과가 top-5에 없습니다"

    def test_species_filter(self, conn):
        """species 컬럼에 유효한 값만 존재"""
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT species FROM domain_qna ORDER BY species")
            species = [r[0] for r in cur.fetchall()]
        assert set(species) <= {"dog", "cat", "both"}, f"예상 외 species: {species}"


# ── breed_meta 테스트 ──────────────────────────────────────────

class TestBreedMetaHybridSearch:

    def test_golden_retriever_puppy(self, conn, embed_model, kiwi):
        """'골든 리트리버 퍼피 관절' → 관련 품종 검색"""
        query = "골든 리트리버 퍼피 관절 건강"
        vec = _embed(embed_model, query)
        tsq = _tokenize(kiwi, query)
        results = hybrid_search(conn, "breed_meta", "id", vec, tsq)
        assert len(results) > 0, "breed_meta 검색 결과가 없습니다"

        ids = [r[1] for r in results]
        with conn.cursor() as cur:
            cur.execute(
                "SELECT count(*) FROM breed_meta WHERE id = ANY(%s) AND breed_name LIKE '%%골든%%'",
                (ids,),
            )
            match_count = cur.fetchone()[0]
        assert match_count > 0, "골든 리트리버가 top-5에 없습니다"

    def test_exact_match(self, conn):
        """breed_name + age_group exact match 조회"""
        with conn.cursor() as cur:
            cur.execute("""
                SELECT breed_name, age_group, preferred_food
                FROM breed_meta
                WHERE breed_name = '말티즈' AND age_group = '어덜트'
            """)
            rows = cur.fetchall()
        assert len(rows) == 1, f"말티즈 어덜트 행: {len(rows)} (기대: 1)"
        assert rows[0][2] is not None, "preferred_food가 NULL입니다"

    def test_persian_senior(self, conn, embed_model, kiwi):
        """'페르시안 시니어 사료' → 페르시안 시니어 top 매칭"""
        query = "페르시안 시니어 사료 추천"
        vec = _embed(embed_model, query)
        tsq = _tokenize(kiwi, query)
        results = hybrid_search(conn, "breed_meta", "id", vec, tsq)
        assert len(results) > 0

        top_id = results[0][1]
        with conn.cursor() as cur:
            cur.execute("SELECT breed_name, age_group FROM breed_meta WHERE id = %s", (top_id,))
            row = cur.fetchone()
        assert row[0] == "페르시안", f"top-1 품종: {row[0]} (기대: 페르시안)"
        assert row[1] == "시니어", f"top-1 연령대: {row[1]} (기대: 시니어)"
