from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.db.models import Avg, Count, F, IntegerField, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from orders.models import OrderItem, UserInteraction
from products.catalog_menu import build_catalog_menu_context
from products.models import Product
from products.review_metrics import (
    get_actual_rating_label,
    get_actual_review_count,
    normalize_rating_label,
    with_actual_review_metrics,
)

VENDOR_ADMIN_SESSION_KEY = "tailtalk_vendor_admin_id"
DEMO_VENDOR_ACCOUNTS = {
    "orijen": {
        "password": "tailtalk2026!",
        "brand_name": "오리젠",
        "display_name": "오리젠",
    }
}
VENDOR_PRODUCT_SORT_OPTIONS = {
    "default": {
        "label": "최신 등록순",
        "description": "최근 수집된 상품부터 정렬합니다",
    },
    "reviews": {
        "label": "리뷰 많은순",
        "description": "리뷰 수가 많은 상품 순으로 정렬합니다",
    },
    "price_low": {
        "label": "가격 낮은순",
        "description": "판매가가 낮은 상품부터 정렬합니다",
    },
    "price_high": {
        "label": "가격 높은순",
        "description": "판매가가 높은 상품부터 정렬합니다",
    },
    "rating_high": {
        "label": "평점 높은순",
        "description": "평점이 높은 상품부터 정렬합니다",
    },
}
VENDOR_ORDER_FOCUS_OPTIONS = (
    ("all", "전체"),
    ("processing", "주문 접수"),
    ("packing", "출고 준비"),
    ("refund", "취소/환불"),
    ("delayed", "배송 지연"),
)


def _normalize_vendor_login_id(value):
    return (value or "").strip().lower()


def _get_vendor_account(login_id):
    normalized_id = _normalize_vendor_login_id(login_id)
    account = DEMO_VENDOR_ACCOUNTS.get(normalized_id)
    if not account:
        return None
    return {
        "login_id": normalized_id,
        **account,
    }


def _get_active_vendor_account(request):
    return _get_vendor_account(request.session.get(VENDOR_ADMIN_SESSION_KEY))


def _format_vendor_price(value):
    if value is None:
        return "-"

    try:
        normalized = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return "-"

    return f"{int(normalized):,}원"


def _format_vendor_rating(value):
    return normalize_rating_label(value) or "-"


def _format_vendor_metric(value, digits=2):
    if value is None:
        return "-"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def _format_vendor_percent(value, digits=1):
    if value is None:
        return "-"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "-"


def _get_demo_soldout_goods_ids(vendor_products, minimum_count=4):
    soldout_ids = list(vendor_products.filter(soldout_yn=True).values_list("goods_id", flat=True))
    if len(soldout_ids) >= minimum_count:
        return set(soldout_ids)

    remaining_queryset = vendor_products.exclude(goods_id__in=soldout_ids).order_by("goods_name")
    remaining_ids = list(remaining_queryset.values_list("goods_id", flat=True))
    if not remaining_ids:
        return set(soldout_ids)

    fallback_count = max(minimum_count - len(soldout_ids), 0)
    start_index = max((len(remaining_ids) // 2) - (fallback_count // 2), 0)
    fallback_ids = remaining_ids[start_index : start_index + fallback_count]

    if len(fallback_ids) < fallback_count:
        fallback_ids.extend(remaining_ids[: fallback_count - len(fallback_ids)])

    return set(soldout_ids + fallback_ids)


def _get_demo_pending_goods_ids(vendor_products, excluded_goods_ids=None, minimum_count=3):
    excluded_goods_ids = set(excluded_goods_ids or [])
    candidate_ids = list(
        vendor_products.exclude(goods_id__in=excluded_goods_ids).order_by("goods_name").values_list("goods_id", flat=True)
    )
    if not candidate_ids:
        return set()

    start_index = max((len(candidate_ids) // 3) - (minimum_count // 2), 0)
    pending_ids = candidate_ids[start_index : start_index + minimum_count]
    if len(pending_ids) < minimum_count:
        pending_ids.extend(candidate_ids[: minimum_count - len(pending_ids)])
    return set(pending_ids)


def _serialize_vendor_product(product, demo_soldout_goods_ids=None, demo_pending_goods_ids=None):
    is_demo_soldout = bool(demo_soldout_goods_ids and product.goods_id in demo_soldout_goods_ids)
    is_demo_pending = bool(
        not is_demo_soldout and demo_pending_goods_ids and product.goods_id in demo_pending_goods_ids
    )
    price_value = None
    if product.discount_price is not None:
        price_value = Decimal(product.discount_price)
    elif product.price is not None:
        price_value = Decimal(product.price)
    discount_rate_label = None
    if product.price and product.discount_price and product.price > 0 and product.discount_price < product.price:
        discount_rate = int(round((1 - (Decimal(product.discount_price) / Decimal(product.price))) * 100))
        discount_rate_label = f"{discount_rate}%"
    return {
        "goods_id": product.goods_id,
        "goods_name": product.goods_name,
        "brand_name": product.brand_name,
        "thumbnail_url": product.thumbnail_url,
        "product_url": product.product_url,
        "detail_url": reverse("vendor-product-detail", args=[product.goods_id]),
        "edit_url": reverse("vendor-product-edit", args=[product.goods_id]),
        "crawled_at": product.crawled_at,
        "price_label": _format_vendor_price(product.price),
        "discount_price_label": _format_vendor_price(product.discount_price),
        "discount_price_value": price_value,
        "discount_rate_label": discount_rate_label,
        "rating_label": get_actual_rating_label(product) or "-",
        "review_count": get_actual_review_count(product),
        "soldout": product.soldout_yn or is_demo_soldout,
        "pending": is_demo_pending,
        "status_label": "품절" if (product.soldout_yn or is_demo_soldout) else ("준비중" if is_demo_pending else "판매중"),
        "pet_type_label": ", ".join(product.pet_type) if product.pet_type else "미분류",
        "category_label": " · ".join(product.category) if product.category else "카테고리 미지정",
    }


def _apply_demo_registered_dates(products):
    base_date = date(2026, 3, 31)
    for index, product in enumerate(products):
        product["registered_date_label"] = (base_date - timedelta(days=index % 6)).strftime("%Y.%m.%d")
    return products


def _get_vendor_product_registered_date_label(product):
    if product.crawled_at:
        return product.crawled_at.strftime("%Y.%m.%d")
    return "-"


def _get_vendor_product_status_tone(serialized_product):
    if serialized_product["soldout"]:
        return "rose"
    if serialized_product["pending"]:
        return "amber"
    return "green"


def _normalize_vendor_tokens(value):
    tokens = []

    if isinstance(value, dict):
        for key, item in value.items():
            key_label = str(key).strip()
            if not key_label:
                continue
            if isinstance(item, (list, tuple)):
                item_values = [str(entry).strip() for entry in item if str(entry).strip()]
                detail = ", ".join(item_values[:2])
                tokens.append(f"{key_label}: {detail}" if detail else key_label)
            elif item in (None, "", [], {}):
                tokens.append(key_label)
            else:
                tokens.append(f"{key_label}: {item}")
    elif isinstance(value, (list, tuple)):
        tokens = [str(item).strip() for item in value if str(item).strip()]
    elif value:
        tokens = [str(value).strip()]

    return tokens[:8]


def _build_vendor_product_detail_context(product, serialized_product):
    status_tone = _get_vendor_product_status_tone(serialized_product)
    price_gap = None
    if product.price is not None and product.discount_price is not None:
        price_gap = max(product.price - product.discount_price, 0)

    category_segments = list(product.category or [])
    subcategory_segments = list(product.subcategory or [])
    ingredient_tokens = _normalize_vendor_tokens(product.main_ingredients)
    health_tags = [str(tag).strip() for tag in (product.health_concern_tags or []) if str(tag).strip()]
    health_tag_preview = health_tags[:3]
    ingredient_token_preview = ingredient_tokens[:3]

    detail_highlights = [
        {
            "label": "실판매가",
            "value": serialized_product["discount_price_label"],
        },
        {
            "label": "할인율",
            "value": serialized_product["discount_rate_label"] or "할인 없음",
        },
        {
            "label": "리뷰 / 평점",
            "value": f"{serialized_product['review_count']:,}개 / {serialized_product['rating_label']}",
        },
        {
            "label": "추천 점수",
            "value": _format_vendor_metric(product.popularity_score, 2),
        },
    ]

    detail_signals = [
        {
            "label": "반복 구매율",
            "value": _format_vendor_percent(product.repeat_rate, 1),
        },
        {
            "label": "리뷰 정서",
            "value": _format_vendor_percent(product.sentiment_avg, 1),
        },
        {
            "label": "기호성",
            "value": _format_vendor_metric(product.aspect_palatability, 2),
        },
        {
            "label": "배송/포장",
            "value": _format_vendor_metric(product.aspect_delivery_packaging, 2),
        },
        {
            "label": "가격 반응",
            "value": _format_vendor_metric(product.aspect_price_purchase, 2),
        },
    ]

    info_rows = [
        {"label": "상품 ID", "value": product.goods_id},
        {"label": "브랜드", "value": product.brand_name},
        {"label": "등록일", "value": _get_vendor_product_registered_date_label(product)},
        {"label": "카테고리", "value": serialized_product["category_label"]},
        {"label": "세부 분류", "value": " · ".join(subcategory_segments) if subcategory_segments else "-"},
        {"label": "정가", "value": serialized_product["price_label"]},
    ]

    action_links = [
        {
            "label": "상품 수정",
            "href": reverse("vendor-product-edit", args=[product.goods_id]),
            "tone": "primary",
            "external": False,
        },
        {
            "label": "리뷰 관리",
            "href": f"{reverse('vendor-reviews')}?focus=pending",
            "tone": "secondary",
            "external": False,
        },
        {
            "label": "주문 관리",
            "href": f"{reverse('vendor-orders')}?focus=processing",
            "tone": "secondary",
            "external": False,
        },
    ]

    checkpoint_rows = [
        {
            "title": "가격/할인 점검",
            "status": "확인 필요" if price_gap and float(product.aspect_price_purchase or 0) < 0.6 else "안정",
        },
        {
            "title": "재고/노출 상태",
            "status": "품절 대응" if serialized_product["soldout"] else ("등록 검수" if serialized_product["pending"] else "판매중"),
        },
        {
            "title": "리뷰 대응",
            "status": "우선 확인" if serialized_product["review_count"] >= 100 else "모니터링",
        },
    ]

    return {
        "vendor_product_status_tone": status_tone,
        "vendor_product_detail_highlights": detail_highlights,
        "vendor_product_detail_signals": detail_signals,
        "vendor_product_info_rows": info_rows,
        "vendor_product_action_links": action_links,
        "vendor_product_checkpoint_rows": checkpoint_rows,
        "vendor_product_health_tags": health_tags,
        "vendor_product_health_tag_preview": health_tag_preview,
        "vendor_product_health_tag_overflow_count": max(len(health_tags) - len(health_tag_preview), 0),
        "vendor_product_ingredient_tokens": ingredient_tokens,
        "vendor_product_ingredient_token_preview": ingredient_token_preview,
        "vendor_product_ingredient_token_overflow_count": max(len(ingredient_tokens) - len(ingredient_token_preview), 0),
        "vendor_product_subcategory_label": " · ".join(subcategory_segments) if subcategory_segments else "-",
        "vendor_product_category_path": " · ".join(category_segments) if category_segments else "카테고리 미지정",
        "vendor_product_registered_date_label": _get_vendor_product_registered_date_label(product),
    }


def _sort_vendor_products(products, sort_key):
    if sort_key == "reviews":
        products.sort(
            key=lambda product: (
                -product["review_count"],
                -(float(product["rating_label"]) if product["rating_label"] != "-" else 0.0),
                product["goods_name"],
            )
        )
        return

    if sort_key == "price_low":
        products.sort(
            key=lambda product: (
                product["discount_price_value"] if product["discount_price_value"] is not None else float("inf"),
                -product["review_count"],
                product["goods_name"],
            )
        )
        return

    if sort_key == "price_high":
        products.sort(
            key=lambda product: (
                -(product["discount_price_value"] if product["discount_price_value"] is not None else -1),
                -product["review_count"],
                product["goods_name"],
            )
        )
        return

    if sort_key == "rating_high":
        products.sort(
            key=lambda product: (
                -(float(product["rating_label"]) if product["rating_label"] != "-" else 0.0),
                -product["review_count"],
                product["goods_name"],
            )
        )
        return

    products.sort(
        key=lambda product: (
            -(product["crawled_at"].timestamp() if product["crawled_at"] else 0),
            product["goods_name"],
        )
    )


def _build_vendor_breakdown_items(counter):
    total = sum(counter.values())
    items = []
    for label, count in counter.most_common(4):
        share = round((count / total) * 100, 1) if total else 0
        items.append(
            {
                "label": label,
                "count_label": f"{count:,}개",
                "share_label": f"{share:.1f}%" if share % 1 else f"{int(share)}%",
                "share_percent": share if count else 0,
            }
        )
    return items


def _pick_vendor_performance_strength(ctr, conversion, repeat_rate):
    candidates = [
        ("CTR 우수", "blue", ctr / 6 if ctr else 0),
        ("전환 안정", "slate", conversion / 10 if conversion else 0),
        ("재구매 강점", "green", repeat_rate / 40 if repeat_rate else 0),
    ]
    return max(candidates, key=lambda item: item[2])[:2]


def _build_vendor_attention_products(vendor_products, demo_soldout_goods_ids, demo_pending_goods_ids):
    attention_items = []
    added_goods_ids = set()

    def append_item(product, issue_label, summary, action_label, tone):
        if product.goods_id in added_goods_ids:
            return

        serialized = _serialize_vendor_product(product, demo_soldout_goods_ids, demo_pending_goods_ids)
        attention_items.append(
            {
                "goods_id": product.goods_id,
                "goods_name": product.goods_name,
                "href": serialized["detail_url"],
                "issue_label": issue_label,
                "summary": summary,
                "action_label": action_label,
                "meta": f"{serialized['category_label']} · 리뷰 {serialized['review_count']:,}개",
                "tone": tone,
            }
        )
        added_goods_ids.add(product.goods_id)

    for product in vendor_products.filter(goods_id__in=demo_soldout_goods_ids).order_by("-_actual_review_count", "goods_name")[:2]:
        append_item(product, "품절", "판매 재개를 위해 재고 또는 대체 노출을 먼저 확인해 주세요.", "재입고 확인", "rose")

    for product in vendor_products.filter(goods_id__in=demo_pending_goods_ids).order_by("-_actual_review_count", "goods_name")[:2]:
        append_item(product, "검수 대기", "상품 정보와 노출 문구를 점검해 판매 상태로 전환할 수 있습니다.", "등록 검수", "amber")

    low_rating_products = vendor_products.exclude(_actual_review_score_avg__isnull=True).filter(_actual_review_count__gte=30).order_by(
        "_actual_review_score_avg", "-_actual_review_count", "goods_name"
    )[:2]
    for product in low_rating_products:
        append_item(product, "리뷰 점검", "평점과 리뷰 반응을 확인해 상세 설명 또는 CS 대응이 필요한 상품입니다.", "리뷰 확인", "blue")

    return attention_items[:4]


def _build_vendor_mock_order_rows(vendor_products, demo_soldout_goods_ids, demo_pending_goods_ids):
    serialized_products = [
        _serialize_vendor_product(product, demo_soldout_goods_ids, demo_pending_goods_ids)
        for product in vendor_products.order_by("-_actual_review_count", "goods_name")[:8]
    ]

    if not serialized_products:
        return []

    blueprints = [
        {
            "focus": "processing",
            "order_number": "TT-260408-1041",
            "ordered_at_label": "2026.04.08 10:41",
            "customer_name": "김하늘",
            "customer_phone": "010-2387-1145",
            "quantity": 1,
            "amount": 72000,
            "payment_status": "결제 완료",
            "next_step": "출고 지시",
            "tone": "blue",
        },
        {
            "focus": "processing",
            "order_number": "TT-260408-1024",
            "ordered_at_label": "2026.04.08 10:24",
            "customer_name": "박도윤",
            "customer_phone": "010-8173-5208",
            "quantity": 2,
            "amount": 118000,
            "payment_status": "결제 완료",
            "next_step": "주문 확인",
            "tone": "blue",
        },
        {
            "focus": "packing",
            "order_number": "TT-260408-0932",
            "ordered_at_label": "2026.04.08 09:32",
            "customer_name": "이서윤",
            "customer_phone": "010-5521-8834",
            "quantity": 1,
            "amount": 86000,
            "payment_status": "출고 준비",
            "next_step": "송장 입력",
            "tone": "amber",
        },
        {
            "focus": "packing",
            "order_number": "TT-260408-0908",
            "ordered_at_label": "2026.04.08 09:08",
            "customer_name": "최민준",
            "customer_phone": "010-2943-6671",
            "quantity": 3,
            "amount": 149000,
            "payment_status": "출고 준비",
            "next_step": "포장 완료",
            "tone": "amber",
        },
        {
            "focus": "refund",
            "order_number": "TT-260407-1825",
            "ordered_at_label": "2026.04.07 18:25",
            "customer_name": "정유진",
            "customer_phone": "010-7312-9844",
            "quantity": 1,
            "amount": 69000,
            "payment_status": "환불 요청",
            "next_step": "사유 확인",
            "tone": "rose",
        },
        {
            "focus": "refund",
            "order_number": "TT-260407-1713",
            "ordered_at_label": "2026.04.07 17:13",
            "customer_name": "송지호",
            "customer_phone": "010-4448-2910",
            "quantity": 1,
            "amount": 54000,
            "payment_status": "취소 요청",
            "next_step": "회수 접수",
            "tone": "rose",
        },
        {
            "focus": "delayed",
            "order_number": "TT-260406-1537",
            "ordered_at_label": "2026.04.06 15:37",
            "customer_name": "윤아린",
            "customer_phone": "010-6128-7730",
            "quantity": 2,
            "amount": 98000,
            "payment_status": "배송 지연",
            "next_step": "고객 안내",
            "tone": "slate",
        },
    ]

    order_rows = []
    for index, blueprint in enumerate(blueprints):
        product = serialized_products[index % len(serialized_products)]
        order_rows.append(
            {
                "focus": blueprint["focus"],
                "order_number": blueprint["order_number"],
                "ordered_at_label": blueprint["ordered_at_label"],
                "customer_name": blueprint["customer_name"],
                "customer_phone": blueprint["customer_phone"],
                "quantity_label": f"{blueprint['quantity']}개",
                "amount_label": _format_vendor_price(blueprint["amount"]),
                "payment_status": blueprint["payment_status"],
                "next_step": blueprint["next_step"],
                "tone": blueprint["tone"],
                "status_label": dict(VENDOR_ORDER_FOCUS_OPTIONS).get(blueprint["focus"], "전체"),
                "product_name": product["goods_name"],
                "product_meta": f"{product['pet_type_label']} · {product['category_label']}",
                "product_thumbnail_url": product["thumbnail_url"],
                "product_detail_url": product["detail_url"],
            }
        )

    return order_rows


def _collect_vendor_product_form_options():
    sections = build_catalog_menu_context()
    pet_type_options = [section["label"] for section in sections]
    pet_category_map = {}
    pet_category_group_map = {}
    pet_category_group_item_map = {}

    for section in sections:
        pet_label = section["label"]
        pet_category_map[pet_label] = []
        pet_category_group_map[pet_label] = {}
        pet_category_group_item_map[pet_label] = {}

        for category in section.get("categories", []):
            category_label = category["label"]
            pet_category_map[pet_label].append(category_label)
            pet_category_group_map[pet_label][category_label] = []
            pet_category_group_item_map[pet_label][category_label] = {}

            for group in category.get("groups", []):
                if category_label == "사료" and group["label"] == "주요 브랜드":
                    continue
                group_label = group["label"]
                pet_category_group_map[pet_label][category_label].append(group_label)
                pet_category_group_item_map[pet_label][category_label][group_label] = [
                    item["label"] for item in group.get("items", [])
                ]

    return {
        "pet_type_options": pet_type_options,
        "pet_category_map": {
            pet_type: values
            for pet_type, values in pet_category_map.items()
        },
        "pet_category_group_map": pet_category_group_map,
        "pet_category_group_item_map": pet_category_group_item_map,
    }


def _build_vendor_navigation(current_view):
    return [
        {
            "label": "대시보드",
            "href": reverse("vendor-dashboard"),
            "active": current_view == "dashboard",
            "disabled": False,
        },
        {
            "label": "상품 목록",
            "href": reverse("vendor-products"),
            "active": current_view == "products",
            "disabled": False,
        },
        {
            "label": "주문 관리",
            "href": reverse("vendor-orders"),
            "active": current_view == "orders",
            "disabled": False,
        },
        {
            "label": "통계",
            "href": reverse("vendor-analytics"),
            "active": current_view == "analytics",
            "disabled": False,
        },
    ]


def _build_vendor_base_context(request, current_view):
    account = _get_active_vendor_account(request)
    if not account:
        return None

    return {
        "vendor_account": account,
        "vendor_navigation": _build_vendor_navigation(current_view),
    }


def vendor_login_view(request):
    if _get_active_vendor_account(request):
        return redirect("vendor-dashboard")

    context = {
        "vendor_login_error": False,
        "vendor_login_id": "",
    }

    if request.method == "POST":
        login_id = request.POST.get("login_id", "")
        password = request.POST.get("password", "")
        account = _get_vendor_account(login_id)
        if not account or password != account["password"]:
            context["vendor_login_error"] = True
            context["vendor_login_id"] = login_id.strip()
            return render(request, "users/vendor_login.html", context)

        request.session[VENDOR_ADMIN_SESSION_KEY] = account["login_id"]
        return redirect("vendor-dashboard")

    return render(request, "users/vendor_login.html", context)


def vendor_logout_view(request):
    request.session.pop(VENDOR_ADMIN_SESSION_KEY, None)
    return redirect("vendor-login")


def vendor_dashboard_view(request):
    base_context = _build_vendor_base_context(request, "dashboard")
    if base_context is None:
        return redirect("vendor-login")

    brand_name = base_context["vendor_account"]["brand_name"]
    vendor_products = with_actual_review_metrics(Product.objects.filter(brand_name=brand_name))
    demo_soldout_goods_ids = _get_demo_soldout_goods_ids(vendor_products)
    demo_pending_goods_ids = _get_demo_pending_goods_ids(vendor_products, demo_soldout_goods_ids)
    total_products = vendor_products.count()
    display_soldout_products = len(demo_soldout_goods_ids)
    display_pending_products = len(demo_pending_goods_ids)
    total_reviews = vendor_products.aggregate(total=Sum("_actual_review_count"))["total"] or 0
    average_rating = vendor_products.exclude(_actual_review_score_avg__isnull=True).aggregate(avg=Avg("_actual_review_score_avg"))["avg"]
    average_repeat_rate = vendor_products.exclude(repeat_rate__isnull=True).aggregate(avg=Avg("repeat_rate"))["avg"]
    average_sentiment = vendor_products.exclude(sentiment_avg__isnull=True).aggregate(avg=Avg("sentiment_avg"))["avg"]
    average_delivery_score = vendor_products.exclude(aspect_delivery_packaging__isnull=True).aggregate(avg=Avg("aspect_delivery_packaging"))["avg"]
    average_price_score = vendor_products.exclude(aspect_price_purchase__isnull=True).aggregate(avg=Avg("aspect_price_purchase"))["avg"]

    pet_type_counter = Counter()
    for types in vendor_products.values_list("pet_type", flat=True):
        for pet_type in types or []:
            pet_type_counter[pet_type] += 1

    category_counter = Counter()
    for categories in vendor_products.values_list("category", flat=True):
        if categories:
            category_counter[categories[0]] += 1

    top_products = [
        _serialize_vendor_product(product, demo_soldout_goods_ids, demo_pending_goods_ids)
        for product in vendor_products.order_by("-_actual_review_count", "-_actual_review_score_avg", "goods_name")[:5]
    ]
    attention_products = _build_vendor_attention_products(vendor_products, demo_soldout_goods_ids, demo_pending_goods_ids)
    active_products = max(total_products - display_soldout_products - display_pending_products, 0)
    brand_order_items = OrderItem.objects.filter(product__brand_name=brand_name)
    active_brand_order_items = brand_order_items.exclude(order__status="cancelled")
    today_date = date.today()
    trend_start_date = today_date - timedelta(days=6)
    today_revenue = (
        active_brand_order_items.filter(order__created_at__date=today_date).aggregate(
            total=Sum(F("quantity") * F("price_at_order"), output_field=IntegerField())
        )["total"]
        or 0
    )
    today_order_count = (
        active_brand_order_items.filter(order__created_at__date=today_date).values("order_id").distinct().count()
    )
    processing_order_count = (
        brand_order_items.filter(order__status="pending").values("order_id").distinct().count()
    )
    cancelled_order_count = (
        brand_order_items.filter(order__status="cancelled").values("order_id").distinct().count()
    )
    review_check_count = vendor_products.filter(_actual_review_count__gte=100).count()
    trend_rows = {
        row["order_day"]: row
        for row in active_brand_order_items.filter(order__created_at__date__gte=trend_start_date)
        .annotate(order_day=TruncDate("order__created_at"))
        .values("order_day")
        .annotate(
            order_count=Count("order_id", distinct=True),
            revenue=Sum(F("quantity") * F("price_at_order"), output_field=IntegerField()),
        )
        .order_by("order_day")
    }
    trend_points = []
    for offset in range(6, -1, -1):
        day = today_date - timedelta(days=offset)
        row = trend_rows.get(day, {})
        trend_points.append(
            {
                "label": day.strftime("%m/%d"),
                "value": row.get("order_count", 0) or 0,
                "revenue": row.get("revenue", 0) or 0,
            }
        )
    max_trend_value = max((point["value"] for point in trend_points), default=0) or 1
    for point in trend_points:
        point["height_percent"] = max(18, int(point["value"] / max_trend_value * 100))
        point["revenue_label"] = _format_vendor_price(point["revenue"])
    trend_order_total = sum(point["value"] for point in trend_points)
    trend_revenue_total = sum(point["revenue"] for point in trend_points)
    peak_point = max(trend_points, key=lambda point: point["value"], default={"label": "-", "value": 0})

    return render(
        request,
        "users/vendor_dashboard.html",
        {
            **base_context,
            "vendor_primary_kpis": [
                {
                    "label": "오늘 매출",
                    "value": f"₩{today_revenue:,}",
                    "description": "브랜드 기준 오늘 결제 금액",
                    "action_label": "매출 흐름 보기",
                    "href": reverse("vendor-analytics"),
                    "tone": "blue",
                },
                {
                    "label": "신규 주문",
                    "value": f"{today_order_count}건",
                    "description": "오늘 생성된 브랜드 주문 기준",
                    "action_label": "주문 처리",
                    "href": f"{reverse('vendor-orders')}?focus=processing",
                    "tone": "blue",
                },
                {
                    "label": "취소 / 환불 대기",
                    "value": f"{cancelled_order_count}건",
                    "description": "현재 취소된 브랜드 주문 기준",
                    "action_label": "클레임 확인",
                    "href": f"{reverse('vendor-orders')}?focus=refund",
                    "tone": "rose",
                },
                {
                    "label": "품절 / 검수 필요",
                    "value": f"{display_soldout_products + display_pending_products}개",
                    "description": f"품절 {display_soldout_products:,}개 · 검수 {display_pending_products:,}개",
                    "action_label": "상품 점검",
                    "href": reverse("vendor-products"),
                    "tone": "amber",
                },
            ],
            "vendor_secondary_metrics": [
                {"label": "평균 평점", "value": _format_vendor_rating(average_rating)},
                {"label": "총 리뷰 수", "value": f"{total_reviews:,}개"},
                {"label": "운영 상품", "value": f"{active_products:,}개"},
            ],
            "vendor_queue_items": [
                {
                    "title": "신규 주문",
                    "count_label": f"{processing_order_count}건",
                    "href": f"{reverse('vendor-orders')}?focus=processing",
                    "tone": "blue",
                },
                {
                    "title": "취소 / 환불",
                    "count_label": f"{cancelled_order_count}건",
                    "href": f"{reverse('vendor-orders')}?focus=refund",
                    "tone": "rose",
                },
                {
                    "title": "상품 검수",
                    "count_label": f"{display_pending_products}개",
                    "href": f"{reverse('vendor-products')}?stock=pending",
                    "tone": "amber",
                },
                {
                    "title": "리뷰 확인",
                    "count_label": f"{review_check_count}건",
                    "href": f"{reverse('vendor-reviews')}?focus=pending",
                    "tone": "blue",
                },
            ],
            "vendor_trend_highlights": [
                {"label": "7일 주문", "value": f"{trend_order_total}건", "description": "최근 7일 누적"},
                {"label": "7일 매출", "value": f"₩{trend_revenue_total:,}", "description": "주문 금액 합산"},
                {"label": "최고 주문일", "value": f"{peak_point['label']} · {peak_point['value']}건", "description": "주문 수 기준"},
            ],
            "vendor_order_trend": trend_points,
            "vendor_mix_sections": [
                {"title": "카테고리 구성", "items": _build_vendor_breakdown_items(category_counter)},
                {"title": "반려동물 유형", "items": _build_vendor_breakdown_items(pet_type_counter)},
            ],
            "vendor_customer_signals": [
                {
                    "label": "재구매율",
                    "value": _format_vendor_percent(average_repeat_rate, 1),
                    "description": "리뷰/구매 반응 기반 반복 구매 지표",
                },
                {
                    "label": "리뷰 정서",
                    "value": _format_vendor_percent(average_sentiment, 1),
                    "description": "고객 반응 전반의 긍정도",
                },
                {
                    "label": "배송/포장 점수",
                    "value": _format_vendor_metric(average_delivery_score, 2),
                    "description": "배송 품질 관련 리뷰 반응",
                },
                {
                    "label": "가격 반응",
                    "value": _format_vendor_metric(average_price_score, 2),
                    "description": "가격 수용성과 구매 만족도",
                },
            ],
            "vendor_review_focus_items": [
                "평점이 낮은 상품은 상세 설명 보강 또는 리뷰 응답 우선순위를 높입니다.",
                "품절 상품은 대체 노출 또는 재입고 일정 안내가 먼저 필요합니다.",
                "배송/포장 점수가 흔들리면 주문 처리 속도와 출고 흐름을 함께 점검합니다.",
            ],
            "vendor_attention_products": attention_products,
            "vendor_top_products": top_products,
        },
    )


def vendor_products_view(request):
    base_context = _build_vendor_base_context(request, "products")
    if base_context is None:
        return redirect("vendor-login")

    keyword = request.GET.get("q", "").strip()
    soldout_filter = request.GET.get("stock", "all")
    sort_key = request.GET.get("sort", "default")
    if sort_key not in VENDOR_PRODUCT_SORT_OPTIONS:
        sort_key = "default"
    vendor_products = with_actual_review_metrics(Product.objects.filter(brand_name=base_context["vendor_account"]["brand_name"]))
    demo_soldout_goods_ids = _get_demo_soldout_goods_ids(vendor_products)
    demo_pending_goods_ids = _get_demo_pending_goods_ids(vendor_products, demo_soldout_goods_ids)

    if keyword:
        vendor_products = vendor_products.filter(goods_name__icontains=keyword)
    ordered_products = list(vendor_products.order_by("goods_name")[:60])
    serialized_products = [
        _serialize_vendor_product(product, demo_soldout_goods_ids, demo_pending_goods_ids)
        for product in ordered_products
    ]
    product_status_counts = {
        "all": len(serialized_products),
        "active": sum(1 for product in serialized_products if not product["soldout"] and not product["pending"]),
        "pending": sum(1 for product in serialized_products if product["pending"]),
        "soldout": sum(1 for product in serialized_products if product["soldout"]),
    }

    if soldout_filter == "active":
        serialized_products = [product for product in serialized_products if not product["soldout"] and not product["pending"]]
    elif soldout_filter == "soldout":
        serialized_products = [product for product in serialized_products if product["soldout"]]
    elif soldout_filter == "pending":
        serialized_products = [product for product in serialized_products if product["pending"]]

    _sort_vendor_products(serialized_products, sort_key)
    _apply_demo_registered_dates(serialized_products)

    sort_options = []
    for key, option in VENDOR_PRODUCT_SORT_OPTIONS.items():
        sort_options.append(
            {
                "label": option["label"],
                "value": key,
                "is_active": key == sort_key,
            }
        )

    stock_options = []
    for value, label in (
        ("all", "전체"),
        ("active", "판매중"),
        ("pending", "준비중"),
        ("soldout", "품절"),
    ):
        query = {}
        if keyword:
            query["q"] = keyword
        if sort_key != "default":
            query["sort"] = sort_key
        if value != "all":
            query["stock"] = value
        stock_options.append(
            {
                "label": label,
                "count": product_status_counts[value],
                "query": urlencode(query),
                "is_active": value == soldout_filter,
            }
        )

    return render(
        request,
        "users/vendor_products.html",
        {
            **base_context,
            "vendor_product_items": serialized_products,
            "vendor_product_count": len(serialized_products),
            "vendor_search_keyword": keyword,
            "vendor_stock_filter": soldout_filter,
            "vendor_sort_key": sort_key,
            "vendor_sort_options": sort_options,
            "vendor_stock_options": stock_options,
            "vendor_sort_description": VENDOR_PRODUCT_SORT_OPTIONS[sort_key]["description"],
        },
    )


def vendor_analytics_view(request):
    base_context = _build_vendor_base_context(request, "analytics")
    if base_context is None:
        return redirect("vendor-login")

    period_definitions = {
        "7": {"label": "최근 7일", "days": 7},
        "30": {"label": "최근 30일", "days": 30},
        "all": {"label": "전체", "days": None},
    }
    selected_period = (request.GET.get("period") or "30").strip() or "30"
    if selected_period not in period_definitions:
        selected_period = "30"
    selected_period_meta = period_definitions[selected_period]
    period_start_date = None
    if selected_period_meta["days"] is not None:
        period_start_date = date.today() - timedelta(days=selected_period_meta["days"] - 1)

    brand_name = base_context["vendor_account"]["brand_name"]
    vendor_products = with_actual_review_metrics(Product.objects.filter(brand_name=brand_name))
    demo_soldout_goods_ids = _get_demo_soldout_goods_ids(vendor_products)
    demo_pending_goods_ids = _get_demo_pending_goods_ids(vendor_products, demo_soldout_goods_ids)
    total_products = vendor_products.count()
    soldout_count = len(demo_soldout_goods_ids)
    pending_count = len(demo_pending_goods_ids)
    active_count = max(total_products - soldout_count - pending_count, 0)
    total_reviews = vendor_products.aggregate(total=Sum("_actual_review_count"))["total"] or 0
    average_rating = vendor_products.exclude(_actual_review_score_avg__isnull=True).aggregate(avg=Avg("_actual_review_score_avg"))["avg"]
    average_discount_price = vendor_products.aggregate(avg=Avg("discount_price"))["avg"]
    average_price_purchase = vendor_products.exclude(aspect_price_purchase__isnull=True).aggregate(avg=Avg("aspect_price_purchase"))["avg"]
    average_delivery = vendor_products.exclude(aspect_delivery_packaging__isnull=True).aggregate(avg=Avg("aspect_delivery_packaging"))["avg"]
    interaction_queryset = UserInteraction.objects.filter(product__brand_name=brand_name)
    brand_order_items = OrderItem.objects.filter(product__brand_name=brand_name).exclude(order__status="cancelled")
    if period_start_date is not None:
        interaction_queryset = interaction_queryset.filter(created_at__date__gte=period_start_date)
        brand_order_items = brand_order_items.filter(order__created_at__date__gte=period_start_date)

    interaction_counts = {
        row["interaction_type"]: row["total"]
        for row in interaction_queryset
        .values("interaction_type")
        .annotate(total=Count("id"))
    }
    revenue_total = (
        brand_order_items.aggregate(total=Sum(F("quantity") * F("price_at_order"), output_field=IntegerField()))["total"]
        or 0
    )
    orders = brand_order_items.values("order_id").distinct().count()
    buyer_order_counts = brand_order_items.values("order__user_id").annotate(order_count=Count("order_id", distinct=True))
    buyer_count = buyer_order_counts.count()
    repeat_buyer_count = buyer_order_counts.filter(order_count__gte=2).count()

    category_counter = Counter()
    pet_type_counter = Counter()
    for product in vendor_products:
        for pet_type in product.pet_type or []:
            pet_type_counter[pet_type] += 1
        if product.category:
            category_counter[product.category[0]] += 1

    impressions = interaction_counts.get("impression", 0)
    clicks = interaction_counts.get("click", 0)
    detail_views = interaction_counts.get("detail_view", 0)
    carts = interaction_counts.get("cart", 0)
    checkout_starts = interaction_counts.get("checkout_start", 0)
    wishlist_adds = interaction_counts.get("wishlist", 0)
    sample_total = impressions + clicks + detail_views + carts + checkout_starts + wishlist_adds + orders
    ctr = (clicks / impressions) * 100 if impressions else 0
    detail_rate = (detail_views / clicks) * 100 if clicks else 0
    cart_rate = (carts / detail_views) * 100 if detail_views else 0
    order_rate = (orders / detail_views) * 100 if detail_views else 0
    repeat_rate_percent = (repeat_buyer_count / buyer_count) * 100 if buyer_count else 0
    price_resistance = max(0.0, 100 - float((average_price_purchase or 0) * 100))
    revenue_label = f"{selected_period_meta['label']} 매출" if selected_period != "all" else "누적 매출"
    revenue_basis_label = (
        f"{selected_period_meta['label']} 결제 금액 기준" if selected_period != "all" else "전체 기간 결제 금액 기준"
    )
    period_caption = (
        f"{selected_period_meta['label']} 실제 이벤트 로그 기준"
        if selected_period != "all"
        else "전체 기간 실제 이벤트 로그 기준"
    )

    funnel_items = [
        {
            "label": "노출",
            "value": f"{impressions:,}",
            "rate_label": "기준 모수",
            "rate_tone": "slate",
            "detail": "추천 카드 노출 이벤트 기준",
        },
        {
            "label": "클릭",
            "value": f"{clicks:,}",
            "rate_label": f"CTR {ctr:.1f}%",
            "rate_tone": "blue",
            "detail": "추천 카드 클릭 이벤트 수",
        },
        {
            "label": "상세 진입",
            "value": f"{detail_views:,}",
            "rate_label": f"클릭 대비 {detail_rate:.1f}%",
            "rate_tone": "indigo",
            "detail": "상품 링크 상세 진입 이벤트 수",
        },
        {
            "label": "장바구니",
            "value": f"{carts:,}",
            "rate_label": f"상세 대비 {cart_rate:.1f}%",
            "rate_tone": "green",
            "detail": "장바구니 담기 이벤트 수",
        },
        {
            "label": "구매",
            "value": f"{orders:,}",
            "rate_label": f"상세 대비 {order_rate:.1f}%",
            "rate_tone": "amber",
            "detail": "브랜드 주문 완료 건수",
        },
    ]

    explicit_metrics = [
        {
            "label": "평균 평점",
            "value": _format_vendor_rating(average_rating),
            "description": "리뷰가 직접 보여주는 만족도",
        },
        {
            "label": "리뷰 수",
            "value": f"{total_reviews:,}개",
            "description": "구매 후 반응 모수",
        },
        {
            "label": "가격 저항",
            "value": f"{price_resistance:.1f}",
            "description": "가격/구매 반응 역산 지표",
        },
        {
            "label": "배송 만족",
            "value": f"{float(average_delivery or 0):.2f}",
            "description": "배송·포장 체감 품질",
        },
    ]

    implicit_metrics = [
        {
            "label": "추천 클릭률",
            "value": f"{ctr:.1f}%",
            "description": "노출 대비 클릭 반응",
        },
        {
            "label": "상세 진입률",
            "value": f"{detail_rate:.1f}%",
            "description": "클릭 이후 상세 탐색 비율",
        },
        {
            "label": "장바구니 전환율",
            "value": f"{cart_rate:.1f}%",
            "description": "상세 진입 이후 담기 비율",
        },
        {
            "label": "구매 전환율",
            "value": f"{order_rate:.1f}%",
            "description": "상세 진입 대비 구매 전환",
        },
        {
            "label": "체크아웃 시작 수",
            "value": f"{checkout_starts:,}회",
            "description": "결제 진입 이벤트 수",
        },
        {
            "label": "관심상품 추가 수",
            "value": f"{wishlist_adds:,}회",
            "description": "위시리스트 저장 이벤트 수",
        },
    ]

    bottlenecks = [
        {
            "label": "추천 클릭률",
            "value": f"{ctr:.1f}%",
            "status": "안정" if ctr >= 3 else "개선 필요",
            "tone": "green" if ctr >= 3 else "amber",
        },
        {
            "label": "상세 진입률",
            "value": f"{detail_rate:.1f}%",
            "status": "안정" if detail_rate >= 45 else "보강 필요",
            "tone": "blue" if detail_rate >= 45 else "amber",
        },
        {
            "label": "구매 전환율",
            "value": f"{order_rate:.1f}%",
            "status": "안정" if order_rate >= 8 else "개선 필요",
            "tone": "green" if order_rate >= 8 else "rose",
        },
    ]

    recommended_actions = [
        {
            "title": "추천 카드 문구 점검",
            "tag": "추천",
            "tag_tone": "blue",
            "reason": f"추천 노출 {impressions:,}회 대비 클릭률이 {ctr:.1f}%입니다.",
            "impact": "추천 문구·썸네일 매력도 확인",
        },
        {
            "title": "상세 유입 경로 보강",
            "tag": "상세",
            "tag_tone": "green",
            "reason": f"클릭 {clicks:,}회 중 상세 진입은 {detail_views:,}회입니다.",
            "impact": "상품 링크·상세 페이지 연결 점검",
        },
        {
            "title": "결제 진입 전환 확인",
            "tag": "전환",
            "tag_tone": "amber",
            "reason": f"상세 진입 {detail_views:,}회 대비 구매 {orders:,}건, 체크아웃 시작 {checkout_starts:,}회입니다.",
            "impact": "장바구니·결제 단계 이탈 확인",
        },
    ]

    performance_rows = []
    ranked_products = vendor_products.order_by("-_actual_review_count", "-_actual_review_score_avg", "goods_name")[:6]
    product_interaction_counts = {
        (row["product_id"], row["interaction_type"]): row["total"]
        for row in UserInteraction.objects.filter(product__in=ranked_products)
        .values("product_id", "interaction_type")
        .annotate(total=Count("id"))
    }
    product_order_stats = {
        row["product_id"]: {
            "revenue": row["revenue"] or 0,
            "order_count": row["order_count"] or 0,
        }
        for row in brand_order_items.filter(product__in=ranked_products)
        .values("product_id")
        .annotate(
            revenue=Sum(F("quantity") * F("price_at_order"), output_field=IntegerField()),
            order_count=Count("order_id", distinct=True),
        )
    }
    for product in ranked_products:
        item = _serialize_vendor_product(product, demo_soldout_goods_ids, demo_pending_goods_ids)
        product_impressions = product_interaction_counts.get((product.goods_id, "impression"), 0)
        product_clicks = product_interaction_counts.get((product.goods_id, "click"), 0)
        product_detail_views = product_interaction_counts.get((product.goods_id, "detail_view"), 0)
        product_orders = product_order_stats.get(product.goods_id, {}).get("order_count", 0)
        product_revenue = product_order_stats.get(product.goods_id, {}).get("revenue", 0)
        product_ctr = (product_clicks / product_impressions) * 100 if product_impressions else 0
        product_conversion = (product_orders / product_detail_views) * 100 if product_detail_views else 0
        product_repeat = max(float((product.repeat_rate or 0) * 100), 0.0)
        strength_label, strength_tone = _pick_vendor_performance_strength(
            product_ctr,
            product_conversion,
            product_repeat,
        )
        performance_rows.append(
            {
                "goods_id": item["goods_id"],
                "goods_name": item["goods_name"],
                "status_label": item["status_label"],
                "revenue_label": f"₩{product_revenue:,}",
                "ctr_label": f"{product_ctr:.1f}%",
                "conversion_label": f"{product_conversion:.1f}%",
                "repeat_label": f"{product_repeat:.1f}%",
                "strength_label": strength_label,
                "strength_tone": strength_tone,
            }
        )

    category_breakdown = _build_vendor_breakdown_items(category_counter)
    pet_type_breakdown = _build_vendor_breakdown_items(pet_type_counter)
    vendor_analytics_period_options = [
        {
            "label": option_meta["label"],
            "url": f"{reverse('vendor-analytics')}?{urlencode({'period': option_code})}",
            "is_active": option_code == selected_period,
        }
        for option_code, option_meta in period_definitions.items()
    ]

    return render(
        request,
        "users/vendor_analytics.html",
        {
            **base_context,
            "vendor_analytics_period_label": selected_period_meta["label"],
            "vendor_analytics_period_options": vendor_analytics_period_options,
            "vendor_analytics_data_note": (
                f"퍼널·매출은 {period_caption}, 상품·리뷰 지표는 현재 브랜드 데이터 기준입니다."
            ),
            "vendor_analytics_sample_items": [
                {"label": "노출", "value": f"{impressions:,}"},
                {"label": "클릭", "value": f"{clicks:,}"},
                {"label": "체크아웃 시작", "value": f"{checkout_starts:,}"},
                {"label": "구매", "value": f"{orders:,}"},
                {"label": "이벤트 표본", "value": f"{sample_total:,}"},
            ],
            "vendor_analytics_revenue_basis_label": revenue_basis_label,
            "vendor_analytics_summary": [
                {"label": revenue_label, "value": f"₩{revenue_total:,}", "delta": period_caption, "delta_tone": "neutral"},
                {"label": "구매 전환율", "value": f"{order_rate:.1f}%", "delta": f"{selected_period_meta['label']} 상세 진입 대비", "delta_tone": "neutral"},
                {"label": "반복 구매율", "value": f"{repeat_rate_percent:.1f}%", "delta": f"{selected_period_meta['label']} 브랜드 구매자 기준", "delta_tone": "neutral"},
                {"label": "평균 실판매가", "value": _format_vendor_price(average_discount_price), "delta": "현재 브랜드 상품 평균", "delta_tone": "neutral"},
            ],
            "vendor_funnel_items": funnel_items,
            "vendor_explicit_metrics": explicit_metrics,
            "vendor_implicit_metrics": implicit_metrics,
            "vendor_personalization_note": "추천 노출, 클릭, 상세 진입, 장바구니, 체크아웃 시작, 구매 이벤트를 실제 집계해 브랜드 퍼널과 암묵적 반응 지표로 활용할 수 있습니다.",
            "vendor_bottlenecks": bottlenecks,
            "vendor_recommended_actions": recommended_actions,
            "vendor_performance_rows": performance_rows,
            "vendor_category_breakdown": category_breakdown,
            "vendor_pet_type_breakdown": pet_type_breakdown,
            "vendor_inventory_summary": [
                {"label": "판매중", "value": f"{active_count:,}개"},
                {"label": "준비중", "value": f"{pending_count:,}개"},
                {"label": "품절", "value": f"{soldout_count:,}개"},
            ],
        },
    )


def vendor_product_create_view(request):
    base_context = _build_vendor_base_context(request, "products")
    if base_context is None:
        return redirect("vendor-login")

    sample_columns = [
        "goods_id",
        "goods_name",
        "price",
        "discount_price",
        "thumbnail_url",
        "product_url",
        "pet_type",
        "category",
        "subcategory",
        "main_ingredients",
    ]
    form_options = _collect_vendor_product_form_options()
    return render(
        request,
        "users/vendor_product_create.html",
        {
            **base_context,
            "vendor_product_form_mode": "create",
            "vendor_product_form_title": "상품 등록",
            "vendor_upload_sample_columns": sample_columns,
            **form_options,
        },
    )


def vendor_product_detail_view(request, goods_id):
    base_context = _build_vendor_base_context(request, "products")
    if base_context is None:
        return redirect("vendor-login")

    product = get_object_or_404(
        Product,
        goods_id=goods_id,
        brand_name=base_context["vendor_account"]["brand_name"],
    )
    vendor_products = Product.objects.filter(brand_name=base_context["vendor_account"]["brand_name"])
    demo_soldout_goods_ids = _get_demo_soldout_goods_ids(vendor_products)
    demo_pending_goods_ids = _get_demo_pending_goods_ids(vendor_products, demo_soldout_goods_ids)
    serialized_product = _serialize_vendor_product(product, demo_soldout_goods_ids, demo_pending_goods_ids)

    return render(
        request,
        "users/vendor_product_detail.html",
        {
            **base_context,
            "vendor_product": serialized_product,
            **_build_vendor_product_detail_context(product, serialized_product),
        },
    )


def vendor_product_edit_view(request, goods_id):
    base_context = _build_vendor_base_context(request, "products")
    if base_context is None:
        return redirect("vendor-login")

    sample_columns = [
        "goods_id",
        "goods_name",
        "price",
        "discount_price",
        "thumbnail_url",
        "product_url",
        "pet_type",
        "category",
        "subcategory",
        "main_ingredients",
    ]
    product = get_object_or_404(
        Product,
        goods_id=goods_id,
        brand_name=base_context["vendor_account"]["brand_name"],
    )
    vendor_products = Product.objects.filter(brand_name=base_context["vendor_account"]["brand_name"])
    demo_soldout_goods_ids = _get_demo_soldout_goods_ids(vendor_products)
    demo_pending_goods_ids = _get_demo_pending_goods_ids(vendor_products, demo_soldout_goods_ids)
    serialized_product = _serialize_vendor_product(product, demo_soldout_goods_ids, demo_pending_goods_ids)
    form_options = _collect_vendor_product_form_options()
    category_path = list(product.category or [])
    group_value = category_path[1] if len(category_path) > 1 else ""
    subcategory_value = category_path[2] if len(category_path) > 2 else ""

    return render(
        request,
        "users/vendor_product_create.html",
        {
            **base_context,
            "vendor_product_form_mode": "edit",
            "vendor_product_form_title": "상품 수정",
            "vendor_product_form_initial": {
                "goods_name": product.goods_name,
                "price": f"{product.price:,}" if product.price is not None else "",
                "discount_price": f"{product.discount_price:,}" if product.discount_price is not None else "",
                "pet_type": product.pet_type[0] if product.pet_type else "",
                "category": category_path[0] if category_path else "",
                "subcategory_group": group_value,
                "subcategory": subcategory_value,
            },
            "vendor_product_meta": {
                "goods_id": product.goods_id,
                "registered_date_label": _get_vendor_product_registered_date_label(product),
                "status_label": serialized_product["status_label"],
                "status_tone": _get_vendor_product_status_tone(serialized_product),
            },
            "vendor_upload_sample_columns": sample_columns,
            **form_options,
        },
    )


def vendor_orders_view(request):
    base_context = _build_vendor_base_context(request, "orders")
    if base_context is None:
        return redirect("vendor-login")

    focus = request.GET.get("focus", "all")
    if focus not in dict(VENDOR_ORDER_FOCUS_OPTIONS):
        focus = "all"

    vendor_products = with_actual_review_metrics(Product.objects.filter(brand_name=base_context["vendor_account"]["brand_name"]))
    demo_soldout_goods_ids = _get_demo_soldout_goods_ids(vendor_products)
    demo_pending_goods_ids = _get_demo_pending_goods_ids(vendor_products, demo_soldout_goods_ids)
    order_rows = _build_vendor_mock_order_rows(vendor_products, demo_soldout_goods_ids, demo_pending_goods_ids)

    focus_counts = Counter(row["focus"] for row in order_rows)
    summary_items = [
        {
            "label": "주문 접수",
            "count": focus_counts["processing"],
            "status": "결제 완료 기준",
            "href": f"{reverse('vendor-orders')}?focus=processing",
            "is_active": focus == "processing",
        },
        {
            "label": "출고 준비",
            "count": focus_counts["packing"],
            "status": "송장 입력 전",
            "href": f"{reverse('vendor-orders')}?focus=packing",
            "is_active": focus == "packing",
        },
        {
            "label": "취소/환불",
            "count": focus_counts["refund"],
            "status": "우선 확인",
            "href": f"{reverse('vendor-orders')}?focus=refund",
            "is_active": focus == "refund",
        },
        {
            "label": "배송 지연",
            "count": focus_counts["delayed"],
            "status": "고객 안내 필요",
            "href": f"{reverse('vendor-orders')}?focus=delayed",
            "is_active": focus == "delayed",
        },
    ]
    focus_options = []
    for value, label in VENDOR_ORDER_FOCUS_OPTIONS:
        focus_options.append(
            {
                "label": label,
                "count": len(order_rows) if value == "all" else focus_counts[value],
                "href": reverse("vendor-orders") if value == "all" else f"{reverse('vendor-orders')}?focus={value}",
                "is_active": value == focus,
            }
        )

    filtered_order_rows = order_rows if focus == "all" else [row for row in order_rows if row["focus"] == focus]
    return render(
        request,
        "users/vendor_orders.html",
        {
            **base_context,
            "vendor_orders_focus": focus,
            "vendor_order_summary_items": summary_items,
            "vendor_order_focus_options": focus_options,
            "vendor_order_rows": filtered_order_rows,
            "vendor_order_filtered_count": len(filtered_order_rows),
        },
    )


def vendor_reviews_view(request):
    base_context = _build_vendor_base_context(request, "reviews")
    if base_context is None:
        return redirect("vendor-login")

    focus = request.GET.get("focus", "pending")
    review_items = [
        {"title": "배송이 빨라서 재구매 의향이 있어요", "score": "5.0", "status": "확인 필요"},
        {"title": "기호성은 좋지만 가격이 조금 높아요", "score": "4.0", "status": "응답 검토"},
        {"title": "품절이 잦아서 아쉬워요", "score": "3.0", "status": "운영 전달"},
    ]
    return render(
        request,
        "users/vendor_reviews.html",
        {
            **base_context,
            "vendor_reviews_focus": focus,
            "vendor_review_items": review_items,
        },
    )
