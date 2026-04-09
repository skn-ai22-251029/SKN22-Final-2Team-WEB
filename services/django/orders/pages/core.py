from collections import defaultdict
from urllib.parse import parse_qs, urlencode, urlparse

from django.db.models import Case, DecimalField, IntegerField, Q, Value, When
from django.db.models.functions import Coalesce
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from chat.models import ChatSession
from products.catalog_menu import build_catalog_menu_context
from products.models import Product
from ..models import Cart, Order, Wishlist


def _format_price(value):
    return f"{value:,}원"


def _product_summary(product):
    pet_type = ", ".join(product.pet_type[:2]) if product.pet_type else "반려동물 공용"
    category = product.subcategory[0] if product.subcategory else (product.category[0] if product.category else "기타")
    return f"{pet_type} · {category}"


def _display_product_name(brand_name, goods_name):
    return (goods_name or "").strip()


def _display_delivery_address(value):
    fallback = "배송지 정보가 아직 등록되지 않았어요"
    if not value:
        return fallback

    parts = [part.strip() for part in value.split("|", 1)]
    base_address = parts[0] if parts else ""
    detail_address = parts[1] if len(parts) > 1 else ""

    placeholder_values = {
        "기본 배송지가 아직 등록되지 않았습니다.",
        "상세 주소 정보가 아직 없습니다.",
    }

    base_is_placeholder = not base_address or base_address in placeholder_values
    detail_is_placeholder = not detail_address or detail_address in placeholder_values

    if base_is_placeholder and detail_is_placeholder:
        return fallback
    if detail_is_placeholder:
        return base_address or fallback
    if base_is_placeholder:
        return detail_address or fallback
    return f"{base_address}, {detail_address}"


def _split_delivery_address(value):
    if not value:
        return "", ""

    parts = [part.strip() for part in value.split("|", 1)]
    base_address = parts[0] if parts else ""
    detail_address = parts[1] if len(parts) > 1 else ""
    return base_address, detail_address


def _recommended_note(index):
    notes = [
        "최근 상담 키워드와 잘 맞는 후보",
        "재구매 후보로 저장된 상품",
        "가격 비교를 위해 보관한 상품",
    ]
    return notes[index % len(notes)]


def _build_catalog_filter_tree(catalog_menu_sections):
    tree = {"pets": [], "brands": {}}

    for section in catalog_menu_sections:
        pet_label = section.get("label") or ""
        pet_entry = {"label": pet_label, "categories": []}
        for category in section.get("categories", []):
            category_label = category.get("label") or ""
            groups = []
            for group in category.get("groups", []):
                items = []
                for item in group.get("items", []):
                    query = parse_qs(urlparse(item.get("href") or "").query)
                    subcategory_value = (query.get("subcategory") or [""])[0]
                    if not subcategory_value:
                        continue
                    items.append(
                        {
                            "label": item.get("label") or subcategory_value,
                            "value": subcategory_value,
                        }
                    )
                if items:
                    groups.append({"label": group.get("label") or "", "items": items})
            pet_entry["categories"].append({"label": category_label, "groups": groups})
        tree["pets"].append(pet_entry)

    brand_map = defaultdict(lambda: defaultdict(lambda: defaultdict(set)))
    rows = Product.objects.filter(soldout_yn=False).values_list("pet_type", "category", "subcategory", "brand_name")[:10000]
    for pet_types, categories, subcategories, brand_name in rows:
        if not brand_name:
            continue
        normalized_pet_types = [value for value in (pet_types or []) if value]
        normalized_categories = [value for value in (categories or []) if value]
        normalized_subcategories = [value for value in (subcategories or []) if value]
        for pet_value in normalized_pet_types:
            for category_value in normalized_categories:
                for subcategory_value in normalized_subcategories:
                    brand_map[pet_value][category_value][subcategory_value].add(brand_name)

    tree["brands"] = {
        pet_value: {
            category_value: {
                subcategory_value: sorted(values)
                for subcategory_value, values in subcategory_map.items()
            }
            for category_value, subcategory_map in category_map.items()
        }
        for pet_value, category_map in brand_map.items()
    }
    return tree


def _member_nav_indicator_state(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return {
        "member_nav_has_cart_items": cart.items.exists(),
        "member_nav_has_wishlist_items": wishlist.items.exists(),
    }


ORDER_STATUS_VIEW_META = {
    "pending": {
        "label": "주문 접수",
        "class": "bg-[#fef3c7] text-[#b45309]",
        "can_reorder": True,
        "detail_hint": "상품 준비가 시작되면\n배송 상태가 업데이트됩니다",
        "cta_label": "다시 담기",
    },
    "shipping": {
        "label": "배송 중",
        "class": "bg-[#dbeafe] text-[#2563eb]",
        "can_reorder": True,
        "detail_hint": "상품이 배송 중입니다\n필요한 구성은 다시 주문할 수 있어요",
        "cta_label": "다시 담기",
    },
    "completed": {
        "label": "배송 완료",
        "class": "bg-[#dcfce7] text-[#15803d]",
        "can_reorder": True,
        "detail_hint": "배송이 완료된 주문입니다\n필요한 상품은 다시 주문할 수 있어요",
        "cta_label": "다시 담기",
    },
    "cancelled": {
        "label": "주문 취소",
        "class": "bg-[#fee2e2] text-[#dc2626]",
        "can_reorder": False,
        "detail_hint": "취소된 주문입니다\n결제와 배송 정보를 확인해 주세요",
        "cta_label": "주문 정보 확인",
    },
}

ORDER_LIST_ORDERING = {
    "latest": {"label": "최신순", "queryset": "-created_at"},
    "oldest": {"label": "오래된순", "queryset": "created_at"},
}
DEFAULT_ORDER_PAGE_SIZE = 12
DEFAULT_CATALOG_PAGE_SIZE = 24
CATALOG_SORT_OPTIONS = {
    "tailtalk": {
        "label": "TailTalk 추천순",
        "ordering": ("-_sort_popularity_score", "-_sort_review_count", "-_sort_rating", "goods_name"),
    },
    "reviews": {
        "label": "리뷰 많은순",
        "ordering": ("-_sort_review_count", "-_sort_popularity_score", "-_sort_rating", "goods_name"),
    },
    "price_low": {
        "label": "가격 낮은순",
        "ordering": ("price", "-_sort_review_count", "-_sort_popularity_score", "goods_name"),
    },
    "price_high": {
        "label": "가격 높은순",
        "ordering": ("-price", "-_sort_review_count", "-_sort_popularity_score", "goods_name"),
    },
    "rating_high": {
        "label": "평점 높은순",
        "ordering": ("-_sort_has_rating", "-_sort_rating", "-_sort_review_count", "-_sort_popularity_score", "goods_name"),
    },
}


def _serialize_order_item(product, quantity=1):
    return {
        "product_id": product.goods_id,
        "thumbnail_url": product.thumbnail_url,
        "emoji": "📦",
        "name": _display_product_name(product.brand_name, product.goods_name),
        "quantity": quantity,
        "unit_price": _format_price(product.price),
        "price": _format_price(product.price * quantity),
    }


def _serialize_catalog_item(product, *, is_wishlisted=False, cart_quantity=0):
    return {
        "product_id": product.goods_id,
        "thumbnail_url": product.thumbnail_url,
        "product_url": product.product_url,
        "brand_name": product.brand_name,
        "name": _display_product_name(product.brand_name, product.goods_name),
        "summary": _product_summary(product),
        "price": product.price,
        "price_label": _format_price(product.price),
        "rating": f"{product.rating:.1f}" if product.rating is not None else None,
        "review_count": product.review_count or 0,
        "pet_type": product.pet_type,
        "category": product.category,
        "subcategory": product.subcategory,
        "is_wishlisted": is_wishlisted,
        "cart_quantity": cart_quantity,
        "is_in_cart": cart_quantity > 0,
    }


def _catalog_query_params(request, overrides=None):
    params = {}
    for key in ("q", "pet", "category", "subcategory", "brand", "sort", "session", "page"):
        value = (request.GET.get(key) or "").strip()
        if value:
            params[key] = value
    if overrides:
        for key, value in overrides.items():
            if value:
                params[key] = value
            else:
                params.pop(key, None)
    if not params:
        return ""
    return "&".join(f"{key}={value}" for key, value in params.items())


def _build_catalog_filter_options(queryset, field_name):
    values = []
    for row in queryset.values_list(field_name, flat=True):
        if not row:
            continue
        for item in row:
            if item and item not in values:
                values.append(item)
    return values


def _catalog_brand_sort_key(value):
    normalized = (value or "").strip()
    return tuple(ord(char) for char in normalized)


def _with_catalog_sort_fields(queryset):
    return queryset.annotate(
        _sort_has_rating=Case(
            When(rating__isnull=False, then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        ),
        _sort_popularity_score=Coalesce(
            "popularity_score",
            Value(0),
            output_field=DecimalField(max_digits=10, decimal_places=4),
        ),
        _sort_review_count=Coalesce(
            "review_count",
            Value(0),
            output_field=IntegerField(),
        ),
        _sort_rating=Coalesce(
            "rating",
            Value(0),
            output_field=DecimalField(max_digits=3, decimal_places=1),
        ),
    )


def _catalog_querystring(current_params, **overrides):
    params = dict(current_params)
    for key, value in overrides.items():
        if value is None or value == "":
            params.pop(key, None)
        else:
            params[key] = value
    page_value = params.get("page")
    if page_value in {"", None, 1, "1"}:
        params.pop("page", None)
    if not params:
        return ""
    return urlencode(params)


def _href_query_matches(href, current_params, keys=("pet", "category", "subcategory", "brand")):
    parsed = parse_qs(urlparse(href).query)
    for key in keys:
        current_value = (current_params.get(key) or "").strip()
        href_value = (parsed.get(key) or [""])[0].strip()
        if current_value != href_value:
            return False
    return True


def _query_value_from_href(href, key):
    parsed = parse_qs(urlparse(href).query)
    return (parsed.get(key) or [""])[0].strip()


def _serialize_recommendation_item(recommendation, *, is_wishlisted=False, cart_quantity=0):
    product = recommendation.product
    return {
        "product_id": product.goods_id,
        "thumbnail_url": product.thumbnail_url,
        "product_url": product.product_url,
        "brand_name": product.brand_name,
        "name": _display_product_name(product.brand_name, product.goods_name),
        "summary": _product_summary(product),
        "price_label": _format_price(product.price),
        "rating": f"{product.rating:.1f}" if product.rating is not None else None,
        "review_count": product.review_count or 0,
        "rank_order": recommendation.rank_order,
        "is_wishlisted": is_wishlisted,
        "cart_quantity": cart_quantity,
        "is_in_cart": cart_quantity > 0,
    }


def _serialize_order_group(order):
    status_meta = ORDER_STATUS_VIEW_META.get(
        order.status,
        {
            "label": order.status,
            "class": "bg-[#edf2f7] text-[#4a5568]",
            "can_reorder": False,
            "detail_hint": "",
            "cta_label": "주문 정보 확인",
        },
    )
    items = []
    total_quantity = 0
    for item in order.items.select_related("product").all():
        total_quantity += item.quantity
        items.append(
            {
                "product_id": item.product.goods_id,
                "thumbnail_url": item.product.thumbnail_url,
                "emoji": "📦",
                "name": _display_product_name(item.product.brand_name, item.product.goods_name),
                "quantity": item.quantity,
                "unit_price": _format_price(item.price_at_order),
                "price": _format_price(item.price_at_order * item.quantity),
            }
        )

    return {
        "order_id": str(order.order_id),
        "created_at": order.created_at.strftime("%Y.%m.%d"),
        "status": status_meta["label"],
        "status_class": status_meta["class"],
        "can_reorder": status_meta["can_reorder"],
        "detail_hint": status_meta["detail_hint"],
        "cta_label": status_meta["cta_label"],
        "recipient": order.recipient_name,
        "recipient_phone": order.recipient_phone,
        "delivery_address": _display_delivery_address(order.delivery_address),
        "total_price": _format_price(order.total_price),
        "delivery_message": order.delivery_message,
        "payment_method": order.payment_method,
        "item_count": total_quantity,
        "items": items,
    }


def _serialize_order_completion(order):
    base_address, detail_address = _split_delivery_address(order.delivery_address)
    items = []
    total_quantity = 0

    for item in order.items.select_related("product").all():
        total_quantity += item.quantity
        items.append(
            {
                "product_id": item.product.goods_id,
                "name": _display_product_name(item.product.brand_name, item.product.goods_name),
                "brand": item.product.brand_name,
                "thumbnail_url": item.product.thumbnail_url,
                "quantity": item.quantity,
                "unit_price_raw": int(item.price_at_order),
                "line_total": _format_price(item.price_at_order * item.quantity),
            }
        )

    return {
        "order_id": str(order.order_id),
        "created_at": order.created_at.strftime("%Y.%m.%d %H:%M"),
        "recipient_name": order.recipient_name,
        "recipient_phone": order.recipient_phone,
        "delivery_base_address": base_address,
        "delivery_detail_address": detail_address,
        "delivery_address_display": _display_delivery_address(order.delivery_address),
        "delivery_message": order.delivery_message or "배송 메시지 없음",
        "payment_method": order.payment_method,
        "product_total": _format_price(order.product_total),
        "coupon_discount": _format_price(order.coupon_discount),
        "mileage_discount": _format_price(order.mileage_discount),
        "shipping_fee": "무료" if order.shipping_fee == 0 else _format_price(order.shipping_fee),
        "shipping_fee_raw": int(order.shipping_fee),
        "total_price": _format_price(order.total_price),
        "total_price_raw": int(order.total_price),
        "item_count": total_quantity,
        "items": items,
        "primary_item_name": items[0]["name"] if items else "주문 상품",
    }


def _parse_order_list_options(request):
    status_filter = (request.GET.get("status") or "all").strip() or "all"
    if status_filter != "all" and status_filter not in ORDER_STATUS_VIEW_META:
        status_filter = "all"

    ordering_key = (request.GET.get("ordering") or "latest").strip() or "latest"
    if ordering_key not in ORDER_LIST_ORDERING:
        ordering_key = "latest"

    try:
        page = max(int(request.GET.get("page", 1) or 1), 1)
    except (TypeError, ValueError):
        page = 1

    return {
        "status_filter": status_filter,
        "ordering_key": ordering_key,
        "page": page,
    }


def _build_order_list_query(status_filter, ordering_key, page=None):
    return _build_order_list_query_with_demo(status_filter, ordering_key, page=page, demo_mode=False)


def _build_order_list_query_with_demo(status_filter, ordering_key, page=None, demo_mode=False):
    query = []
    if status_filter and status_filter != "all":
        query.append(f"status={status_filter}")
    if ordering_key and ordering_key != "latest":
        query.append(f"ordering={ordering_key}")
    if page and page != 1:
        query.append(f"page={page}")
    if demo_mode:
        query.append("demo=1")
    return "&".join(query)


def _is_demo_mode(request):
    return (request.GET.get("demo") or "").strip().lower() in {"1", "true", "yes", "demo"}


def _filter_demo_order_groups(order_groups, options):
    filtered = list(order_groups)
    if options["status_filter"] != "all":
        filtered = [
            order for order in filtered
            if order.get("status_code") == options["status_filter"]
        ]

    reverse = options["ordering_key"] != "oldest"
    filtered.sort(key=lambda order: order.get("created_at", ""), reverse=reverse)
    return filtered


def _single_product_queryset():
    excluded_terms = [
        "모음",
        "모아보기",
        "세트",
        "BEST",
        "color",
        "Color",
        "S-XL",
        "S-M",
        "SM-",
        "2XL",
        "3XL",
        "4XL",
        "무료배송",
        "샘플",
        "스쿱",
    ]
    query = Product.objects.filter(
        soldout_yn=False,
    ).filter(
        Q(goods_name__icontains="영양제") | Q(goods_name__icontains="사료")
    )

    for term in excluded_terms:
        query = query.exclude(goods_name__icontains=term)

    return query.order_by("-review_count", "-price", "goods_id")


def _load_product_panels():
    base_products = list(_single_product_queryset()[:30])

    if not base_products:
        return [], []

    sorted_by_name_length = sorted(
        base_products,
        key=lambda product: len(_display_product_name(product.brand_name, product.goods_name)),
        reverse=True,
    )

    selected_products = []
    longest_product = sorted_by_name_length[0]
    selected_products.append(longest_product)

    for product in base_products:
        if product.goods_id == longest_product.goods_id:
            continue
        selected_products.append(product)
        if len(selected_products) >= 9:
            break

    cart_source = selected_products[:5]
    wishlist_source = []
    if len(cart_source) > 1:
        wishlist_source.extend(cart_source[:2])
    wishlist_source.extend(selected_products[5:7])

    wishlist_goods_ids = {product.goods_id for product in wishlist_source}

    cart_items = []
    wishlist_items = []
    for index, product in enumerate(cart_source):
        cart_items.append(
            {
                "goods_id": product.goods_id,
                "thumbnail_url": product.thumbnail_url,
                "brand": product.brand_name,
                "name": _display_product_name(product.brand_name, product.goods_name),
                "summary": _product_summary(product),
                "price": product.price,
                "rating": product.rating,
                "review_count": product.review_count,
                "quantity": (index % 3) + 1,
                "note": _recommended_note(index),
                "is_wishlisted": product.goods_id in wishlist_goods_ids,
            }
        )

    for index, product in enumerate(wishlist_source):
        wishlist_items.append(
            {
                "goods_id": product.goods_id,
                "thumbnail_url": product.thumbnail_url,
                "brand": product.brand_name,
                "name": _display_product_name(product.brand_name, product.goods_name),
                "summary": _product_summary(product),
                "price": product.price,
                "rating": product.rating,
                "review_count": product.review_count,
                "note": _recommended_note(index),
            }
        )

    return cart_items, wishlist_items


def _serialize_panel_product(product, quantity=1, is_wishlisted=False, note="가격 비교를 위해 보관한 상품"):
    return {
        "goods_id": product.goods_id,
        "thumbnail_url": product.thumbnail_url,
        "product_url": product.product_url,
        "brand": product.brand_name,
        "name": _display_product_name(product.brand_name, product.goods_name),
        "summary": _product_summary(product),
        "price": product.price,
        "rating": product.rating,
        "review_count": product.review_count,
        "quantity": quantity,
        "note": note,
        "is_wishlisted": is_wishlisted,
    }


def _load_user_product_panels(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    wishlist, _ = Wishlist.objects.get_or_create(user=user)

    wishlist_items_qs = list(wishlist.items.select_related("product").order_by("-added_at"))
    wishlist_ids = {item.product_id for item in wishlist_items_qs}

    cart_items = [
        _serialize_panel_product(
            item.product,
            quantity=item.quantity,
            is_wishlisted=item.product_id in wishlist_ids,
        )
        for item in cart.items.select_related("product").order_by("-added_at")
    ]
    wishlist_items = [
        _serialize_panel_product(item.product, quantity=1)
        for item in wishlist_items_qs
    ]

    return cart_items, wishlist_items


def _order_groups():
    base_products = list(_single_product_queryset()[:5])

    if len(base_products) >= 5:
        order_items = [
            [
                _serialize_order_item(base_products[0], 1),
                _serialize_order_item(base_products[1], 1),
                _serialize_order_item(base_products[2], 1),
                _serialize_order_item(base_products[3], 1),
                _serialize_order_item(base_products[4], 1),
            ],
            [_serialize_order_item(base_products[3], 2)],
            [_serialize_order_item(base_products[4], 1)],
        ]
        order_totals = [
            sum(product.price for product in [base_products[0], base_products[1], base_products[2], base_products[3], base_products[4]]),
            base_products[3].price * 2,
            base_products[4].price,
        ]
    else:
        order_items = [
            [
                {"product_id": None, "thumbnail_url": "", "emoji": "🐟", "name": "닥터독 하이포알러지 연어 사료", "quantity": 1, "unit_price": _format_price(39800), "price": _format_price(39800)},
                {"product_id": None, "thumbnail_url": "", "emoji": "👀", "name": "베러펫 눈물 케어 영양제", "quantity": 1, "unit_price": _format_price(25900), "price": _format_price(25900)},
                {"product_id": None, "thumbnail_url": "", "emoji": "🦴", "name": "벨버드 덴탈 케어 껌", "quantity": 1, "unit_price": _format_price(12900), "price": _format_price(12900)},
                {"product_id": None, "thumbnail_url": "", "emoji": "🛁", "name": "저자극 샴푸", "quantity": 1, "unit_price": _format_price(5400), "price": _format_price(5400)},
                {"product_id": None, "thumbnail_url": "", "emoji": "🍗", "name": "동결건조 치킨 트릿", "quantity": 1, "unit_price": _format_price(18400), "price": _format_price(18400)},
            ],
            [
                {"product_id": None, "thumbnail_url": "", "emoji": "🦴", "name": "벨버드 덴탈 케어 껌", "quantity": 2, "unit_price": _format_price(12900), "price": _format_price(25800)},
            ],
            [
                {"product_id": None, "thumbnail_url": "", "emoji": "🛁", "name": "저자극 샴푸", "quantity": 1, "unit_price": _format_price(5400), "price": _format_price(5400)},
            ],
        ]
        order_totals = [102400, 25800, 5400]

    return [
        {
            "order_id": "TT-20260325-1024",
            "status_code": "shipping",
            "created_at": "2026.03.25",
            "status": "배송 중",
            "status_class": "bg-[#dbeafe] text-[#2563eb]",
            "can_reorder": True,
            "detail_hint": "상품이 배송 중입니다\n필요한 구성은 다시 주문할 수 있어요",
            "cta_label": "다시 담기",
            "recipient": "왈냥",
            "recipient_phone": "010-1234-5678",
            "delivery_address": "서울 강동구 올림픽로 123, 101동 1203호",
            "total_price": _format_price(order_totals[0]),
            "delivery_message": "부재 시 문 앞에 놓아주세요",
            "payment_method": "우리카드 1234 / 일시불",
            "items": order_items[0],
        },
        {
            "order_id": "TT-20260318-0841",
            "status_code": "completed",
            "created_at": "2026.03.18",
            "status": "배송 완료",
            "status_class": "bg-[#dcfce7] text-[#15803d]",
            "can_reorder": True,
            "detail_hint": "배송이 완료된 주문입니다\n필요한 상품은 다시 주문할 수 있어요",
            "cta_label": "다시 담기",
            "recipient": "왈냥",
            "recipient_phone": "010-1234-5678",
            "delivery_address": "서울 강동구 올림픽로 123, 101동 1203호",
            "total_price": _format_price(order_totals[1]),
            "delivery_message": "배송이 완료되었습니다",
            "payment_method": "카카오페이 / 일시불",
            "items": order_items[1],
        },
        {
            "order_id": "TT-20260310-2217",
            "status_code": "cancelled",
            "created_at": "2026.03.10",
            "status": "주문 취소",
            "status_class": "bg-[#fee2e2] text-[#dc2626]",
            "can_reorder": False,
            "detail_hint": "취소된 주문입니다\n결제와 배송 정보를 확인해 주세요",
            "cta_label": "주문 정보 확인",
            "recipient": "왈냥",
            "recipient_phone": "010-1234-5678",
            "delivery_address": "서울 강동구 올림픽로 123, 101동 1203호",
            "total_price": _format_price(order_totals[2]),
            "delivery_message": "단순 변심으로 주문이 취소되었습니다",
            "payment_method": "네이버페이 / 일시불",
            "items": order_items[2],
        },
    ]


@login_required
def order_list(request):
    options = _parse_order_list_options(request)
    demo_mode = _is_demo_mode(request)

    if demo_mode:
        demo_orders = _filter_demo_order_groups(_order_groups(), options)
        paginator = Paginator(demo_orders, DEFAULT_ORDER_PAGE_SIZE)
        page_obj = paginator.get_page(options["page"])
        orders = list(page_obj.object_list)
    else:
        order_queryset = Order.objects.filter(user=request.user).prefetch_related("items__product")
        if options["status_filter"] != "all":
            order_queryset = order_queryset.filter(status=options["status_filter"])
        order_queryset = order_queryset.order_by(ORDER_LIST_ORDERING[options["ordering_key"]]["queryset"])

        paginator = Paginator(order_queryset, DEFAULT_ORDER_PAGE_SIZE)
        page_obj = paginator.get_page(options["page"])
        orders = [_serialize_order_group(order) for order in page_obj.object_list]

    filter_options = [
        {
            "code": "all",
            "label": "전체",
            "is_active": options["status_filter"] == "all",
            "query": _build_order_list_query_with_demo("all", options["ordering_key"], demo_mode=demo_mode),
        }
    ]
    filter_options.extend(
        {
            "code": code,
            "label": meta["label"],
            "is_active": options["status_filter"] == code,
            "query": _build_order_list_query_with_demo(code, options["ordering_key"], demo_mode=demo_mode),
        }
        for code, meta in ORDER_STATUS_VIEW_META.items()
    )
    ordering_options = [
        {
            "code": key,
            "label": meta["label"],
            "is_active": options["ordering_key"] == key,
            "query": _build_order_list_query_with_demo(options["status_filter"], key, demo_mode=demo_mode),
        }
        for key, meta in ORDER_LIST_ORDERING.items()
    ]

    pagination_links = []
    if paginator.num_pages > 1:
        start_page = max(page_obj.number - 2, 1)
        end_page = min(start_page + 4, paginator.num_pages)
        start_page = max(end_page - 4, 1)
        for number in range(start_page, end_page + 1):
            pagination_links.append(
                {
                    "number": number,
                    "is_active": page_obj.number == number,
                    "query": _build_order_list_query_with_demo(
                        options["status_filter"],
                        options["ordering_key"],
                        page=number,
                        demo_mode=demo_mode,
                    ),
                }
            )

    return render(
        request,
        "orders/list.html",
        {
            "order_groups": orders,
            "order_count": paginator.count,
            "active_tab": "orders",
            "order_filter_options": filter_options,
            "order_ordering_options": ordering_options,
            "order_page_obj": page_obj,
            "order_pagination_links": pagination_links,
            "order_current_status": options["status_filter"],
            "order_current_ordering": options["ordering_key"],
            "order_demo_mode": demo_mode,
            **_member_nav_indicator_state(request.user),
        },
    )


@login_required
def used_products(request):
    if (request.GET.get("tab") or "").strip().lower() == "wishlist":
        return redirect("wishlist_products")

    return _render_used_products(request, active_tab="cart")


@login_required
def wishlist_products(request):
    return _render_used_products(request, active_tab="wishlist")


@login_required
def checkout(request):
    selected_items_query = (request.GET.get("items") or "").strip()
    selected_goods_ids = [item.strip() for item in selected_items_query.split(",") if item.strip()]
    context = _build_products_page_context(
        request.user,
        active_tab="cart",
        selected_goods_ids=selected_goods_ids or None,
    )
    if context["item_count"] == 0:
        return redirect("used_products")
    return render(request, "orders/checkout.html", context)


def _build_products_page_context(user, *, active_tab, selected_goods_ids=None):
    items, wishlist_items = _load_user_product_panels(user)
    if selected_goods_ids is not None:
        selected_goods_ids = {str(goods_id).strip() for goods_id in selected_goods_ids if str(goods_id).strip()}
        items = [item for item in items if str(item["goods_id"]) in selected_goods_ids]

    product_total = sum(item["price"] * item["quantity"] for item in items)
    discount = 0
    shipping_fee = 0 if product_total >= 30000 else 3000
    final_total = product_total - discount + shipping_fee
    profile = getattr(user, "profile", None)
    recipient_name = getattr(profile, "nickname", "") or user.email.split("@")[0] or "주문자 정보 미등록"
    address = getattr(profile, "address", "") or ""
    address_parts = [part.strip() for part in address.split("|", 1)] if address else []
    base_address = address_parts[0] if address_parts else "배송지 정보가 아직 등록되지 않았어요"
    detail_address = address_parts[1] if len(address_parts) > 1 else ""
    phone = getattr(profile, "phone", "") or "연락처 정보가 아직 없습니다."
    postal_code = getattr(profile, "postal_code", "") or ""
    payment_method = getattr(profile, "payment_method", "") or "결제 수단 정보가 아직 없습니다."
    for item in items:
        item["price_label"] = _format_price(item["price"])
        item["line_total_label"] = _format_price(item["price"] * item["quantity"])
    for item in wishlist_items:
        item["price_label"] = _format_price(item["price"])

    return {
        "cart_items": items,
        "wishlist_items": wishlist_items,
        "item_count": sum(item["quantity"] for item in items),
        "wishlist_count": len(wishlist_items),
        "product_total": _format_price(product_total),
        "product_total_raw": product_total,
        "discount_total": _format_price(discount),
        "shipping_fee": "무료" if shipping_fee == 0 else _format_price(shipping_fee),
        "final_total": _format_price(final_total),
        "recipient_name": recipient_name,
        "delivery_base_address": base_address,
        "delivery_detail_address": detail_address,
        "recipient_phone": phone,
        "delivery_postal_code": postal_code,
        "delivery_message": "",
        "payment_method": payment_method,
        "coupon_summary": "적용된 쿠폰 없음",
        "mileage_summary": "사용 가능 3,200원",
        "discount_total_raw": discount,
        "shipping_fee_raw": shipping_fee,
        "active_tab": active_tab,
        **_member_nav_indicator_state(user),
    }


def _render_used_products(request, *, active_tab):
    return render(
        request,
        "orders/products.html",
        _build_products_page_context(request.user, active_tab=active_tab),
    )


@login_required
def catalog(request):
    keyword = (request.GET.get("q") or "").strip()[:50]
    pet = (request.GET.get("pet") or "").strip()
    category = (request.GET.get("category") or "").strip()
    subcategory = (request.GET.get("subcategory") or "").strip()
    brand = (request.GET.get("brand") or "").strip()
    session_id = (request.GET.get("session") or "").strip()
    sort_key = (request.GET.get("sort") or "tailtalk").strip()
    if sort_key not in CATALOG_SORT_OPTIONS:
        sort_key = "tailtalk"

    base_queryset = Product.objects.filter(soldout_yn=False)
    queryset = base_queryset
    if keyword:
        queryset = queryset.filter(Q(goods_name__icontains=keyword) | Q(brand_name__icontains=keyword))
    if pet:
        queryset = queryset.filter(pet_type__contains=[pet])
    if category:
        queryset = queryset.filter(category__contains=[category])
    if subcategory:
        queryset = queryset.filter(subcategory__contains=[subcategory])
    if brand:
        queryset = queryset.filter(brand_name=brand)

    brand_queryset = base_queryset
    if keyword:
        brand_queryset = brand_queryset.filter(Q(goods_name__icontains=keyword) | Q(brand_name__icontains=keyword))
    if pet:
        brand_queryset = brand_queryset.filter(pet_type__contains=[pet])
    if category:
        brand_queryset = brand_queryset.filter(category__contains=[category])
    if subcategory:
        brand_queryset = brand_queryset.filter(subcategory__contains=[subcategory])

    brand_values = sorted(
        [
        value
        for value in brand_queryset.order_by("brand_name").values_list("brand_name", flat=True).distinct()
        if value
        ],
        key=_catalog_brand_sort_key,
    )
    visible_brand_values = brand_values[:10]
    if brand and brand in brand_values and brand not in visible_brand_values:
        visible_brand_values.append(brand)
    hidden_brand_values = [value for value in brand_values if value not in visible_brand_values]

    queryset = _with_catalog_sort_fields(queryset).order_by(*CATALOG_SORT_OPTIONS[sort_key]["ordering"])
    paginator = Paginator(queryset, DEFAULT_CATALOG_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page") or 1)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    wishlist, _ = Wishlist.objects.get_or_create(user=request.user)
    wishlist_product_ids = set(wishlist.items.values_list("product_id", flat=True))
    cart_quantities = {
        product_id: quantity
        for product_id, quantity in cart.items.values_list("product_id", "quantity")
    }

    current_params = {
        "q": keyword,
        "pet": pet,
        "category": category,
        "subcategory": subcategory,
        "brand": brand,
        "session": session_id,
        "sort": sort_key,
        "page": request.GET.get("page") or "",
    }
    catalog_menu_sections = build_catalog_menu_context()
    selected_pet_section = next((section for section in catalog_menu_sections if section["label"] == pet), None)
    selected_category = None
    if selected_pet_section and category:
        selected_category = next(
            (
                item
                for item in selected_pet_section["categories"]
                if item["label"] == category or _query_value_from_href(item["href"], "category") == category
            ),
            None,
        )
        if selected_category is None:
            selected_category = next(
                (
                    item
                    for item in selected_pet_section["categories"]
                    if any(
                        _href_query_matches(entry["href"], current_params)
                        for group in item.get("groups", [])
                        for entry in group.get("items", [])
                    )
                ),
                None,
            )

    pagination_links = []
    if paginator.num_pages > 1:
        start_page = max(page_obj.number - 2, 1)
        end_page = min(start_page + 4, paginator.num_pages)
        start_page = max(end_page - 4, 1)
        for number in range(start_page, end_page + 1):
            pagination_links.append(
                {
                    "number": number,
                    "is_active": page_obj.number == number,
                    "query": _catalog_querystring(current_params, page=number),
                }
            )

    recommended_session = None
    recommended_items = []
    if session_id:
        recommended_session = (
            ChatSession.objects.filter(session_id=session_id, user=request.user)
            .prefetch_related("messages__recommended_products__product")
            .first()
        )
        if recommended_session:
            latest_recommendation_message = next(
                (
                    message
                    for message in recommended_session.messages.order_by("-created_at")
                    if hasattr(message, "recommended_products") and message.recommended_products.exists()
                ),
                None,
            )
            if latest_recommendation_message is not None:
                recommended_items = [
                    _serialize_recommendation_item(
                        recommendation,
                        is_wishlisted=recommendation.product_id in wishlist_product_ids,
                        cart_quantity=cart_quantities.get(recommendation.product_id, 0),
                    )
                    for recommendation in latest_recommendation_message.recommended_products.select_related("product").order_by("rank_order", "created_at")
                ]

    context = {
        "catalog_items": [
            _serialize_catalog_item(
                product,
                is_wishlisted=product.goods_id in wishlist_product_ids,
                cart_quantity=cart_quantities.get(product.goods_id, 0),
            )
            for product in page_obj.object_list
        ],
        "catalog_count": paginator.count,
        "catalog_page_obj": page_obj,
        "catalog_pagination_links": pagination_links,
        "catalog_prev_query": _catalog_querystring(current_params, page=page_obj.previous_page_number()) if page_obj.has_previous() else "",
        "catalog_next_query": _catalog_querystring(current_params, page=page_obj.next_page_number()) if page_obj.has_next() else "",
        "catalog_current_keyword": keyword,
        "catalog_current_pet": pet,
        "catalog_current_category": category,
        "catalog_current_subcategory": subcategory,
        "catalog_current_brand": brand,
        "catalog_current_sort": sort_key,
        "catalog_sort_options": [
            {
                "key": key,
                "label": option["label"],
                "is_active": key == sort_key,
                "query": _catalog_querystring(current_params, sort=key, page=None),
            }
            for key, option in CATALOG_SORT_OPTIONS.items()
        ],
        "catalog_menu_sections": [
            {
                **section,
                "is_active": section["label"] == pet,
            }
            for section in catalog_menu_sections
        ],
        "catalog_category_options": [
            {
                **item,
                "is_active": item["label"] == category,
            }
            for item in (selected_pet_section["categories"] if selected_pet_section else [])
        ],
        "catalog_group_options": [
            {
                "label": group["label"],
                "items": [
                    {
                        **entry,
                        "is_active": _href_query_matches(
                            entry["href"],
                            current_params,
                            keys=("pet", "category", "subcategory"),
                        ),
                    }
                    for entry in group["items"]
                ],
            }
            for group in (selected_category["groups"] if selected_category else [])
        ],
        "catalog_brand_options": [
            {
                "label": value,
                "href": f"/catalog/{('?' + _catalog_querystring(current_params, brand=value, page=None)) if _catalog_querystring(current_params, brand=value, page=None) else ''}",
                "is_active": value == brand,
            }
            for value in visible_brand_values
        ],
        "catalog_brand_hidden_options": [
            {
                "label": value,
                "href": f"/catalog/{('?' + _catalog_querystring(current_params, brand=value, page=None)) if _catalog_querystring(current_params, brand=value, page=None) else ''}",
                "is_active": value == brand,
            }
            for value in hidden_brand_values
        ],
        "catalog_filter_tree": _build_catalog_filter_tree(catalog_menu_sections),
        "catalog_query_all": _catalog_querystring(current_params, page=None),
        "catalog_clear_category_query": _catalog_querystring(current_params, category=None, subcategory=None, brand=None, page=None),
        "catalog_clear_detail_query": _catalog_querystring(current_params, subcategory=None, brand=None, page=None),
        "catalog_clear_brand_query": _catalog_querystring(current_params, brand=None, page=None),
        "catalog_current_session_id": session_id,
        "catalog_recommended_session": recommended_session,
        "catalog_recommended_items": recommended_items,
        **_member_nav_indicator_state(request.user),
    }
    return render(request, "orders/catalog.html", context)


@login_required
def order_complete(request, order_id):
    order = get_object_or_404(
        Order.objects.filter(user=request.user).prefetch_related("items__product"),
        order_id=order_id,
    )
    entry = (request.GET.get("entry") or "cart").strip().lower()
    if entry not in {"cart", "quick"}:
        entry = "cart"

    return render(
        request,
        "orders/complete.html",
        {
            "active_tab": "orders",
            "order_completion": _serialize_order_completion(order),
            "order_entry": entry,
            **_member_nav_indicator_state(request.user),
        },
    )
