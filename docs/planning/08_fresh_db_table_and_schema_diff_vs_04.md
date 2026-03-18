# Fresh DB 테이블 목록 및 `04_data_model_detail.md` 스키마 비교

기준:
- 실제 DB: WSL Docker `tailtalk-postgres-1` / `tailtalk_db`
- 생성 방식: current `models.py` 기준 fresh `makemigrations -> migrate`
- 비교 문서: `docs/planning/04_data_model_detail.md`

## 1. 실제 DB 테이블 목록

### Django 기본 테이블

- `auth_group`
- `auth_group_permissions`
- `auth_permission`
- `django_admin_log`
- `django_content_type`
- `django_migrations`
- `django_session`
- `user_groups`
- `user_user_permissions`

### 프로젝트 테이블

- `user`
- `user_profile`
- `pet`
- `pet_health_concern`
- `pet_allergy`
- `pet_food_preference`
- `pet_used_product`
- `product`
- `product_category_tag`
- `product_admin_config`
- `review`
- `chat_session`
- `chat_message`
- `message_product_card`
- `cart`
- `cart_item`
- `order`
- `order_item`
- `user_interaction`

## 2. 문서와 대체로 일치하는 부분

아래 테이블은 큰 구조 기준으로는 문서와 실제 DB가 맞는다.

- `user`
- `user_profile`
- `pet`
- `pet_health_concern`
- `pet_allergy`
- `pet_food_preference`
- `pet_used_product`
- `product`
- `product_category_tag`
- `product_admin_config`
- `review`
- `chat_session`
- `chat_message`
- `cart`
- `cart_item`
- `order`
- `order_item`
- `user_interaction`

즉 현재 fresh DB는, 이전 상태와 달리 문서의 방향과 대체로 맞게 재생성되어 있다.

## 3. 문서와 다른 점

### 3.1 `message_product_card` 테이블 존재

실제 DB에는 아래 테이블이 존재한다.

- `message_product_card`

컬럼:

- `id uuid not null`
- `reason text not null`
- `message_id uuid not null`
- `product_id varchar not null`

문서 차이:

- ERD 상단 테이블 정의에는 `MESSAGE_PRODUCT_CARD`가 없음
- 하지만 문서 본문 `## 3. Chat Session` 예시에는 `product_cards`와 `MESSAGE_PRODUCT_CARD` 설명이 들어 있음

해석:

- 문서 내부에서도 이 테이블 정의가 일관되지 않음
- 현재 실제 DB는 `chat/models.py` 기준으로 `message_product_card`를 생성하고 있음

### 3.2 `CHAT_SESSION.title` 타입

문서:

- `string`

실제 DB:

- `title text not null`

해석:

- 의미는 같지만 구현은 `TextField`라서 PostgreSQL에는 `text`로 생성됨

### 3.3 `PRODUCT`의 JSON/배열 표현 차이

문서:

- `main_ingredients`: ERD에서는 `jsonb`, 본문에서는 `string[] | null`
- `ingredient_composition`: `jsonb`
- `nutrition_info`: `jsonb`

실제 DB:

- `main_ingredients jsonb null`
- `ingredient_composition jsonb null`
- `nutrition_info jsonb null`

해석:

- `main_ingredients`는 문서 내부 표현이 서로 다름
- 실제 구현은 `jsonb` 기준

### 3.4 datetime 표기와 실제 PostgreSQL 타입

문서:

- `datetime`

실제 DB:

- 대부분 `timestamp with time zone` (`timestamptz`)

대표 예시:

- `user.created_at`
- `pet.created_at`
- `pet.updated_at`
- `chat_session.created_at`
- `chat_session.updated_at`
- `chat_message.created_at`
- `cart.updated_at`
- `order.created_at`
- `user_interaction.created_at`

해석:

- 문서의 논리 타입 `datetime`이 PostgreSQL 물리 타입으로는 `timestamptz`로 구현된 것

### 3.5 numeric/float 표기 차이

문서:

- 일부 컬럼을 `float` 또는 `numeric`으로 서술

실제 DB:

- 수치 정밀도 필요한 컬럼은 대부분 `numeric`

대표 예시:

- `pet.weight_kg`
- `product.rating`
- `product.popularity_score`
- `product.sentiment_avg`
- `product.repeat_rate`
- `review.score`
- `review.sentiment_score`
- `review.pet_weight_kg`
- `product_admin_config.admin_weight`

해석:

- 문서의 논리 타입과 실제 PostgreSQL 물리 타입 차이
- 설계상 문제라기보다 구현 세부 차이

## 4. 현재 fresh DB 기준 테이블별 핵심 구조

### `user`

- `id integer pk`
- `email varchar`
- `created_at timestamptz`
- `is_active boolean`
- `password varchar`
- `last_login timestamptz null`
- `is_superuser boolean`
- `is_staff boolean`

### `user_profile`

- `user_id integer pk/fk`
- `nickname varchar`
- `age integer null`
- `gender varchar null`
- `address text null`
- `phone varchar null`
- `marketing_consent boolean`
- `profile_image_url text null`
- `updated_at timestamptz`

### `pet`

- `pet_id uuid pk`
- `user_id integer fk`
- `name varchar`
- `species varchar`
- `breed varchar null`
- `gender varchar`
- `age_years integer`
- `age_months integer`
- `weight_kg numeric null`
- `neutered boolean null`
- `vaccination_date date null`
- `budget_range varchar`
- `special_notes text null`
- `created_at timestamptz`
- `updated_at timestamptz`

### `pet_health_concern`

- `id uuid pk`
- `pet_id uuid fk`
- `concern varchar`

### `pet_allergy`

- `id uuid pk`
- `pet_id uuid fk`
- `ingredient varchar`

### `pet_food_preference`

- `id uuid pk`
- `pet_id uuid fk`
- `food_type varchar`

### `pet_used_product`

- `id uuid pk`
- `pet_id uuid fk`
- `product_id varchar fk`

### `product`

- `goods_id varchar pk`
- `goods_name text`
- `brand_name varchar`
- `price integer`
- `discount_price integer`
- `rating numeric null`
- `review_count integer`
- `thumbnail_url text`
- `product_url text`
- `soldout_yn boolean`
- `soldout_reliable boolean`
- `pet_type varchar[]`
- `category varchar[]`
- `subcategory varchar[]`
- `health_concern_tags varchar[]`
- `popularity_score numeric null`
- `sentiment_avg numeric null`
- `repeat_rate numeric null`
- `main_ingredients jsonb null`
- `ingredient_composition jsonb null`
- `nutrition_info jsonb null`
- `ingredient_text_ocr text null`
- `crawled_at timestamptz`

### `product_category_tag`

- `id uuid pk`
- `product_id varchar fk`
- `tag varchar`

### `product_admin_config`

- `id uuid pk`
- `product_id varchar fk`
- `admin_weight numeric`
- `pinned boolean`
- `memo text null`
- `updated_at timestamptz`

### `review`

- `review_id varchar pk`
- `product_id varchar fk`
- `score numeric`
- `content text`
- `author_nickname varchar`
- `written_at date`
- `purchase_label varchar null`
- `sentiment_score numeric null`
- `sentiment_label varchar null`
- `absa_result jsonb null`
- `pet_age_months integer null`
- `pet_weight_kg numeric null`
- `pet_gender varchar null`
- `pet_breed varchar null`

### `chat_session`

- `session_id uuid pk`
- `user_id integer fk`
- `target_pet_id uuid fk null`
- `title text`
- `created_at timestamptz`
- `updated_at timestamptz`

### `chat_message`

- `message_id uuid pk`
- `session_id uuid fk`
- `role varchar`
- `content text`
- `created_at timestamptz`

### `message_product_card`

- `id uuid pk`
- `message_id uuid fk`
- `product_id varchar fk`
- `reason text`

### `cart`

- `cart_id uuid pk`
- `user_id integer fk`
- `updated_at timestamptz`

### `cart_item`

- `cart_item_id uuid pk`
- `cart_id uuid fk`
- `product_id varchar fk`
- `quantity integer`
- `added_at timestamptz`

### `order`

- `order_id uuid pk`
- `user_id integer fk`
- `recipient_name varchar`
- `delivery_address text`
- `total_price integer`
- `status varchar`
- `created_at timestamptz`

### `order_item`

- `order_item_id uuid pk`
- `order_id uuid fk`
- `product_id varchar fk`
- `quantity integer`
- `price_at_order integer`

### `user_interaction`

- `id uuid pk`
- `user_id integer fk`
- `product_id varchar fk`
- `session_id uuid null`
- `interaction_type varchar`
- `weight smallint`
- `created_at timestamptz`

## 5. 결론

현재 fresh DB는 `04_data_model_detail.md`의 최신 방향과 대부분 일치한다.

실질적인 차이는 아래 두 범주다.

1. 문서 내부 표현 불일치
- `MESSAGE_PRODUCT_CARD`처럼 본문에는 있지만 ERD 테이블 정의에는 빠진 항목
- `main_ingredients`처럼 ERD와 본문 타입 표기가 다른 항목

2. 구현 세부 타입 차이
- `datetime` → PostgreSQL `timestamptz`
- `float`/`numeric` → 실제 PostgreSQL `numeric`
- `string` → PostgreSQL `varchar` 또는 `text`
