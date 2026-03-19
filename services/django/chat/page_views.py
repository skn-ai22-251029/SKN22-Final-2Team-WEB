from django.shortcuts import render


def _serialize_pet(pet):
    age_parts = []
    if pet.age_years:
        age_parts.append(f"{pet.age_years}년")
    if pet.age_months:
        age_parts.append(f"{pet.age_months}개월")
    age_label = " ".join(age_parts) if age_parts else "나이 정보 없음"
    breed = pet.breed or pet.get_species_display()
    return {
        "id": str(pet.pet_id),
        "name": pet.name,
        "species": pet.species,
        "emoji": "🐱" if pet.species == "cat" else "🐶",
        "summary": f"{breed} · {age_label}",
    }


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


def chat_view(request):
    sessions = []
    preview_member = request.GET.get("preview") == "member"
    is_authenticated = request.user.is_authenticated
    is_member_view = is_authenticated or preview_member
    is_preview_member = preview_member and not is_authenticated
    member_pets = []
    recommended_products = [
        {
            "name": "닥터독 하이포알러지 연어 사료",
            "summary": "민감한 아이를 위한 저알러지 레시피",
            "price": "39,800원",
            "rating": "4.8",
            "reviews": "리뷰 312",
            "badge": "추천",
            "accent": "bg-[#dbeafe] text-[#2563eb]",
        },
        {
            "name": "벨버드 덴탈 케어 껌",
            "summary": "치석 관리와 구취 케어에 적합",
            "price": "12,900원",
            "rating": "4.7",
            "reviews": "리뷰 188",
            "badge": "인기",
            "accent": "bg-[#dcfce7] text-[#16a34a]",
        },
        {
            "name": "뉴트리플랜 피부/모질 영양제",
            "summary": "오메가 밸런스 중심 영양 보충",
            "price": "27,500원",
            "rating": "4.6",
            "reviews": "리뷰 96",
            "badge": "영양",
            "accent": "bg-[#fef3c7] text-[#d97706]",
        },
    ]
    cart_products = [
        {
            "name": "하림 더리얼 퍼피 사료",
            "summary": "장바구니에 담긴 상품",
            "price": "34,900원",
            "rating": "4.8",
            "reviews": "리뷰 421",
            "badge": "장바구니",
            "accent": "bg-[#e9d5ff] text-[#7c3aed]",
        }
    ]
    if is_authenticated:
        sessions = list(
            request.user.chat_sessions.order_by("-created_at").values("session_id", "title", "created_at")[:50]
        )
        member_pets = [_serialize_pet(pet) for pet in request.user.pets.order_by("created_at")[:5]]

    if preview_member and not member_pets:
        member_pets = _preview_member_pets()

    if preview_member and not sessions:
        sessions = _preview_sessions()

    session_threads = _preview_session_threads() if preview_member else {}

    active_pet_id = request.GET.get("pet") or (member_pets[0]["id"] if member_pets else "")
    active_pet = next((pet for pet in member_pets if pet["id"] == active_pet_id), member_pets[0] if member_pets else None)
    return render(
        request,
        "chat/index.html",
        {
            "sessions": sessions,
            "is_member_view": is_member_view,
            "is_preview_member": is_preview_member,
            "member_pets": member_pets,
            "active_pet_id": active_pet_id,
            "active_pet": active_pet,
            "recommended_products": recommended_products,
            "cart_products": cart_products,
            "session_threads": session_threads,
        },
    )
