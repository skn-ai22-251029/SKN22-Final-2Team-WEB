"""
상품 상세 페이지 이미지 구조 조사
editor/goods_desc/ 경로의 이미지가 OCR 대상인지 확인
"""

import asyncio
import json
from playwright.async_api import async_playwright

# 카테고리별 샘플 상품 (이전 세션에서 확인된 것들 + 추가)
SAMPLE_GOODS = [
    # 건식사료 (식품)
    "GI251094382",
    "GI251085719",
    "GI251073214",
    # 간식
    "GP251077026",
    "GP251064312",
    # 완구
    "PI000003505",
    "PI000004418",
    "PI000003982",
    # 용품
    "PI000005123",
    "PI000004812",
]

BASE_URL = "https://www.aboutpet.co.kr"


async def inspect_product(page, goods_id: str) -> dict:
    url = f"{BASE_URL}/goods/indexGoodsDetail?goodsId={goods_id}"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20000)
        await page.wait_for_timeout(1500)

        # 1) editor/goods_desc/ 경로 이미지
        desc_imgs = await page.eval_on_selector_all(
            "img[src*='editor/goods_desc/']",
            "els => els.map(e => e.src)"
        )

        # 2) html_editor 클래스 컨테이너 내 이미지
        html_editor_imgs = await page.eval_on_selector_all(
            "[class*='html_editor'] img",
            "els => els.map(e => e.src)"
        )

        # 3) .detail-area 또는 .detail-content 내 이미지
        detail_area_imgs = await page.eval_on_selector_all(
            ".detail-area img, .detail-content img, #detail img",
            "els => els.map(e => e.src)"
        )

        # 4) 모든 이미지 src 중 goods_desc 포함 여부
        all_imgs = await page.eval_on_selector_all(
            "img",
            "els => els.map(e => ({src: e.src, parent: e.parentElement ? e.parentElement.className : ''}))"
        )
        goods_desc_all = [i for i in all_imgs if "goods_desc" in i.get("src", "")]

        # 5) section/div parent class 확인
        containers = await page.evaluate("""
            () => {
                const imgs = Array.from(document.querySelectorAll("img[src*='editor/goods_desc/']"));
                return imgs.map(img => {
                    let el = img;
                    let parents = [];
                    for (let i = 0; i < 5; i++) {
                        el = el.parentElement;
                        if (!el) break;
                        parents.push({tag: el.tagName, cls: el.className, id: el.id});
                    }
                    return {src: img.src, parents};
                });
            }
        """)

        return {
            "goods_id": goods_id,
            "desc_imgs_count": len(desc_imgs),
            "desc_imgs": desc_imgs[:5],  # 최대 5개
            "html_editor_imgs_count": len(html_editor_imgs),
            "detail_area_imgs_count": len(detail_area_imgs),
            "goods_desc_from_all_imgs": len(goods_desc_all),
            "container_parents": containers[:3],  # 최대 3개
        }
    except Exception as e:
        return {"goods_id": goods_id, "error": str(e)}


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        results = []
        for goods_id in SAMPLE_GOODS:
            print(f"  조사 중: {goods_id} ...", flush=True)
            result = await inspect_product(page, goods_id)
            results.append(result)
            print(f"    desc_imgs: {result.get('desc_imgs_count', 'ERR')}, html_editor: {result.get('html_editor_imgs_count', 'ERR')}")
            await asyncio.sleep(0.8)

        await browser.close()

    # 결과 출력
    print("\n" + "="*60)
    print("결과 요약")
    print("="*60)
    for r in results:
        if "error" in r:
            print(f"{r['goods_id']}: ERROR - {r['error']}")
            continue
        print(f"\n[{r['goods_id']}]")
        print(f"  editor/goods_desc/ 이미지 수: {r['desc_imgs_count']}")
        print(f"  html_editor 내 이미지 수:    {r['html_editor_imgs_count']}")
        print(f"  detail-area 내 이미지 수:    {r['detail_area_imgs_count']}")
        if r['desc_imgs']:
            print(f"  샘플 URL: {r['desc_imgs'][0]}")
        if r['container_parents']:
            print(f"  부모 계층:")
            for item in r['container_parents'][:1]:
                for p_info in item['parents'][:4]:
                    print(f"    <{p_info['tag']}> cls='{p_info['cls']}' id='{p_info['id']}'")

    # JSON 저장
    with open("/tmp/detail_image_investigation.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n전체 결과: /tmp/detail_image_investigation.json")


if __name__ == "__main__":
    asyncio.run(main())
