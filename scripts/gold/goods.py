"""
Gold Goods 어셈블리
Silver goods + OCR 결과 + ingredients 파싱 결과 + (선택) 리뷰 → Gold goods parquet

선행 스크립트:
  1. scripts/gold/ocr.py          → output/gold/ocr/YYYYMMDD_ocr.parquet
  2. scripts/gold/ingredients.py  → output/gold/ingredients/YYYYMMDD_ingredients.parquet

처리 순서:
  1. Silver goods 로드 (canonical만)
  2. health_concern_tags 파생 (subcategory_names → 태그 매핑)
  3. OCR 결과 JOIN → ingredient_text_ocr
  4. ingredients 파싱 결과 JOIN → main_ingredients, ingredient_composition, nutrition_info
  5. popularity_score / trend_score 파생
  6. 출력: output/gold/goods/YYYYMMDD_goods_gold.parquet

실행:
  conda run -n final-project python scripts/gold/goods.py
  conda run -n final-project python scripts/gold/goods.py --sample 10
  conda run -n final-project python scripts/gold/goods.py \\
      --reviews-input output/silver/reviews/20260310_reviews_silver.parquet
"""

import argparse
import math
import sys
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# ── 상수 ──────────────────────────────────────────────────────────────────────

HEALTH_TAG_RULES: list[tuple[str, list[str]]] = [
    ("관절",   ["관절"]),
    ("피부",   ["피부", "피모", "모질"]),
    ("소화",   ["위장", "소화"]),
    ("체중",   ["체중조절"]),
    ("요로",   ["요로기계"]),
    ("눈물",   ["눈/눈물", "눈물"]),
    ("헤어볼", ["헤어볼"]),
    ("치아",   ["치아", "구강", "덴탈"]),
    ("면역",   ["면역력"]),
]

OCR_CACHE_GLOB         = "output/gold/ocr/*_ocr.parquet"
INGREDIENTS_CACHE_GLOB = "output/gold/ingredients/*_ingredients.parquet"

GOLD_COLUMNS = [
    "goods_id", "prefix", "product_name", "brand_id", "brand_name",
    "price", "discount_price", "rating", "rating_5pt", "review_count",
    "sold_out", "thumbnail_url", "product_url",
    "subcategories", "subcategory_names",
    "review_count_source", "soldout_reliable", "ocr_target",
    "is_canonical", "duplicate_of", "crawled_at",
    "health_concern_tags",
    "ingredient_text_ocr",
    "main_ingredients",
    "ingredient_composition",
    "nutrition_info",
    "popularity_score", "trend_score", "processed_at",
]


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def map_health_tags(subcategory_names) -> list[str]:
    tags: set[str] = set()
    joined = " ".join(subcategory_names) if subcategory_names is not None else ""
    for tag, keywords in HEALTH_TAG_RULES:
        if any(kw in joined for kw in keywords):
            tags.add(tag)
    return sorted(tags)


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


def calc_trend_scores(df_goods: pd.DataFrame, df_reviews: pd.DataFrame | None) -> pd.Series:
    if df_reviews is None:
        return pd.Series([None] * len(df_goods), index=df_goods.index, dtype=object)

    cutoff = pd.Timestamp.now(tz="UTC") - timedelta(days=30)
    date_col = pd.to_datetime(df_reviews.get("review_date"), utc=True, errors="coerce")
    if date_col is None:
        return pd.Series([None] * len(df_goods), index=df_goods.index, dtype=object)

    df_rev = df_reviews.copy()
    df_rev["_date"] = date_col
    total = df_rev.groupby("goods_id").size().rename("total")
    recent = df_rev[df_rev["_date"] >= cutoff].groupby("goods_id").size().rename("recent")
    stat = total.to_frame().join(recent, how="left").fillna(0)
    stat["trend_score"] = stat["recent"] / stat["total"].replace(0, 1)
    return df_goods["goods_id"].map(stat["trend_score"])


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(
    input_path: str,
    ocr_cache_path: str | None,
    ingredients_path: str | None,
    reviews_input: str | None,
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

    # 2. health_concern_tags
    print("[1/4] health_concern_tags 매핑 중...")
    df["health_concern_tags"] = df["subcategory_names"].apply(map_health_tags)
    tag_counts = df["health_concern_tags"].apply(len)
    print(f"  태그 있는 상품: {(tag_counts > 0).sum():,}개 / 없음: {(tag_counts == 0).sum():,}개")

    # 3. OCR JOIN → ingredient_text_ocr
    print("[2/4] OCR 결과 병합 중...")
    ocr_glob = f"{ocr_cache_path}" if ocr_cache_path else OCR_CACHE_GLOB
    df_ocr = load_latest(ocr_glob if "*" in ocr_glob else OCR_CACHE_GLOB, "OCR 결과")
    if ocr_cache_path:
        p = Path(ocr_cache_path)
        df_ocr = pd.read_parquet(p) if p.exists() else None
        if df_ocr is not None:
            print(f"  OCR 결과 로드: {p} ({len(df_ocr):,}개)")

    if df_ocr is not None:
        ocr_map = dict(zip(df_ocr["goods_id"], df_ocr["ocr_text"]))
        df["ingredient_text_ocr"] = df.apply(
            lambda row: ocr_map.get(row["goods_id"]) if row.get("ocr_target") else None,
            axis=1,
        )
    else:
        df["ingredient_text_ocr"] = None
    print(f"  ingredient_text_ocr 보유: {df['ingredient_text_ocr'].notna().sum():,}개 / ocr_target: {df['ocr_target'].sum():,}개")

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

    # 5. popularity_score + trend_score
    print("[4/4] 추천 신호 점수 계산 중...")
    df["rating_5pt"] = df["rating"].apply(lambda r: round(r / 2, 2) if pd.notna(r) else None)
    df["popularity_score"] = df.apply(
        lambda row: calc_popularity_score(row["review_count"], row["rating_5pt"]), axis=1
    )
    print(f"  popularity_score 유효: {df['popularity_score'].notna().sum():,}개")

    df_reviews = None
    if reviews_input:
        try:
            df_reviews = pd.read_parquet(reviews_input)
            print(f"  리뷰 로드: {len(df_reviews):,}행")
        except Exception as e:
            print(f"  리뷰 로드 실패 (trend_score=None): {e}")
    else:
        print("  --reviews-input 미지정 → trend_score=None")

    df["trend_score"] = calc_trend_scores(df, df_reviews)

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
    parser.add_argument("--reviews-input", default=None, help="Silver reviews parquet (trend_score용)")
    parser.add_argument("--all", action="store_true", help="non-canonical 포함")
    parser.add_argument("--sample", type=int, default=None, metavar="N", help="N개 샘플 (검증용)")
    args = parser.parse_args()

    main(
        input_path=args.input,
        ocr_cache_path=args.ocr_cache,
        ingredients_path=args.ingredients,
        reviews_input=args.reviews_input,
        canonical_only=not args.all,
        sample_n=args.sample,
    )
