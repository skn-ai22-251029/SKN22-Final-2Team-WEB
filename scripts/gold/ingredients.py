"""
Gold Ingredients ETL
OCR 결과 parquet → LLM 원료/영양성분 파싱 parquet

선행 스크립트:
  scripts/gold/ocr.py → output/gold/ocr/YYYYMMDD_ocr.parquet

출력 컬럼:
  goods_id              string
  main_ingredients      list[str]   원료 키워드 배열 (치킨, 연어 등)
  ingredient_composition dict|None  {원료명: 함량%}
  nutrition_info         dict|None  {영양성분명: 수치}

실행:
  conda run -n final-project python scripts/gold/ingredients.py
  conda run -n final-project python scripts/gold/ingredients.py --sample 5
  conda run -n final-project python scripts/gold/ingredients.py \\
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

# OCR 텍스트에서 원재료/영양성분 섹션 앞뒤 N자만 추출 (토큰 절감)
SECTION_WINDOW = 800

SYSTEM_PROMPT = """당신은 반려동물 식품 원재료 정보를 추출하는 전문가입니다.
주어진 텍스트(사료/간식 패키지 OCR)에서 다음 세 가지를 JSON으로 반환하세요.

반환 형식 (JSON만 반환, 설명 없이):
{
  "main_ingredients": ["치킨", "연어"],
  "ingredient_composition": {"치킨(미국산)": "40%", "연어": "20%"},
  "nutrition_info": {"조단백질": "28% 이상", "조지방": "15% 이상", "수분": "10% 이하"}
}

규칙:
- main_ingredients: 원료명만 (함량 제외), 주요 단백질·곡물 원료 키워드 배열
- ingredient_composition: 원재료명 및 함량 섹션 기반. 없으면 null
- nutrition_info: 영양성분 보증 성분 섹션 기반. 없으면 null
- 원재료/영양성분 정보가 전혀 없으면 {"main_ingredients": [], "ingredient_composition": null, "nutrition_info": null}
"""


# ── OCR 텍스트 전처리 ──────────────────────────────────────────────────────────

SECTION_HEADERS = [
    "원재료명", "원료명", "원재료", "성분", "재료",
    "영양성분", "보증성분", "조단백질", "분석성분",
]

def extract_relevant_section(ocr_text: str) -> str:
    """
    OCR 전체 텍스트에서 원재료/영양성분 관련 섹션만 추출.
    섹션 헤더 기준 앞뒤 SECTION_WINDOW 자만 반환해 토큰 절감.
    """
    if not isinstance(ocr_text, str):
        return ""

    best_pos = -1
    for header in SECTION_HEADERS:
        pos = ocr_text.find(header)
        if pos != -1 and (best_pos == -1 or pos < best_pos):
            best_pos = pos

    if best_pos == -1:
        # 섹션 헤더 없으면 앞 SECTION_WINDOW 자만
        return ocr_text[:SECTION_WINDOW]

    start = max(0, best_pos - 50)
    end = min(len(ocr_text), best_pos + SECTION_WINDOW)
    return ocr_text[start:end]


# ── LLM 호출 ──────────────────────────────────────────────────────────────────

def parse_ingredients_with_llm(client: OpenAI, ocr_text: str) -> dict:
    """OCR 텍스트 → LLM → 구조화 결과"""
    section = extract_relevant_section(ocr_text)
    if not section.strip():
        return {"main_ingredients": [], "ingredient_composition": None, "nutrition_info": None}

    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": section},
                ],
                response_format={"type": "json_object"},
                temperature=0,
            )
            result = json.loads(response.choices[0].message.content)
            # 필수 키 보정
            return {
                "main_ingredients": result.get("main_ingredients", []),
                "ingredient_composition": result.get("ingredient_composition"),
                "nutrition_info": result.get("nutrition_info"),
            }
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue
            print(f"\n[LLM Error] {e}")
            return {"main_ingredients": [], "ingredient_composition": None, "nutrition_info": None}

    return {"main_ingredients": [], "ingredient_composition": None, "nutrition_info": None}


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main(ocr_input: str | None, output_path: str, sample_n: int | None) -> None:
    print(f"[gold/ingredients] 시작 — {datetime.now().strftime('%H:%M:%S')}")

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
    # ocr_text가 비어있지 않은 것만 처리
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

    # 3. LLM 호출
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise ValueError(".env에 OPENAI_API_KEY 설정 필요")
    client = OpenAI(api_key=api_key)

    try:
        for _, row in tqdm(df_todo.iterrows(), total=len(df_todo), desc="LLM 파싱"):
            parsed = parse_ingredients_with_llm(client, row["ocr_text"])
            results.append({
                "goods_id": row["goods_id"],
                "main_ingredients": parsed["main_ingredients"],
                "ingredient_composition": parsed["ingredient_composition"],
                "nutrition_info": parsed["nutrition_info"],
            })

            if len(results) % CHECKPOINT_INTERVAL == 0:
                pd.DataFrame(results).to_parquet(out_path, index=False)

    except KeyboardInterrupt:
        print("\n중단됨. 현재까지 저장...")
    finally:
        if results:
            pd.DataFrame(results).to_parquet(out_path, index=False)
            filled = sum(1 for r in results if r["ingredient_composition"])
            print(f"\n저장 완료: {out_path} ({len(results):,}개)")
            print(f"  ingredient_composition 파싱 성공: {filled:,}개")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ocr-input", default=None, help="OCR 결과 parquet 경로 (기본: output/gold/ocr/ 최신)")
    parser.add_argument(
        "--output",
        default=f"output/gold/ingredients/{datetime.now().strftime('%Y%m%d')}_ingredients.parquet",
    )
    parser.add_argument("--sample", type=int, default=None, metavar="N")
    args = parser.parse_args()
    main(args.ocr_input, args.output, args.sample)
