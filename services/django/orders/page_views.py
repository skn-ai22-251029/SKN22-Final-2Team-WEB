from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

from products.models import Product
from .models import Cart, Order, Wishlist


def _format_price(value):
    return f"{value:,}원"


def _product_summary(product):
    pet_type = ", ".join(product.pet_type[:2]) if product.pet_type else "반려동물 공용"
    category = product.subcategory[0] if product.subcategory else (product.category[0] if product.category else "기타")
    return f"{pet_type} · {category}"


def _display_product_name(brand_name, goods_name):
    if not goods_name:
        return ""

    normalized_brand = (brand_name or "").strip()
    normalized_name = goods_name.strip()

    if normalized_brand and normalized_name.lower().startswith(normalized_brand.lower()):
        trimmed = normalized_name[len(normalized_brand):].lstrip(" -_/|")
        if trimmed:
            return trimmed

    return normalized_name


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


def _recommended_note(index):
    notes = [
        "최근 상담 키워드와 잘 맞는 후보",
        "재구매 후보로 저장된 상품",
        "가격 비교를 위해 보관한 상품",
    ]
    return notes[index % len(notes)]


ORDER_STATUS_VIEW_META = {
    "pending": {
        "label": "주문 접수",
        "class": "bg-[#fef3c7] text-[#b45309]",
        "can_reorder": True,
        "detail_hint": "상품 준비가 시작되면\n배송 상태가 업데이트됩니다",
        "cta_label": "같은 구성 다시 담기",
    },
    "shipping": {
        "label": "배송 중",
        "class": "bg-[#dbeafe] text-[#2563eb]",
        "can_reorder": True,
        "detail_hint": "상품이 배송 중입니다\n필요한 구성은 다시 주문할 수 있어요",
        "cta_label": "같은 구성 다시 담기",
    },
    "completed": {
        "label": "배송 완료",
        "class": "bg-[#dcfce7] text-[#15803d]",
        "can_reorder": True,
        "detail_hint": "배송이 완료된 주문입니다. 필요한 상품은 다시 주문할 수 있어요.",
        "cta_label": "다시 주문하기",
    },
    "cancelled": {
        "label": "주문 취소",
        "class": "bg-[#fee2e2] text-[#dc2626]",
        "can_reorder": False,
        "detail_hint": "취소된 주문입니다. 결제와 배송 정보를 확인해 주세요.",
        "cta_label": "주문 정보 확인",
    },
}

ORDER_LIST_ORDERING = {
    "latest": {"label": "최신순", "queryset": "-created_at"},
    "oldest": {"label": "오래된순", "queryset": "created_at"},
}
DEFAULT_ORDER_PAGE_SIZE = 12


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
            "cta_label": "같은 구성 다시 담기",
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
            "detail_hint": "배송이 완료된 주문입니다. 필요한 상품은 다시 주문할 수 있어요.",
            "cta_label": "다시 주문하기",
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
            "detail_hint": "취소된 주문입니다. 결제와 배송 정보를 확인해 주세요.",
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
        },
    )


@login_required
def used_products(request):
    items, wishlist_items = _load_user_product_panels(request.user)
    product_total = sum(item["price"] * item["quantity"] for item in items)
    discount = 0
    shipping_fee = 0 if product_total >= 30000 else 3000
    final_total = product_total - discount + shipping_fee
    profile = getattr(request.user, "profile", None)
    recipient_name = getattr(profile, "nickname", "") or request.user.username or "주문자 정보 미등록"
    address = getattr(profile, "address", "") or ""
    address_parts = [part.strip() for part in address.split("|", 1)] if address else []
    base_address = address_parts[0] if address_parts else "배송지 정보가 아직 등록되지 않았어요"
    detail_address = address_parts[1] if len(address_parts) > 1 else ""
    phone = getattr(profile, "phone", "") or "연락처 정보가 아직 없습니다."
    for item in items:
        item["price_label"] = _format_price(item["price"])
        item["line_total_label"] = _format_price(item["price"] * item["quantity"])
    for item in wishlist_items:
        item["price_label"] = _format_price(item["price"])

    return render(
        request,
        "orders/products.html",
        {
            "cart_items": items,
            "wishlist_items": wishlist_items,
            "item_count": sum(item["quantity"] for item in items),
            "wishlist_count": len(wishlist_items),
            "product_total": _format_price(product_total),
            "discount_total": _format_price(discount),
            "shipping_fee": "무료" if shipping_fee == 0 else _format_price(shipping_fee),
            "final_total": _format_price(final_total),
            "recipient_name": recipient_name,
            "delivery_base_address": base_address,
            "delivery_detail_address": detail_address,
            "recipient_phone": phone,
            "delivery_message": "",
            "payment_method": "우리카드 1234 / 일시불",
            "coupon_summary": "적용된 쿠폰 없음",
            "mileage_summary": "사용 가능 3,200원",
            "discount_total_raw": discount,
            "shipping_fee_raw": shipping_fee,
            "active_tab": "cart",
        },
    )
