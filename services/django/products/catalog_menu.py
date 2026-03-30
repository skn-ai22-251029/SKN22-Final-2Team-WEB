from collections import Counter, defaultdict

from .models import Product


def build_catalog_menu_context():
    pet_labels = ["강아지", "고양이"]
    rows = Product.objects.filter(soldout_yn=False).values_list("pet_type", "category", "subcategory")[:5000]
    grouped_raw = {label: defaultdict(Counter) for label in pet_labels}

    for pet_types, categories, subcategories in rows:
        normalized_pet_types = [value for value in (pet_types or []) if value in pet_labels]
        normalized_categories = [value for value in (categories or []) if value]
        normalized_subcategories = [value for value in (subcategories or []) if value]

        for pet_type in normalized_pet_types:
            for category in normalized_categories:
                for subcategory in normalized_subcategories or ["(없음)"]:
                    grouped_raw[pet_type][category][subcategory] += 1

    category_order = {
        "강아지": ["사료", "간식", "용품", "배변용품", "덴탈관"],
        "고양이": ["사료", "간식", "용품", "모래", "습식관"],
    }
    category_labels = {}
    group_definitions = {
        "강아지": {
            "사료": [
                ("급여 연령", ["퍼피(1세미만)", "어덜트(1~7세)", "시니어(7세이상)", "전연령"]),
                ("종류", ["건식사료", "화식", "소프트사료", "습식사료", "동결건조/에어드라이"]),
                ("기능", ["처방식", "눈/눈물", "체중조절", "피부/모질", "위장/소화", "관절", "중성화", "스트레스 완화", ("구강/치아 (덴탈케어)", "구강/치아(덴탈케어)"), "견종별"]),
                ("주요 브랜드", ["아카나", "오리젠"]),
                ("기타", [("맛보기 샘플", "맛보기샘플"), ("유통기한임박", "유통기한 임박")]),
            ],
            "간식": [
                ("전체", ["덴탈껌", "원물/뼈간식", "캔/파우치", "져키/트릿", "비스킷/쿠키", "사사미", "통살/소시지", "동결/건조간식", "수제간식", "파우더", "음료/분유/우유", "영양/기능", ("유통기한 임박", "유통기한 임박")]),
            ],
            "용품": [
                ("전체", ["구강관리", "건강관리", "미용/목욕", "급식/급수기", "장난감/훈련", "의류/악세사리", "하우스/방석", "이동장/캐리어", "목줄/하네스", "반려인용품", ("유통기한 임박", "유통기한 임박")]),
            ],
            "덴탈관": [
                ("전체", ["수의사인증", "덴탈껌", "칫솔", "치약", "원물/뼈간식"]),
            ],
            "배변용품": [
                ("전체", ["배변패드", "배변판", "기저귀/팬티", "탈취/소독", "배변봉투/집게", "배변유도제", "물티슈/클리너"]),
            ],
        },
        "고양이": {
            "사료": [
                ("급여 연령", ["키튼(1세미만)", "어덜트(1~7세)", "시니어(7세이상)", "전연령"]),
                ("종류", ["주식캔", "건식", "주식파우치", "에어/동결건조"]),
                ("기능", ["처방식", "헤어볼", "피부/피모", "위장/소화", "요로기계", "체중조절", ("구강/치아 (덴탈케어)", "구강/치아(덴탈케어)"), "면역력", "묘종별"]),
                ("기타", [("맛보기 샘플", "맛보기샘플"), ("유통기한 임박", "유통기한 임박")]),
            ],
            "습식관": [
                ("전체", ["주식캔", "주식파우치"]),
            ],
            "간식": [
                ("전체", ["간식캔", "간식파우치", "동결/건조간식", "스낵/캔디", "져키/스틱", "통살/소시지", "음료", "파우더/토퍼", "영양/기능", ("유통기한 임박", "유통기한 임박")]),
            ],
            "모래": [
                ("전체", ["두부모래", "카사바/천연모래", "벤토나이트", ("기타 모래", "기타모래")]),
            ],
            "용품": [
                ("전체", ["건강관리", "장난감/캣닢", "스크래쳐/캣타워", "치아관리", "화장실/위생", "미용/목욕", "급식/급수기", "의류/악세사리", "하우스/방석", "이동장/캐리어", "반려인용품", ("유통기한 임박", "유통기한 임박")]),
            ],
        },
    }
    strict_category_groups = {
        "강아지": {"사료", "간식", "용품", "배변용품", "덴탈관"},
        "고양이": {"사료", "습식관", "간식", "용품", "모래"},
    }
    strict_category_order_pets = {"강아지", "고양이"}

    def build_category_href(pet_type, category):
        if category:
            return f"/catalog/?pet={pet_type}&category={category}"
        return f"/catalog/?pet={pet_type}"

    sections = []
    for pet_type in pet_labels:
        categories = []
        ordered_categories = []
        seen_categories = set()
        for category in category_order.get(pet_type, []):
            if category in grouped_raw[pet_type]:
                ordered_categories.append(category)
                seen_categories.add(category)
        if pet_type not in strict_category_order_pets:
            for category, _counter in sorted(grouped_raw[pet_type].items(), key=lambda item: (-sum(item[1].values()), item[0])):
                if category not in seen_categories:
                    ordered_categories.append(category)

        for category in ordered_categories:
            raw_counter = grouped_raw[pet_type].get(category, Counter())
            if not raw_counter:
                continue

            group_config = group_definitions.get(pet_type, {}).get(category, [])
            used_subcategories = set()
            groups = []
            for group_label, group_items in group_config:
                items = []
                for subcategory in group_items:
                    display_label = subcategory
                    raw_value = subcategory
                    is_brand = False
                    if isinstance(subcategory, (tuple, list)) and len(subcategory) >= 2:
                        display_label = subcategory[0]
                        raw_value = subcategory[1]
                    if category == "사료" and group_label == "주요 브랜드":
                        is_brand = True
                        brand_products = Product.objects.filter(
                            soldout_yn=False,
                            pet_type__contains=[pet_type],
                            brand_name=raw_value,
                        )
                        if not brand_products.exists():
                            continue
                    elif raw_counter.get(raw_value, 0) <= 0:
                        continue
                    if not is_brand:
                        used_subcategories.add(raw_value)
                    href = build_category_href(pet_type, category)
                    if is_brand:
                        href += f"&brand={raw_value}"
                    elif category:
                        href += f"&subcategory={raw_value}"
                    else:
                        href = f"/catalog/?pet={pet_type}&subcategory={raw_value}"
                    items.append({"label": display_label, "href": href})
                if items:
                    groups.append({"label": group_label, "items": items})

            remaining = []
            if category not in strict_category_groups.get(pet_type, set()):
                remaining = [
                    subcategory
                    for subcategory, _count in sorted(raw_counter.items(), key=lambda item: (-item[1], item[0]))
                    if subcategory not in used_subcategories
                ]
            if remaining:
                items = []
                for subcategory in remaining:
                    href = build_category_href(pet_type, category)
                    if category:
                        href += f"&subcategory={subcategory}"
                    else:
                        href = f"/catalog/?pet={pet_type}&subcategory={subcategory}"
                    items.append({"label": subcategory, "href": href})
                groups.append({"label": "기타", "items": items})

            categories.append(
                {
                    "label": category_labels.get(category, category),
                    "href": build_category_href(pet_type, category),
                    "groups": groups,
                }
            )

        sections.append(
            {
                "label": pet_type,
                "href": f"/catalog/?pet={pet_type}",
                "categories": categories,
            }
        )

    return sections
