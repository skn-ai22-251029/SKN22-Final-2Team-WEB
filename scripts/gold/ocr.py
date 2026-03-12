"""
Gold OCR Pipeline
Silver goods parquet → OCR 결과 parquet

- ocr_target=True & is_canonical=True & detail_image_urls 있는 상품만 처리
- 기존 결과 자동 감지 → 미처리 상품만 이어서 실행 (resume 지원)
- .env의 GOOGLE_APPLICATION_CREDENTIALS 사용

실행:
  conda run -n final-project python scripts/gold/ocr.py
  conda run -n final-project python scripts/gold/ocr.py --sample 5
  conda run -n final-project python scripts/gold/ocr.py --input output/silver/goods/20260310_goods_silver.parquet
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────────────────────
MAX_RETRIES = 3
REQUEST_DELAY = 0.1
CHECKPOINT_INTERVAL = 10


# ── Vision API ────────────────────────────────────────────────────────────────

def setup_vision_client():
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    if not creds_path or not Path(creds_path).exists():
        raise FileNotFoundError(
            f"GCP 인증 파일 없음: '{creds_path}'\n"
            ".env에 GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcp_api_key.json 설정 필요"
        )
    try:
        from google.cloud import vision
        return vision.ImageAnnotatorClient()
    except ImportError:
        raise ImportError("pip install google-cloud-vision")


def detect_text_from_url(client, url: str) -> str:
    import requests
    from google.cloud import vision

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return ""
            image = vision.Image(content=resp.content)
            response = client.text_detection(image=image)
            if response.error.message:
                if attempt < MAX_RETRIES - 1:
                    time.sleep((attempt + 1) * 2)
                    continue
                raise Exception(f"Vision API Error: {response.error.message}")
            texts = response.text_annotations
            return texts[0].description if texts else ""
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep((attempt + 1) * 2)
                continue
            print(f"\n[Error] {url}: {e}")
            return ""
    return ""


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(input_path: str, output_path: str, sample_n: int | None) -> None:
    print(f"[gold/ocr] 시작 — {datetime.now().strftime('%H:%M:%S')}")

    # 1. Silver 로드 → ocr_target=True, canonical만
    df = pd.read_parquet(input_path)
    df_targets = df[
        (df["ocr_target"] == True) &
        (df["is_canonical"] == True) &
        (df["detail_image_urls"].apply(lambda x: len(x) > 0 if isinstance(x, (list, type(None))) else False))
    ].copy()
    print(f"  OCR 대상: {len(df_targets):,}개")

    if sample_n:
        df_targets = df_targets.sample(n=min(sample_n, len(df_targets)), random_state=42)
        print(f"  샘플링: {len(df_targets)}개")

    # 2. 기존 결과 로드 (resume)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    existing_results: list[dict] = []
    processed_ids: set = set()
    if out_path.exists():
        try:
            existing_df = pd.read_parquet(out_path)
            existing_results = existing_df.to_dict("records")
            processed_ids = set(existing_df["goods_id"].unique())
            print(f"  기존 결과: {len(processed_ids):,}개 → 건너뜀")
        except Exception as e:
            print(f"  기존 결과 로드 실패 (새로 시작): {e}")

    df_todo = df_targets[~df_targets["goods_id"].isin(processed_ids)]
    if len(df_todo) == 0:
        print("  모든 대상 처리 완료 (resume 불필요)")
        return

    print(f"  미처리: {len(df_todo):,}개")

    # 3. Vision API 실행
    client = setup_vision_client()
    results = list(existing_results)

    try:
        for _, row in tqdm(df_todo.iterrows(), total=len(df_todo), desc="OCR"):
            goods_id = row["goods_id"]
            urls = list(row["detail_image_urls"])
            combined: list[str] = []

            for url in urls:
                text = detect_text_from_url(client, url)
                if text:
                    combined.append(text)
                time.sleep(REQUEST_DELAY)

            results.append({
                "goods_id": goods_id,
                "product_name": row["product_name"],
                "ocr_text": "\n".join(combined),
            })

            if len(results) % CHECKPOINT_INTERVAL == 0:
                pd.DataFrame(results).to_parquet(out_path, index=False)

    except KeyboardInterrupt:
        print("\n중단됨. 현재까지 저장...")
    finally:
        if results:
            pd.DataFrame(results).to_parquet(out_path, index=False)
            print(f"\n저장 완료: {out_path} ({len(results):,}개)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="output/silver/goods/20260310_goods_silver.parquet",
    )
    parser.add_argument(
        "--output",
        default=f"output/gold/ocr/{datetime.now().strftime('%Y%m%d')}_ocr.parquet",
    )
    parser.add_argument("--sample", type=int, default=None, metavar="N")
    args = parser.parse_args()
    main(args.input, args.output, args.sample)
