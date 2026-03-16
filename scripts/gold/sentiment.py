"""
Gold Sentiment ETL (벌크 업데이트용)
Silver reviews → Basic sentiment + ABSA → output/gold/sentiment/

출력:
  output/gold/sentiment/basic.parquet   — review_id, sentiment_label, sentiment_score
  output/gold/sentiment/absa.parquet    — review_id, 문장, 8개 속성, 종합_확신도

실행:
  # 팀원 결과물 변환 (최초 1회 / 컬럼 정규화 + 저장)
  conda run -n final-project python scripts/gold/sentiment.py --use-cache

  # GP 등 신규 벌크 수집 후 전체 재실행 (GPU 권장)
  conda run -n final-project python scripts/gold/sentiment.py \\
      --input output/silver/reviews/20260311_reviews_silver.parquet

  # 샘플 검증
  conda run -n final-project python scripts/gold/sentiment.py --sample 20
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

# ── 기본 경로 ─────────────────────────────────────────────────────────────────

SILVER_REVIEWS_GLOB = "output/silver/reviews/*_reviews_silver.parquet"

# 팀원 원본 캐시 (--use-cache 시 변환 소스)
TEAMMATE_BASIC_CACHE = "output/gold/sentiment/sentiment_results_basic.parquet"
TEAMMATE_ABSA_CACHE  = "output/gold/sentiment/sentiment_results.parquet"

# 출력
OUTPUT_BASIC = f"output/gold/sentiment/{datetime.now().strftime('%Y%m%d')}_basic.parquet"
OUTPUT_ABSA  = f"output/gold/sentiment/{datetime.now().strftime('%Y%m%d')}_absa.parquet"

# ── ABSA 속성 ─────────────────────────────────────────────────────────────────

ASPECT_COLS = ["기호성", "생체반응", "소화/배변", "제품 성상", "성분/원료", "냄새", "가격/구매", "배송/포장"]

ASPECT_KEYWORDS = {
    "기호성":    ["먹어", "먹는", "순삭", "기호성", "입맛", "뇸뇸", "거부", "식탐", "안 먹", "잘 먹", "안먹", "잘먹", "먹이"],
    "생체반응":  ["눈물", "가려움", "긁어", "털", "모질", "피부", "활력", "알러지", "알레르기", "눈물자국", "눈물터", "가렵", "두드러기", "발진", "귀지", "구내염"],
    "소화/배변": ["설사", "묽은", "변", "황금변", "맛동산", "응가", "똥", "구토", "토해", "소화", "토하", "변비"],
    "제품 성상": ["알갱이", "크기", "사이즈", "키블", "가루", "단단", "딱딱", "부드러운", "성상", "입자", "알이", "알맹이"],
    "성분/원료": ["원료", "성분", "가수분해", "그레인프리", "육류", "함량", "원산지", "첨가물", "단백질", "조단백", "지방", "조지방", "탄수화물", "오메가", "칼슘"],
    "냄새":      ["냄새", "향", "구려", "꼬순내", "비린내", "역해", "악취", "냄나"],
    "가격/구매": ["가격", "가성비", "저렴", "비싸", "쿠폰", "할인", "재구매", "재주문", "또 살", "또살", "또구매"],
    "배송/포장": ["배송", "포장", "배달", "유통기한", "택배", "총알배송", "새벽배송", "빠르게", "빠른"],
}


# ── 전처리 ────────────────────────────────────────────────────────────────────

def preprocess(text: str) -> str:
    if not isinstance(text, str):
        return ""
    return (
        text.replace("#상품후기", "")
            .replace("\r", " ").replace("\n", " ").replace("\t", " ")
            .strip()
    )

def get_aspects(sentence: str) -> list[str]:
    return [asp for asp, kws in ASPECT_KEYWORDS.items() if any(kw in sentence for kw in kws)]


# ── 모델 ──────────────────────────────────────────────────────────────────────

def load_classifier():
    import torch
    from transformers import pipeline
    if torch.cuda.is_available():
        device = 0
        device_name = "CUDA"
    elif torch.backends.mps.is_available():
        device = "mps"
        device_name = "MPS"
    else:
        device = -1
        device_name = "CPU"
    print(f"  모델 로드 중... (device={device_name})")
    clf = pipeline(
        "sentiment-analysis",
        model="Copycats/koelectra-base-v3-generalized-sentiment-analysis",
        device=device,
    )
    print("  모델 로드 완료")
    return clf


def run_basic(df: pd.DataFrame, clf) -> pd.DataFrame:
    """전체 리뷰 → basic.parquet 형식 DataFrame"""
    from tqdm import tqdm
    texts = df["review_text"].tolist()
    results = []
    for out in tqdm(clf(texts, batch_size=64, truncation=True, max_length=512),
                    total=len(texts), desc="Basic Sentiment"):
        results.append(out)

    label_map = {"1": "positive", "0": "negative"}
    out = df[["review_id"]].copy()
    out["sentiment_label"] = [label_map.get(r["label"], "neutral") for r in results]
    out["sentiment_score"] = [
        r["score"] if r["label"] == "1" else 1 - r["score"]
        for r in results
    ]
    return out


def run_absa(df: pd.DataFrame, clf) -> pd.DataFrame:
    """리뷰 단위 ABSA → absa.parquet 형식 DataFrame (행: 리뷰)"""
    from tqdm import tqdm
    rows = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="ABSA"):
        review_id = str(row["review_id"])
        review = preprocess(row["review_text"])
        aspects = get_aspects(review)
        res = clf(review[:512])[0]
        label = "긍정" if res["label"] == "1" else "부정"
        entry = {"review_id": review_id, "문장": review}
        for asp in ASPECT_COLS:
            entry[asp] = label if asp in aspects else "-"
        entry["종합_확신도"] = round(res["score"], 4)
        rows.append(entry)
    return pd.DataFrame(rows)


# ── 팀원 캐시 변환 (--use-cache) ──────────────────────────────────────────────

def convert_basic_cache() -> pd.DataFrame:
    p = Path(TEAMMATE_BASIC_CACHE)
    if not p.exists():
        raise FileNotFoundError(f"팀원 basic 캐시 없음: {p}")
    df = pd.read_parquet(p)
    print(f"  팀원 basic 캐시 로드: {len(df):,}개")

    # 컬럼 정규화
    if "sentiment" in df.columns and "sentiment_label" not in df.columns:
        df["sentiment_label"] = df["sentiment"].map({"긍정": "positive", "부정": "negative"}).fillna("neutral")
    mask_neg = df["sentiment_label"] == "negative"
    if mask_neg.any() and (df.loc[mask_neg, "sentiment_score"] > 0.5).all():
        df.loc[mask_neg, "sentiment_score"] = 1 - df.loc[mask_neg, "sentiment_score"]

    df["review_id"] = df["review_id"].astype(str)
    df = df.drop_duplicates(subset=["review_id"])
    return df[["review_id", "sentiment_label", "sentiment_score"]]


def convert_absa_cache() -> pd.DataFrame:
    p = Path(TEAMMATE_ABSA_CACHE)
    if not p.exists():
        raise FileNotFoundError(f"팀원 ABSA 캐시 없음: {p}")
    df = pd.read_parquet(p)
    print(f"  팀원 ABSA 캐시 로드: {len(df):,}행")

    if "종합 확신도" in df.columns:
        df = df.rename(columns={"종합 확신도": "종합_확신도"})
    df["review_id"] = df["review_id"].astype(str)

    cols = ["review_id", "문장"] + ASPECT_COLS + ["종합_확신도"]
    return df[[c for c in cols if c in df.columns]]


# ── 메인 ──────────────────────────────────────────────────────────────────────

def latest_silver() -> str:
    files = sorted(Path(".").glob(SILVER_REVIEWS_GLOB))
    if not files:
        raise FileNotFoundError(f"Silver reviews 파일 없음: {SILVER_REVIEWS_GLOB}")
    return str(files[-1])


def main(input_path: str | None, use_cache: bool, sample_n: int | None) -> None:
    print(f"[gold/sentiment] 시작 — {datetime.now().strftime('%H:%M:%S')}")

    output_dir = Path("output/gold/sentiment")
    output_dir.mkdir(parents=True, exist_ok=True)

    if use_cache:
        print("[--use-cache] 팀원 결과물 변환 중...")
        df_basic = convert_basic_cache()
        df_absa  = convert_absa_cache()
    else:
        path = input_path or latest_silver()
        print(f"  입력: {path}")
        df = pd.read_parquet(path)
        print(f"  Silver 행 수: {len(df):,}")
        if sample_n:
            df = df.sample(n=min(sample_n, len(df)), random_state=42).copy()
            print(f"  샘플링: {len(df)}행")

        clf = load_classifier()

        print("[1/2] Basic sentiment 실행 중...")
        df_basic = run_basic(df, clf)

        print("[2/2] ABSA 실행 중...")
        df_absa = run_absa(df, clf)

    # 저장
    df_basic.to_parquet(OUTPUT_BASIC, index=False)
    df_absa.to_parquet(OUTPUT_ABSA, index=False)

    print(f"\n저장 완료")
    print(f"  {OUTPUT_BASIC}: {len(df_basic):,}개")
    print(f"  {OUTPUT_ABSA}: {len(df_absa):,}행 / {df_absa['review_id'].nunique():,}개 리뷰")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Silver reviews → Sentiment parquets")
    parser.add_argument("--input", default=None, help="Silver reviews parquet 경로 (기본: 최신 파일 자동 탐색)")
    parser.add_argument("--use-cache", action="store_true", help="팀원 결과물(sentiment_results_*.parquet) 변환")
    parser.add_argument("--sample", type=int, default=None, metavar="N")
    args = parser.parse_args()

    main(
        input_path=args.input,
        use_cache=args.use_cache,
        sample_n=args.sample,
    )
