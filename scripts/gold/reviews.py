"""
Gold Reviews ETL
Silver reviews + Sentiment 결과 → Gold reviews parquet

선행 작업:
  conda run -n final-project python scripts/gold/sentiment.py --use-cache
  (또는 직접 실행: python scripts/gold/sentiment.py)

실행:
  conda run -n final-project python scripts/gold/reviews.py
  conda run -n final-project python scripts/gold/reviews.py --sample 10
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# ── 기본 경로 ─────────────────────────────────────────────────────────────────

SILVER_REVIEWS_GLOB = "output/silver/reviews/*_reviews_silver.parquet"
BASIC_GLOB          = "output/gold/sentiment/*_basic.parquet"
ABSA_GLOB           = "output/gold/sentiment/*_absa.parquet"

ASPECT_COLS = ["기호성", "생체반응", "소화/배변", "제품 성상", "성분/원료", "냄새", "가격/구매", "배송/포장"]

# ── Gold 컬럼 ─────────────────────────────────────────────────────────────────

GOLD_COLUMNS = [
    "review_id", "goods_id", "nickname", "review_date",
    "rating_5pt", "purchase_label", "review_text",
    "has_photo", "pet_name", "pet_gender",
    "pet_age_months", "pet_weight_kg", "pet_breed", "review_info",
    "sentiment_score", "sentiment_label", "absa_result",
    "processed_at",
]


# ── ABSA 로드 ─────────────────────────────────────────────────────────────────

def load_absa(path: str) -> dict[str, list] | None:
    p = Path(path)
    if not p.exists():
        print(f"  ABSA 파일 없음: {p}")
        return None
    df = pd.read_parquet(p)
    print(f"  ABSA 로드: {p} ({len(df):,}행)")

    absa_map: dict[str, list] = {}
    for review_id, group in df.groupby("review_id"):
        rows = []
        for _, row in group.iterrows():
            entry = {"sentence": row.get("문장", "")}
            for asp in ASPECT_COLS:
                entry[asp] = row.get(asp, "-")
            entry["종합_확신도"] = float(row.get("종합_확신도", 0))
            rows.append(entry)
        absa_map[str(review_id)] = rows

    print(f"  ABSA review 수: {len(absa_map):,}개")
    return absa_map


# ── 메인 ──────────────────────────────────────────────────────────────────────

def latest_silver() -> str:
    files = sorted(Path(".").glob(SILVER_REVIEWS_GLOB))
    if not files:
        raise FileNotFoundError(f"Silver reviews 파일 없음: {SILVER_REVIEWS_GLOB}")
    return str(files[-1])


def main(input_path: str | None, sample_n: int | None) -> None:
    print(f"[gold/reviews] 시작 — {datetime.now().strftime('%H:%M:%S')}")

    # 1. Silver reviews 로드
    path = input_path or latest_silver()
    print(f"  입력: {path}")
    df = pd.read_parquet(path)
    print(f"  Silver 전체: {len(df):,}행")

    if sample_n:
        df = df.sample(n=min(sample_n, len(df)), random_state=42).copy()
        print(f"  샘플링: {len(df)}행")

    df["review_id"] = df["review_id"].astype(str)

    # 2. Basic sentiment join
    print("[1/2] Basic sentiment 로드 중...")
    basic_files = sorted(Path(".").glob(BASIC_GLOB))
    if basic_files:
        df_basic = pd.read_parquet(basic_files[-1])
        df_basic["review_id"] = df_basic["review_id"].astype(str)
        df_basic = df_basic.drop_duplicates(subset=["review_id"])
        df = df.merge(df_basic[["review_id", "sentiment_label", "sentiment_score"]],
                      on="review_id", how="left")
        print(f"  sentiment 매핑: {df['sentiment_label'].notna().sum():,}개 / {len(df):,}개")
    else:
        print(f"  basic parquet 없음 — sentiment.py 먼저 실행하세요")
        df["sentiment_label"] = None
        df["sentiment_score"] = None

    # 3. ABSA join
    print("[2/2] ABSA 로드 중...")
    absa_files = sorted(Path(".").glob(ABSA_GLOB))
    absa_path = str(absa_files[-1]) if absa_files else ABSA_GLOB
    absa_map = load_absa(absa_path)
    if absa_map:
        df["absa_result"] = df["review_id"].map(absa_map)
        print(f"  ABSA 매핑: {df['absa_result'].notna().sum():,}개 / {len(df):,}개")
    else:
        df["absa_result"] = None

    # 4. 저장
    df["processed_at"] = pd.Timestamp.now(tz="UTC")
    df_out = df[[c for c in GOLD_COLUMNS if c in df.columns]]

    output_dir = Path("output/gold/reviews")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{datetime.now().strftime('%Y%m%d')}_reviews_gold.parquet"
    df_out.to_parquet(output_path, index=False)

    print(f"\n저장 완료: {output_path}")
    print(f"  행: {len(df_out):,}개 / 컬럼: {len(df_out.columns)}개")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Silver reviews + Sentiment → Gold reviews ETL")
    parser.add_argument("--input", default=None, help="Silver reviews parquet 경로 (기본: 최신 파일 자동 탐색)")
    parser.add_argument("--sample", type=int, default=None, metavar="N")
    args = parser.parse_args()

    main(input_path=args.input, sample_n=args.sample)
