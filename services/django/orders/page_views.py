from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q

from products.models import Product


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


def _recommended_note(index):
    notes = [
        "최근 상담 키워드와 잘 맞는 후보",
        "재구매 후보로 저장된 상품",
        "가격 비교를 위해 보관한 상품",
    ]
    return notes[index % len(notes)]


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

    return query.order_by("-review_count", "-discount_price", "goods_id")


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

    cart_items = []
    wishlist_items = []
    for index, product in enumerate(selected_products[:5]):
        cart_items.append(
            {
                "goods_id": product.goods_id,
                "thumbnail_url": product.thumbnail_url,
                "brand": product.brand_name,
                "name": _display_product_name(product.brand_name, product.goods_name),
                "summary": _product_summary(product),
                "price": product.discount_price or product.price,
                "rating": product.rating,
                "review_count": product.review_count,
                "quantity": (index % 3) + 1,
            }
        )

    for index, product in enumerate(selected_products[5:9]):
        wishlist_items.append(
            {
                "goods_id": product.goods_id,
                "thumbnail_url": product.thumbnail_url,
                "brand": product.brand_name,
                "name": _display_product_name(product.brand_name, product.goods_name),
                "summary": _product_summary(product),
                "price": product.discount_price or product.price,
                "rating": product.rating,
                "review_count": product.review_count,
                "note": _recommended_note(index),
            }
        )

    return cart_items, wishlist_items


def _order_groups():
    return [
        {
            "order_id": "TT-20260325-1024",
            "created_at": "2026.03.25",
            "status": "배송 중",
            "status_class": "bg-[#dbeafe] text-[#2563eb]",
            "recipient": "황하령",
            "total_price": _format_price(65700),
            "delivery_message": "부재 시 문 앞에 놓아주세요",
            "items": [
                {
                    "emoji": "🐟",
                    "name": "닥터독 하이포알러지 연어 사료",
                    "summary": "2kg · 1개",
                    "price": _format_price(39800),
                },
                {
                    "emoji": "👀",
                    "name": "베러펫 눈물 케어 영양제",
                    "summary": "30일분 · 1개",
                    "price": _format_price(25900),
                },
            ],
        },
        {
            "order_id": "TT-20260318-0841",
            "created_at": "2026.03.18",
            "status": "배송 완료",
            "status_class": "bg-[#dcfce7] text-[#15803d]",
            "recipient": "황하령",
            "total_price": _format_price(31200),
            "delivery_message": "배송이 완료되었습니다",
            "items": [
                {
                    "emoji": "🦴",
                    "name": "벨버드 덴탈 케어 껌",
                    "summary": "30개입 · 2개",
                    "price": _format_price(25800),
                },
                {
                    "emoji": "🛁",
                    "name": "저자극 샴푸",
                    "summary": "민감 피부용 · 1개",
                    "price": _format_price(5400),
                },
            ],
        },
        {
            "order_id": "TT-20260310-2217",
            "created_at": "2026.03.10",
            "status": "주문 접수",
            "status_class": "bg-[#fef3c7] text-[#b45309]",
            "recipient": "황하령",
            "total_price": _format_price(18400),
            "delivery_message": "결제 확인 후 출고 준비 중입니다",
            "items": [
                {
                    "emoji": "🍗",
                    "name": "동결건조 치킨 트릿",
                    "summary": "80g · 1개",
                    "price": _format_price(18400),
                },
            ],
        },
    ]


@login_required
def order_list(request):
    orders = _order_groups()
    return render(
        request,
        "orders/list.html",
        {
            "order_groups": orders,
            "order_count": len(orders),
            "active_tab": "orders",
        },
    )


@login_required
def used_products(request):
    items, wishlist_items = _load_product_panels()
    product_total = sum(item["price"] * item["quantity"] for item in items)
    discount = 5400
    shipping_fee = 0 if product_total >= 30000 else 3000
    final_total = product_total - discount + shipping_fee
    profile = getattr(request.user, "profile", None)
    recipient_name = getattr(profile, "nickname", "") or request.user.username or "주문자 정보 미등록"
    address = getattr(profile, "address", "") or "기본 배송지가 아직 등록되지 않았습니다."
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
            "delivery_address": address,
            "recipient_phone": phone,
            "payment_method": "우리카드 1234 / 일시불",
            "coupon_summary": "적용 가능한 쿠폰 2장",
            "mileage_summary": "사용 가능 3,200원",
            "discount_total_raw": discount,
            "shipping_fee_raw": shipping_fee,
            "active_tab": "cart",
        },
    )
