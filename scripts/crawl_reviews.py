"""
어바웃펫 상품 리뷰 전수 수집
- Bronze goods parquet (또는 --goods-input 경로)에서 고유 goods_id 추출
- getGoodsEntireCommentList 전 페이지 수집
- 출력: output/bronze/reviews/YYYYMMDD_reviews.parquet
- 체크포인트: output/checkpoint_reviews.json (중단 후 재실행 시 완료 상품 스킵)

실행:
  conda run -n final-project python scripts/crawl_reviews.py
  conda run -n final-project python scripts/crawl_reviews.py --goods-input output/bronze/goods/20260309_goods.parquet
  conda run -n final-project python scripts/crawl_reviews.py --goods-input output/bronze/goods/20260309_goods.parquet --max-pages 20
"""

import argparse
import asyncio
import json
import random
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from config import (
    BASE_URL,
    CHECKPOINT_REVIEWS,
    DELAY_RANGE,
    MAX_RETRIES,
    USER_AGENT,
)

LOG_INTERVAL = 50       # N개 상품마다 진행 요약 출력
SAVE_INTERVAL = 200     # N개 상품마다 중간 parquet 저장


# ── 체크포인트 ────────────────────────────────────────────

def load_checkpoint() -> set:
    """완료된 goods_id 집합 로드"""
    path = Path(CHECKPOINT_REVIEWS)
    if path.exists():
        with open(path) as f:
            return set(json.load(f))
    return set()


def save_checkpoint(completed: set) -> None:
    Path(CHECKPOINT_REVIEWS).parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_REVIEWS, "w") as f:
        json.dump(list(completed), f)


# ── 리뷰 API 호출 ─────────────────────────────────────────

async def fetch_review_page(page, goods_id: str, page_num: int) -> str:
    """리뷰 한 페이지 요청 → HTML 반환 (page=1부터 시작)"""
    for attempt in range(MAX_RETRIES):
        try:
            resp = await page.request.post(
                f"{BASE_URL}/goods/getGoodsEntireCommentList",
                form={
                    "goodsId":          goods_id,
                    "goodsCstrtTpCd":   "ITEM",   # 필수 — 누락 시 빈 응답
                    "page":             str(page_num),
                    "sidx":             "",
                    "sord":             "",
                    "optGoodsId":       "",
                    "detailYn":         "Y",
                    "petKindNm":        "",
                    "petAge":           "",
                    "petWeight":        "",
                    "pageGoodsEstmNo":  "",
                },
            )
            return await resp.text()
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            print(f"      재시도 {attempt + 1}/{MAX_RETRIES}: {e}")
            await asyncio.sleep(2)


# ── HTML 파싱 ─────────────────────────────────────────────

def parse_total_pages(html: str) -> int:
    """goodsComment.totalPageCount = 8; → 8"""
    m = re.search(r"totalPageCount\s*=\s*(\d+)", html)
    return int(m.group(1)) if m else 1


def parse_star_class(el) -> float | None:
    """class p_X_Y → float (p_5_0→5.0, p_4_5→4.5)"""
    if not el:
        return None
    for cls in el.get("class", []):
        if cls.startswith("p_"):
            parts = cls[2:].split("_")
            if len(parts) == 2:
                try:
                    return float(f"{parts[0]}.{parts[1]}")
                except ValueError:
                    pass
    return None


def parse_review_page(html: str, goods_id: str) -> list[dict]:
    """HTML → Bronze 리뷰 레코드 리스트"""
    soup = BeautifulSoup(html, "html.parser")
    records = []

    for box in soup.select('div[name="estmDataArea"]'):
        review_id  = box.get("data-goods-estm-no", "")
        if not review_id:
            continue

        # 별점
        stars_el = box.select_one(".stars.sm")
        score = parse_star_class(stars_el)

        # 본문
        msg_el = box.select_one(".msgs")
        content = msg_el.get_text(strip=True) if msg_el else ""

        # 작성자 / 날짜
        nick_el  = box.select_one(".writer-info .ids")
        date_el  = box.select_one(".writer-info .date")
        author   = nick_el.get_text(strip=True) if nick_el else ""
        written  = date_el.get_text(strip=True) if date_el else ""  # YYYY.MM.DD

        # 구매 유형 (항상 존재 확인됨)
        pl_el = box.select_one(".purchase-label")
        if pl_el:
            classes = pl_el.get("class", [])
            purchase_label = "first" if "first" in classes else "repeat" if "repeat" in classes else None
        else:
            purchase_label = None

        # 펫 프로필 (조건부)
        pet_name = pet_gender = pet_age_raw = pet_weight_raw = pet_breed = None
        spec = box.select_one("div.spec")
        if spec:
            name_el   = spec.select_one("em.b")
            gender_el = spec.select_one("em.b > i.g")
            ems       = spec.select("em")
            pet_gender    = gender_el.get_text(strip=True) if gender_el else None
            pet_name      = name_el.get_text(strip=True).replace(f"({pet_gender})", "").strip() if name_el else None
            pet_age_raw   = ems[1].get_text(strip=True) if len(ems) > 1 else None  # "7개월" / "3살"
            pet_weight_raw = ems[2].get_text(strip=True) if len(ems) > 2 else None  # "2.5kg"
            pet_breed     = ems[3].get_text(strip=True) if len(ems) > 3 else None

        # review_info (완구/용품만 존재, 식품 없음)
        review_info = {}
        for li in box.select("ul.satis li"):
            dt = li.select_one(".dt")
            dd = li.select_one(".dd")
            if dt and dd:
                review_info[dt.get_text(strip=True)] = dd.get_text(strip=True)

        records.append({
            "review_id":       review_id,
            "goods_id":        goods_id,
            "score_raw":       score,           # 이미 float
            "content":         content,
            "author_nickname": author,
            "written_at_raw":  written,         # YYYY.MM.DD (Silver에서 date 변환)
            "purchase_label":  purchase_label,
            "pet_name":        pet_name,
            "pet_gender":      pet_gender,
            "pet_age_raw":     pet_age_raw,     # "7개월" / "3살" (Silver에서 months 변환)
            "pet_weight_raw":  pet_weight_raw,  # "2.5kg" (Silver에서 float 변환)
            "pet_breed":       pet_breed,
            "review_info":     json.dumps(review_info, ensure_ascii=False) if review_info else None,
        })

    return records


# ── 상품별 리뷰 전수 수집 ──────────────────────────────────

async def crawl_reviews_for_goods(
    page, goods_id: str, max_pages: int | None
) -> list[dict]:
    """goods_id 하나의 리뷰 전 페이지 수집"""
    all_records = []

    html = await fetch_review_page(page, goods_id, 1)
    total_pages = parse_total_pages(html)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    records = parse_review_page(html, goods_id)
    all_records.extend(records)

    for page_num in range(2, total_pages + 1):
        await asyncio.sleep(random.uniform(*DELAY_RANGE))
        html = await fetch_review_page(page, goods_id, page_num)
        records = parse_review_page(html, goods_id)
        if not records:
            break
        all_records.extend(records)

    return all_records


# ── 중간 저장 ─────────────────────────────────────────────

def save_parquet(records: list[dict], output_dir: Path, date_str: str) -> Path:
    df = pd.DataFrame(records)
    path = output_dir / f"{date_str}_reviews.parquet"
    df.to_parquet(path, index=False)
    return path


# ── 메인 ─────────────────────────────────────────────────

async def main(goods_input: str, max_pages: int | None):
    # goods_id 목록 로드
    df_goods = pd.read_parquet(goods_input)
    goods_ids = df_goods["goods_id"].unique().tolist()
    total = len(goods_ids)

    completed = load_checkpoint()
    remaining = [gid for gid in goods_ids if gid not in completed]

    date_str   = datetime.now().strftime("%Y%m%d")
    output_dir = Path("output/bronze/reviews")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[crawl_reviews] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  goods 파일: {goods_input}")
    print(f"  전체 고유 상품: {total:,}개")
    print(f"  완료(체크포인트): {len(completed):,}개")
    print(f"  수집 대상: {len(remaining):,}개")
    if max_pages:
        print(f"  리뷰 페이지 상한: {max_pages}페이지/상품")
    print()

    if not remaining:
        print("모두 완료됨.")
        return

    all_records: list[dict] = []
    start_time  = time.time()
    processed   = 0
    total_reviews = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page    = await context.new_page()

        # 세션 초기화
        await page.goto(f"{BASE_URL}/shop/home/", wait_until="domcontentloaded")
        await asyncio.sleep(1)

        for goods_id in remaining:
            try:
                records = await crawl_reviews_for_goods(page, goods_id, max_pages)
            except Exception as e:
                print(f"  [오류] {goods_id}: {e} — 스킵")
                completed.add(goods_id)
                save_checkpoint(completed)
                continue

            all_records.extend(records)
            completed.add(goods_id)
            processed   += 1
            total_reviews += len(records)

            elapsed  = time.time() - start_time
            rate     = processed / elapsed if elapsed > 0 else 0
            eta_sec  = (len(remaining) - processed) / rate if rate > 0 else 0
            eta_str  = str(timedelta(seconds=int(eta_sec)))

            print(
                f"  [{processed:>4}/{len(remaining)}] {goods_id}"
                f"  리뷰:{len(records):>5}개  누적:{total_reviews:,}"
                f"  | 속도:{rate:.1f}/s  ETA:{eta_str}"
            )

            if processed % LOG_INTERVAL == 0:
                save_checkpoint(completed)
                print(f"\n  ── 중간 요약 ({processed}/{len(remaining)}) ──")
                print(f"     누적 리뷰 수: {total_reviews:,}개")
                print(f"     경과: {str(timedelta(seconds=int(elapsed)))}  ETA: {eta_str}\n")

            if processed % SAVE_INTERVAL == 0:
                path = save_parquet(all_records, output_dir, date_str)
                print(f"  [중간저장] {path}  ({len(all_records):,}건)\n")

            await asyncio.sleep(random.uniform(*DELAY_RANGE))

        await browser.close()

    save_checkpoint(completed)

    if not all_records:
        print("수집된 리뷰 없음")
        return

    # 최종 저장
    path = save_parquet(all_records, output_dir, date_str)
    df   = pd.DataFrame(all_records)
    csv_path = output_dir / f"{date_str}_reviews.csv"
    df.to_csv(csv_path, index=False)

    print(f"\n저장 완료")
    print(f"  총 리뷰 수: {len(df):,}건")
    print(f"  고유 상품 수: {df['goods_id'].nunique():,}개")
    print(f"  Parquet: {path}")
    print(f"  CSV:     {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--goods-input",
        default="output/bronze/goods/20260309_goods.parquet",
        help="goods_id 목록을 담은 Bronze goods parquet 경로",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="상품당 최대 수집 페이지 수 (기본: 전체, 테스트 시 --max-pages 5 권장)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.goods_input, args.max_pages))
