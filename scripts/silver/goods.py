"""
Silver Goods ETL
Bronze goods parquet → Silver goods parquet

처리 순서:
  1. goods_id별 집계 (동일 goods_id가 여러 소분류에 등장 → 소분류 목록으로 수합)
  2. 타입 변환 (price/discount_price → int, rating → float, review_count → int,
                sold_out_yn → bool, crawled_at → datetime)
  3. 파생 컬럼 추가 (prefix, review_count_source, soldout_reliable)
  4. 상세 이미지 수 계산 + 이미지 URL dedup (동일 URL 중복 제거)
  5. dedup (동일 product_name × discount_price → canonical goods_id 1개 선택)
  6. 출력: output/silver/goods/YYYYMMDD_goods_silver.parquet

실행:
  conda run -n final-project python scripts/etl_silver_goods.py
  conda run -n final-project python scripts/etl_silver_goods.py --input output/bronze/goods/20260309_goods.parquet
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# ── 상수 ──────────────────────────────────────────────────────────────────────

# dedup 우선순위: 낮을수록 우선
PREFIX_PRIORITY = {"GP": 0, "PI": 1, "GI": 2, "GS": 3, "GO": 4}

# OCR 대상 카테고리 (Gold 단계 참고용으로 Silver에 플래그 기록)
OCR_TARGET_MIDCATE = {"사료", "간식", "습식관", "덴탈관"}
OCR_TARGET_SUBCATE = {
    "강아지_용품_건강관리",
    "고양이_용품_건강관리",
    "강아지_용품_구강관리",
    "고양이_용품_치아관리",
}


# ── 헬퍼 ──────────────────────────────────────────────────────────────────────

def parse_price(val: str) -> int | None:
    """'38,900원' / '38900' → 38900"""
    if not val or str(val).strip() in ("", "nan", "None"):
        return None
    cleaned = re.sub(r"[^\d]", "", str(val))
    return int(cleaned) if cleaned else None


def parse_rating(val: str) -> float | None:
    """'9.7' / '' → 9.7 / None"""
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_review_count(val: str) -> int:
    """'1,234' / '1234' → 1234"""
    try:
        return int(re.sub(r"[^\d]", "", str(val)))
    except (ValueError, TypeError):
        return 0


def extract_prefix(goods_id: str) -> str:
    """'GP251077034' → 'GP'"""
    return goods_id[:2] if goods_id else "??"


def midcate_name(subcate: str) -> str:
    """'강아지_사료_퍼피(1세미만)' → '사료'"""
    parts = subcate.split("_")
    return parts[1] if len(parts) >= 2 else ""


def parse_category_fields(subcategory_names: list[str]) -> tuple[list[str], list[str], list[str]]:
    """
    subcategory_names 배열에서 pet_type / category / subcategory 파싱.
    '강아지_사료_퍼피(1세미만)' → ('강아지', '사료', '퍼피(1세미만)')
    다중 카테고리 상품은 각 필드가 배열로 반환 (중복 제거).
    """
    pet_types, categories, subcategories = set(), set(), set()
    for name in subcategory_names:
        parts = name.split("_", 2)
        if len(parts) >= 1:
            pet_types.add(parts[0])
        if len(parts) >= 2:
            categories.add(parts[1])
        if len(parts) >= 3:
            subcategories.add(parts[2])
    return sorted(pet_types), sorted(categories), sorted(subcategories)


def is_ocr_target(subcategories: list[str]) -> bool:
    """소분류 목록 중 OCR 대상이 하나라도 있으면 True"""
    for sc in subcategories:
        if midcate_name(sc) in OCR_TARGET_MIDCATE:
            return True
        if sc in OCR_TARGET_SUBCATE:
            return True
    return False


def dedup_image_urls(urls) -> list[str]:
    """URL 리스트에서 중복 제거 (순서 유지)"""
    if urls is None:
        return []
    urls = list(urls) if not isinstance(urls, list) else urls
    if len(urls) == 0:
        return []
    seen = set()
    result = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


# ── Step 1: goods_id별 집계 ────────────────────────────────────────────────────

def aggregate_by_goods_id(df: pd.DataFrame) -> pd.DataFrame:
    """
    동일 goods_id가 여러 소분류 행으로 존재 → goods_id 1행으로 수합.
    상품 정보(이름/가격 등)는 첫 행 기준, 소분류는 리스트로 수집.
    """
    # detail_image_urls: None이 아닌 첫 번째 값 사용
    def first_valid_images(series):
        for v in series:
            if v is not None and len(v) > 0:
                return v
        return []

    agg = (
        df.sort_values("goods_id")
        .groupby("goods_id", sort=False)
        .agg(
            product_name=("product_name", "first"),
            brand_id=("brand_id", "first"),
            brand_name=("brand_name", "first"),
            price_raw=("price_raw", "first"),
            discount_price_raw=("discount_price_raw", "first"),
            rating_raw=("rating_raw", "first"),
            review_count_raw=("review_count_raw", "first"),
            sold_out_yn=("sold_out_yn", "first"),
            thumbnail_url=("thumbnail_url", "first"),
            detail_image_urls=("detail_image_urls", first_valid_images),
            crawled_at=("crawled_at", "first"),
            subcategories=("disp_clsf_no", lambda x: sorted(set(x.tolist()))),  # 소분류 코드
            subcategory_names=("product_name", "first"),  # 임시, 아래서 대체
        )
        .reset_index()
    )

    # subcategory_names: disp_clsf_no 코드 대신 사람이 읽을 수 있는 이름으로
    # Bronze parquet에 소분류 이름 컬럼이 없으므로 config.CATEGORIES에서 매핑
    from config import CATEGORIES
    code_to_name = {code: name for _, _, code, name in CATEGORIES}

    def codes_to_names(codes):
        return [code_to_name.get(c, c) for c in codes]

    agg["subcategory_names"] = agg["subcategories"].apply(codes_to_names)
    agg = agg.drop(columns=["subcategory_names"])  # 중복 컬럼 제거
    # 이름 컬럼 추가
    agg["subcategory_names"] = agg["subcategories"].apply(codes_to_names)

    return agg


# ── Step 2: 타입 변환 ──────────────────────────────────────────────────────────

def cast_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["price"]          = df["price_raw"].apply(parse_price)
    df["discount_price"] = df["discount_price_raw"].apply(parse_price)
    df["rating"]         = df["rating_raw"].apply(parse_rating)
    df["review_count"]   = df["review_count_raw"].apply(parse_review_count)
    df["sold_out"]       = df["sold_out_yn"].str.upper() == "Y"
    df["crawled_at"]     = pd.to_datetime(df["crawled_at"], errors="coerce", utc=True)
    return df


# ── Step 3: 파생 컬럼 ──────────────────────────────────────────────────────────

def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["prefix"] = df["goods_id"].apply(extract_prefix)

    # GP: 하위 단품 리뷰 합산 → 과다 집계 가능성 있음
    df["review_count_source"] = df["prefix"].map(
        lambda p: "aggregated" if p == "GP" else "direct"
    )

    # GO: 옵션 단위 품절 아닌 상품 단위 품절 → 신뢰 불가
    df["soldout_reliable"] = df["prefix"] != "GO"

    # OCR 대상 여부 (Gold 단계 판단 기준)
    df["ocr_target"] = df["subcategory_names"].apply(is_ocr_target)

    # subcategory_names → pet_type / category / subcategory 파싱
    parsed = df["subcategory_names"].apply(parse_category_fields)
    df["pet_type"]    = parsed.apply(lambda x: x[0])
    df["category"]    = parsed.apply(lambda x: x[1])
    df["subcategory"] = parsed.apply(lambda x: x[2])

    return df


# ── Step 4: 이미지 처리 ────────────────────────────────────────────────────────

def process_images(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["detail_image_urls"] = df["detail_image_urls"].apply(dedup_image_urls)
    df["detail_image_count"] = df["detail_image_urls"].apply(len)
    return df


# ── Step 5: dedup ──────────────────────────────────────────────────────────────

def dedup_goods(df: pd.DataFrame) -> pd.DataFrame:
    """
    동일 (product_name, discount_price) 조합에 여러 goods_id가 존재하면
    우선순위(GP > PI > GI > GS > GO)에 따라 1개만 canonical로 유지.
    제거된 goods_id는 canonical의 duplicate_of에 기록.
    """
    df = df.copy()
    df["prefix_priority"] = df["prefix"].map(lambda p: PREFIX_PRIORITY.get(p, 99))
    df["duplicate_of"] = None  # canonical goods_id (제거된 경우만)
    df["is_canonical"] = True

    # (product_name, discount_price) 중복 그룹
    dup_key = ["product_name", "discount_price"]
    dup_groups = df[df.duplicated(subset=dup_key, keep=False)]

    removed_ids = set()

    for _, group in dup_groups.groupby(dup_key, sort=False):
        if len(group) <= 1:
            continue

        # 우선순위 가장 낮은 숫자(=높은 우선순위)를 canonical로 선택
        sorted_group = group.sort_values("prefix_priority")
        canonical_id = sorted_group.iloc[0]["goods_id"]
        duplicate_ids = sorted_group.iloc[1:]["goods_id"].tolist()

        for dup_id in duplicate_ids:
            df.loc[df["goods_id"] == dup_id, "duplicate_of"] = canonical_id
            df.loc[df["goods_id"] == dup_id, "is_canonical"] = False
            removed_ids.add(dup_id)

    df = df.drop(columns=["prefix_priority"])

    print(f"  dedup: {len(removed_ids)}개 비정규 상품 → duplicate_of 기록")
    print(f"  canonical 상품 수: {df['is_canonical'].sum():,}개")

    return df


# ── 컬럼 정리 및 순서 ──────────────────────────────────────────────────────────

SILVER_COLUMNS = [
    # 식별자
    "goods_id",
    "prefix",
    # 상품 정보
    "product_name",
    "brand_id",
    "brand_name",
    "price",
    "discount_price",
    "rating",
    "review_count",
    "sold_out",
    # 이미지
    "thumbnail_url",
    "detail_image_urls",
    "detail_image_count",
    # 카테고리
    "subcategories",        # 소분류 코드 리스트
    "subcategory_names",    # 소분류 이름 리스트 ('{pet_type}_{category}_{subcategory}' 형태)
    "pet_type",             # 강아지/고양이 (list[str])
    "category",             # 사료/간식/용품/... (list[str])
    "subcategory",          # 전연령/퍼피/시니어/... (list[str])
    # 데이터 품질 플래그
    "review_count_source",  # 'direct' | 'aggregated'
    "soldout_reliable",     # bool (GO=False)
    "ocr_target",           # bool (Gold OCR 대상)
    # dedup
    "is_canonical",         # bool
    "duplicate_of",         # canonical goods_id (비정규 상품만)
    # 메타
    "crawled_at",
    "etl_at",
    # raw 보존 (검증용)
    "price_raw",
    "discount_price_raw",
    "rating_raw",
    "review_count_raw",
    "sold_out_yn",
]


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(input_path: str) -> None:
    print(f"[etl_silver_goods] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  입력: {input_path}")

    # 로드
    df_bronze = pd.read_parquet(input_path)
    print(f"  Bronze 행 수: {len(df_bronze):,}  (unique goods_id: {df_bronze['goods_id'].nunique():,})")

    # Step 1: goods_id별 집계
    print("\n[1/5] goods_id 집계 중...")
    df = aggregate_by_goods_id(df_bronze)
    print(f"  집계 후 고유 goods_id: {len(df):,}개")

    # Step 2: 타입 변환
    print("[2/5] 타입 변환 중...")
    df = cast_types(df)

    # Step 3: 파생 컬럼
    print("[3/5] 파생 컬럼 추가 중...")
    df = add_derived_columns(df)
    print(f"  prefix 분포: {df['prefix'].value_counts().to_dict()}")
    print(f"  OCR 대상: {df['ocr_target'].sum():,}개")

    # Step 4: 이미지 처리
    print("[4/5] 이미지 URL dedup 중...")
    df = process_images(df)
    print(f"  detail_image_count 분포 (0/1~10/11~30/31~50/50+):")
    bins = [0, 1, 11, 31, 51, 9999]
    labels = ["0", "1~10", "11~30", "31~50", "50+"]
    df["_img_bin"] = pd.cut(df["detail_image_count"], bins=bins, labels=labels, right=False)
    print(f"  {df['_img_bin'].value_counts().sort_index().to_dict()}")
    df = df.drop(columns=["_img_bin"])

    # Step 5: dedup
    print("[5/5] 상품 dedup 중...")
    df = dedup_goods(df)

    # etl_at 추가
    df["etl_at"] = pd.Timestamp.now(tz="UTC")

    # 컬럼 정렬
    available = [c for c in SILVER_COLUMNS if c in df.columns]
    df = df[available]

    # 저장
    date_str   = datetime.now().strftime("%Y%m%d")
    output_dir = Path("output/silver/goods")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date_str}_goods_silver.parquet"

    df.to_parquet(output_path, index=False)

    print(f"\n저장 완료: {output_path}")
    print(f"  전체 행: {len(df):,}개")
    print(f"  canonical: {df['is_canonical'].sum():,}개")
    print(f"  non-canonical(duplicate_of 있음): {(~df['is_canonical']).sum():,}개")
    print(f"  null price: {df['price'].isna().sum()}개")
    print(f"  null discount_price: {df['discount_price'].isna().sum()}개")

    # canonical goods_id 목록 별도 저장 (crawl_reviews.py 입력용)
    canonical_path = output_dir / f"{date_str}_canonical_goods_ids.json"
    canonical_ids = df.loc[df["is_canonical"], "goods_id"].tolist()
    with open(canonical_path, "w") as f:
        json.dump(canonical_ids, f)
    print(f"  canonical goods_id 목록: {canonical_path}  ({len(canonical_ids):,}개)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="output/bronze/goods/20260309_goods.parquet",
        help="Bronze goods parquet 경로",
    )
    args = parser.parse_args()
    main(args.input)
