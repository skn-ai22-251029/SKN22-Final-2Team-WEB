# Test RDS 실제 스키마 스냅샷

## 개요

이 문서는 `2026-03-26` 기준 테스트 Django Elastic Beanstalk 환경이 실제로 바라보고 있는 RDS PostgreSQL의 `public` 스키마를 스냅샷한 결과다.

수집 대상:

- EB 환경: `test-tailtalk-django-env`
- RDS 인스턴스: `test-tailtalk-postgres`
- DB 엔진: `PostgreSQL`

수집 방식:

- 로컬에서 RDS로 직접 붙는 대신
- 배포 중인 Django EB 인스턴스의 `current-django-1` 컨테이너 안에서
- `information_schema.tables`, `information_schema.columns`를 조회해 실제 스키마를 읽어왔다

주의:

- 이 문서는 로컬 `models.py` 기준이 아니라 실제 운영 중인 테스트 RDS 기준이다
- 따라서 현재 로컬 코드와 차이가 있을 수 있다

## 전체 테이블 수

- 총 `37`개 테이블

## 전체 테이블 목록

### 앱 비즈니스 테이블

- `cart`
- `cart_item`
- `chat_message`
- `chat_session`
- `order`
- `order_item`
- `pet`
- `pet_allergy`
- `pet_food_preference`
- `pet_health_concern`
- `pet_used_product`
- `product`
- `product_admin_config`
- `product_category_tag`
- `review`
- `social_account`
- `user`
- `user_interaction`
- `user_preference`
- `user_profile`
- `user_used_product`

### Django/Auth/세션/소셜 로그인 지원 테이블

- `auth_group`
- `auth_group_permissions`
- `auth_permission`
- `django_admin_log`
- `django_content_type`
- `django_migrations`
- `django_session`
- `social_auth_association`
- `social_auth_code`
- `social_auth_nonce`
- `social_auth_partial`
- `social_auth_usersocialauth`
- `token_blacklist_blacklistedtoken`
- `token_blacklist_outstandingtoken`
- `user_groups`
- `user_user_permissions`

## 현재 스냅샷에 없는 테이블

현재 테스트 RDS 스냅샷에는 아래 테이블이 없다.

- `wishlist`
- `wishlist_item`
- `domain_qna`
- `breed_meta`

즉, 로컬 코드나 별도 적재 스크립트 기준으로는 존재를 기대할 수 있어도 현재 테스트 EB가 바라보는 실제 RDS에는 아직 없는 상태다.

## 주요 테이블 컬럼 구조

### `user`

| Column | Type | Nullable |
| --- | --- | --- |
| `password` | `character varying` | `NO` |
| `last_login` | `timestamp with time zone` | `YES` |
| `is_superuser` | `boolean` | `NO` |
| `id` | `integer` | `NO` |
| `email` | `character varying` | `NO` |
| `created_at` | `timestamp with time zone` | `NO` |
| `is_active` | `boolean` | `NO` |
| `is_staff` | `boolean` | `NO` |

### `user_profile`

| Column | Type | Nullable |
| --- | --- | --- |
| `user_id` | `integer` | `NO` |
| `nickname` | `character varying` | `NO` |
| `age` | `integer` | `YES` |
| `gender` | `character varying` | `YES` |
| `address` | `text` | `YES` |
| `phone` | `character varying` | `YES` |
| `marketing_consent` | `boolean` | `NO` |
| `profile_image_url` | `text` | `YES` |
| `updated_at` | `timestamp with time zone` | `NO` |

### `social_account`

| Column | Type | Nullable |
| --- | --- | --- |
| `id` | `bigint` | `NO` |
| `provider` | `character varying` | `NO` |
| `provider_user_id` | `character varying` | `NO` |
| `email` | `character varying` | `NO` |
| `extra_data` | `jsonb` | `NO` |
| `created_at` | `timestamp with time zone` | `NO` |
| `updated_at` | `timestamp with time zone` | `NO` |
| `user_id` | `integer` | `NO` |

### `user_preference`

| Column | Type | Nullable |
| --- | --- | --- |
| `user_id` | `integer` | `NO` |
| `theme` | `character varying` | `NO` |
| `updated_at` | `timestamp with time zone` | `NO` |

### `user_used_product`

| Column | Type | Nullable |
| --- | --- | --- |
| `id` | `uuid` | `NO` |
| `created_at` | `timestamp with time zone` | `NO` |
| `product_id` | `character varying` | `NO` |
| `user_id` | `integer` | `NO` |

### `pet`

| Column | Type | Nullable |
| --- | --- | --- |
| `pet_id` | `uuid` | `NO` |
| `name` | `character varying` | `NO` |
| `species` | `character varying` | `NO` |
| `breed` | `character varying` | `YES` |
| `gender` | `character varying` | `NO` |
| `age_years` | `integer` | `NO` |
| `age_months` | `integer` | `NO` |
| `weight_kg` | `numeric` | `YES` |
| `neutered` | `boolean` | `YES` |
| `vaccination_date` | `date` | `YES` |
| `budget_range` | `character varying` | `NO` |
| `special_notes` | `text` | `YES` |
| `created_at` | `timestamp with time zone` | `NO` |
| `updated_at` | `timestamp with time zone` | `NO` |
| `user_id` | `integer` | `NO` |

### `pet_health_concern`

| Column | Type | Nullable |
| --- | --- | --- |
| `id` | `uuid` | `NO` |
| `concern` | `character varying` | `NO` |
| `pet_id` | `uuid` | `NO` |

### `pet_allergy`

| Column | Type | Nullable |
| --- | --- | --- |
| `id` | `uuid` | `NO` |
| `ingredient` | `character varying` | `NO` |
| `pet_id` | `uuid` | `NO` |

### `pet_food_preference`

| Column | Type | Nullable |
| --- | --- | --- |
| `id` | `uuid` | `NO` |
| `food_type` | `character varying` | `NO` |
| `pet_id` | `uuid` | `NO` |

### `pet_used_product`

| Column | Type | Nullable |
| --- | --- | --- |
| `id` | `uuid` | `NO` |
| `pet_id` | `uuid` | `NO` |
| `product_id` | `character varying` | `NO` |

### `chat_session`

| Column | Type | Nullable |
| --- | --- | --- |
| `session_id` | `uuid` | `NO` |
| `title` | `text` | `NO` |
| `created_at` | `timestamp with time zone` | `NO` |
| `updated_at` | `timestamp with time zone` | `NO` |
| `target_pet_id` | `uuid` | `YES` |
| `user_id` | `integer` | `NO` |

### `chat_message`

| Column | Type | Nullable |
| --- | --- | --- |
| `message_id` | `uuid` | `NO` |
| `role` | `character varying` | `NO` |
| `content` | `text` | `NO` |
| `created_at` | `timestamp with time zone` | `NO` |
| `session_id` | `uuid` | `NO` |

### `cart`

| Column | Type | Nullable |
| --- | --- | --- |
| `cart_id` | `uuid` | `NO` |
| `updated_at` | `timestamp with time zone` | `NO` |
| `user_id` | `integer` | `NO` |

### `cart_item`

| Column | Type | Nullable |
| --- | --- | --- |
| `cart_item_id` | `uuid` | `NO` |
| `quantity` | `integer` | `NO` |
| `added_at` | `timestamp with time zone` | `NO` |
| `cart_id` | `uuid` | `NO` |
| `product_id` | `character varying` | `NO` |

### `order`

| Column | Type | Nullable |
| --- | --- | --- |
| `order_id` | `uuid` | `NO` |
| `recipient_name` | `character varying` | `NO` |
| `delivery_address` | `text` | `NO` |
| `total_price` | `integer` | `NO` |
| `status` | `character varying` | `NO` |
| `created_at` | `timestamp with time zone` | `NO` |
| `user_id` | `integer` | `NO` |

### `order_item`

| Column | Type | Nullable |
| --- | --- | --- |
| `order_item_id` | `uuid` | `NO` |
| `quantity` | `integer` | `NO` |
| `price_at_order` | `integer` | `NO` |
| `order_id` | `uuid` | `NO` |
| `product_id` | `character varying` | `NO` |

### `user_interaction`

| Column | Type | Nullable |
| --- | --- | --- |
| `id` | `uuid` | `NO` |
| `session_id` | `uuid` | `YES` |
| `interaction_type` | `character varying` | `NO` |
| `weight` | `smallint` | `NO` |
| `created_at` | `timestamp with time zone` | `NO` |
| `product_id` | `character varying` | `NO` |
| `user_id` | `integer` | `NO` |

### `product`

| Column | Type | Nullable |
| --- | --- | --- |
| `goods_id` | `character varying` | `NO` |
| `goods_name` | `text` | `NO` |
| `brand_name` | `character varying` | `NO` |
| `price` | `integer` | `NO` |
| `discount_price` | `integer` | `NO` |
| `rating` | `numeric` | `YES` |
| `review_count` | `integer` | `NO` |
| `thumbnail_url` | `text` | `NO` |
| `product_url` | `text` | `NO` |
| `soldout_yn` | `boolean` | `NO` |
| `soldout_reliable` | `boolean` | `NO` |
| `pet_type` | `ARRAY` | `NO` |
| `category` | `ARRAY` | `NO` |
| `subcategory` | `ARRAY` | `NO` |
| `health_concern_tags` | `ARRAY` | `NO` |
| `popularity_score` | `numeric` | `YES` |
| `sentiment_avg` | `numeric` | `YES` |
| `repeat_rate` | `numeric` | `YES` |
| `main_ingredients` | `jsonb` | `YES` |
| `ingredient_composition` | `jsonb` | `YES` |
| `nutrition_info` | `jsonb` | `YES` |
| `ingredient_text_ocr` | `text` | `YES` |
| `crawled_at` | `timestamp with time zone` | `NO` |
| `embedding` | `USER-DEFINED` | `YES` |
| `embedding_text` | `text` | `YES` |
| `prefix` | `character varying` | `NO` |
| `search_vector` | `tsvector` | `YES` |
| `생체반응` | `numeric` | `NO` |
| `배송/포장` | `numeric` | `NO` |
| `소화/배변` | `numeric` | `NO` |
| `성분/원료` | `numeric` | `NO` |
| `기호성` | `numeric` | `NO` |
| `가격/구매` | `numeric` | `NO` |
| `제품 성상` | `numeric` | `NO` |
| `냄새` | `numeric` | `NO` |

참고:

- `information_schema` 기준으로 `embedding` 타입은 `USER-DEFINED`로 보인다
- 현재 프로젝트 문맥상 `pgvector`의 `vector` 타입 컬럼으로 해석하는 것이 자연스럽다

### `product_admin_config`

| Column | Type | Nullable |
| --- | --- | --- |
| `id` | `uuid` | `NO` |
| `admin_weight` | `numeric` | `NO` |
| `pinned` | `boolean` | `NO` |
| `memo` | `text` | `YES` |
| `updated_at` | `timestamp with time zone` | `NO` |
| `product_id` | `character varying` | `NO` |

### `product_category_tag`

| Column | Type | Nullable |
| --- | --- | --- |
| `id` | `uuid` | `NO` |
| `tag` | `character varying` | `NO` |
| `product_id` | `character varying` | `NO` |

### `review`

| Column | Type | Nullable |
| --- | --- | --- |
| `review_id` | `character varying` | `NO` |
| `score` | `numeric` | `NO` |
| `content` | `text` | `NO` |
| `author_nickname` | `character varying` | `NO` |
| `written_at` | `date` | `NO` |
| `purchase_label` | `character varying` | `YES` |
| `sentiment_score` | `numeric` | `YES` |
| `sentiment_label` | `character varying` | `YES` |
| `absa_result` | `jsonb` | `YES` |
| `pet_age_months` | `integer` | `YES` |
| `pet_weight_kg` | `numeric` | `YES` |
| `pet_gender` | `character varying` | `YES` |
| `pet_breed` | `character varying` | `YES` |
| `product_id` | `character varying` | `NO` |
| `생체반응` | `integer` | `NO` |
| `배송/포장` | `integer` | `NO` |
| `소화/배변` | `integer` | `NO` |
| `성분/원료` | `integer` | `NO` |
| `기호성` | `integer` | `NO` |
| `가격/구매` | `integer` | `NO` |
| `제품 성상` | `integer` | `NO` |
| `냄새` | `integer` | `NO` |

## 참고 메모

- 현재 스냅샷에는 `wishlist`, `wishlist_item` 테이블이 없다
- 현재 스냅샷에는 `domain_qna`, `breed_meta` 테이블도 없다
- 즉, 로컬 코드나 적재 스크립트와 실제 테스트 RDS가 완전히 같은 상태라고 가정하면 안 된다
- 스키마 변경 여부를 판단할 때는 이 문서와 함께 `django_migrations` 상태도 같이 확인하는 편이 안전하다
