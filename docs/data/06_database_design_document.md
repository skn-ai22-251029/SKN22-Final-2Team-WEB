## 개요

- 산출물 단계: 데이터 수집 및 저장
- 평가 산출물: 데이터베이스 설계 문서
- 기준 문서: `docs/planning/04_data_model_detail.md`
- 구현 기준: Django ORM

본 문서는 서비스 전반에서 사용하는 관계형 데이터베이스 구조를 정의한다.  
현재 프로젝트의 인증, 온보딩, 반려동물 프로필, 상품, 리뷰, 채팅, 장바구니, 주문, 사용자 행동 로그를 저장하고 관리하기 위한 엔티티와 관계를 정리한다.

---

## 소개

### 목적

- 서비스 핵심 도메인의 엔티티와 관계를 명확히 정의한다.
- Django ORM 구현 전에 테이블 역할과 데이터 흐름을 확정한다.
- 온보딩 완료 회원만 핵심 기능을 사용할 수 있는 서비스 정책을 데이터 모델에 반영한다.

### 범위

- 사용자 인증 및 온보딩 프로필 관리
- 반려동물 프로필 및 다중값 속성 관리
- 상품, 리뷰, 태그, 어드민 설정 관리
- 채팅 세션 및 메시지 관리
- 장바구니 및 주문 관리
- 추천 고도화를 위한 사용자 행동 로그 관리

---

## 시스템 개요

### 시스템 역할

- 사용자는 회원가입 또는 로그인 후 온보딩을 완료해야 서비스 핵심 기능을 사용할 수 있다.
- 온보딩 완료 회원은 반려동물 정보를 등록하고, 상품 추천/탐색, 채팅, 장바구니, 주문 기능을 사용할 수 있다.
- 시스템은 상품 및 리뷰 기반 데이터를 저장하고, 사용자와 반려동물 맥락에 따라 추천 서비스의 기반 데이터를 관리한다.

### 주요 기능

- 사용자 인증 및 계정 상태 관리
- 온보딩 완료 프로필 관리
- 반려동물 정보 및 건강 관심사/알레르기/사료 선호 관리
- 상품 및 리뷰 데이터 저장
- 채팅 세션 및 메시지 이력 저장
- 장바구니 및 주문 이력 저장
- 추천 고도화를 위한 사용자 상호작용 로그 저장

---

## 시스템 아키텍처

### 데이터베이스 구조

본 시스템은 관계형 데이터베이스 구조를 기준으로 설계한다. 주요 엔티티는 다음과 같다.

- `user`, `user_profile`
- `pet`, `pet_health_concern`, `pet_allergy`, `pet_food_preference`, `pet_used_product`
- `product`, `product_category_tag`, `product_admin_config`, `review`
- `chat_session`, `chat_message`
- `cart`, `cart_item`
- `order`, `order_item`
- `user_interaction`

### 적용 기준

- 데이터 모델은 `docs/planning/04_data_model_detail.md`를 최종 기준으로 사용한다.
- 실제 구현은 Django ORM 기반으로 진행한다.
- 다중값 속성은 배열 컬럼 대신 별도 엔티티로 분리하여 관리한다.

---

## 요구사항 매트릭스

| 요구사항 | 관련 엔티티 |
|---|---|
| 회원가입 및 로그인 관리 | `user` |
| 온보딩 완료 프로필 저장 | `user_profile` |
| 반려동물 정보 관리 | `pet` |
| 반려동물 건강 관심사/알레르기/선호 정보 관리 | `pet_health_concern`, `pet_allergy`, `pet_food_preference` |
| 반려동물 사용 상품 관리 | `pet_used_product`, `product` |
| 상품 정보 저장 | `product` |
| 상품 건강 태그 저장 | `product_category_tag` |
| 어드민 추천 설정 관리 | `product_admin_config` |
| 상품 리뷰 및 감성 분석 결과 저장 | `review` |
| 채팅 세션 및 메시지 저장 | `chat_session`, `chat_message` |
| 장바구니 관리 | `cart`, `cart_item` |
| 주문 및 주문 상세 저장 | `order`, `order_item` |
| 사용자 행동 로그 저장 | `user_interaction` |

---

## 데이터 설계

### 1. 사용자 도메인

#### `user`

- 인증 전용 계정 엔티티
- 자체 가입과 소셜 가입을 모두 수용
- 주요 컬럼
  - `user_id`
  - `email`
  - `password_hash`
  - `oauth_provider`
  - `created_at`
  - `is_active`

#### `user_profile`

- 온보딩 완료 시 생성되는 1:1 서비스 프로필
- `user_profile`이 없는 회원은 채팅, 장바구니, 구매 기능 사용 불가
- 주요 컬럼
  - `user_id`
  - `nickname`
  - `age`
  - `gender`
  - `address`
  - `phone`
  - `marketing_consent`
  - `profile_image_url`
  - `updated_at`

### 2. 반려동물 도메인

#### `pet`

- 사용자 소유 반려동물 프로필
- 주요 컬럼
  - `pet_id`
  - `user_id`
  - `name`
  - `species`
  - `breed`
  - `gender`
  - `age_years`
  - `age_months`
  - `weight_kg`
  - `neutered`
  - `vaccination_date`
  - `budget_range`
  - `special_notes`

#### 다중값 엔티티

- `pet_health_concern`: 건강 관심사
- `pet_allergy`: 알레르기 원료
- `pet_food_preference`: 선호 사료 형태
- `pet_used_product`: 현재 사용 중인 상품

### 3. 상품/리뷰 도메인

#### `product`

- 상품 마스터 엔티티
- 리뷰 기반 파생 점수와 OCR 기반 성분 정보를 포함
- 주요 컬럼
  - `goods_id`
  - `goods_name`
  - `brand_name`
  - `price`
  - `discount_price`
  - `rating`
  - `review_count`
  - `thumbnail_url`
  - `product_url`
  - `soldout_yn`
  - `popularity_score`
  - `trend_score`
  - `main_ingredients`
  - `ingredient_composition`
  - `nutrition_info`
  - `ingredient_text_ocr`
  - `crawled_at`

#### `product_category_tag`

- 상품 건강 관심사 태그 다중값 저장
- 예: `관절`, `피부`, `소화`, `체중`, `요로`, `눈물`, `헤어볼`, `치아`, `면역`

#### `product_admin_config`

- 어드민 전용 상품 운영 설정
- 추천 노출 가중치와 고정 노출 여부를 관리

#### `review`

- 상품 리뷰 및 감성 분석 결과 저장
- 주요 컬럼
  - `review_id`
  - `goods_id`
  - `score`
  - `content`
  - `author_nickname`
  - `written_at`
  - `purchase_label`
  - `sentiment_score`
  - `sentiment_label`
  - `absa_result`
  - `pet_age_months`
  - `pet_weight_kg`
  - `pet_gender`
  - `pet_breed`

### 4. 채팅 도메인

#### `chat_session`

- 사용자별 대화 세션
- 온보딩 완료 회원만 사용 가능
- `target_pet_id`는 nullable

#### `chat_message`

- 세션 내 메시지 단위 저장
- `chat_session`에 종속되는 1:N 구조

### 5. 커머스 도메인

#### `cart`

- 회원별 장바구니
- 온보딩 완료 회원만 사용 가능
- 회원당 1개 기준으로 관리

#### `cart_item`

- 장바구니 내 상품 항목
- 상품과 수량을 저장

#### `order`

- 주문 헤더
- 주문 시점 스냅샷을 저장
- 주요 컬럼
  - `recipient_name`
  - `delivery_address`
  - `total_price`
  - `status`
  - `created_at`

#### `order_item`

- 주문 상세 항목
- 주문 상품별 수량과 주문 당시 가격 저장

### 6. 로그 도메인

#### `user_interaction`

- 추천 고도화를 위한 사용자 행동 로그
- 이벤트 타입
  - `click`
  - `cart`
  - `purchase`
  - `reject`
- 가중치
  - `click=1`
  - `cart=3`
  - `purchase=5`
  - `reject=-1`

> `user_interaction.user_id` nullable 정책은 추후 확정한다.

---

## 테이블 간 주요 관계

- `user` 1:1 `user_profile`
- `user` 1:N `pet`
- `user` 1:N `chat_session`
- `user` 1:1 `cart`
- `user` 1:N `order`
- `pet` 1:N `pet_health_concern`, `pet_allergy`, `pet_food_preference`, `pet_used_product`
- `product` 1:N `product_category_tag`, `review`, `cart_item`, `order_item`, `pet_used_product`
- `product` 1:1 `product_admin_config`
- `chat_session` 1:N `chat_message`
- `cart` 1:N `cart_item`
- `order` 1:N `order_item`

---

## 설계 근거

- 인증 계정과 서비스 프로필을 분리하여 로그인과 온보딩 단계를 명확하게 나눔
- 다중값 속성을 별도 엔티티로 분리하여 정규화와 확장성 확보
- 상품 메타데이터와 어드민 운영 설정을 분리하여 파이프라인 데이터와 수동 운영 데이터를 구분
- 장바구니/주문을 헤더-아이템 구조로 분리하여 1:N 관계를 자연스럽게 표현
- 사용자 행동 로그를 별도 엔티티로 분리하여 추천 고도화에 필요한 데이터 축적 기반 확보

---

## ERD

상세 ERD는 다음 문서를 최종 기준으로 사용한다.

- `docs/planning/04_data_model_detail.md`
