-- =============================================================
-- SKN22 Final Project — PostgreSQL DDL
-- 기준 문서: docs/planning/04_data_model_detail.md
-- =============================================================

-- pgcrypto (gen_random_uuid) 활성화
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================
-- USER
-- =============================================================
CREATE TABLE "user" (
    user_id           UUID          PRIMARY KEY DEFAULT gen_random_uuid(),
    email             VARCHAR(255)  NOT NULL UNIQUE,
    password_hash     TEXT,
    oauth_provider    VARCHAR(10)   CHECK (oauth_provider IN ('google', 'kakao', 'naver')),
    name              VARCHAR(100)  NOT NULL,
    age               INT,
    gender            VARCHAR(20),
    address           TEXT,
    profile_image_url TEXT,
    created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

-- =============================================================
-- USER_PREFERENCE
-- =============================================================
CREATE TABLE user_preference (
    preference_id  UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID         NOT NULL UNIQUE REFERENCES "user"(user_id) ON DELETE CASCADE,
    response_style VARCHAR(10)  NOT NULL DEFAULT 'concise' CHECK (response_style IN ('concise', 'detailed')),
    card_count     SMALLINT     NOT NULL DEFAULT 3          CHECK (card_count IN (1, 3, 5)),
    save_history   BOOLEAN      NOT NULL DEFAULT TRUE,
    language       VARCHAR(5)   NOT NULL DEFAULT 'ko'       CHECK (language IN ('ko', 'en'))
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
    main_ingredients    JSONB,                               -- Gold 파생, 식품류만
    ingredient_text_ocr TEXT,                               -- Gold 파생, OCR 원문
    crawled_at          TIMESTAMPTZ    NOT NULL
);

CREATE INDEX idx_product_brand        ON product(brand_name);
CREATE INDEX idx_product_popularity   ON product(popularity_score DESC NULLS LAST);
CREATE INDEX idx_product_trend        ON product(trend_score DESC NULLS LAST);
CREATE INDEX idx_product_main_ingr    ON product USING GIN(main_ingredients);

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
    sentiment_score NUMERIC(4,3)  CHECK (sentiment_score BETWEEN 0 AND 1),  -- Gold
    sentiment_label VARCHAR(10)   CHECK (sentiment_label IN ('positive', 'negative', 'neutral')),  -- Gold
    pet_age_months  INT,
    pet_weight_kg   NUMERIC(5,2),
    pet_gender      VARCHAR(10),
    pet_breed       VARCHAR(100)
);

CREATE INDEX idx_review_goods_id  ON review(goods_id);
CREATE INDEX idx_review_written   ON review(written_at DESC);

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
    order_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES "user"(user_id) ON DELETE RESTRICT,
    total_price INT         NOT NULL,
    status      VARCHAR(15) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'cancelled')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
