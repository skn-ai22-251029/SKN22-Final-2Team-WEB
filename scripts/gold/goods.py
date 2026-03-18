"""
Gold Goods 어셈블리
Silver goods + OCR 결과 + health_tags + ingredients 파싱 결과 → Gold goods parquet

선행 스크립트:
  1. scripts/gold/ocr.py          → output/gold/ocr/YYYYMMDD_ocr.parquet
  2. scripts/gold/health_tags.py  → output/gold/health_tags/YYYYMMDD_health_tags.parquet
  3. scripts/gold/ingredients.py  → output/gold/ingredients/YYYYMMDD_ingredients.parquet
  4. scripts/gold/sentiment.py    → output/gold/sentiment/YYYYMMDD_basic.parquet

처리 순서:
  1. Silver goods 로드 (canonical만)
  2. OCR 결과 JOIN → ingredient_text_ocr
  3. health_concern_tags JOIN (ocr_target=True → health_tags parquet, 나머지 → [])
  4. ingredients 파싱 결과 JOIN → main_ingredients, ingredient_composition, nutrition_info
  5. popularity_score 파생
  6. sentiment_avg / repeat_rate 집계 (sentiment basic.parquet + silver reviews)
  7. 출력: output/gold/goods/YYYYMMDD_goods_gold.parquet

실행:
  conda run -n final-project python scripts/gold/goods.py
  conda run -n final-project python scripts/gold/goods.py --sample 10
  conda run -n final-project python scripts/gold/goods.py \\
      --reviews-input output/silver/reviews/20260310_reviews_silver.parquet \\
      --sentiment-input output/gold/sentiment/20260310_basic.parquet
"""

import argparse
import math
import sys
from datetime import datetime
from glob import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# ── 상수 ──────────────────────────────────────────────────────────────────────

OCR_CACHE_GLOB          = "output/gold/ocr/*_ocr.parquet"
HEALTH_TAGS_CACHE_GLOB  = "output/gold/health_tags/*_health_tags.parquet"
INGREDIENTS_CACHE_GLOB  = "output/gold/ingredients/*_ingredients.parquet"
SENTIMENT_CACHE_GLOB    = "output/gold/sentiment/*_basic.parquet"

GOLD_COLUMNS = [
    "goods_id", "prefix", "product_name", "brand_id", "brand_name",
    "price", "discount_price", "rating", "rating_5pt", "review_count",
    "sold_out", "thumbnail_url", "product_url",
    "subcategories", "subcategory_names", "pet_type", "category", "subcategory",
    "review_count_source", "soldout_reliable", "ocr_target",
    "is_canonical", "duplicate_of", "crawled_at",
    "health_concern_tags",
    "ingredient_text_ocr",
    "main_ingredients",
    "ingredient_composition",
    "nutrition_info",
    "popularity_score", "sentiment_avg", "repeat_rate", "processed_at",
]


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def load_latest(glob_pattern: str, label: str) -> pd.DataFrame | None:
    """glob 패턴으로 최신 parquet 로드. 없으면 None 반환."""
    files = sorted(glob(glob_pattern))
    if not files:
        print(f"  {label} 없음 → 해당 컬럼 NULL 처리")
        return None
    path = files[-1]
    df = pd.read_parquet(path)
    print(f"  {label} 로드: {path} ({len(df):,}개)")
    return df


def calc_popularity_score(review_count, rating_5pt) -> float | None:
    if pd.isna(rating_5pt) or pd.isna(review_count):
        return None
    return math.log(review_count + 1) * rating_5pt


def calc_sentiment_avg(df_goods: pd.DataFrame, df_sentiment: pd.DataFrame | None, df_reviews: pd.DataFrame | None) -> pd.Series:
    """goods_id별 sentiment_score 평균. sentiment parquet은 review_id 기준이므로 reviews를 통해 goods_id 매핑."""
    null_series = pd.Series([None] * len(df_goods), index=df_goods.index, dtype=object)
    if df_sentiment is None or df_reviews is None:
        return null_series

    # review_id → goods_id 매핑
    id_map = df_reviews[["review_id", "goods_id"]].drop_duplicates()
    df_s = df_sentiment.merge(id_map, on="review_id", how="inner")
    avg = df_s.groupby("goods_id")["sentiment_score"].mean().round(4)
    return df_goods["goods_id"].map(avg)


def calc_repeat_rate(df_goods: pd.DataFrame, df_reviews: pd.DataFrame | None) -> pd.Series:
    """goods_id별 재구매 리뷰 비율 (purchase_label == 'repeat' / 전체)."""
    null_series = pd.Series([None] * len(df_goods), index=df_goods.index, dtype=object)
    if df_reviews is None or "purchase_label" not in df_reviews.columns:
        return null_series

    total = df_reviews.groupby("goods_id").size().rename("total")
    repeat = df_reviews[df_reviews["purchase_label"] == "repeat"].groupby("goods_id").size().rename("repeat")
    stat = total.to_frame().join(repeat, how="left").fillna(0)
    stat["repeat_rate"] = (stat["repeat"] / stat["total"].replace(0, 1)).round(4)
    return df_goods["goods_id"].map(stat["repeat_rate"])


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(
    input_path: str,
    ocr_cache_path: str | None,
    ingredients_path: str | None,
    reviews_input: str | None,
    sentiment_input: str | None,
    canonical_only: bool,
    sample_n: int | None,
) -> None:
    print(f"[gold/goods] 시작 — {datetime.now().strftime('%H:%M:%S')}")

    # 1. Silver 로드
    df = pd.read_parquet(input_path)
    print(f"  Silver 전체: {len(df):,}행")

    if canonical_only:
        df = df[df["is_canonical"] == True].copy()
        print(f"  canonical 필터 후: {len(df):,}행")

    if sample_n:
        df = df.sample(n=min(sample_n, len(df)), random_state=42).copy()
        print(f"  샘플링: {len(df)}행")

    if "product_url" not in df.columns:
        df["product_url"] = df["goods_id"].apply(
            lambda gid: f"https://www.aboutpet.co.kr/goods/indexGoodsDetail?goodsId={gid}"
        )

    # 2. OCR JOIN → ingredient_text_ocr
    print("[1/4] OCR 결과 병합 중...")
    if ocr_cache_path:
        p = Path(ocr_cache_path)
        df_ocr = pd.read_parquet(p) if p.exists() else None
        if df_ocr is not None:
            print(f"  OCR 결과 로드: {p} ({len(df_ocr):,}개)")
    else:
        df_ocr = load_latest(OCR_CACHE_GLOB, "OCR 결과")

    if df_ocr is not None:
        ocr_map = dict(zip(df_ocr["goods_id"], df_ocr["ocr_text"]))
        df["ingredient_text_ocr"] = df.apply(
            lambda row: ocr_map.get(row["goods_id"]) if row.get("ocr_target") else None,
            axis=1,
        )
    else:
        df["ingredient_text_ocr"] = None
    print(f"  ingredient_text_ocr 보유: {df['ingredient_text_ocr'].notna().sum():,}개 / ocr_target: {df['ocr_target'].sum():,}개")

    # 3. health_concern_tags JOIN (ocr_target=True → health_tags parquet, 나머지 → [])
    print("[2/4] health_concern_tags 병합 중...")
    df_ht = load_latest(HEALTH_TAGS_CACHE_GLOB, "health_tags")
    if df_ht is not None:
        ht_map = dict(zip(df_ht["goods_id"], df_ht["health_concern_tags"]))
        df["health_concern_tags"] = df.apply(
            lambda row: ht_map.get(row["goods_id"], []) if row.get("ocr_target") else [],
            axis=1,
        )
    else:
        df["health_concern_tags"] = [[] for _ in range(len(df))]
        print("  health_tags 없음 → 전체 [] 처리 (scripts/gold/health_tags.py 먼저 실행 필요)")
    tag_counts = df["health_concern_tags"].apply(len)
    print(f"  태그 있는 상품: {(tag_counts > 0).sum():,}개 / 없음: {(tag_counts == 0).sum():,}개")

    # 4. ingredients JOIN → main_ingredients, ingredient_composition, nutrition_info
    print("[3/4] ingredients 파싱 결과 병합 중...")
    ingr_glob = INGREDIENTS_CACHE_GLOB
    df_ingr = load_latest(ingr_glob, "ingredients 파싱 결과") if not ingredients_path else None
    if ingredients_path:
        p = Path(ingredients_path)
        df_ingr = pd.read_parquet(p) if p.exists() else None
        if df_ingr is not None:
            print(f"  ingredients 로드: {p} ({len(df_ingr):,}개)")

    if df_ingr is not None:
        df = df.merge(
            df_ingr[["goods_id", "main_ingredients", "ingredient_composition", "nutrition_info"]],
            on="goods_id",
            how="left",
        )
        filled = df["ingredient_composition"].notna().sum()
        print(f"  ingredient_composition 보유: {filled:,}개")
    else:
        df["main_ingredients"] = [[] for _ in range(len(df))]
        df["ingredient_composition"] = None
        df["nutrition_info"] = None

    # 5. popularity_score
    print("[4/5] popularity_score 계산 중...")
    df["rating_5pt"] = df["rating"].apply(lambda r: round(r / 2, 2) if pd.notna(r) else None)
    df["popularity_score"] = df.apply(
        lambda row: calc_popularity_score(row["review_count"], row["rating_5pt"]), axis=1
    )
    print(f"  popularity_score 유효: {df['popularity_score'].notna().sum():,}개")

    # 6. sentiment_avg + repeat_rate
    print("[5/5] sentiment_avg / repeat_rate 집계 중...")
    df_reviews = None
    if reviews_input:
        try:
            df_reviews = pd.read_parquet(reviews_input)
            print(f"  리뷰 로드: {len(df_reviews):,}행")
        except Exception as e:
            print(f"  리뷰 로드 실패: {e}")
    else:
        print("  --reviews-input 미지정 → sentiment_avg / repeat_rate = None")

    df_sentiment = None
    if sentiment_input:
        try:
            df_sentiment = pd.read_parquet(sentiment_input)
            print(f"  sentiment 로드: {len(df_sentiment):,}행")
        except Exception as e:
            print(f"  sentiment 로드 실패: {e}")
    else:
        sent_files = sorted(glob(SENTIMENT_CACHE_GLOB))
        if sent_files:
            df_sentiment = pd.read_parquet(sent_files[-1])
            print(f"  sentiment 자동 로드: {sent_files[-1]} ({len(df_sentiment):,}행)")
        else:
            print("  sentiment 파일 없음 (gold/sentiment.py 먼저 실행) → sentiment_avg = None")

    df["sentiment_avg"] = calc_sentiment_avg(df, df_sentiment, df_reviews)
    df["repeat_rate"] = calc_repeat_rate(df, df_reviews)
    print(f"  sentiment_avg 유효: {df['sentiment_avg'].notna().sum():,}개")
    print(f"  repeat_rate 유효: {df['repeat_rate'].notna().sum():,}개")

    # 저장
    df["processed_at"] = pd.Timestamp.now(tz="UTC")
    df_out = df[[c for c in GOLD_COLUMNS if c in df.columns]]

    output_dir = Path("output/gold/goods")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{datetime.now().strftime('%Y%m%d')}_goods_gold.parquet"
    df_out.to_parquet(output_path, index=False)

    print(f"\n저장 완료: {output_path}")
    print(f"  행: {len(df_out):,}개 / 컬럼: {len(df_out.columns)}개")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Silver goods → Gold goods 어셈블리")
    parser.add_argument("--input", default="output/silver/goods/20260310_goods_silver.parquet")
    parser.add_argument("--ocr-cache", default=None, help="OCR 결과 parquet 경로 (기본: output/gold/ocr/ 최신)")
    parser.add_argument("--ingredients", default=None, help="ingredients 파싱 결과 parquet 경로 (기본: output/gold/ingredients/ 최신)")
    parser.add_argument("--reviews-input", default=None, help="Silver reviews parquet (sentiment_avg / repeat_rate용)")
    parser.add_argument("--sentiment-input", default=None, help="Gold sentiment basic parquet (기본: output/gold/sentiment/ 최신)")
    parser.add_argument("--all", action="store_true", help="non-canonical 포함")
    parser.add_argument("--sample", type=int, default=None, metavar="N", help="N개 샘플 (검증용)")
    args = parser.parse_args()

    main(
        input_path=args.input,
        ocr_cache_path=args.ocr_cache,
        ingredients_path=args.ingredients,
        reviews_input=args.reviews_input,
        sentiment_input=args.sentiment_input,
        canonical_only=not args.all,
        sample_n=args.sample,
    )
