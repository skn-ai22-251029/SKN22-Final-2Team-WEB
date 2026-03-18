"""
Silver Reviews ETL
Bronze reviews parquet → Silver reviews parquet

처리 순서:
  1. Bronze parquet 로드 (기본 + GP 병합 옵션)
  2. review_id 기준 중복 제거
  3. canonical goods_id 필터링 (orphan review 방지)
  4. 타입 변환
     - written_at_raw (YYYY.MM.DD) → review_date (date)
     - score_raw (float) → rating_5pt
     - pet_age_raw (9살/9개월) → pet_age_months (int)
     - pet_weight_raw (23kg / 500g) → pet_weight_kg (float)
     - pet_gender ((수컷)/(암컷)) → 수컷/암컷
     - review_info (NaN) → {}
  5. 텍스트 정제 (content → review_text)
  6. 출력: output/silver/reviews/YYYYMMDD_reviews_silver.parquet

실행:
  # GP 수집 완료 전
  conda run -n final-project python scripts/silver/reviews.py

  # GP 수집 완료 후 (전체 병합)
  conda run -n final-project python scripts/silver/reviews.py \\
      --gp-input output/bronze/reviews/YYYYMMDD_reviews_gp.parquet
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
    """'23kg' / '2.5kg' → 23.0 / 2.5, '500g' → 0.5"""
    if not isinstance(val, str):
        return None
    m_kg = re.search(r"([\d.]+)\s*kg", val, re.IGNORECASE)
    if m_kg:
        try:
            return float(m_kg.group(1))
        except (ValueError, TypeError):
            return None
    m_g = re.search(r"([\d.]+)\s*g\b", val, re.IGNORECASE)
    if m_g:
        try:
            return round(float(m_g.group(1)) / 1000, 4)
        except (ValueError, TypeError):
            return None
    return None


def parse_gender(val) -> str | None:
    """'(수컷)' → '수컷', '(암컷)' → '암컷', 빈 문자열 → None"""
    if not isinstance(val, str) or not val.strip():
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


# ── Silver canonical goods 로드 ───────────────────────────────────────────────

def load_canonical_ids(goods_path: str) -> set[str]:
    p = Path(goods_path)
    if not p.exists():
        print(f"  [경고] Silver goods 파일 없음: {p} — canonical 필터링 생략")
        return set()
    df = pd.read_parquet(p, columns=["goods_id", "is_canonical"])
    ids = set(df.loc[df["is_canonical"] == True, "goods_id"].astype(str))
    print(f"  canonical goods: {len(ids):,}개")
    return ids


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(input_path: str, gp_input_path: str | None, goods_path: str) -> None:
    print(f"[silver/reviews] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  입력: {input_path}")
    if gp_input_path:
        print(f"  GP  : {gp_input_path}")

    # 1. Bronze 로드 및 병합
    df = pd.read_parquet(input_path)
    if gp_input_path and Path(gp_input_path).exists():
        df_gp = pd.read_parquet(gp_input_path)
        df = pd.concat([df, df_gp], ignore_index=True)
        print(f"  Bronze 행 수 (GI+GP): {len(df):,}")
    else:
        print(f"  Bronze 행 수: {len(df):,}")

    # 2. 중복 제거
    before = len(df)
    df = df.drop_duplicates(subset=["review_id"]).copy()
    print(f"  중복 제거: {before - len(df):,}개 → {len(df):,}개")

    # 3. canonical 필터링 (orphan review 방지)
    canonical_ids = load_canonical_ids(goods_path)
    if canonical_ids:
        before = len(df)
        df = df[df["goods_id"].astype(str).isin(canonical_ids)].copy()
        print(f"  canonical 필터: {before - len(df):,}개 제거 → {len(df):,}개")

    # 4. 컬럼 매핑 & 타입 변환
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

    df["purchase_label"] = df["purchase_label"].apply(
        lambda v: v if isinstance(v, str) and v in ("first", "repeat") else None
    )

    # 5. 품질 필터링
    before = len(df)
    df = df[df["review_text"].apply(lambda x: isinstance(x, str) and len(x.strip()) > 0)].copy()
    print(f"  빈 review_text 제거: {before - len(df):,}개 → {len(df):,}개")

    before = len(df)
    df.loc[df["pet_weight_kg"] > 100, "pet_weight_kg"] = None
    print(f"  pet_weight_kg > 100 이상값 null 처리: {before - len(df[df['pet_weight_kg'].notna()]):,}개")

    # 6. 컬럼 정리
    available = [c for c in SILVER_COLUMNS if c in df.columns]
    df_out = df[available]

    # 7. 저장
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
    parser.add_argument("--input", default="output/bronze/reviews/20260310_reviews.parquet")
    parser.add_argument("--gp-input", default=None, help="Bronze GP reviews parquet 경로 (수집 완료 후 사용)")
    parser.add_argument("--goods", default="output/silver/goods/20260310_goods_silver.parquet",
                        help="Silver goods parquet 경로 (canonical 필터링 기준)")
    args = parser.parse_args()
    main(args.input, args.gp_input, args.goods)
