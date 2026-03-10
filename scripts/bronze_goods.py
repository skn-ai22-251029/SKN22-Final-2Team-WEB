"""
어바웃펫 상품 목록 크롤러
- 106개 소분류 전체 순회 → Bronze Parquet 저장
- 실행: conda run -n final-project python scripts/bronze_goods.py
- 출력: output/bronze/goods/YYYYMMDD_goods.parquet
- 체크포인트: output/checkpoint_goods.json (중단 후 재실행 시 완료된 소분류 스킵)
"""

import asyncio
import json
import random
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from config import (
    BASE_URL,
    CATEGORIES,
    CHECKPOINT_GOODS,
    DELAY_RANGE,
    MAX_RETRIES,
    OUTPUT_DIR,
    ROWS_PER_PAGE,
    USER_AGENT,
)


# ── 체크포인트 ────────────────────────────────────────────

def load_checkpoint() -> set:
    """완료된 소분류 코드 목록 로드"""
    path = Path(CHECKPOINT_GOODS)
    if path.exists():
        with open(path) as f:
            return set(json.load(f))
    return set()


def save_checkpoint(completed: set) -> None:
    """완료된 소분류 코드 목록 저장"""
    Path(CHECKPOINT_GOODS).parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_GOODS, "w") as f:
        json.dump(list(completed), f)


# ── API 호출 ─────────────────────────────────────────────

async def fetch_goods_page(page, cate_cd_l: str, cate_cd_m: str,
                           disp_clsf_no: str, page_num: int) -> str:
    """상품 목록 한 페이지 요청 → HTML 반환"""
    for attempt in range(MAX_RETRIES):
        try:
            resp = await page.request.post(
                f"{BASE_URL}/shop/getScateGoodsList",
                form={
                    "dispClsfNo": disp_clsf_no,
                    "cateCdL": cate_cd_l,
                    "cateCdM": cate_cd_m,
                    "order": "APET",
                    "page": str(page_num),   # 0-based
                    "rows": str(ROWS_PER_PAGE),
                    "filters": "",
                    "bndNos": "",
                },
            )
            return await resp.text()
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                raise
            print(f"    재시도 {attempt + 1}/{MAX_RETRIES}: {e}")
            await asyncio.sleep(2)


# ── HTML 파싱 ─────────────────────────────────────────────

def parse_goods_page(html: str, cate_cd_l: str, cate_cd_m: str,
                     disp_clsf_no: str, crawled_at: str) -> tuple[int, list[dict]]:
    """
    HTML → (총 상품 수, Bronze 레코드 리스트)
    Bronze 스키마: docs/data/03_medallion_schema.md 참고
    """
    soup = BeautifulSoup(html, "html.parser")

    # 총 상품 수: var goodsCount = '224';
    total_match = re.search(r"var goodsCount\s*=\s*'(\d+)'", html)
    total_count = int(total_match.group(1)) if total_match else 0

    records = []
    for item in soup.select(".gd-item[data-goodsid]"):
        thumb_el = item.select_one(".thumb-img")
        records.append({
            # 카테고리 정보
            "cate_cd_l":          cate_cd_l,
            "cate_cd_m":          cate_cd_m,
            "disp_clsf_no":       disp_clsf_no,
            # 상품 기본 정보 (Bronze: 원시 문자열 그대로)
            "goods_id":           item.get("data-goodsid", ""),
            "product_name":       item.get("data-productname", ""),
            "brand_id":           item.get("data-brandid", ""),
            "brand_name":         item.get("data-brandname", ""),
            "price_raw":          item.get("data-price", ""),
            "discount_price_raw": item.get("data-discountprice", ""),
            "rating_raw":         item.get("data-goodsstarsavgcnt", ""),   # 10점 만점
            "review_count_raw":   item.get("data-scorecnt", ""),
            "sold_out_yn":        item.get("data-soldoutyn", ""),
            "thumbnail_url":      thumb_el["src"] if thumb_el and thumb_el.get("src") else "",
            # detail_image_urls: indexGoodsDetail에서 별도 수집 (식품류만)
            # img[src*='editor/goods_desc/'] 셀렉터로 추출
            "detail_image_urls":  None,
            "crawled_at":         crawled_at,
        })

    return total_count, records


# ── 소분류 전체 수집 ──────────────────────────────────────

async def crawl_category(page, cate_cd_l: str, cate_cd_m: str,
                         disp_clsf_no: str, subcate_name: str,
                         crawled_at: str) -> list[dict]:
    """소분류 하나의 전체 상품 수집 (페이지 반복)"""
    all_records = []
    page_num = 0

    while True:
        html = await fetch_goods_page(page, cate_cd_l, cate_cd_m, disp_clsf_no, page_num)
        total_count, records = parse_goods_page(html, cate_cd_l, cate_cd_m,
                                                disp_clsf_no, crawled_at)

        if not records:
            break

        all_records.extend(records)

        fetched_so_far = (page_num + 1) * ROWS_PER_PAGE
        if fetched_so_far >= total_count:
            break  # 마지막 페이지

        page_num += 1
        await asyncio.sleep(random.uniform(*DELAY_RANGE))

    print(f"  [{subcate_name}] {len(all_records)}개 수집 (총 {total_count}개 공고)")
    return all_records


# ── 메인 ─────────────────────────────────────────────────

async def main():
    crawled_at = datetime.now().isoformat()
    output_dir = Path(OUTPUT_DIR) / "goods"
    output_dir.mkdir(parents=True, exist_ok=True)

    completed = load_checkpoint()
    all_records: list[dict] = []

    print(f"크롤링 시작 — 총 {len(CATEGORIES)}개 소분류")
    print(f"이미 완료된 소분류: {len(completed)}개 스킵\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        # 세션/쿠키 초기화를 위해 메인 페이지 한 번 방문
        await page.goto(f"{BASE_URL}/shop/home/", wait_until="domcontentloaded")
        await asyncio.sleep(1)

        for cate_cd_l, cate_cd_m, disp_clsf_no, subcate_name in CATEGORIES:
            if disp_clsf_no in completed:
                print(f"  [{subcate_name}] 스킵")
                continue

            try:
                records = await crawl_category(
                    page, cate_cd_l, cate_cd_m, disp_clsf_no, subcate_name, crawled_at
                )
                all_records.extend(records)
                completed.add(disp_clsf_no)
                save_checkpoint(completed)

            except Exception as e:
                print(f"  [{subcate_name}] 오류 발생: {e} — 스킵")
                continue

            await asyncio.sleep(random.uniform(*DELAY_RANGE))

        await browser.close()

    if not all_records:
        print("수집된 데이터 없음")
        return

    # ── Parquet 저장 ──────────────────────────────────────
    df = pd.DataFrame(all_records)

    date_str = datetime.now().strftime("%Y%m%d")
    output_path = output_dir / f"{date_str}_goods.parquet"
    df.to_parquet(output_path, index=False)

    unique_count = df["goods_id"].nunique()
    print(f"\n저장 완료")
    print(f"  총 행 수 (소분류 중복 포함): {len(df):,}")
    print(f"  고유 상품 수 (goodsId dedup): {unique_count:,}")
    print(f"  출력 경로: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
