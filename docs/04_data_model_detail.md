# 데이터 모델 상세 명세

> `requirements_spec_v1.md` 6.0 ERD의 각 엔티티별 컬럼 상세 정의

---

## 6.1 User

```json
{
  "user_id": "uuid",
  "email": "string",
  "password_hash": "string | null",
  "oauth_provider": "google | kakao | naver | null",
  "name": "string",
  "age": "int | null",
  "gender": "string | null",
  "address": "string | null",
  "profile_image_url": "string | null",
  "created_at": "datetime",
  "preferences": {
    "response_style": "concise | detailed",
    "card_count": 1 | 3 | 5,
    "save_history": true | false,
    "language": "ko | en"
  }
}
```

## 6.2 Pet Profile

```json
{
  "pet_id": "uuid",
  "user_id": "uuid",
  "name": "string",
  "species": "cat | dog",
  "breed": "string | null",
  "gender": "male | female",
  "age_years": "int",
  "age_months": "int",
  "weight_kg": "float | null",
  "neutered": "true | false | null",
  "vaccination_date": "date | null",
  "health_concerns": ["skin", "joint", "digestion", "weight", "urinary", "eye", "hairball", "dental", "immunity"],
  "allergies": ["string"],
  "food_type_preference": ["dry", "wet_can", "wet_pouch", "freeze_dried", "raw"],
  "budget_range": "under_10k | 10k_30k | 30k_50k | over_50k",
  "used_product_ids": ["string"],
  "special_notes": "string | null",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## 6.3 Chat Session

```json
{
  "session_id": "uuid",
  "user_id": "uuid | null",
  "title": "string",
  "target_pet_id": "uuid | null",
  "messages": [
    {
      "role": "user | assistant",
      "content": "string",
      "product_cards": ["ProductCard"],
      "created_at": "datetime"
    }
  ],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## 6.4 Product Card

```json
{
  "goods_id": "string",
  "goods_name": "string",
  "brand_name": "string",
  "price": "int",
  "discount_price": "int",
  "rating": "float",
  "review_count": "int",
  "thumbnail_url": "string",
  "product_url": "string",
  "category_tags": ["string"],
  "reason": "string"
}
```

## 6.5 Cart

```json
{
  "cart_id": "uuid",
  "user_id": "uuid | null",
  "items": [
    {
      "goods_id": "string",
      "goods_name": "string",
      "price": "int",
      "thumbnail_url": "string",
      "quantity": "int",
      "added_at": "datetime"
    }
  ],
  "updated_at": "datetime"
}
```

## 6.6 Order

```json
{
  "order_id": "uuid",
  "user_id": "uuid",
  "items": ["CartItem"],
  "total_price": "int",
  "status": "pending | completed | cancelled",
  "created_at": "datetime"
}
```
