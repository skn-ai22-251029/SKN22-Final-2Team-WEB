"""
어바웃펫 상품 리뷰 전수 수집 (Bronze layer)

- Silver goods parquet에서 is_canonical=True 인 goods_id만 수집 대상으로 사용
  (orphan 리뷰 방지 — dedup 이전 goods_id 기준 수집 금지)
- CONCURRENCY개 Playwright 페이지를 동시에 운영 (기본 5개)
- getGoodsEntireCommentList 전 페이지 수집

두 가지 모드:
  기본 (--gp-only 없음): GP 제외, GI/GO/GS/PI 수집
    출력: output/bronze/reviews/YYYYMMDD_reviews.parquet
    체크포인트: output/checkpoint_reviews.json

  GP 전용 (--gp-only): GP만 수집 (다른 컴퓨터에서 병행 실행)
    출력: output/bronze/reviews/YYYYMMDD_reviews_gp.parquet
    체크포인트: output/checkpoint_reviews_gp.json

실행:
  conda run -n final-project python scripts/bronze_reviews.py
  conda run -n final-project python scripts/bronze_reviews.py --gp-only
  conda run -n final-project python scripts/bronze_reviews.py \
      --goods-input output/silver/goods/20260310_goods_silver.parquet \
      --max-pages 20 --concurrency 5
  conda run -n final-project python scripts/bronze_reviews.py --gp-only \
      --max-pages 100 --concurrency 3
"""

import argparse
import asyncio
import json
import random
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm

from config import (
    BASE_URL,
    CHECKPOINT_REVIEWS,
    CHECKPOINT_REVIEWS_GP,
    DELAY_RANGE,
    MAX_RETRIES,
    USER_AGENT,
)

SAVE_INTERVAL = 200   # N개 상품마다 중간 parquet 저장


# ── 체크포인트 ────────────────────────────────────────────────────────────────

def load_checkpoint(gp_only: bool) -> set:
    path = Path(CHECKPOINT_REVIEWS_GP if gp_only else CHECKPOINT_REVIEWS)
    if path.exists():
        with open(path) as f:
            return set(json.load(f))
    return set()


def save_checkpoint(completed: set, gp_only: bool) -> None:
    path = Path(CHECKPOINT_REVIEWS_GP if gp_only else CHECKPOINT_REVIEWS)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(list(completed), f)


# ── goods_id 목록 로드 ────────────────────────────────────────────────────────

def load_goods_ids(goods_input: str, gp_only: bool) -> list[str]:
    path = Path(goods_input)
    if not path.exists():
        raise FileNotFoundError(f"파일 없음: {goods_input}")

    df = pd.read_parquet(goods_input)

    if "is_canonical" in df.columns:
        non_canonical = (~df["is_canonical"]).sum()
        if non_canonical > 0:
            tqdm.write(f"  [참고] non-canonical {non_canonical}개 제외")
        goods_ids = df[df["is_canonical"] == True]["goods_id"].unique().tolist()
    else:
        tqdm.write("  [경고] is_canonical 컬럼 없음 — Bronze parquet 입력으로 판단, 전체 사용")
        tqdm.write("         Silver goods ETL 먼저 실행 권장: python scripts/silver_goods.py")
        goods_ids = df["goods_id"].unique().tolist()

    if gp_only:
        # GP 전용 모드: GP만 수집 (다른 컴퓨터에서 병행 실행용)
        # GP 리뷰 = 하위 variant 리뷰 합산. 하위 단품은 카탈로그 GI와 별개
        # 근거: docs/data/04_eda_issues.md 이슈 2 참고
        goods_ids = [gid for gid in goods_ids if gid.startswith("GP")]
        tqdm.write(f"  [GP 전용 모드] GP {len(goods_ids)}개 수집")
    else:
        # 기본 모드: GP 제외 (크롤링 비용 + review-product 매핑 모호)
        gp_count  = sum(1 for gid in goods_ids if gid.startswith("GP"))
        goods_ids = [gid for gid in goods_ids if not gid.startswith("GP")]
        tqdm.write(f"  [참고] GP {gp_count}개 수집 제외 — 이슈 2 참고 (--gp-only 로 별도 수집)")

    return goods_ids


# ── 리뷰 API 호출 ──────────────────────────────────────────────────────────────

def goods_cstrt_tp_cd(goods_id: str) -> str:
    """GP 상품은 PAK, 나머지는 ITEM"""
    return "PAK" if goods_id.startswith("GP") else "ITEM"


async def fetch_review_page(page, goods_id: str, page_num: int) -> str:
    for attempt in range(MAX_RETRIES):
        try:
            resp = await page.request.post(
                f"{BASE_URL}/goods/getGoodsEntireCommentList",
                form={
                    "goodsId":          goods_id,
                    "goodsCstrtTpCd":   goods_cstrt_tp_cd(goods_id),
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
            await asyncio.sleep(2)


# ── HTML 파싱 ──────────────────────────────────────────────────────────────────

def parse_total_pages(html: str) -> int:
    m = re.search(r"totalPageCount\s*=\s*(\d+)", html)
    return int(m.group(1)) if m else 1


def parse_star_class(el) -> float | None:
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
    soup    = BeautifulSoup(html, "html.parser")
    records = []

    for box in soup.select('div[name="estmDataArea"]'):
        review_id = box.get("data-goods-estm-no", "")
        if not review_id:
            continue

        score   = parse_star_class(box.select_one(".stars.sm"))
        msg_el  = box.select_one(".msgs")
        content = msg_el.get_text(strip=True) if msg_el else ""

        nick_el = box.select_one(".writer-info .ids")
        date_el = box.select_one(".writer-info .date")
        author  = nick_el.get_text(strip=True) if nick_el else ""
        written = date_el.get_text(strip=True) if date_el else ""

        pl_el = box.select_one(".purchase-label")
        if pl_el:
            classes        = pl_el.get("class", [])
            purchase_label = "first" if "first" in classes else "repeat" if "repeat" in classes else None
        else:
            purchase_label = None

        pet_name = pet_gender = pet_age_raw = pet_weight_raw = pet_breed = None
        spec = box.select_one("div.spec")
        if spec:
            name_el    = spec.select_one("em.b")
            gender_el  = spec.select_one("em.b > i.g")
            ems        = spec.select("em")
            pet_gender     = gender_el.get_text(strip=True) if gender_el else None
            pet_name       = name_el.get_text(strip=True).replace(f"({pet_gender})", "").strip() if name_el else None
            pet_age_raw    = ems[1].get_text(strip=True) if len(ems) > 1 else None
            pet_weight_raw = ems[2].get_text(strip=True) if len(ems) > 2 else None
            pet_breed      = ems[3].get_text(strip=True) if len(ems) > 3 else None

        review_info = {}
        for li in box.select("ul.satis li"):
            dt = li.select_one(".dt")
            dd = li.select_one(".dd")
            if dt and dd:
                review_info[dt.get_text(strip=True)] = dd.get_text(strip=True)

        records.append({
            "review_id":       review_id,
            "goods_id":        goods_id,
            "score_raw":       score,
            "content":         content,
            "author_nickname": author,
            "written_at_raw":  written,
            "purchase_label":  purchase_label,
            "pet_name":        pet_name,
            "pet_gender":      pet_gender,
            "pet_age_raw":     pet_age_raw,
            "pet_weight_raw":  pet_weight_raw,
            "pet_breed":       pet_breed,
            "review_info":     json.dumps(review_info, ensure_ascii=False) if review_info else None,
        })

    return records


# ── 상품별 리뷰 전수 수집 ───────────────────────────────────────────────────────

async def crawl_reviews_for_goods(page, goods_id: str, max_pages: int | None) -> list[dict]:
    html        = await fetch_review_page(page, goods_id, 1)
    total_pages = parse_total_pages(html)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    all_records = list(parse_review_page(html, goods_id))

    for page_num in range(2, total_pages + 1):
        await asyncio.sleep(random.uniform(*DELAY_RANGE))
        html    = await fetch_review_page(page, goods_id, page_num)
        records = parse_review_page(html, goods_id)
        if not records:
            break
        all_records.extend(records)

    return all_records


# ── 저장 ──────────────────────────────────────────────────────────────────────

def save_parquet(records: list[dict], output_dir: Path, date_str: str, suffix: str = "") -> Path:
    path = output_dir / f"{date_str}_reviews{suffix}.parquet"
    pd.DataFrame(records).to_parquet(path, index=False)
    return path


# ── 워커 ──────────────────────────────────────────────────────────────────────

async def worker(
    worker_id:    int,
    chunk:        list[str],
    page,
    all_records:  list,
    completed:    set,
    lock:         asyncio.Lock,
    pbar,
    output_dir:   Path,
    date_str:     str,
    max_pages:    int | None,
    gp_only:      bool,
    filename_suffix: str,
) -> None:
    for goods_id in chunk:
        try:
            records = await crawl_reviews_for_goods(page, goods_id, max_pages)
        except Exception as e:
            tqdm.write(f"  [W{worker_id}] 오류 {goods_id}: {e}")
            records = []

        async with lock:
            all_records.extend(records)
            completed.add(goods_id)
            pbar.update(1)
            pbar.set_postfix(reviews=f"{len(all_records):,}", refresh=False)

            if len(completed) % SAVE_INTERVAL == 0:
                save_checkpoint(completed, gp_only)
                save_parquet(all_records, output_dir, date_str, filename_suffix)
                tqdm.write(f"  [중간저장] {len(all_records):,}건")

        await asyncio.sleep(random.uniform(*DELAY_RANGE))


# ── 메인 ──────────────────────────────────────────────────────────────────────

async def main(goods_input: str, max_pages: int | None, concurrency: int, gp_only: bool) -> None:
    filename_suffix = "_gp" if gp_only else ""
    goods_ids = load_goods_ids(goods_input, gp_only)
    total     = len(goods_ids)

    completed = load_checkpoint(gp_only)
    remaining = [gid for gid in goods_ids if gid not in completed]

    date_str   = datetime.now().strftime("%Y%m%d")
    output_dir = Path("output/bronze/reviews")
    output_dir.mkdir(parents=True, exist_ok=True)

    mode_label = "GP 전용" if gp_only else "GP 제외"
    print(f"[bronze_reviews] 시작 — {datetime.now().strftime('%H:%M:%S')}  ({mode_label})")
    print(f"  goods 파일  : {goods_input}")
    print(f"  수집 대상   : {total:,}개")
    print(f"  체크포인트  : {len(completed):,}개 완료")
    print(f"  남은 대상   : {len(remaining):,}개")
    print(f"  동시 워커   : {concurrency}개")
    if max_pages:
        print(f"  페이지 상한 : {max_pages}페이지/상품")
    print()

    if not remaining:
        print("모두 완료됨.")
        return

    n_workers  = min(concurrency, len(remaining))
    all_records: list[dict] = []
    lock       = asyncio.Lock()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=USER_AGENT)

        # 워커마다 전용 페이지 생성 + 세션 초기화
        pages = []
        for i in range(n_workers):
            pg = await context.new_page()
            await pg.goto(f"{BASE_URL}/shop/home/", wait_until="domcontentloaded")
            pages.append(pg)
        await asyncio.sleep(1)

        # 작업 분배 (라운드로빈)
        chunks = [remaining[i::n_workers] for i in range(n_workers)]

        with tqdm(
            total=len(remaining),
            unit="상품",
            dynamic_ncols=True,
            bar_format="{l_bar}{bar}| {n:>5}/{total} [{elapsed}<{remaining}, {rate_fmt}] {postfix}",
        ) as pbar:
            await asyncio.gather(*[
                worker(
                    worker_id=i,
                    chunk=chunks[i],
                    page=pages[i],
                    all_records=all_records,
                    completed=completed,
                    lock=lock,
                    pbar=pbar,
                    output_dir=output_dir,
                    date_str=date_str,
                    max_pages=max_pages,
                    gp_only=gp_only,
                    filename_suffix=filename_suffix,
                )
                for i in range(n_workers)
            ])

        await browser.close()

    save_checkpoint(completed, gp_only)

    if not all_records:
        print("수집된 리뷰 없음")
        return

    path     = save_parquet(all_records, output_dir, date_str, filename_suffix)
    df       = pd.DataFrame(all_records)
    csv_path = output_dir / f"{date_str}_reviews{filename_suffix}.csv"
    df.to_csv(csv_path, index=False)

    print(f"\n저장 완료")
    print(f"  총 리뷰   : {len(df):,}건")
    print(f"  고유 상품 : {df['goods_id'].nunique():,}개")
    print(f"  Parquet   : {path}")
    print(f"  CSV       : {csv_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--goods-input",
        default="output/silver/goods/20260310_goods_silver.parquet",
        help="Silver goods parquet 경로",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="상품당 최대 수집 페이지 수 (기본: 전체)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="동시 수집 워커 수 (기본: 5)",
    )
    parser.add_argument(
        "--gp-only",
        action="store_true",
        default=False,
        help="GP 상품만 수집 (다른 컴퓨터에서 병행 실행용, 체크포인트 분리)",
    )
    args = parser.parse_args()
    asyncio.run(main(args.goods_input, args.max_pages, args.concurrency, args.gp_only))
