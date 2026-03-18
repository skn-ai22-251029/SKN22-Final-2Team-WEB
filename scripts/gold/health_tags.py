"""
Gold Health Tags ETL
OCR 결과 parquet → LLM 건강 관심사 태그 분류 parquet

ocr_target=True 식품류 상품에 한해 product_name + OCR 텍스트를 LLM에 전달해
9개 건강 관심사 태그(관절/피부/소화/체중/요로/눈물/헤어볼/치아/면역) 중
해당하는 태그를 분류한다.

선행 스크립트:
  scripts/gold/ocr.py → output/gold/ocr/YYYYMMDD_ocr.parquet

출력 컬럼:
  goods_id              string
  health_concern_tags   list[str]

실행:
  conda run -n final-project python scripts/gold/health_tags.py
  conda run -n final-project python scripts/gold/health_tags.py --sample 10
  conda run -n final-project python scripts/gold/health_tags.py \\
      --ocr-input output/gold/ocr/20260310_ocr.parquet
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from glob import glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from tqdm import tqdm

load_dotenv()

# ── 설정 ──────────────────────────────────────────────────────────────────────

MODEL = "gpt-4o-mini"
MAX_RETRIES = 3
RETRY_DELAY = 2
CHECKPOINT_INTERVAL = 50
OCR_CACHE_GLOB = "output/gold/ocr/*_ocr.parquet"
OCR_TEXT_LIMIT = 1000  # 토큰 절감용 OCR 텍스트 최대 길이

VALID_TAGS = ["관절", "피부", "소화", "체중", "요로", "눈물", "헤어볼", "치아", "면역"]

SYSTEM_PROMPT = f"""당신은 반려동물 식품의 건강 관심사 태그를 분류하는 전문가입니다.
상품명과 패키지 OCR 텍스트를 보고, 아래 9개 태그 중 해당하는 것만 골라 JSON 배열로 반환하세요.

허용 태그: {VALID_TAGS}

반환 형식 (JSON 배열만, 설명 없이):
["관절", "피부"]

규칙:
- 해당하는 태그가 없으면 빈 배열 [] 반환
- 명확한 근거(성분, 기능 표기, 카테고리명)가 있을 때만 태그 부여
- 추측하지 말 것
"""


# ── LLM 호출 ──────────────────────────────────────────────────────────────────

def classify_health_tags(client: OpenAI, product_name: str, ocr_text: str) -> list[str]:
    """product_name + OCR 텍스트 → LLM → 건강 관심사 태그 리스트"""
    text = ocr_text[:OCR_TEXT_LIMIT] if isinstance(ocr_text, str) else ""
    user_content = f"상품명: {product_name}\n\nOCR 텍스트:\n{text}"

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            raw = response.choices[0].message.content
            parsed = json.loads(raw)
            # {"tags": [...]} 또는 [...] 형태 모두 처리
            if isinstance(parsed, list):
                tags = parsed
            elif isinstance(parsed, dict):
                tags = next((v for v in parsed.values() if isinstance(v, list)), [])
            else:
                tags = []
            return sorted(set(t for t in tags if t in VALID_TAGS))
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            print(f"\n[LLM Error] {e}")
            return []

    return []


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(ocr_input: str | None, output_path: str, sample_n: int | None) -> None:
    print(f"[gold/health_tags] 시작 — {datetime.now().strftime('%H:%M:%S')}")

    # 1. OCR 결과 로드
    if ocr_input:
        ocr_path = Path(ocr_input)
    else:
        files = sorted(glob(OCR_CACHE_GLOB))
        ocr_path = Path(files[-1]) if files else None

    if not ocr_path or not ocr_path.exists():
        print("OCR 결과 없음. scripts/gold/ocr.py 먼저 실행 필요.")
        return

    df_ocr = pd.read_parquet(ocr_path)
    df_ocr = df_ocr[df_ocr["ocr_text"].apply(lambda x: isinstance(x, str) and len(x.strip()) > 0)].copy()
    print(f"  OCR 결과 로드: {ocr_path} ({len(df_ocr):,}개)")

    if sample_n:
        df_ocr = df_ocr.sample(n=min(sample_n, len(df_ocr)), random_state=42)
        print(f"  샘플링: {len(df_ocr)}개")

    # 2. 기존 결과 로드 (resume)
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    results: list[dict] = []
    processed_ids: set = set()
    if out_path.exists():
        try:
            existing = pd.read_parquet(out_path)
            results = existing.to_dict("records")
            processed_ids = set(existing["goods_id"].unique())
            print(f"  기존 결과: {len(processed_ids):,}개 → 건너뜀")
        except Exception as e:
            print(f"  기존 결과 로드 실패 (새로 시작): {e}")

    df_todo = df_ocr[~df_ocr["goods_id"].isin(processed_ids)]
    if len(df_todo) == 0:
        print("  모든 대상 처리 완료")
        return

    print(f"  미처리: {len(df_todo):,}개")

    # 3. LLM 분류
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError(".env에 OPENAI_API_KEY 설정 필요")
    client = OpenAI(api_key=api_key)

    try:
        for _, row in tqdm(df_todo.iterrows(), total=len(df_todo), desc="LLM 분류"):
            tags = classify_health_tags(client, row.get("product_name", ""), row["ocr_text"])
            results.append({
                "goods_id": row["goods_id"],
                "health_concern_tags": tags,
            })

            if len(results) % CHECKPOINT_INTERVAL == 0:
                pd.DataFrame(results).to_parquet(out_path, index=False)

    except KeyboardInterrupt:
        print("\n중단됨. 현재까지 저장...")
    finally:
        if results:
            pd.DataFrame(results).to_parquet(out_path, index=False)
            tagged = sum(1 for r in results if r["health_concern_tags"])
            print(f"\n저장 완료: {out_path} ({len(results):,}개)")
            print(f"  태그 부여: {tagged:,}개 / 없음: {len(results) - tagged:,}개")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OCR parquet → LLM 건강 관심사 태그 분류")
    parser.add_argument("--ocr-input", default=None, help="OCR 결과 parquet 경로 (기본: output/gold/ocr/ 최신)")
    parser.add_argument(
        "--output",
        default=f"output/gold/health_tags/{datetime.now().strftime('%Y%m%d')}_health_tags.parquet",
    )
    parser.add_argument("--sample", type=int, default=None, metavar="N")
    args = parser.parse_args()
    main(args.ocr_input, args.output, args.sample)
