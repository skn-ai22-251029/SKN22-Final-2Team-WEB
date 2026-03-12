"""
Silver Reviews ETL
Bronze reviews parquet → Silver reviews parquet

처리 순서:
  1. 중복 제거 (review_id 기준)
  2. 타입 변환
     - written_at_raw (YYYY.MM.DD) → review_date (date)
     - score_raw (float) → rating_5pt
     - pet_age_raw (9살/9개월) → pet_age_months (int)
     - pet_weight_raw (23kg) → pet_weight_kg (float)
     - pet_gender ((수컷)/(암컷)) → 수컷/암컷
     - review_info (NaN) → {}
  3. 텍스트 정제 (content → review_text)
  4. 출력: output/silver/reviews/YYYYMMDD_reviews_silver.parquet

실행:
  conda run -n final-project python scripts/silver/reviews.py
  conda run -n final-project python scripts/silver/reviews.py \\
      --input output/bronze/reviews/20260310_reviews.parquet
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# ── 파싱 헬퍼 ─────────────────────────────────────────────────────────────────

def parse_date(val) -> str | None:
    """'2025.12.01' → '2025-12-01'"""
    if not isinstance(val, str):
        return None
    try:
        return datetime.strptime(val.strip(), "%Y.%m.%d").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_rating(val) -> float | None:
    """5.0 / '5.0' → 5.0"""
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def parse_age_months(val) -> int | None:
    """'9살' → 108, '9개월' → 9, '1살 3개월' → 15"""
    if not isinstance(val, str):
        return None
    val = val.strip()
    years = sum(int(m) for m in re.findall(r"(\d+)\s*살", val))
    months = sum(int(m) for m in re.findall(r"(\d+)\s*개월", val))
    total = years * 12 + months
    return total if total > 0 else None


def parse_weight(val) -> float | None:
    """'23kg' / '2.5kg' → 23.0 / 2.5"""
    if not isinstance(val, str):
        return None
    m = re.search(r"([\d.]+)\s*kg", val, re.IGNORECASE)
    try:
        return float(m.group(1)) if m else None
    except (ValueError, TypeError):
        return None


def parse_gender(val) -> str | None:
    """'(수컷)' → '수컷', '(암컷)' → '암컷'"""
    if not isinstance(val, str):
        return None
    cleaned = re.sub(r"[()（）]", "", val).strip()
    return cleaned if cleaned in ("수컷", "암컷") else (cleaned or None)


def parse_review_info(val) -> dict:
    """NaN / JSON 문자열 / dict → dict"""
    if isinstance(val, dict):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def clean_text(val) -> str:
    """리뷰 본문 정제: #상품후기 제거, 공백 정리"""
    if not isinstance(val, str):
        return ""
    return (
        val.replace("#상품후기", "")
           .replace("\r", " ").replace("\n", " ").replace("\t", " ")
           .strip()
    )


# ── Silver 컬럼 순서 ──────────────────────────────────────────────────────────

SILVER_COLUMNS = [
    "review_id",
    "goods_id",
    "nickname",
    "review_date",
    "rating_5pt",
    "purchase_label",
    "review_text",
    "has_photo",
    "pet_name",
    "pet_gender",
    "pet_age_months",
    "pet_weight_kg",
    "pet_breed",
    "review_info",
    "processed_at",
]


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(input_path: str) -> None:
    print(f"[silver/reviews] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  입력: {input_path}")

    df = pd.read_parquet(input_path)
    print(f"  Bronze 행 수: {len(df):,}")

    # 1. 중복 제거
    before = len(df)
    df = df.drop_duplicates(subset=["review_id"]).copy()
    print(f"  중복 제거: {before - len(df):,}개 → {len(df):,}개")

    # 2. 컬럼 매핑 & 타입 변환
    df["nickname"]       = df["author_nickname"].astype(str).str.strip()
    df["review_date"]    = df["written_at_raw"].apply(parse_date)
    df["rating_5pt"]     = df["score_raw"].apply(parse_rating)
    df["review_text"]    = df["content"].apply(clean_text)
    df["pet_gender"]     = df["pet_gender"].apply(parse_gender)
    df["pet_age_months"] = df["pet_age_raw"].apply(parse_age_months)
    df["pet_weight_kg"]  = df["pet_weight_raw"].apply(parse_weight)
    df["review_info"]    = df["review_info"].apply(parse_review_info)
    df["has_photo"]      = df["has_photo"] if "has_photo" in df.columns else False
    df["processed_at"]   = pd.Timestamp.now(tz="UTC")

    # purchase_label: 정규화
    df["purchase_label"] = df["purchase_label"].apply(
        lambda v: v if isinstance(v, str) and v in ("first", "repeat") else None
    )

    # 3. 컬럼 정리
    available = [c for c in SILVER_COLUMNS if c in df.columns]
    df_out = df[available]

    # 4. 저장
    date_str = datetime.now().strftime("%Y%m%d")
    output_dir = Path("output/silver/reviews")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{date_str}_reviews_silver.parquet"
    df_out.to_parquet(output_path, index=False)

    print(f"\n저장 완료: {output_path}")
    print(f"  전체 행: {len(df_out):,}개")
    print(f"  null review_date: {df_out['review_date'].isna().sum():,}개")
    print(f"  null rating_5pt: {df_out['rating_5pt'].isna().sum():,}개")
    print(f"  pet_age_months 파싱: {df_out['pet_age_months'].notna().sum():,}개")
    print(f"  pet_weight_kg 파싱: {df_out['pet_weight_kg'].notna().sum():,}개")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="output/bronze/reviews/20260310_reviews.parquet",
    )
    args = parser.parse_args()
    main(args.input)
