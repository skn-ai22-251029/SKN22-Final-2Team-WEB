# 추천 시스템 아키텍처

> **Phase 1**: RAG + Content-based Filtering (서비스 런칭)
> **Phase 2**: CF 레이어 추가 (사용자 상호작용 데이터 축적 후)

---

## Phase 1 — RAG 기반 추천

### 추천 흐름

```
사용자 입력 (대화 메시지)
        │
        ▼
┌─────────────────────┐
│  Agent 1: 의도 분류  │  상품추천 / 일반질문 / 후속질문
└─────────┬───────────┘
          │ 상품추천
          ▼
┌──────────────────────────┐
│  Agent 2: 컨텍스트 추출   │
│  · 펫 프로필 로드 (DB)    │
│  · 대화에서 추가 조건 추출 │  → species, allergy, health_concern,
│  · 필터 파라미터 구성      │     budget, food_type, keyword
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│  Agent 3: 상품 검색       │
│  · Pre-filter (PostgreSQL)│  알레르기 성분 포함 상품 제외, 품절 제외
│  · Qdrant Hybrid Search   │  Dense + Sparse + RRF → top-K 후보
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│  Agent 4: 재랭킹          │  ← Phase 2 확장 포인트
│  · popularity_score       │
│  · trend_score            │
│  · sentiment_score        │
│  · (Phase 2) CF_score     │
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│  Agent 5: 응답 생성       │
│  · 선택 상품 + 펫 프로필   │
│  · LLM → 설명 텍스트 생성  │
│  · 스트리밍 출력            │
└──────────────────────────┘
```

### Qdrant 임베딩 대상

```python
product_text = (
    f"{goods_name} {brand_name} "
    f"{' '.join(main_ingredients or [])} "
    f"{' '.join(category_tags or [])} "
    f"{review_summary or ''}"
)
# embed(product_text) → dense vector
# BM25(product_text)  → sparse vector
```

`main_ingredients`: Gold OCR 파이프라인에서 추출
`review_summary`: 리뷰 감성 분석 후 LLM 요약 생성
`category_tags`: `product_category_tag` 테이블 (관절/피부/소화 등)

### Phase 1 랭킹 수식

```
final_score =
    α × vector_similarity      # Qdrant RRF score
  + β × popularity_score       # log(review_count+1) × rating (GP 보정 포함)
  + γ × trend_score            # 최근 N일 리뷰 증가율
  + δ × sentiment_score        # 긍정 리뷰 비율

# 초기 가중치 (튜닝 필요)
α=0.4, β=0.3, γ=0.2, δ=0.1
```

---

## Phase 2 — CF 레이어 추가

### 전제 조건

- 서비스 런칭 후 실사용자 상호작용 데이터 최소 **수천 건** 이상 축적
- 신규 유저(상호작용 < N건)는 CF_score 미적용 (cold-start fallback = Phase 1 그대로)

### 수집할 상호작용 데이터 (Day 1부터 로깅)

| 이벤트 | 신호 방향 | 가중치 |
|--------|---------|-------|
| 상품 카드 클릭 | 약한 긍정 | 1 |
| 장바구니 담기 | 강한 긍정 | 3 |
| 구매 완료 | 가장 강한 긍정 | 5 |
| "이거 말고 다른 거" 요청 | 약한 거절 | -1 |
| 대화 종료 후 미구매 | 중립 | 0 |

```sql
-- Phase 2 준비: schema.sql에 추가 예정
CREATE TABLE user_interaction (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id          UUID         REFERENCES "user"(user_id) ON DELETE SET NULL,
    goods_id         VARCHAR(20)  REFERENCES product(goods_id) ON DELETE CASCADE,
    session_id       UUID         REFERENCES chat_session(session_id) ON DELETE SET NULL,
    interaction_type VARCHAR(20)  NOT NULL
                     CHECK (interaction_type IN ('click', 'cart', 'purchase', 'reject')),
    weight           SMALLINT     NOT NULL DEFAULT 1,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ui_user_id  ON user_interaction(user_id);
CREATE INDEX idx_ui_goods_id ON user_interaction(goods_id);
```

### CF 모델 후보

| 모델 | 특징 | 선택 기준 |
|------|------|---------|
| **Implicit ALS** | 암묵적 피드백 특화, 빠른 학습 | 상호작용 데이터만 있을 때 |
| **LightFM** | Content feature 결합 가능 | 상품 메타데이터(성분/태그) 활용 시 |

### Phase 2 랭킹 수식

```
final_score =
    α × vector_similarity
  + β × popularity_score
  + γ × trend_score
  + δ × sentiment_score
  + ε × CF_score             # ← 추가

# cold-start 처리
ε = 0  if user_interaction_count < THRESHOLD
ε = 0.2  otherwise
```

### CF 확장을 위한 설계 원칙

1. **랭킹 레이어를 함수로 추상화** — `rank(candidates, context) → scored_list`
   - Phase 1: CF_score 항 = 0으로 호출
   - Phase 2: CF_score 주입

2. **상호작용 로깅은 Day 1부터** — CF 모델 학습 전에도 데이터 쌓기

3. **A/B 테스트 준비** — 유저 세그먼트별 가중치 실험 가능하도록 config 분리

---

## 단계별 로드맵

```
[현재] Bronze 크롤링 → Silver ETL → Gold (OCR, 감성분석)
                                            │
                                            ▼
[Phase 1] PostgreSQL + Qdrant 적재 → LangGraph 에이전트 구현 → 서비스 배포
                                            │
                                            ▼ (런칭 후 수개월)
[Phase 2] user_interaction 로그 축적 → CF 모델 학습 → 랭킹 레이어에 CF_score 추가
```
