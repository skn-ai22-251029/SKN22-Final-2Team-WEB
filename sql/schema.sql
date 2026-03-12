-- =============================================================
-- SKN22 Final Project — PostgreSQL DDL
-- 기준 문서: docs/planning/04_data_model_detail.md
-- =============================================================

-- pgcrypto (gen_random_uuid) 활성화
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================
-- USER  (auth 전용)
-- =============================================================
CREATE TABLE "user" (
    user_id        UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email          VARCHAR(255) NOT NULL UNIQUE,
    password_hash  TEXT,                                          -- 자체 가입: 필수, 소셜 가입: NULL
    oauth_provider VARCHAR(10)  CHECK (oauth_provider IN ('google', 'kakao', 'naver')),  -- 소셜 가입: 필수, 자체 가입: NULL
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    CONSTRAINT chk_auth_method CHECK (
        oauth_provider IS NOT NULL OR password_hash IS NOT NULL
    )
);

-- =============================================================
-- USER_PROFILE  (온보딩에서 채움, 1:1)
-- =============================================================
CREATE TABLE user_profile (
    user_id           UUID         PRIMARY KEY REFERENCES "user"(user_id) ON DELETE CASCADE,
    nickname          VARCHAR(100) NOT NULL,                      -- OAuth provider에서 pre-fill
    age               INT,
    gender            VARCHAR(20),
    address           TEXT,                                       -- 기본 배송지
    phone             VARCHAR(20),
    marketing_consent BOOLEAN      NOT NULL DEFAULT FALSE,
    profile_image_url TEXT,
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- =============================================================
-- PET
-- =============================================================
CREATE TABLE pet (
    pet_id           UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID         NOT NULL REFERENCES "user"(user_id) ON DELETE CASCADE,
    name             VARCHAR(100) NOT NULL,
    species          VARCHAR(5)   NOT NULL CHECK (species IN ('cat', 'dog')),
    breed            VARCHAR(100),
    gender           VARCHAR(10)  NOT NULL CHECK (gender IN ('male', 'female')),
    age_years        INT          NOT NULL DEFAULT 0,
    age_months       INT          NOT NULL DEFAULT 0,
    weight_kg        NUMERIC(5,2),
    neutered         BOOLEAN,
    vaccination_date DATE,
    budget_range     VARCHAR(20)  NOT NULL,
    special_notes    TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pet_user_id ON pet(user_id);

-- =============================================================
-- PET_HEALTH_CONCERN
-- =============================================================
CREATE TABLE pet_health_concern (
    id      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id  UUID        NOT NULL REFERENCES pet(pet_id) ON DELETE CASCADE,
    concern VARCHAR(20) NOT NULL CHECK (concern IN ('skin', 'joint', 'digestion', 'weight', 'urinary', 'eye', 'hairball', 'dental', 'immunity')),
    UNIQUE (pet_id, concern)
);

-- =============================================================
-- PET_ALLERGY
-- =============================================================
CREATE TABLE pet_allergy (
    id         UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id     UUID         NOT NULL REFERENCES pet(pet_id) ON DELETE CASCADE,
    ingredient VARCHAR(100) NOT NULL,
    UNIQUE (pet_id, ingredient)
);

-- =============================================================
-- PET_FOOD_PREFERENCE
-- =============================================================
CREATE TABLE pet_food_preference (
    id        UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id    UUID        NOT NULL REFERENCES pet(pet_id) ON DELETE CASCADE,
    food_type VARCHAR(20) NOT NULL CHECK (food_type IN ('dry', 'wet_can', 'wet_pouch', 'freeze_dried', 'raw')),
    UNIQUE (pet_id, food_type)
);

-- =============================================================
-- PRODUCT  (Gold 레이어 적재 기준)
-- =============================================================
CREATE TABLE product (
    goods_id            VARCHAR(20)    PRIMARY KEY,
    goods_name          TEXT           NOT NULL,
    brand_name          VARCHAR(200)   NOT NULL,
    price               INT            NOT NULL,
    discount_price      INT            NOT NULL,
    rating              NUMERIC(3,1),                        -- 5점 만점, 리뷰 없으면 NULL
    review_count        INT            NOT NULL DEFAULT 0,
    thumbnail_url       TEXT           NOT NULL,
    product_url         TEXT           NOT NULL,
    soldout_yn          BOOLEAN        NOT NULL DEFAULT FALSE,
    popularity_score    NUMERIC(10,4),                       -- Gold 파생
    trend_score         NUMERIC(6,4),                        -- Gold 파생
    main_ingredients        JSONB,                           -- Gold 파생, 식품류만 (원료 키워드 배열)
    ingredient_composition  JSONB,                           -- Gold 파생, 식품류만 (원료명: 함량%)
    nutrition_info          JSONB,                           -- Gold 파생, 식품류만 (영양성분명: 수치)
    ingredient_text_ocr     TEXT,                            -- Gold 파생, OCR 원문
    crawled_at          TIMESTAMPTZ    NOT NULL
);

CREATE INDEX idx_product_brand        ON product(brand_name);
CREATE INDEX idx_product_popularity   ON product(popularity_score DESC NULLS LAST);
CREATE INDEX idx_product_trend        ON product(trend_score DESC NULLS LAST);
CREATE INDEX idx_product_main_ingr    ON product USING GIN(main_ingredients);

-- =============================================================
-- PRODUCT_ADMIN_CONFIG  (어드민 추천 가중치 — 파이프라인 데이터와 분리)
-- =============================================================
CREATE TABLE product_admin_config (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    goods_id     VARCHAR(20) NOT NULL UNIQUE REFERENCES product(goods_id) ON DELETE CASCADE,
    admin_weight NUMERIC(5,2) NOT NULL DEFAULT 1.0,  -- 추천 상위 노출 가중치 (1.0=기본, >1.0=부스트)
    pinned       BOOLEAN      NOT NULL DEFAULT FALSE,  -- 최상단 고정 여부
    memo         TEXT,                                 -- 어드민 메모
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pac_goods_id ON product_admin_config(goods_id);

-- =============================================================
-- PRODUCT_CATEGORY_TAG
-- =============================================================
CREATE TABLE product_category_tag (
    id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    goods_id VARCHAR(20) NOT NULL REFERENCES product(goods_id) ON DELETE CASCADE,
    tag      VARCHAR(20) NOT NULL CHECK (tag IN ('관절', '피부', '소화', '체중', '요로', '눈물', '헤어볼', '치아', '면역')),
    UNIQUE (goods_id, tag)
);

CREATE INDEX idx_pct_goods_id ON product_category_tag(goods_id);

-- =============================================================
-- REVIEW  (review_id = goods_estm_no, string PK)
-- =============================================================
CREATE TABLE review (
    review_id       VARCHAR(30)   PRIMARY KEY,              -- goods_estm_no
    goods_id        VARCHAR(20)   NOT NULL REFERENCES product(goods_id) ON DELETE CASCADE,
    score           NUMERIC(2,1)  NOT NULL CHECK (score BETWEEN 0 AND 5),
    content         TEXT          NOT NULL,
    author_nickname VARCHAR(100)  NOT NULL,
    written_at      DATE          NOT NULL,
    purchase_label  VARCHAR(10)   CHECK (purchase_label IN ('first', 'repeat')),
    sentiment_score NUMERIC(4,3)  CHECK (sentiment_score BETWEEN 0 AND 1),  -- Gold: 전체 문장 감성
    sentiment_label VARCHAR(10)   CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),  -- Gold
    absa_result     JSONB,                                                   -- Gold: ABSA 문장별 관점 감성 배열
    pet_age_months  INT,
    pet_weight_kg   NUMERIC(5,2),
    pet_gender      VARCHAR(10),
    pet_breed       VARCHAR(100)
);

CREATE INDEX idx_review_goods_id  ON review(goods_id);
CREATE INDEX idx_review_written   ON review(written_at DESC);
CREATE INDEX idx_review_absa      ON review USING GIN(absa_result);

-- =============================================================
-- CHAT_SESSION
-- =============================================================
CREATE TABLE chat_session (
    session_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        REFERENCES "user"(user_id) ON DELETE SET NULL,  -- guest = NULL
    target_pet_id UUID        REFERENCES pet(pet_id) ON DELETE SET NULL,
    title         TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_session_user ON chat_session(user_id);

-- =============================================================
-- CHAT_MESSAGE
-- =============================================================
CREATE TABLE chat_message (
    message_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID        NOT NULL REFERENCES chat_session(session_id) ON DELETE CASCADE,
    role       VARCHAR(10) NOT NULL CHECK (role IN ('user', 'assistant')),
    content    TEXT        NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_message_session ON chat_message(session_id);

-- =============================================================
-- MESSAGE_PRODUCT_CARD
-- =============================================================
CREATE TABLE message_product_card (
    id         UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID        NOT NULL REFERENCES chat_message(message_id) ON DELETE CASCADE,
    goods_id   VARCHAR(20) NOT NULL REFERENCES product(goods_id) ON DELETE RESTRICT,
    reason     TEXT        NOT NULL
);

CREATE INDEX idx_mpc_message_id ON message_product_card(message_id);

-- =============================================================
-- CART
-- =============================================================
CREATE TABLE cart (
    cart_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    UUID        UNIQUE REFERENCES "user"(user_id) ON DELETE SET NULL,  -- guest = NULL
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- =============================================================
-- CART_ITEM
-- =============================================================
CREATE TABLE cart_item (
    cart_item_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cart_id      UUID        NOT NULL REFERENCES cart(cart_id) ON DELETE CASCADE,
    goods_id     VARCHAR(20) NOT NULL REFERENCES product(goods_id) ON DELETE RESTRICT,
    quantity     INT         NOT NULL DEFAULT 1 CHECK (quantity > 0),
    added_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (cart_id, goods_id)
);

CREATE INDEX idx_cart_item_cart ON cart_item(cart_id);

-- =============================================================
-- ORDER
-- =============================================================
CREATE TABLE "order" (
    order_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID        NOT NULL REFERENCES "user"(user_id) ON DELETE RESTRICT,
    recipient_name    VARCHAR(100) NOT NULL,                      -- 주문 시 스냅샷
    delivery_address  TEXT        NOT NULL,                       -- 주문 시 스냅샷
    total_price       INT         NOT NULL,
    status            VARCHAR(15) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_order_user_id ON "order"(user_id);

-- =============================================================
-- ORDER_ITEM
-- =============================================================
CREATE TABLE order_item (
    order_item_id UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id      UUID        NOT NULL REFERENCES "order"(order_id) ON DELETE CASCADE,
    goods_id      VARCHAR(20) NOT NULL REFERENCES product(goods_id) ON DELETE RESTRICT,
    quantity      INT         NOT NULL CHECK (quantity > 0),
    price_at_order INT        NOT NULL
);

CREATE INDEX idx_order_item_order ON order_item(order_id);

-- =============================================================
-- PET_USED_PRODUCT
-- =============================================================
CREATE TABLE pet_used_product (
    id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    pet_id   UUID        NOT NULL REFERENCES pet(pet_id) ON DELETE CASCADE,
    goods_id VARCHAR(20) NOT NULL REFERENCES product(goods_id) ON DELETE RESTRICT,
    UNIQUE (pet_id, goods_id)
);

-- =============================================================
-- USER_INTERACTION  (Phase 2 CF 준비 — Day 1부터 로깅)
-- =============================================================
CREATE TABLE user_interaction (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID         REFERENCES "user"(user_id) ON DELETE SET NULL,   -- guest = NULL
    goods_id         VARCHAR(20)  REFERENCES product(goods_id) ON DELETE CASCADE,
    session_id       UUID         REFERENCES chat_session(session_id) ON DELETE SET NULL,
    interaction_type VARCHAR(20)  NOT NULL
                     CHECK (interaction_type IN ('click', 'cart', 'purchase', 'reject')),
    weight           SMALLINT     NOT NULL DEFAULT 1,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ui_user_id  ON user_interaction(user_id);
CREATE INDEX idx_ui_goods_id ON user_interaction(goods_id);
