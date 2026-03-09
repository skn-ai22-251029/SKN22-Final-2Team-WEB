"""
PI 아이템의 html_editor 이미지 URL 확인 및
GI/GP 0개 케이스 재확인
"""

import asyncio
from playwright.async_api import async_playwright

SAMPLE = [
    ("PI000003505", "완구"),
    ("PI000004418", "용품"),
    ("GI251085719", "건식사료_0건"),
    ("GI251073214", "건식사료_0건2"),
]

BASE_URL = "https://www.aboutpet.co.kr"


async def inspect(page, goods_id, label):
    url = f"{BASE_URL}/goods/indexGoodsDetail?goodsId={goods_id}"
    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
    await page.wait_for_timeout(2000)

    # html_editor 내 이미지 URL 전체
    html_editor_imgs = await page.evaluate("""
        () => {
            const imgs = document.querySelectorAll("[class*='html_editor'] img");
            return Array.from(imgs).map(img => img.src);
        }
    """)

    # 페이지 내 모든 이미지 중 goods_id 포함
    goods_id_imgs = await page.evaluate(f"""
        () => {{
            const imgs = document.querySelectorAll("img");
            return Array.from(imgs)
                .map(img => img.src)
                .filter(src => src.includes("{goods_id}"));
        }}
    """)

    # getGoodsDetailArea 섹션의 이미지
    detail_section_imgs = await page.evaluate("""
        () => {
            const section = document.getElementById('getGoodsDetailArea');
            if (!section) return [];
            return Array.from(section.querySelectorAll('img')).map(img => ({
                src: img.src,
                parentCls: img.parentElement ? img.parentElement.className : ''
            }));
        }
    """)

    print(f"\n[{goods_id}] {label}")
    print(f"  html_editor 내 이미지 ({len(html_editor_imgs)}개):")
    for url in html_editor_imgs[:6]:
        print(f"    {url}")
    print(f"  goods_id 포함 이미지 ({len(goods_id_imgs)}개):")
    for url in goods_id_imgs[:3]:
        print(f"    {url}")
    print(f"  getGoodsDetailArea 내 이미지 ({len(detail_section_imgs)}개):")
    for item in detail_section_imgs[:5]:
        print(f"    [{item['parentCls'][:40]}] {item['src'][:80]}")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        page = await context.new_page()

        for goods_id, label in SAMPLE:
            await inspect(page, goods_id, label)
            await asyncio.sleep(1)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
