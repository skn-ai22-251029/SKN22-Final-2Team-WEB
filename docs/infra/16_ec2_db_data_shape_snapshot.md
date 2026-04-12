# EC2 PostgreSQL 데이터 형태 스냅샷

- 생성일: 2026-04-12 14:22:48 UTC+09:00
- 대상: `test-tailtalk-db` EC2 내부 PostgreSQL
- 접속 경로: AWS SSM port forwarding `127.0.0.1:15432 -> 172.16.3.249:5432`
- Database: `tailtalk`
- User: `tailtalk`
- 포함 범위: `public` schema의 base table
- 샘플 정책: 실제 값은 저장하지 않고 데이터 형태만 기록한다. 이메일, 전화번호, 주소, 토큰, 비밀번호, 벡터 원문은 노출하지 않는다.

## 전체 요약

| Table | Rows | Primary Key | Foreign Keys |
|---|---:|---|---|
| `auth_group` | 0 | `id` | 0 |
| `auth_group_permissions` | 0 | `id` | 2 |
| `auth_permission` | 152 | `id` | 1 |
| `breed_meta` | 1125 | `id` | 0 |
| `cart` | 8 | `cart_id` | 1 |
| `cart_item` | 3 | `cart_item_id` | 2 |
| `chat_message` | 545 | `message_id` | 1 |
| `chat_message_recommendation` | 495 | `id` | 2 |
| `chat_session` | 67 | `session_id` | 2 |
| `chat_session_memory` | 25 | `session_id` | 1 |
| `django_admin_log` | 0 | `id` | 2 |
| `django_content_type` | 38 | `id` | 0 |
| `django_migrations` | 84 | `id` | 0 |
| `django_session` | 83 | `session_key` | 0 |
| `domain_qna` | 2411 | `id` | 0 |
| `future_pet_profile` | 3 | `id` | 1 |
| `order` | 16 | `order_id` | 1 |
| `order_item` | 26 | `order_item_id` | 2 |
| `pet` | 8 | `pet_id` | 1 |
| `pet_allergy` | 19 | `id` | 1 |
| `pet_food_preference` | 3 | `id` | 1 |
| `pet_health_concern` | 5 | `id` | 1 |
| `pet_used_product` | 0 | `id` | 2 |
| `product` | 4902 | `goods_id` | 0 |
| `product_admin_config` | 0 | `id` | 1 |
| `product_category_tag` | 659 | `id` | 1 |
| `review` | 349277 | `review_id` | 1 |
| `social_account` | 9 | `id` | 1 |
| `social_auth_association` | 0 | `id` | 0 |
| `social_auth_code` | 0 | `id` | 0 |
| `social_auth_nonce` | 0 | `id` | 0 |
| `social_auth_partial` | 0 | `id` | 0 |
| `social_auth_usersocialauth` | 9 | `id` | 1 |
| `token_blacklist_blacklistedtoken` | 0 | `id` | 1 |
| `token_blacklist_outstandingtoken` | 106 | `id` | 1 |
| `user` | 25 | `id` | 0 |
| `user_groups` | 0 | `id` | 2 |
| `user_interaction` | 658 | `id` | 2 |
| `user_preference` | 0 | `user_id` | 1 |
| `user_profile` | 20 | `user_id` | 1 |
| `user_used_product` | 0 | `id` | 2 |
| `user_user_permissions` | 0 | `id` | 2 |
| `wishlist` | 8 | `wishlist_id` | 1 |
| `wishlist_item` | 3 | `wishlist_item_id` | 2 |

## `auth_group`

- Rows: `0`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `integer` | `NO` | `` | `-` |
| `name` | `varchar(150)` | `NO` | `` | `-` |

## `auth_group_permissions`

- Rows: `0`
- Primary key: `id`
- Foreign keys:
  - `group_id` -> `auth_group.id`
  - `permission_id` -> `auth_permission.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `-` |
| `group_id` | `integer` | `NO` | `` | `-` |
| `permission_id` | `integer` | `NO` | `` | `-` |

## `auth_permission`

- Rows: `152`
- Primary key: `id`
- Foreign keys:
  - `content_type_id` -> `django_content_type.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `integer` | `NO` | `` | `<integer>` |
| `name` | `varchar(255)` | `NO` | `` | `<string len=17>` |
| `content_type_id` | `integer` | `NO` | `` | `<integer>` |
| `codename` | `varchar(100)` | `NO` | `` | `<string len=12>` |

## `breed_meta`

- Rows: `1125`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `integer` | `NO` | `nextval('breed_meta_id_seq'::regclass)` | `<integer>` |
| `species` | `varchar(10)` | `YES` | `` | `<string len=3>` |
| `breed_name` | `varchar(100)` | `YES` | `` | `<string len=5>` |
| `breed_name_en` | `varchar(100)` | `YES` | `` | `<string len=13>` |
| `group_name` | `varchar(50)` | `YES` | `` | `<string len=3>` |
| `size_class` | `_text[]` | `YES` | `` | `<array len=1 item=<string len=1>>` |
| `age_group` | `varchar(20)` | `YES` | `` | `<string len=2>` |
| `care_difficulty` | `integer` | `YES` | `` | `<integer>` |
| `preferred_food` | `text` | `YES` | `` | `<string len=10>` |
| `health_products` | `text` | `YES` | `` | `<string len=6>` |
| `chunk_text` | `text` | `YES` | `` | `-` |
| `embedding` | `vector` | `YES` | `` | `-` |
| `search_vector` | `tsvector` | `YES` | `` | `-` |

## `cart`

- Rows: `8`
- Primary key: `cart_id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `cart_id` | `uuid` | `NO` | `` | `<uuid>` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `user_id` | `integer` | `NO` | `` | `<integer>` |

## `cart_item`

- Rows: `3`
- Primary key: `cart_item_id`
- Foreign keys:
  - `cart_id` -> `cart.cart_id`
  - `product_id` -> `product.goods_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `cart_item_id` | `uuid` | `NO` | `` | `<uuid>` |
| `quantity` | `integer` | `NO` | `` | `<integer>` |
| `added_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `cart_id` | `uuid` | `NO` | `` | `<uuid>` |
| `product_id` | `varchar(20)` | `NO` | `` | `<string len=11>` |

## `chat_message`

- Rows: `545`
- Primary key: `message_id`
- Foreign keys:
  - `session_id` -> `chat_session.session_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `message_id` | `uuid` | `NO` | `` | `<uuid>` |
| `role` | `varchar(10)` | `NO` | `` | `<string len=9>` |
| `content` | `text` | `NO` | `` | `<string len=35>` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `session_id` | `uuid` | `NO` | `` | `<uuid>` |

## `chat_message_recommendation`

- Rows: `495`
- Primary key: `id`
- Foreign keys:
  - `message_id` -> `chat_message.message_id`
  - `product_id` -> `product.goods_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `uuid` | `NO` | `` | `<uuid>` |
| `rank_order` | `integer` | `NO` | `` | `<integer>` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `message_id` | `uuid` | `NO` | `` | `<uuid>` |
| `product_id` | `varchar(20)` | `NO` | `` | `<string len=11>` |

## `chat_session`

- Rows: `67`
- Primary key: `session_id`
- Foreign keys:
  - `target_pet_id` -> `pet.pet_id`
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `session_id` | `uuid` | `NO` | `` | `<uuid>` |
| `title` | `text` | `NO` | `` | `<string len=7>` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `target_pet_id` | `uuid` | `YES` | `` | `<uuid>` |
| `user_id` | `integer` | `NO` | `` | `<integer>` |
| `profile_context_type` | `varchar(10)` | `NO` | `` | `<string len=3>` |

## `chat_session_memory`

- Rows: `25`
- Primary key: `session_id`
- Foreign keys:
  - `session_id` -> `chat_session.session_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `session_id` | `uuid` | `NO` | `` | `<uuid>` |
| `summary_text` | `text` | `NO` | `` | `<empty string>` |
| `dialog_state` | `jsonb` | `NO` | `` | `<text len=612>` |
| `last_compacted_message_id` | `uuid` | `YES` | `` | `<null>` |
| `version` | `integer` | `NO` | `` | `<integer>` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |

## `django_admin_log`

- Rows: `0`
- Primary key: `id`
- Foreign keys:
  - `content_type_id` -> `django_content_type.id`
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `integer` | `NO` | `` | `-` |
| `action_time` | `timestamp with time zone` | `NO` | `` | `-` |
| `object_id` | `text` | `YES` | `` | `-` |
| `object_repr` | `varchar(200)` | `NO` | `` | `-` |
| `action_flag` | `smallint` | `NO` | `` | `-` |
| `change_message` | `text` | `NO` | `` | `-` |
| `content_type_id` | `integer` | `YES` | `` | `-` |
| `user_id` | `integer` | `NO` | `` | `-` |

## `django_content_type`

- Rows: `38`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `integer` | `NO` | `` | `<integer>` |
| `app_label` | `varchar(100)` | `NO` | `` | `<string len=5>` |
| `model` | `varchar(100)` | `NO` | `` | `<string len=8>` |

## `django_migrations`

- Rows: `84`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `<integer>` |
| `app` | `varchar(255)` | `NO` | `` | `<string len=12>` |
| `name` | `varchar(255)` | `NO` | `` | `<string len=12>` |
| `applied` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |

## `django_session`

- Rows: `83`
- Primary key: `session_key`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `session_key` | `varchar(40)` | `NO` | `` | `<string len=32>` |
| `session_data` | `text` | `NO` | `` | `<text len=296>` |
| `expire_date` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |

## `domain_qna`

- Rows: `2411`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `integer` | `NO` | `nextval('domain_qna_id_seq'::regclass)` | `<integer>` |
| `no` | `integer` | `NO` | `` | `<integer>` |
| `species` | `varchar(10)` | `YES` | `` | `<string len=3>` |
| `category` | `varchar(50)` | `YES` | `` | `<string len=7>` |
| `source` | `varchar(20)` | `YES` | `` | `<string len=7>` |
| `chunk_text` | `text` | `YES` | `` | `<text len=286>` |
| `embedding` | `vector` | `YES` | `` | `<vector dims~1024>` |
| `search_vector` | `tsvector` | `YES` | `` | `<text len=314>` |

## `future_pet_profile`

- Rows: `3`
- Primary key: `id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `<integer>` |
| `preferred_species` | `varchar(20)` | `NO` | `` | `<string len=3>` |
| `housing_type` | `varchar(20)` | `NO` | `` | `<empty string>` |
| `experience_level` | `varchar(20)` | `NO` | `` | `<empty string>` |
| `interests` | `jsonb` | `NO` | `` | `<array len=0>` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `user_id` | `integer` | `NO` | `` | `<integer>` |

## `order`

- Rows: `16`
- Primary key: `order_id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `order_id` | `uuid` | `NO` | `` | `<uuid>` |
| `recipient_name` | `varchar(100)` | `NO` | `` | `<string len=10>` |
| `delivery_address` | `text` | `NO` | `` | `<string len=23>` |
| `total_price` | `integer` | `NO` | `` | `<integer>` |
| `status` | `varchar(15)` | `NO` | `` | `<string len=9>` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `user_id` | `integer` | `NO` | `` | `<integer>` |
| `applied_coupon_id` | `varchar(50)` | `NO` | `` | `<string len=4>` |
| `coupon_discount` | `integer` | `NO` | `` | `<integer>` |
| `delivery_message` | `text` | `NO` | `` | `<string len=12>` |
| `mileage_discount` | `integer` | `NO` | `` | `-` |
| `payment_method` | `varchar(120)` | `NO` | `` | `-` |
| `product_total` | `integer` | `NO` | `` | `-` |
| `recipient_phone` | `varchar(20)` | `NO` | `` | `-` |
| `shipping_fee` | `integer` | `NO` | `` | `-` |

## `order_item`

- Rows: `26`
- Primary key: `order_item_id`
- Foreign keys:
  - `order_id` -> `order.order_id`
  - `product_id` -> `product.goods_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `order_item_id` | `uuid` | `NO` | `` | `<uuid>` |
| `quantity` | `integer` | `NO` | `` | `<integer>` |
| `price_at_order` | `integer` | `NO` | `` | `<integer>` |
| `order_id` | `uuid` | `NO` | `` | `<uuid>` |
| `product_id` | `varchar(20)` | `NO` | `` | `<string len=11>` |

## `pet`

- Rows: `8`
- Primary key: `pet_id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `pet_id` | `uuid` | `NO` | `` | `<uuid>` |
| `name` | `varchar(100)` | `NO` | `` | `<string len=1>` |
| `species` | `varchar(5)` | `NO` | `` | `<string len=3>` |
| `breed` | `varchar(100)` | `YES` | `` | `<string len=2>` |
| `gender` | `varchar(10)` | `NO` | `` | `<empty string>` |
| `age_years` | `integer` | `NO` | `` | `<integer>` |
| `age_months` | `integer` | `NO` | `` | `<integer>` |
| `weight_kg` | `numeric(5,2)` | `YES` | `` | `<number>` |
| `neutered` | `boolean` | `YES` | `` | `<null>` |
| `vaccination_date` | `date` | `YES` | `` | `<null>` |
| `budget_range` | `varchar(20)` | `NO` | `` | `-` |
| `special_notes` | `text` | `YES` | `` | `-` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `-` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `-` |
| `user_id` | `integer` | `NO` | `` | `-` |
| `age_unknown` | `boolean` | `NO` | `false` | `-` |

## `pet_allergy`

- Rows: `19`
- Primary key: `id`
- Foreign keys:
  - `pet_id` -> `pet.pet_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `uuid` | `NO` | `` | `<uuid>` |
| `ingredient` | `varchar(100)` | `NO` | `` | `<string len=3>` |
| `pet_id` | `uuid` | `NO` | `` | `<uuid>` |

## `pet_food_preference`

- Rows: `3`
- Primary key: `id`
- Foreign keys:
  - `pet_id` -> `pet.pet_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `uuid` | `NO` | `` | `<uuid>` |
| `food_type` | `varchar(20)` | `NO` | `` | `<string len=3>` |
| `pet_id` | `uuid` | `NO` | `` | `<uuid>` |

## `pet_health_concern`

- Rows: `5`
- Primary key: `id`
- Foreign keys:
  - `pet_id` -> `pet.pet_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `uuid` | `NO` | `` | `<uuid>` |
| `concern` | `varchar(20)` | `NO` | `` | `<string len=7>` |
| `pet_id` | `uuid` | `NO` | `` | `<uuid>` |

## `pet_used_product`

- Rows: `0`
- Primary key: `id`
- Foreign keys:
  - `pet_id` -> `pet.pet_id`
  - `product_id` -> `product.goods_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `uuid` | `NO` | `` | `-` |
| `pet_id` | `uuid` | `NO` | `` | `-` |
| `product_id` | `varchar(20)` | `NO` | `` | `-` |

## `product`

- Rows: `4902`
- Primary key: `goods_id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `goods_id` | `varchar(20)` | `NO` | `` | `<string len=12>` |
| `goods_name` | `text` | `NO` | `` | `<string len=23>` |
| `brand_name` | `varchar(200)` | `NO` | `` | `<string len=3>` |
| `price` | `integer` | `NO` | `` | `<integer>` |
| `discount_price` | `integer` | `NO` | `` | `<integer>` |
| `rating` | `numeric(3,1)` | `YES` | `` | `<number>` |
| `review_count` | `integer` | `NO` | `` | `<integer>` |
| `thumbnail_url` | `text` | `NO` | `` | `<url len=153>` |
| `product_url` | `text` | `NO` | `` | `<url len=70>` |
| `soldout_yn` | `boolean` | `NO` | `` | `<boolean>` |
| `soldout_reliable` | `boolean` | `NO` | `` | `-` |
| `pet_type` | `_varchar[]` | `NO` | `` | `-` |
| `category` | `_varchar[]` | `NO` | `` | `-` |
| `subcategory` | `_varchar[]` | `NO` | `` | `-` |
| `health_concern_tags` | `_varchar[]` | `NO` | `` | `-` |
| `popularity_score` | `numeric(10,4)` | `YES` | `` | `-` |
| `sentiment_avg` | `numeric(5,4)` | `YES` | `` | `-` |
| `repeat_rate` | `numeric(5,4)` | `YES` | `` | `-` |
| `main_ingredients` | `jsonb` | `YES` | `` | `-` |
| `ingredient_composition` | `jsonb` | `YES` | `` | `-` |
| `nutrition_info` | `jsonb` | `YES` | `` | `-` |
| `ingredient_text_ocr` | `text` | `YES` | `` | `-` |
| `crawled_at` | `timestamp with time zone` | `NO` | `` | `-` |
| `embedding` | `vector` | `YES` | `` | `-` |
| `embedding_text` | `text` | `YES` | `` | `-` |
| `prefix` | `varchar(5)` | `NO` | `` | `-` |
| `search_vector` | `tsvector` | `YES` | `` | `-` |
| `냄새` | `numeric(5,4)` | `YES` | `0` | `-` |
| `기호성` | `numeric(5,4)` | `YES` | `0` | `-` |
| `생체반응` | `numeric(5,4)` | `YES` | `0` | `-` |
| `가격/구매` | `numeric(5,4)` | `YES` | `0` | `-` |
| `배송/포장` | `numeric(5,4)` | `YES` | `0` | `-` |
| `성분/원료` | `numeric(5,4)` | `YES` | `0` | `-` |
| `소화/배변` | `numeric(5,4)` | `YES` | `0` | `-` |
| `제품 성상` | `numeric(5,4)` | `YES` | `0` | `-` |
| `guide_embedding` | `vector` | `YES` | `` | `-` |
| `guide_text` | `text` | `YES` | `` | `-` |
| `identity_embedding` | `vector` | `YES` | `` | `-` |
| `identity_text` | `text` | `YES` | `` | `-` |

## `product_admin_config`

- Rows: `0`
- Primary key: `id`
- Foreign keys:
  - `product_id` -> `product.goods_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `uuid` | `NO` | `` | `-` |
| `admin_weight` | `numeric(5,2)` | `NO` | `` | `-` |
| `pinned` | `boolean` | `NO` | `` | `-` |
| `memo` | `text` | `YES` | `` | `-` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `-` |
| `product_id` | `varchar(20)` | `NO` | `` | `-` |

## `product_category_tag`

- Rows: `659`
- Primary key: `id`
- Foreign keys:
  - `product_id` -> `product.goods_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `uuid` | `NO` | `` | `<uuid>` |
| `tag` | `varchar(20)` | `NO` | `` | `<string len=2>` |
| `product_id` | `varchar(20)` | `NO` | `` | `<string len=11>` |

## `review`

- Rows: `349277`
- Primary key: `review_id`
- Foreign keys:
  - `product_id` -> `product.goods_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `review_id` | `varchar(30)` | `NO` | `` | `<string len=6>` |
| `score` | `numeric(2,1)` | `NO` | `` | `<number>` |
| `content` | `text` | `NO` | `` | `<string len=38>` |
| `author_nickname` | `varchar(100)` | `NO` | `` | `<string len=7>` |
| `written_at` | `date` | `NO` | `` | `<string len=10>` |
| `purchase_label` | `varchar(10)` | `YES` | `` | `<string len=5>` |
| `sentiment_score` | `numeric(4,3)` | `YES` | `` | `<null>` |
| `sentiment_label` | `varchar(10)` | `YES` | `` | `<null>` |
| `absa_result` | `jsonb` | `YES` | `` | `<null>` |
| `pet_age_months` | `integer` | `YES` | `` | `<null>` |
| `pet_weight_kg` | `numeric(5,2)` | `YES` | `` | `-` |
| `pet_gender` | `varchar(10)` | `YES` | `` | `-` |
| `pet_breed` | `varchar(100)` | `YES` | `` | `-` |
| `product_id` | `varchar(20)` | `NO` | `` | `-` |
| `냄새` | `integer` | `YES` | `0` | `-` |
| `기호성` | `integer` | `YES` | `0` | `-` |
| `생체반응` | `integer` | `YES` | `0` | `-` |
| `가격/구매` | `integer` | `YES` | `0` | `-` |
| `배송/포장` | `integer` | `YES` | `0` | `-` |
| `성분/원료` | `integer` | `YES` | `0` | `-` |
| `소화/배변` | `integer` | `YES` | `0` | `-` |
| `제품 성상` | `integer` | `YES` | `0` | `-` |

## `social_account`

- Rows: `9`
- Primary key: `id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `<integer>` |
| `provider` | `varchar(20)` | `NO` | `` | `<string len=5>` |
| `provider_user_id` | `varchar(255)` | `NO` | `` | `<phone-like string>` |
| `email` | `varchar(254)` | `NO` | `` | `<email-like string>` |
| `extra_data` | `jsonb` | `NO` | `` | `<email-like string>` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `user_id` | `integer` | `NO` | `` | `<integer>` |

## `social_auth_association`

- Rows: `0`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `-` |
| `server_url` | `varchar(255)` | `NO` | `` | `-` |
| `handle` | `varchar(255)` | `NO` | `` | `-` |
| `secret` | `varchar(255)` | `NO` | `` | `-` |
| `issued` | `integer` | `NO` | `` | `-` |
| `lifetime` | `integer` | `NO` | `` | `-` |
| `assoc_type` | `varchar(64)` | `NO` | `` | `-` |

## `social_auth_code`

- Rows: `0`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `-` |
| `email` | `varchar(254)` | `NO` | `` | `-` |
| `code` | `varchar(32)` | `NO` | `` | `-` |
| `verified` | `boolean` | `NO` | `` | `-` |
| `timestamp` | `timestamp with time zone` | `NO` | `` | `-` |

## `social_auth_nonce`

- Rows: `0`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `-` |
| `server_url` | `varchar(255)` | `NO` | `` | `-` |
| `timestamp` | `integer` | `NO` | `` | `-` |
| `salt` | `varchar(65)` | `NO` | `` | `-` |

## `social_auth_partial`

- Rows: `0`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `-` |
| `token` | `varchar(32)` | `NO` | `` | `-` |
| `next_step` | `smallint` | `NO` | `` | `-` |
| `backend` | `varchar(32)` | `NO` | `` | `-` |
| `timestamp` | `timestamp with time zone` | `NO` | `` | `-` |
| `data` | `jsonb` | `NO` | `` | `-` |

## `social_auth_usersocialauth`

- Rows: `9`
- Primary key: `id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `<integer>` |
| `provider` | `varchar(32)` | `NO` | `` | `<string len=5>` |
| `uid` | `varchar(255)` | `NO` | `` | `<phone-like string>` |
| `user_id` | `integer` | `NO` | `` | `<integer>` |
| `created` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `modified` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `extra_data` | `jsonb` | `NO` | `` | `<text len=376>` |

## `token_blacklist_blacklistedtoken`

- Rows: `0`
- Primary key: `id`
- Foreign keys:
  - `token_id` -> `token_blacklist_outstandingtoken.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `-` |
| `blacklisted_at` | `timestamp with time zone` | `NO` | `` | `-` |
| `token_id` | `bigint` | `NO` | `` | `-` |

## `token_blacklist_outstandingtoken`

- Rows: `106`
- Primary key: `id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `<integer>` |
| `token` | `text` | `NO` | `` | `<text len=232>` |
| `created_at` | `timestamp with time zone` | `YES` | `` | `<timestamp>` |
| `expires_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `user_id` | `integer` | `YES` | `` | `<integer>` |
| `jti` | `varchar(255)` | `NO` | `` | `<string len=32>` |

## `user`

- Rows: `25`
- Primary key: `id`
- Foreign keys: -

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `password` | `varchar(128)` | `NO` | `` | `<string len=41>` |
| `last_login` | `timestamp with time zone` | `YES` | `` | `<timestamp>` |
| `is_superuser` | `boolean` | `NO` | `` | `<boolean>` |
| `id` | `integer` | `NO` | `` | `<integer>` |
| `email` | `varchar(254)` | `NO` | `` | `<email-like string>` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `is_active` | `boolean` | `NO` | `` | `<boolean>` |
| `is_staff` | `boolean` | `NO` | `` | `<boolean>` |

## `user_groups`

- Rows: `0`
- Primary key: `id`
- Foreign keys:
  - `group_id` -> `auth_group.id`
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `-` |
| `user_id` | `integer` | `NO` | `` | `-` |
| `group_id` | `integer` | `NO` | `` | `-` |

## `user_interaction`

- Rows: `658`
- Primary key: `id`
- Foreign keys:
  - `product_id` -> `product.goods_id`
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `uuid` | `NO` | `` | `<uuid>` |
| `session_id` | `uuid` | `YES` | `` | `<uuid>` |
| `interaction_type` | `varchar(20)` | `NO` | `` | `<string len=5>` |
| `weight` | `smallint` | `NO` | `` | `<integer>` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `product_id` | `varchar(20)` | `NO` | `` | `<string len=11>` |
| `user_id` | `integer` | `NO` | `` | `<integer>` |

## `user_preference`

- Rows: `0`
- Primary key: `user_id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `user_id` | `integer` | `NO` | `` | `-` |
| `theme` | `varchar(10)` | `NO` | `` | `-` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `-` |

## `user_profile`

- Rows: `20`
- Primary key: `user_id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `user_id` | `integer` | `NO` | `` | `<integer>` |
| `nickname` | `varchar(100)` | `NO` | `` | `<string len=3>` |
| `age` | `integer` | `YES` | `` | `<null>` |
| `gender` | `varchar(20)` | `YES` | `` | `<null>` |
| `address` | `text` | `YES` | `` | `<empty string>` |
| `phone` | `varchar(20)` | `YES` | `` | `<empty string>` |
| `marketing_consent` | `boolean` | `NO` | `` | `<boolean>` |
| `profile_image_url` | `text` | `YES` | `` | `<url len=82>` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `payment_method` | `varchar(120)` | `YES` | `` | `<empty string>` |
| `phone_verified` | `boolean` | `NO` | `` | `-` |
| `phone_verified_at` | `timestamp with time zone` | `YES` | `` | `-` |
| `phone_verification_code` | `varchar(6)` | `YES` | `` | `-` |
| `phone_verification_target` | `varchar(20)` | `YES` | `` | `-` |
| `phone_verification_expires_at` | `timestamp with time zone` | `YES` | `` | `-` |
| `recipient_name` | `varchar(100)` | `YES` | `` | `-` |
| `postal_code` | `varchar(10)` | `YES` | `` | `-` |
| `address_main` | `text` | `YES` | `` | `-` |
| `address_detail` | `text` | `YES` | `` | `-` |
| `payment_card_provider` | `varchar(100)` | `YES` | `` | `-` |
| `payment_card_masked_number` | `varchar(32)` | `YES` | `` | `-` |
| `payment_is_default` | `boolean` | `NO` | `` | `-` |
| `payment_token_reference` | `varchar(255)` | `YES` | `` | `-` |

## `user_used_product`

- Rows: `0`
- Primary key: `id`
- Foreign keys:
  - `product_id` -> `product.goods_id`
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `uuid` | `NO` | `` | `-` |
| `created_at` | `timestamp with time zone` | `NO` | `` | `-` |
| `product_id` | `varchar(20)` | `NO` | `` | `-` |
| `user_id` | `integer` | `NO` | `` | `-` |

## `user_user_permissions`

- Rows: `0`
- Primary key: `id`
- Foreign keys:
  - `permission_id` -> `auth_permission.id`
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `id` | `bigint` | `NO` | `` | `-` |
| `user_id` | `integer` | `NO` | `` | `-` |
| `permission_id` | `integer` | `NO` | `` | `-` |

## `wishlist`

- Rows: `8`
- Primary key: `wishlist_id`
- Foreign keys:
  - `user_id` -> `user.id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `wishlist_id` | `uuid` | `NO` | `` | `<uuid>` |
| `updated_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `user_id` | `integer` | `NO` | `` | `<integer>` |

## `wishlist_item`

- Rows: `3`
- Primary key: `wishlist_item_id`
- Foreign keys:
  - `product_id` -> `product.goods_id`
  - `wishlist_id` -> `wishlist.wishlist_id`

| Column | Type | Nullable | Default | Sample Shape |
|---|---|---|---|---|
| `wishlist_item_id` | `uuid` | `NO` | `` | `<uuid>` |
| `added_at` | `timestamp with time zone` | `NO` | `` | `<timestamp>` |
| `product_id` | `varchar(20)` | `NO` | `` | `<string len=11>` |
| `wishlist_id` | `uuid` | `NO` | `` | `<uuid>` |

