# Recommendation Data Audit

Date: 2026-04-06
Issue: #325

## Scope

- Recommendation input columns currently used by the FastAPI recommendation flow
- Product metadata completeness for ranking-related fields
- Current `UserInteraction` logging coverage in Django

## Files Checked

- `services/django/orders/models.py`
- `services/django/orders/api/core.py`
- `services/fastapi/final_ai/infrastructure/repositories/product_repository.py`
- `services/fastapi/final_ai/infrastructure/repositories/product_filters.py`
- `services/fastapi/final_ai/application/recommendation/service.py`
- `services/fastapi/final_ai/api/routers/recommend.py`
- `services/fastapi/final_ai/api/routers/products.py`

## Recommendation Columns In Use

### Retrieval / filter

- `goods_id`
- `goods_name`
- `pet_type`
- `category`
- `subcategory`
- `price`
- `embedding`
- `search_vector`
- `health_concern_tags`

### Rerank

- `popularity_score`
- `sentiment_avg`
- `repeat_rate`
- `health_concern_tags`

### Safety / post-filter

- `main_ingredients`
- `ingredient_text_ocr`

### Response payload

- `brand_name`
- `discount_price`
- `rating`
- `review_count`
- `thumbnail_url`
- `product_url`
- `soldout_yn`

## Product Metadata Snapshot

Source: local PostgreSQL `product` table

- total products: `4902`
- missing `goods_name`: `0`
- missing `pet_type`: `0`
- missing `category`: `0`
- missing `subcategory`: `0`
- missing `health_concern_tags`: `4308`
- missing `main_ingredients`: `2483`
- missing `ingredient_text_ocr`: `2483`
- missing `popularity_score`: `261`
- missing `sentiment_avg`: `3187`
- missing `repeat_rate`: `2588`

## Distribution Snapshot

- distinct `pet_type`: `2`
- distinct `category`: `7`
- distinct `subcategory`: `76`
- distinct `health_concern_tags`: `9`

## Interaction Logging Status

`UserInteraction` model supports:

- `click`
- `cart`
- `purchase`
- `reject`

Current write path found:

- `services/django/orders/api/core.py`
  - only `purchase` is written in `create_order_from_cart()`

Local DB snapshot:

- `purchase`: `39` rows, total weight `55`
- `click`: `0`
- `cart`: `0`
- `reject`: `0`

## ETL / Data Source Notes

Relevant generation paths found:

- `scripts/gold/goods.py`
  - joins OCR into `ingredient_text_ocr`
  - joins health tag results into `health_concern_tags`
  - joins parsed ingredients into `main_ingredients`
  - calculates `popularity_score`
  - calculates `sentiment_avg`
  - calculates `repeat_rate`
- `scripts/gold/health_tags.py`
  - generates `health_concern_tags`
- `scripts/gold/ingredients.py`
  - generates `main_ingredients`
- `scripts/ingest_postgres.py`
  - writes these fields into PostgreSQL `product`

Observed implication from code:

- `sentiment_avg` and `repeat_rate` depend on review-side inputs in `scripts/gold/goods.py`
- when review inputs are missing, these fields are intentionally left as `None`
- `health_concern_tags` are only joined for OCR-target products
- `ingredient_text_ocr` and `main_ingredients` are also tied to OCR / ingredient parsing availability

## Current Risks

1. Ranking features are sparse.
   - `sentiment_avg`, `repeat_rate`, `health_concern_tags` have high null rates.

2. Safety-related ingredient coverage is incomplete.
   - `main_ingredients` and `ingredient_text_ocr` are missing for about half of products.

3. Online feedback loop is effectively absent.
   - recommendation can only rely on product metadata and purchase logs.
   - click/cart/reject signal coverage is now possible but still sparse.

## Event Hook Status

Frontend recommendation panel actions found:

- `services/django/templates/chat/index.html`
  - `addRecommendedToCart(button)`
  - `toggleRecommendedWishlist(button)`
  - product thumbnail / name links open external `product_url`

Backend event handling status:

- recommendation card -> cart
  - goes through `POST /api/orders/cart/`
  - now can be extended by writing `UserInteraction(interaction_type="cart")` in cart API
- recommendation card -> wishlist
  - goes through `POST/DELETE /api/orders/wishlist/`
  - wishlist is currently separate from `UserInteraction`
- recommendation card click
  - can be sent to `POST /api/orders/interactions/` with `interaction_type="click"`
- recommendation reject / dislike
  - can be sent to `POST /api/orders/interactions/` with `interaction_type="reject"`
  - current UI can support lightweight dismiss-style feedback

Practical implication:

- low-risk extension points are cart add logging, recommendation click logging, and lightweight reject logging
- next remaining work is aggregation / feature consumption on the recommendation side

## Next Actions

1. Verify how `popularity_score`, `sentiment_avg`, and `repeat_rate` are generated in ETL.
2. Check whether `health_concern_tags` and `ingredient_text_ocr` can be backfilled from existing pipelines.
3. Define minimal interaction logging scope for recommendation:
   - cart add
   - recommendation click
   - recommendation reject
4. Prepare a feature proposal for rerank input:
   - recent click count
   - recent cart count
   - recent purchase count
   - reject count
   - category preference count

## Candidate Behavior Features

### Short-term feasible

- `recent_purchase_count_by_goods_id`
- `recent_purchase_count_by_category`
- `recent_cart_count_by_goods_id`
- `recent_cart_count_by_category`
- `recent_click_count_by_goods_id`
- `recent_click_count_by_category`

Reason:

- `purchase` is already stored
- `cart` can be added on top of the existing cart API with low write-scope risk
- recommendation card click can be logged through a dedicated interaction endpoint

### Mid-term feasible

- `recent_recommendation_panel_click_count`
- `recent_reject_count_by_goods_id`
- `recent_reject_count_by_category`

Reason:

- needs aggregation strategy on top of raw click/reject events

### Long-term / optional

- `reject_count_by_goods_id`
- `reject_count_by_category`
- `session_level_skip_rate`

Reason:

- reject UI and semantics are not implemented yet

## Suggested Implementation Order

1. backfill / verify metadata fields used by current rerank
2. add `cart` interaction logging
3. define recommendation click logging path
4. add aggregate feature query layer for rerank experiments

## Implementation Progress

Completed in this branch:

- `cart` interaction logging on `POST /api/orders/cart/`
- `click` interaction logging endpoint via `POST /api/orders/interactions/`
- lightweight `reject` logging path from recommendation cards
- FastAPI repository layer for interaction aggregates:
  - goods-level counts
  - category-level counts
