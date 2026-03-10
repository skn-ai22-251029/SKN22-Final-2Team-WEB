"""
Silver Reviews ETL
Bronze reviews parquet → Silver reviews parquet

처리 순서:
  1. Bronze parquet 로드 (기본 + GP 병합 옵션)
  2. review_id 기준 중복 제거
  3. Silver canonical goods_id 필터링 (orphan review 방지)
  4. 타입 변환
     - written_at_raw "YYYY.MM.DD" → date
     - score_raw → float (None 유지)
     - pet_gender 빈 문자열 → None  (이슈 3)
     - pet_age_raw "7개월"→7, "3살"→36 → int months
     - pet_weight_raw "2.5kg"→2.5, "500g"→0.5 → float kg
     - review_info JSON string → dict
  5. 출력: output/silver/reviews/YYYYMMDD_reviews_silver.parquet

실행:
  # GP 수집 완료 전 (기본 리뷰만)
  conda run -n final-project python scripts/silver_reviews.py

  # GP 수집 완료 후 (전체 병합)
  conda run -n final-project python scripts/silver_reviews.py \\
      --gp-input output/bronze/reviews/20260310_reviews_gp.parquet
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd


# ── 타입 변환 헬퍼 ─────────────────────────────────────────────────────────────

def parse_written_at(val: str) -> object:
    """'2026.03.06' → datetime.date"""
    if not val or str(val).strip() in ("", "nan", "None"):
        return None
    try:
        return datetime.strptime(str(val).strip(), "%Y.%m.%d").date()
    except ValueError:
        return None


def parse_pet_age_months(val: str) -> int | None:
    """
    '7개월' → 7
    '3살'   → 36
    '2살 3개월' → 27
    '1살6개월'  → 18
    """
    if not val or str(val).strip() in ("", "nan", "None"):
        return None
    s = str(val).strip()
    years  = re.search(r"(\d+)\s*살", s)
    months = re.search(r"(\d+)\s*개월", s)
    total = 0
    if years:
        total += int(years.group(1)) * 12
    if months:
        total += int(months.group(1))
    return total if total > 0 else None


def parse_pet_weight_kg(val: str) -> float | None:
    """
    '2.5kg'  → 2.5
    '500g'   → 0.5
    '2,500g' → 2.5
    """
    if not val or str(val).strip() in ("", "nan", "None"):
        return None
    s = str(val).strip().replace(",", "")
    kg = re.search(r"([\d.]+)\s*kg", s, re.IGNORECASE)
    g  = re.search(r"([\d.]+)\s*g",  s, re.IGNORECASE)
    try:
        if kg:
            return round(float(kg.group(1)), 3)
        if g:
            return round(float(g.group(1)) / 1000, 3)
    except ValueError:
        pass
    return None


def parse_review_info(val) -> dict | None:
    """JSON string → dict"""
    if val is None or (isinstance(val, float)):
        return None
    s = str(val).strip()
    if not s or s in ("nan", "None", "null"):
        return None
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


# ── ETL 단계 ──────────────────────────────────────────────────────────────────

def load_bronze(input_path: str, gp_input_path: str | None) -> pd.DataFrame:
    """Bronze parquet 로드 및 병합"""
    df = pd.read_parquet(input_path)
    print(f"  기본 리뷰: {len(df):,}건")

    if gp_input_path:
        p = Path(gp_input_path)
        if p.exists():
            df_gp = pd.read_parquet(gp_input_path)
            print(f"  GP 리뷰  : {len(df_gp):,}건")
            df = pd.concat([df, df_gp], ignore_index=True)
            print(f"  병합 후  : {len(df):,}건")
        else:
            print(f"  [경고] GP 파일 없음: {gp_input_path} — GP 제외 진행")

    return df


def dedup_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """review_id 중복 제거 (GP/GI 동일 리뷰 방지)"""
    before = len(df)
    df = df.drop_duplicates(subset="review_id", keep="first")
    removed = before - len(df)
    if removed > 0:
        print(f"  중복 제거: {removed:,}건 → {len(df):,}건")
    return df


def filter_canonical(df: pd.DataFrame, goods_path: str) -> pd.DataFrame:
    """Silver canonical goods_id에 속하지 않는 리뷰 제거 (orphan 방지)"""
    goods = pd.read_parquet(goods_path)
    canonical_ids = set(goods.loc[goods["is_canonical"], "goods_id"])
    before = len(df)
    df = df[df["goods_id"].isin(canonical_ids)].copy()
    removed = before - len(df)
    if removed > 0:
        print(f"  orphan 제거: {removed:,}건 (canonical 외 goods_id)")
    return df


def cast_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # 날짜
    df["written_at"] = df["written_at_raw"].apply(parse_written_at)

    # 점수 (이미 float이나 None 보정)
    df["score"] = pd.to_numeric(df["score_raw"], errors="coerce")

    # pet_gender 빈 문자열 → None  (이슈 3)
    df["pet_gender"] = df["pet_gender"].replace("", None)
    df.loc[df["pet_gender"].apply(lambda x: isinstance(x, str) and x.strip() == ""), "pet_gender"] = None

    # 수치 파싱
    df["pet_age_months"] = df["pet_age_raw"].apply(parse_pet_age_months)
    df["pet_weight_kg"]  = df["pet_weight_raw"].apply(parse_pet_weight_kg)

    # review_info JSON → dict
    df["review_info"] = df["review_info"].apply(parse_review_info)

    return df


# ── 출력 컬럼 ─────────────────────────────────────────────────────────────────

SILVER_COLUMNS = [
    "review_id",
    "goods_id",
    "score",
    "content",
    "author_nickname",
    "written_at",
    "purchase_label",
    "pet_name",
    "pet_gender",
    "pet_age_months",
    "pet_weight_kg",
    "pet_breed",
    "review_info",
    "etl_at",
    # raw 보존 (검증용)
    "score_raw",
    "written_at_raw",
    "pet_age_raw",
    "pet_weight_raw",
]


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(input_path: str, gp_input_path: str | None, goods_path: str) -> None:
    print(f"[silver_reviews] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  입력: {input_path}")
    if gp_input_path:
        print(f"  GP  : {gp_input_path}")
    print(f"  goods: {goods_path}")
    print()

    # Step 1: 로드 및 병합
    print("[1/4] Bronze 로드 중...")
    df = load_bronze(input_path, gp_input_path)

    # Step 2: 중복 제거
    print("[2/4] 중복 제거 중...")
    df = dedup_reviews(df)

    # Step 3: orphan 필터링
    print("[3/4] canonical 필터링 중...")
    df = filter_canonical(df, goods_path)

    # Step 4: 타입 변환
    print("[4/4] 타입 변환 중...")
    df = cast_types(df)
    df["etl_at"] = pd.Timestamp.now(tz="UTC")

    # 컬럼 정렬
    available = [c for c in SILVER_COLUMNS if c in df.columns]
    df = df[available]

    # 저장
    date_str   = datetime.now().strftime("%Y%m%d")
    output_dir = Path("output/silver/reviews")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date_str}_reviews_silver.parquet"
    df.to_parquet(output_path, index=False)

    # 요약
    print(f"\n저장 완료: {output_path}")
    print(f"  전체 리뷰    : {len(df):,}건")
    print(f"  고유 상품    : {df['goods_id'].nunique():,}개")
    print(f"  고유 작성자  : {df['author_nickname'].nunique():,}명")
    print(f"  written_at 결측: {df['written_at'].isna().sum()}건")
    print(f"  score 결측   : {df['score'].isna().sum()}건")
    print(f"  pet_gender 결측: {df['pet_gender'].isna().sum():,}건")
    print(f"  pet_age_months 있음: {df['pet_age_months'].notna().sum():,}건")
    print(f"  pet_weight_kg 있음: {df['pet_weight_kg'].notna().sum():,}건")

    # 점수 분포
    score_dist = df["score"].value_counts().sort_index()
    print(f"\n  점수 분포:")
    for score, cnt in score_dist.items():
        pct = cnt / len(df) * 100
        print(f"    {score:.1f}점: {cnt:,}건 ({pct:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="output/bronze/reviews/20260310_reviews.parquet",
        help="Bronze reviews parquet 경로 (GP 제외)",
    )
    parser.add_argument(
        "--gp-input",
        default=None,
        help="Bronze GP reviews parquet 경로 (수집 완료 후 사용)",
    )
    parser.add_argument(
        "--goods",
        default="output/silver/goods/20260310_goods_silver.parquet",
        help="Silver goods parquet 경로 (canonical 필터링 기준)",
    )
    args = parser.parse_args()
    main(args.input, args.gp_input, args.goods)
