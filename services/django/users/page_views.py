import logging
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from types import SimpleNamespace
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.db import IntegrityError, transaction
from django.db.models import Avg, Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from products.models import Product
from social_core.exceptions import AuthCanceled, AuthConnectionError, AuthException, AuthForbidden, AuthMissingParameter

from .models import UserProfile
from .nickname_utils import build_unique_nickname, get_nickname_validation_error
from .onboarding import (
    ONBOARDING_FORCE_PROFILE_SESSION_KEY,
    get_onboarding_redirect_url,
    has_completed_pet_onboarding,
)
from .quick_purchase import build_payment_info, split_legacy_address
from .social_auth import (
    SOCIAL_AUTH_ACCESS_SESSION_KEY,
    SOCIAL_AUTH_REFRESH_SESSION_KEY,
    SOCIAL_AUTH_REMEMBER_SESSION_KEY,
    SocialAuthServiceError,
    build_callback_url,
    build_authorization_url,
    complete_social_login,
)
from .views import deactivate_user_and_purge_personal_data, issue_user_tokens

User = get_user_model()
logger = logging.getLogger(__name__)
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


def _get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(
        user=user,
        defaults={"nickname": build_unique_nickname(user.email.split("@")[0], exclude_user=user)},
    )
    return profile


def _render_profile(request, profile):
    address_main = (profile.address_main or "").strip()
    address_detail = (profile.address_detail or "").strip()
    if not address_main and not address_detail:
        address_main, address_detail = split_legacy_address(profile.address)
    payment_info = build_payment_info(profile)
    return render(
        request,
        "users/profile.html",
        {
            "profile": profile,
            "profile_zipcode": profile.postal_code or "",
            "profile_address_main": address_main,
            "profile_address_detail": address_detail,
            "profile_payment_method": payment_info["payment_summary"],
            "profile_payment_card_provider": payment_info["card_provider"],
            "profile_payment_card_masked_number": payment_info["masked_card_number"],
            "profile_payment_token_reference": payment_info["payment_token_reference"],
            "profile_phone_verified": profile.phone_verified,
            "social_accounts": {account.provider: account for account in request.user.social_accounts.all()},
            "setup_mode": request.GET.get("setup") == "1",
            "profile_preview": False,
        },
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
    if value is None:
        return "-"
    return f"{value:.1f}"


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
        "crawled_at": product.crawled_at,
        "price_label": _format_vendor_price(product.price),
        "discount_price_label": _format_vendor_price(product.discount_price),
        "discount_price_value": price_value,
        "discount_rate_label": discount_rate_label,
        "rating_label": _format_vendor_rating(product.rating),
        "review_count": product.review_count,
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
            "label": "리뷰 관리",
            "href": reverse("vendor-reviews"),
            "active": current_view == "reviews",
            "disabled": False,
        },
        {
            "label": "운영 점검",
            "href": reverse("vendor-operations"),
            "active": current_view == "operations",
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


def home(request):
    if request.user.is_authenticated:
        onboarding_redirect_url = get_onboarding_redirect_url(request)
        if onboarding_redirect_url:
            return redirect(onboarding_redirect_url)
        return redirect("chat")
    return render(request, "chat/index.html")


def login_view(request):
    if request.user.is_authenticated:
        onboarding_redirect_url = get_onboarding_redirect_url(request)
        if onboarding_redirect_url:
            return redirect(onboarding_redirect_url)
        return redirect("chat")
    return render(request, "users/login.html")


def signup_view(request):
    if request.user.is_authenticated:
        onboarding_redirect_url = get_onboarding_redirect_url(request)
        if onboarding_redirect_url:
            return redirect(onboarding_redirect_url)
        return redirect("chat")
    return render(request, "users/signup.html")


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

    vendor_products = Product.objects.filter(brand_name=base_context["vendor_account"]["brand_name"])
    demo_soldout_goods_ids = _get_demo_soldout_goods_ids(vendor_products)
    demo_pending_goods_ids = _get_demo_pending_goods_ids(vendor_products, demo_soldout_goods_ids)
    total_products = vendor_products.count()
    display_soldout_products = len(demo_soldout_goods_ids)
    display_pending_products = len(demo_pending_goods_ids)
    total_reviews = vendor_products.aggregate(total=Sum("review_count"))["total"] or 0
    average_rating = vendor_products.exclude(rating__isnull=True).aggregate(avg=Avg("rating"))["avg"]

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
        for product in vendor_products.order_by("-review_count", "-rating", "goods_name")[:5]
    ]

    top_categories = [
        {"label": label, "count": count}
        for label, count in category_counter.most_common(4)
    ]
    pet_type_breakdown = [
        {"label": label, "count": count}
        for label, count in pet_type_counter.most_common(4)
    ]
    active_products = max(total_products - display_soldout_products - display_pending_products, 0)
    mock_daily_revenue = 2480000
    mock_daily_orders = 38
    mock_cancel_refund = 3
    trend_points = [
        {"label": "03/25", "value": 42},
        {"label": "03/26", "value": 58},
        {"label": "03/27", "value": 51},
        {"label": "03/28", "value": 66},
        {"label": "03/29", "value": 61},
        {"label": "03/30", "value": 74},
        {"label": "03/31", "value": 69},
    ]
    max_trend_value = max((point["value"] for point in trend_points), default=1)
    for point in trend_points:
        point["height_percent"] = max(18, int(point["value"] / max_trend_value * 100))

    return render(
        request,
        "users/vendor_dashboard.html",
        {
            **base_context,
            "vendor_metrics": [
                {"label": "오늘 매출", "value": f"₩{mock_daily_revenue:,}", "description": "전일 대비 +12.4%"},
                {"label": "주문 / 결제", "value": f"{mock_daily_orders}건", "description": "결제 완료 기준"},
                {
                    "label": "상품 상태",
                    "status_items": [
                        {"label": "판매중", "value": f"{active_products:,}개", "tone": "green"},
                        {"label": "준비중", "value": f"{display_pending_products:,}개", "tone": "amber"},
                        {"label": "품절", "value": f"{display_soldout_products:,}개", "tone": "rose"},
                    ],
                },
                {"label": "취소 / 환불", "value": f"{mock_cancel_refund}건", "description": ""},
            ],
            "vendor_realtime_metrics": [
                {"label": "평균 평점", "value": _format_vendor_rating(average_rating)},
                {"label": "총 리뷰 수", "value": f"{total_reviews:,}개"},
                {"label": "등록 상품", "value": f"{total_products:,}개"},
            ],
            "vendor_alerts": sorted(
                [
                    {
                        "title": f"품절 상품 {display_soldout_products:,}개",
                        "tone": "rose",
                        "priority": 0,
                        "count": display_soldout_products,
                        "href": f"{reverse('vendor-operations')}?focus=inventory",
                    },
                    {
                        "title": f"취소/환불 요청 {mock_cancel_refund}건",
                        "tone": "rose",
                        "priority": 0,
                        "count": mock_cancel_refund,
                        "href": f"{reverse('vendor-orders')}?focus=refund",
                    },
                    {
                        "title": "가격/재고 점검 2건",
                        "tone": "amber",
                        "priority": 1,
                        "count": 2,
                        "href": f"{reverse('vendor-operations')}?focus=pricing",
                    },
                    {
                        "title": "노출 점검 필요 3건",
                        "tone": "amber",
                        "priority": 1,
                        "count": 3,
                        "href": f"{reverse('vendor-operations')}?focus=exposure",
                    },
                    {
                        "title": "리뷰 확인 필요 12건",
                        "tone": "amber",
                        "priority": 1,
                        "count": 12,
                        "href": f"{reverse('vendor-reviews')}?focus=pending",
                    },
                    {
                        "title": f"주문 처리 {mock_daily_orders}건",
                        "tone": "blue",
                        "priority": 2,
                        "count": mock_daily_orders,
                        "href": f"{reverse('vendor-orders')}?focus=processing",
                    },
                    {
                        "title": "신규 등록 검수 2건",
                        "tone": "blue",
                        "priority": 2,
                        "count": 2,
                        "href": f"{reverse('vendor-operations')}?focus=approval",
                    },
                    {
                        "title": "상품 정보 수정 필요 1건",
                        "tone": "blue",
                        "priority": 2,
                        "count": 1,
                        "href": f"{reverse('vendor-operations')}?focus=content",
                    },
                ],
                key=lambda item: (item["priority"], -item["count"], item["title"]),
            ),
            "vendor_order_trend": trend_points,
            "vendor_top_products": top_products,
            "vendor_top_categories": top_categories,
            "vendor_pet_type_breakdown": pet_type_breakdown,
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
    vendor_products = Product.objects.filter(brand_name=base_context["vendor_account"]["brand_name"])
    demo_soldout_goods_ids = _get_demo_soldout_goods_ids(vendor_products)
    demo_pending_goods_ids = _get_demo_pending_goods_ids(vendor_products, demo_soldout_goods_ids)

    if keyword:
        vendor_products = vendor_products.filter(goods_name__icontains=keyword)
    ordered_products = list(vendor_products.order_by("goods_name")[:60])
    serialized_products = [
        _serialize_vendor_product(product, demo_soldout_goods_ids, demo_pending_goods_ids) for product in ordered_products
    ]

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
        query = {"sort": key}
        if keyword:
            query["q"] = keyword
        if soldout_filter != "all":
            query["stock"] = soldout_filter
        sort_options.append(
            {
                "label": option["label"],
                "query": urlencode(query),
                "is_active": key == sort_key,
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
            "vendor_sort_description": VENDOR_PRODUCT_SORT_OPTIONS[sort_key]["description"],
        },
    )


def vendor_orders_view(request):
    base_context = _build_vendor_base_context(request, "orders")
    if base_context is None:
        return redirect("vendor-login")

    focus = request.GET.get("focus", "processing")
    order_items = [
        {"label": "주문 접수", "count": 22, "status": "결제 완료"},
        {"label": "출고 준비", "count": 11, "status": "오늘 출고 예정"},
        {"label": "취소/환불", "count": 3, "status": "우선 확인"},
        {"label": "배송 지연", "count": 2, "status": "확인 필요"},
    ]
    return render(
        request,
        "users/vendor_orders.html",
        {
            **base_context,
            "vendor_orders_focus": focus,
            "vendor_order_items": order_items,
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


def vendor_operations_view(request):
    base_context = _build_vendor_base_context(request, "operations")
    if base_context is None:
        return redirect("vendor-login")

    focus = request.GET.get("focus", "inventory")
    operation_items = [
        {"title": "품절 상품 점검", "count": 4, "summary": "판매 불가 상품 확인"},
        {"title": "가격/재고 점검", "count": 2, "summary": "이상치 상품 확인"},
        {"title": "노출 점검", "count": 3, "summary": "대표 상품 노출 상태"},
        {"title": "신규 등록 검수", "count": 2, "summary": "신규 상품 검토"},
        {"title": "상품 정보 수정", "count": 1, "summary": "상세 정보 보완"},
    ]
    return render(
        request,
        "users/vendor_operations.html",
        {
            **base_context,
            "vendor_operations_focus": focus,
            "vendor_operation_items": operation_items,
        },
    )


def logout_view(request):
    request.session.pop(SOCIAL_AUTH_ACCESS_SESSION_KEY, None)
    request.session.pop(SOCIAL_AUTH_REFRESH_SESSION_KEY, None)
    logout(request)
    return redirect("home")


def profile_view(request):
    preview_mode = request.GET.get("preview") == "1" or not request.user.is_authenticated

    if preview_mode:
        preview_profile = SimpleNamespace(nickname="", phone="", marketing_consent=False)
        preview_social_accounts = {
            "kakao": SimpleNamespace(email="tailtalk_user@kakao.com"),
        }
        if request.method == "POST":
            return redirect("pet_add")
        return render(
            request,
            "users/profile.html",
            {
                "profile": preview_profile,
                "profile_preview": True,
                "social_accounts": preview_social_accounts,
                "setup_mode": request.GET.get("setup") == "1",
            },
        )

    profile = _get_profile(request.user)
    if request.method == "POST":
        setup_mode = request.GET.get("setup") == "1"
        profile.nickname = request.POST.get("nickname", "").strip()
        profile.recipient_name = profile.nickname
        submitted_phone = "".join(char for char in request.POST.get("phone", "") if char.isdigit())[:11]
        if submitted_phone and not 10 <= len(submitted_phone) <= 11:
            messages.error(request, "연락처는 10~11자리 숫자만 입력해 주세요.")
            return _render_profile(request, profile)
        if submitted_phone != (profile.phone or "") and submitted_phone:
            messages.error(request, "연락처 인증을 완료해 주세요.")
            return _render_profile(request, profile)
        if submitted_phone and not profile.phone_verified:
            messages.error(request, "연락처 인증을 완료해 주세요.")
            return _render_profile(request, profile)
        if not submitted_phone:
            profile.phone = ""
            profile.phone_verified = False
            profile.phone_verified_at = None
            profile.clear_phone_verification()
        else:
            profile.phone = submitted_phone
        postal_code = request.POST.get("zipcode", "").strip()
        address_main = request.POST.get("address_main", "").strip()
        address_detail = request.POST.get("address_detail", "").strip()
        profile.postal_code = postal_code
        profile.address_main = address_main
        profile.address_detail = address_detail
        if address_main or address_detail:
            profile.address = " | ".join(part for part in [address_main, address_detail] if part)
        else:
            profile.address = ""
        profile.payment_card_provider = request.POST.get("payment_card_provider", "").strip()
        profile.payment_card_masked_number = request.POST.get("payment_card_masked_number", "").strip()
        profile.payment_token_reference = request.POST.get("payment_token_reference", "").strip()
        profile.payment_is_default = True
        profile.payment_method = request.POST.get("payment_method", "").strip()
        profile.marketing_consent = request.POST.get("marketing") == "on"
        nickname_error = get_nickname_validation_error(profile.nickname, exclude_user=request.user)
        if nickname_error:
            messages.error(request, nickname_error)
            return _render_profile(request, profile)
        try:
            with transaction.atomic():
                profile.save(update_fields=[
                    "nickname",
                    "recipient_name",
                    "phone",
                    "phone_verified",
                    "phone_verified_at",
                    "phone_verification_code",
                    "phone_verification_target",
                    "phone_verification_expires_at",
                    "postal_code",
                    "address_main",
                    "address_detail",
                    "address",
                    "payment_card_provider",
                    "payment_card_masked_number",
                    "payment_is_default",
                    "payment_token_reference",
                    "payment_method",
                    "marketing_consent",
                    "updated_at",
                ])
        except IntegrityError:
            messages.error(request, "이미 사용 중인 닉네임입니다.")
            return _render_profile(request, profile)
        messages.success(request, "프로필 정보가 저장되었습니다.")
        if setup_mode:
            request.session.pop(ONBOARDING_FORCE_PROFILE_SESSION_KEY, None)
            if has_completed_pet_onboarding(request):
                return redirect("chat")
            return redirect("pet_add")
        return redirect("chat")

    return _render_profile(request, profile)


def profile_withdraw_view(request):
    if request.method != "POST":
        return redirect("profile")

    preview_mode = request.GET.get("preview") == "1" or not request.user.is_authenticated
    if preview_mode:
        return redirect("chat")

    deactivate_user_and_purge_personal_data(request.user)

    logout(request)
    messages.success(request, "회원 탈퇴가 완료되었습니다. 주문 기록을 제외한 사용자 정보가 정리되었습니다.")
    return redirect("home")


def social_login_start_view(request, provider):
    remember = request.GET.get("remember") == "on"
    redirect_uri = build_callback_url(request, "social-login-callback", provider)
    next_url = reverse("chat")

    try:
        authorization_url = build_authorization_url(
            request=request,
            provider=provider,
            redirect_uri=redirect_uri,
            next_url=next_url,
        )
    except SocialAuthServiceError as exc:
        messages.error(request, str(exc))
        return redirect("login")

    request.session[SOCIAL_AUTH_REMEMBER_SESSION_KEY] = remember
    return redirect(authorization_url)


def social_login_callback_view(request, provider):
    if request.GET.get("error"):
        logger.warning("OAuth provider returned error", extra={"provider": provider, "error": request.GET.get("error")})
        messages.error(request, "소셜 로그인 인증이 취소되었거나 실패했습니다.")
        return redirect("login")

    redirect_uri = build_callback_url(request, "social-login-callback", provider)

    try:
        result = complete_social_login(
            request=request,
            provider=provider,
            redirect_uri=redirect_uri,
        )
    except (AuthCanceled, AuthConnectionError, AuthMissingParameter, AuthForbidden, AuthException, SocialAuthServiceError) as exc:
        logger.warning("Social login exchange failed", extra={"provider": provider, "error": str(exc)})
        messages.error(request, str(exc))
        return redirect("login")

    user = result.user
    user.backend = result.backend_path
    login(request, user)
    if not request.session.get(SOCIAL_AUTH_REMEMBER_SESSION_KEY):
        request.session.set_expiry(0)

    tokens = issue_user_tokens(user)
    request.session[SOCIAL_AUTH_ACCESS_SESSION_KEY] = tokens["access"]
    request.session[SOCIAL_AUTH_REFRESH_SESSION_KEY] = tokens["refresh"]
    request.session.pop(SOCIAL_AUTH_REMEMBER_SESSION_KEY, None)
    messages.success(request, "소셜 로그인이 완료되었습니다.")
    if result.is_new_user:
        request.session[ONBOARDING_FORCE_PROFILE_SESSION_KEY] = True
        return redirect(f"{reverse('profile')}?setup=1")
    onboarding_redirect_url = get_onboarding_redirect_url(request)
    if onboarding_redirect_url:
        return redirect(onboarding_redirect_url)
    return redirect("chat")
