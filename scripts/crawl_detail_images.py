"""
어바웃펫 상품 상세 이미지 URL 수집
- Bronze goods parquet에서 고유 goods_id 추출
- indexGoodsDetail 페이지 방문 → img[src*='editor/goods_desc/'] 수집
- 기존 parquet의 detail_image_urls 컬럼 업데이트 후 덮어쓰기

실행: conda run -n final-project python scripts/crawl_detail_images.py
     conda run -n final-project python scripts/crawl_detail_images.py --input output/bronze/goods/20260309_goods.parquet
"""

import argparse
import asyncio
import json
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

from config import (
    BASE_URL,
    CHECKPOINT_DETAIL_IMAGES,
    DELAY_RANGE,
    MAX_RETRIES,
    USER_AGENT,
)

LOG_INTERVAL = 50   # N개 처리마다 진행 요약 출력


# ── 체크포인트 ────────────────────────────────────────────

def load_checkpoint() -> dict:
    """완료된 goods_id → url list 매핑 로드"""
    path = Path(CHECKPOINT_DETAIL_IMAGES)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}


def save_checkpoint(done: dict) -> None:
    Path(CHECKPOINT_DETAIL_IMAGES).parent.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT_DETAIL_IMAGES, "w") as f:
        json.dump(done, f, ensure_ascii=False)


# ── 상세 이미지 수집 ──────────────────────────────────────

async def fetch_detail_images(page, goods_id: str) -> list[str]:
    """indexGoodsDetail 페이지에서 editor/goods_desc/ 이미지 URL 목록 반환"""
    url = f"{BASE_URL}/goods/indexGoodsDetail?goodsId={goods_id}"
    for attempt in range(MAX_RETRIES):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await page.wait_for_timeout(800)

            imgs = await page.eval_on_selector_all(
                "img[src*='editor/goods_desc/']",
                "els => els.map(e => e.src)"
            )
            return imgs
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                print(f"    [오류] {goods_id}: {e}")
                return []
            print(f"    재시도 {attempt + 1}/{MAX_RETRIES}: {goods_id} — {e}")
            await asyncio.sleep(2)
    return []


# ── 메인 ─────────────────────────────────────────────────

async def main(input_path: str):
    df = pd.read_parquet(input_path)
    goods_ids = df["goods_id"].unique().tolist()
    total = len(goods_ids)

    done = load_checkpoint()
    remaining = [gid for gid in goods_ids if gid not in done]

    print(f"[crawl_detail_images] 시작 — {datetime.now().strftime('%H:%M:%S')}")
    print(f"  전체 고유 상품: {total:,}개")
    print(f"  완료(체크포인트): {len(done):,}개")
    print(f"  수집 대상: {len(remaining):,}개\n")

    if remaining:
        start_time = time.time()
        processed = 0
        has_images = 0

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent=USER_AGENT)
            page = await context.new_page()

            # 세션 초기화
            await page.goto(f"{BASE_URL}/shop/home/", wait_until="domcontentloaded")
            await asyncio.sleep(1)

            for goods_id in remaining:
                imgs = await fetch_detail_images(page, goods_id)
                done[goods_id] = imgs
                processed += 1
                if imgs:
                    has_images += 1

                elapsed = time.time() - start_time
                rate = processed / elapsed if elapsed > 0 else 0
                eta_sec = (len(remaining) - processed) / rate if rate > 0 else 0
                eta_str = str(timedelta(seconds=int(eta_sec)))

                print(
                    f"  [{processed:>4}/{len(remaining)}] {goods_id}"
                    f"  이미지:{len(imgs)}개"
                    f"  | 속도:{rate:.1f}/s  ETA:{eta_str}"
                )

                if processed % LOG_INTERVAL == 0:
                    save_checkpoint(done)
                    img_rate = has_images / processed * 100
                    print(f"\n  ── 중간 요약 ({processed}/{len(remaining)}) ──")
                    print(f"     이미지 보유 비율: {img_rate:.1f}%")
                    print(f"     경과: {str(timedelta(seconds=int(elapsed)))}  ETA: {eta_str}\n")

                await asyncio.sleep(random.uniform(*DELAY_RANGE))

            await browser.close()

        save_checkpoint(done)
        img_rate = has_images / processed * 100 if processed else 0
        print(f"\n수집 완료 — 이미지 보유: {has_images}/{processed}개 ({img_rate:.1f}%)")

    # ── Parquet 업데이트 ──────────────────────────────────
    print(f"\nParquet 업데이트 중: {input_path}")
    df["detail_image_urls"] = df["goods_id"].map(
        lambda gid: done.get(gid) or None
    )

    df.to_parquet(input_path, index=False)

    csv_path = Path(input_path).with_suffix(".csv")
    if csv_path.exists():
        df.to_csv(csv_path, index=False)
        print(f"CSV 업데이트: {csv_path}")

    filled = df["detail_image_urls"].apply(lambda x: isinstance(x, list) and len(x) > 0).sum()
    print(f"저장 완료")
    print(f"  detail_image_urls 보유: {filled:,}개 / {len(df):,}행")
    print(f"  출력 경로: {input_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="output/bronze/goods/20260309_goods.parquet",
        help="Bronze goods parquet 경로"
    )
    args = parser.parse_args()
    asyncio.run(main(args.input))
