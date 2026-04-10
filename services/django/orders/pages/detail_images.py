import re
from functools import lru_cache
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from .demo_detail_images import PRODUCT_DETAIL_DEMO_IMAGE_MAP

ABOUTPET_HOST_SUFFIX = "aboutpet.co.kr"
ABOUTPET_DETAIL_ENDPOINT = "https://www.aboutpet.co.kr/goods/getGoodsDetail?goodsId={goods_id}"
ABOUTPET_DETAIL_IMAGE_PATTERN = re.compile(
    r"https://prd-main-cdn\.aboutpet\.co\.kr/aboutPet/images/editor/goods_desc/[^\"'<>\s]+"
)
ABOUTPET_REQUEST_TIMEOUT_SECONDS = 5
ABOUTPET_REQUEST_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
ABOUTPET_GOODS_PREFIXES = ("GP", "PI", "GI", "GS", "GO")


def _dedupe_urls(urls):
    seen = set()
    ordered_urls = []
    for url in urls:
        normalized = (url or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered_urls.append(normalized)
    return tuple(ordered_urls)


def _is_aboutpet_product(product):
    product_url = (getattr(product, "product_url", "") or "").strip()
    goods_id = (getattr(product, "goods_id", "") or "").strip()

    if product_url:
        hostname = (urlparse(product_url).hostname or "").lower()
        return hostname.endswith(ABOUTPET_HOST_SUFFIX)

    return goods_id.startswith(ABOUTPET_GOODS_PREFIXES)


def _extract_aboutpet_detail_image_urls(html):
    return _dedupe_urls(ABOUTPET_DETAIL_IMAGE_PATTERN.findall(html or ""))


@lru_cache(maxsize=8192)
def _fetch_aboutpet_detail_image_urls(goods_id):
    normalized_goods_id = (goods_id or "").strip()
    if not normalized_goods_id:
        return ()

    request = Request(
        ABOUTPET_DETAIL_ENDPOINT.format(goods_id=quote(normalized_goods_id)),
        headers={"User-Agent": ABOUTPET_REQUEST_USER_AGENT},
    )

    try:
        with urlopen(request, timeout=ABOUTPET_REQUEST_TIMEOUT_SECONDS) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except (HTTPError, URLError, TimeoutError, ValueError):
        return ()
    except Exception:
        return ()

    return _extract_aboutpet_detail_image_urls(html)


def get_product_detail_image_urls(product):
    seeded_urls = PRODUCT_DETAIL_DEMO_IMAGE_MAP.get(getattr(product, "goods_id", ""))
    if seeded_urls:
        return seeded_urls

    if not _is_aboutpet_product(product):
        return ()

    return _fetch_aboutpet_detail_image_urls(getattr(product, "goods_id", ""))
