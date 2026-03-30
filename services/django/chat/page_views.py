import json

from django.db.models import Q
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie

from orders.models import Cart
from pets.future_profile import get_future_pet_profile_for_request
from products.catalog_menu import build_catalog_menu_context
from products.models import Product
from users.onboarding import get_onboarding_redirect_url


def _format_price(value):
    return f"{value:,}원"


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


def _serialize_recommended_product(product):
    return {
        "product_id": product.goods_id,
        "name": _display_product_name(product.brand_name, product.goods_name),
        "price": _format_price(product.price),
        "discount_price": "",
        "brand_name": product.brand_name,
        "thumbnail_url": product.thumbnail_url,
        "product_url": product.product_url,
        "rating": str(product.rating or "0.0"),
        "reviews": f"리뷰 {product.review_count}",
    }


def _serialize_cart_product(item):
    product = item.product
    price = product.price
    return {
        "product_id": product.goods_id,
        "name": _display_product_name(product.brand_name, product.goods_name),
        "summary": "장바구니에 담긴 상품",
        "price": _format_price(price),
        "thumbnail_url": product.thumbnail_url,
        "brand_name": product.brand_name,
        "rating": str(product.rating or "0.0"),
        "reviews": f"리뷰 {product.review_count}",
        "quantity": item.quantity,
        "unit_price": price,
        "badge": "장바구니",
        "accent": "bg-[#e9d5ff] text-[#7c3aed]",
    }


def _serialize_pet(pet):
    age_parts = []
    if pet.age_years:
        age_parts.append(f"{pet.age_years}년")
    if pet.age_months:
        age_parts.append(f"{pet.age_months}개월")
    age_label = " ".join(age_parts) if age_parts else "나이 정보 없음"
    breed = pet.breed or pet.get_species_display()

    def _list(val, attr_name=None):
        if not val:
            return []
        if isinstance(val, list):
            return val
        if attr_name and hasattr(val, "values_list"):
            return list(val.values_list(attr_name, flat=True))
        return [v.strip() for v in val.split(",") if v.strip()]
    return {
        "id": str(pet.pet_id),
        "name": pet.name,
        "species": pet.species,
        "emoji": "🐱" if pet.species == "cat" else "🐶",
        "summary": f"{breed} · {age_label}",
        # FastAPI로 넘길 전체 프로필
        "profile": {
            "species": pet.species,
            "breed": pet.breed or "",
            "age": age_label,
            "gender": pet.gender if hasattr(pet, "gender") else "",
            "weight": str(pet.weight_kg) if pet.weight_kg else "",
        },
        "health_concerns": _list(getattr(pet, "health_concerns", None), "concern"),
        "allergies": _list(getattr(pet, "allergies", None), "ingredient"),
        "food_preferences": _list(getattr(pet, "food_preferences", None), "food_type"),
        "profile_json": json.dumps(
            {
                "species": pet.species,
                "breed": pet.breed or "",
                "age": age_label,
                "gender": pet.gender if hasattr(pet, "gender") else "",
                "weight": str(pet.weight_kg) if pet.weight_kg else "",
            },
            ensure_ascii=False,
        ),
        "health_concerns_csv": ",".join(_list(getattr(pet, "health_concerns", None), "concern")),
        "allergies_csv": ",".join(_list(getattr(pet, "allergies", None), "ingredient")),
        "food_preferences_csv": ",".join(_list(getattr(pet, "food_preferences", None), "food_type")),
    }


def _serialize_future_pet(profile):
    if not profile:
        return None

    species_labels = {
        "dog": "강아지",
        "cat": "고양이",
        "undecided": "미정",
    }
    housing_labels = {
        "studio": "원룸",
        "apartment": "아파트",
        "house": "주택",
        "other": "기타",
    }
    experience_labels = {
        "first": "처음",
        "experienced": "경험 있음",
    }
    interest_labels = {
        "adoption": "입양 준비",
        "breed_personality": "품종/성격",
        "initial_cost": "초기 비용",
        "starter_items": "필수 용품",
        "food": "사료",
        "health": "건강관리",
        "training": "훈련/교육",
    }

    preferred_species = profile.get("preferred_species", "")
    interests = [interest_labels[value] for value in profile.get("interests", []) if value in interest_labels]

    future_profile = {
        "species": preferred_species if preferred_species in {"dog", "cat"} else "",
        "lifecycle": "future_guardian",
        "preferred_species": preferred_species,
        "housing_type": profile.get("housing_type", ""),
        "experience_level": profile.get("experience_level", ""),
        "interests": profile.get("interests", []),
    }

    if preferred_species == "dog":
        future_summary = "강아지 준비 중"
    elif preferred_species == "cat":
        future_summary = "고양이 준비 중"
    else:
        future_summary = "입양 준비 중"

    return {
        "id": "future-profile",
        "name": "예비 집사",
        "species": "future",
        "emoji": "🏠",
        "summary": future_summary,
        "profile": future_profile,
        "health_concerns": [],
        "allergies": [],
        "food_preferences": [],
        "profile_json": json.dumps(future_profile, ensure_ascii=False),
        "health_concerns_csv": "",
        "allergies_csv": "",
        "food_preferences_csv": "",
        "detail_lines": [
            housing_labels.get(profile.get("housing_type", ""), ""),
            experience_labels.get(profile.get("experience_level", ""), ""),
            ", ".join(interests) if interests else "",
        ],
    }


def _build_catalog_menu_context():
    return build_catalog_menu_context()


def _sort_member_pets(pets):
    return sorted(pets, key=lambda pet: pet.get("species") == "future")


def _preview_member_pets():
    return [
        {
            "id": "preview-dog",
            "name": "콩이",
            "species": "dog",
            "emoji": "🐶",
            "summary": "말티즈 · 2년 3개월",
        },
        {
            "id": "preview-cat",
            "name": "모찌",
            "species": "cat",
            "emoji": "🐱",
            "summary": "브리티시 숏헤어 · 1년 8개월",
        },
        {
            "id": "preview-dog-2",
            "name": "보리",
            "species": "dog",
            "emoji": "🐶",
            "summary": "푸들 · 5년 1개월",
        },
        {
            "id": "preview-cat-2",
            "name": "라떼",
            "species": "cat",
            "emoji": "🐱",
            "summary": "코리안 숏헤어 · 3년 4개월",
        },
        {
            "id": "preview-dog-3",
            "name": "두부",
            "species": "dog",
            "emoji": "🐶",
            "summary": "비숑 프리제 · 10개월",
        },
        {
            "id": "preview-cat-3",
            "name": "나비",
            "species": "cat",
            "emoji": "🐱",
            "summary": "러시안 블루 · 6년 2개월",
        },
    ]


def _preview_sessions():
    return [
        {
            "session_id": "preview-session-1",
            "title": "콩이 피부 가려움 상담",
            "created_at": "26/03/18",
        },
        {
            "session_id": "preview-session-2",
            "title": "모찌 습식 사료 추천",
            "created_at": "26/03/17",
        },
        {
            "session_id": "preview-session-3",
            "title": "눈물 자국 관리 방법",
            "created_at": "26/03/15",
        },
    ]


def _preview_session_threads():
    return {
        "preview-session-1": {
            "messages": [
                {"role": "user", "text": "콩이가 피부를 계속 긁는데 사료를 바꿔야 할까?"},
                {
                    "role": "assistant",
                    "text": "가려움이 반복된다면 원료를 단순화한 사료를 먼저 검토해볼 수 있습니다. 우측 패널에 피부 민감 아이에게 맞는 후보 상품을 정리해두었습니다.",
                },
            ]
        },
        "preview-session-2": {
            "messages": [
                {"role": "user", "text": "모찌가 습식 사료를 잘 안 먹는데 입문용 추천해줘"},
                {
                    "role": "assistant",
                    "text": "기호성이 높은 습식 위주로 먼저 시도해보는 게 좋습니다. 부담이 적은 제품부터 우측 추천 상품으로 확인해 주세요.",
                },
            ]
        },
        "preview-session-3": {
            "messages": [
                {"role": "user", "text": "눈물 자국 관리에 도움 되는 간식이나 영양제가 있을까?"},
                {
                    "role": "assistant",
                    "text": "알레르기 유발 가능성이 낮은 간식과 피부·모질 영양제를 함께 보는 편이 좋습니다. 관련 추천을 우측 패널에 정리해두었습니다.",
                },
            ]
        },
    }


def _build_quick_order_profile_context(user):
    profile = getattr(user, "profile", None)
    if profile is None:
        return {
            "quick_order_recipient": "이름 정보가 없습니다",
            "quick_order_address": "배송지 정보가 없습니다",
            "quick_order_phone": "연락처 정보가 없습니다",
            "quick_order_payment_method": "등록된 결제수단이 없습니다",
        }

    return {
        "quick_order_recipient": (profile.nickname or "").strip() or "이름 정보가 없습니다",
        "quick_order_address": (profile.address or "").strip() or "배송지 정보가 없습니다",
        "quick_order_phone": (profile.phone or "").strip() or "연락처 정보가 없습니다",
        "quick_order_payment_method": (profile.payment_method or "").strip() or "등록된 결제수단이 없습니다",
    }


@ensure_csrf_cookie
def chat_view(request):
    onboarding_redirect_url = get_onboarding_redirect_url(request)
    if onboarding_redirect_url:
        return redirect(onboarding_redirect_url)

    sessions = []
    preview_member = request.GET.get("preview") == "member"
    is_authenticated = request.user.is_authenticated
    is_member_view = is_authenticated or preview_member
    is_preview_member = preview_member and not is_authenticated
    chat_enabled = is_authenticated
    member_pets = []
    registered_pet_count = 0
    recommended_products = [
        {
            "name": "닥터독 하이포알러지 연어 사료",
            "summary": "민감한 아이를 위한 저알러지 레시피",
            "price": "39,800원",
            "emoji": "🐟",
            "rating": "4.8",
            "reviews": "리뷰 312",
            "badge": "추천",
            "accent": "bg-[#dbeafe] text-[#2563eb]",
        },
        {
            "name": "벨버드 덴탈 케어 껌",
            "summary": "치석 관리와 구취 케어에 적합",
            "price": "12,900원",
            "emoji": "🦴",
            "rating": "4.7",
            "reviews": "리뷰 188",
            "badge": "인기",
            "accent": "bg-[#dcfce7] text-[#16a34a]",
        },
        {
            "name": "뉴트리플랜 피부/모질 영양제",
            "summary": "오메가 밸런스 중심 영양 보충",
            "price": "27,500원",
            "emoji": "💊",
            "rating": "4.6",
            "reviews": "리뷰 96",
            "badge": "영양",
            "accent": "bg-[#fef3c7] text-[#d97706]",
        },
        {
            "name": "웰츠 스킨 케어 오리 사료",
            "summary": "피부 민감도를 고려한 저자극 레시피",
            "price": "31,200원",
            "emoji": "🦆",
            "rating": "4.5",
            "reviews": "리뷰 142",
            "badge": "추천",
            "accent": "bg-[#dbeafe] text-[#2563eb]",
        },
        {
            "name": "더리얼 소고기 트릿",
            "summary": "기호성이 좋은 훈련용 간식",
            "price": "9,800원",
            "emoji": "🥩",
            "rating": "4.7",
            "reviews": "리뷰 251",
            "badge": "인기",
            "accent": "bg-[#dcfce7] text-[#16a34a]",
        },
        {
            "name": "리얼펫 프로바이오틱스",
            "summary": "소화 밸런스를 위한 유산균 보충",
            "price": "22,900원",
            "emoji": "🧴",
            "rating": "4.6",
            "reviews": "리뷰 87",
            "badge": "영양",
            "accent": "bg-[#fef3c7] text-[#d97706]",
        },
        {
            "name": "베러펫 눈물 케어 영양제",
            "summary": "눈물 자국 관리 보조 영양제",
            "price": "18,500원",
            "emoji": "👀",
            "rating": "4.4",
            "reviews": "리뷰 64",
            "badge": "추천",
            "accent": "bg-[#dbeafe] text-[#2563eb]",
        },
    ]
    cart_products = [
        {
            "name": "하림 더리얼 퍼피 사료",
            "summary": "장바구니에 담긴 상품",
            "price": _format_price(34900),
            "emoji": "🐶",
            "rating": "4.8",
            "reviews": "리뷰 421",
            "quantity": 1,
            "unit_price": 34900,
            "badge": "장바구니",
            "accent": "bg-[#e9d5ff] text-[#7c3aed]",
        },
        {
            "name": "뉴트리플랜 피부/모질 영양제",
            "summary": "장바구니에 담긴 상품",
            "price": _format_price(27500),
            "emoji": "💊",
            "rating": "4.6",
            "reviews": "리뷰 96",
            "quantity": 2,
            "unit_price": 27500,
            "badge": "장바구니",
            "accent": "bg-[#e9d5ff] text-[#7c3aed]",
        },
        {
            "name": "벨버드 덴탈 케어 껌",
            "summary": "장바구니에 담긴 상품",
            "price": _format_price(12900),
            "emoji": "🦴",
            "rating": "4.7",
            "reviews": "리뷰 188",
            "quantity": 1,
            "unit_price": 12900,
            "badge": "장바구니",
            "accent": "bg-[#e9d5ff] text-[#7c3aed]",
        },
        {
            "name": "베러펫 눈물 케어 영양제",
            "summary": "장바구니에 담긴 상품",
            "price": _format_price(18500),
            "emoji": "👀",
            "rating": "4.4",
            "reviews": "리뷰 64",
            "quantity": 1,
            "unit_price": 18500,
            "badge": "장바구니",
            "accent": "bg-[#e9d5ff] text-[#7c3aed]",
        },
    ]
    cart_total = sum(product["unit_price"] * product["quantity"] for product in cart_products)
    promo_banners = [
        {
            "eyebrow": "기획전",
            "title": "봄맞이 알레르기 케어",
            "subtitle": "인기 사료 최대 30% 할인",
            "emoji": "🎁",
            "style": "background: linear-gradient(135deg, #3182ce 0%, #63b3ed 100%);",
        },
        {
            "eyebrow": "모음전",
            "title": "눈물 자국 케어 추천전",
            "subtitle": "영양제와 간식을 모아보기",
            "emoji": "✨",
            "style": "background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);",
        },
        {
            "eyebrow": "이벤트",
            "title": "첫 구매 고객 혜택",
            "subtitle": "추천 상품 장바구니 담기만 해도 쿠폰 지급",
            "emoji": "🎉",
            "style": "background: linear-gradient(135deg, #dd6b20 0%, #f6ad55 100%);",
        },
    ]
    if is_authenticated:
        sessions = list(
            request.user.chat_sessions.order_by("-updated_at", "-created_at").values("session_id", "title", "created_at", "updated_at")[:50]
        )
        registered_pet_count = request.user.pets.count()
        pets = request.user.pets.prefetch_related("health_concerns", "allergies", "food_preferences").order_by("created_at")[:5]
        member_pets = [_serialize_pet(pet) for pet in pets]
        recommended_source = list(_single_product_queryset()[:6])
        if recommended_source:
            recommended_products = [_serialize_recommended_product(product) for product in recommended_source]

        cart = Cart.objects.filter(user=request.user).prefetch_related("items__product").first()
        if cart:
            cart_products = [_serialize_cart_product(item) for item in cart.items.all().order_by("-added_at")]
            cart_total = sum(product["unit_price"] * product["quantity"] for product in cart_products)
        else:
            cart_products = []
            cart_total = 0

    quick_order_profile = _build_quick_order_profile_context(request.user) if is_authenticated else {
        "quick_order_recipient": "이름 정보가 없습니다",
        "quick_order_address": "배송지 정보가 없습니다",
        "quick_order_phone": "연락처 정보가 없습니다",
        "quick_order_payment_method": "등록된 결제수단이 없습니다",
    }

    future_pet = _serialize_future_pet(get_future_pet_profile_for_request(request))
    if future_pet:
        member_pets.append(future_pet)
        member_pets = _sort_member_pets(member_pets)

    if preview_member and not member_pets:
        member_pets = _preview_member_pets()
        registered_pet_count = len(member_pets)

    if preview_member and not sessions:
        sessions = _preview_sessions()

    session_threads = _preview_session_threads() if preview_member else {}

    active_pet_id = request.GET.get("pet", "")
    active_pet = next((pet for pet in member_pets if pet["id"] == active_pet_id), None)
    return render(
        request,
        "chat/index.html",
        {
            "sessions": sessions,
            "is_member_view": is_member_view,
            "is_preview_member": is_preview_member,
            "chat_enabled": chat_enabled,
            "member_pets": member_pets,
            "can_add_pet": is_member_view and registered_pet_count < 5,
            "active_pet_id": active_pet_id,
            "active_pet": active_pet,
            "recommended_products": recommended_products,
            "cart_products": cart_products,
            "cart_total": _format_price(cart_total),
            "promo_banners": promo_banners,
            "session_threads": session_threads,
            "catalog_menu_sections": _build_catalog_menu_context(),
            **quick_order_profile,
        },
    )
