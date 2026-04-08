# 관리자 통계 개인화 신호 고도화 계획

작성일: 2026-04-08

## 목적
- 관리자 통계 화면의 `개인화 신호` 섹션을 발표용 목업 지표에서 실제 이벤트 기반 지표로 단계적으로 교체합니다.
- 운영 통계와 추천 시스템이 같은 신호를 공유하도록 설계합니다.
- 이후 다른 에이전트가 바로 이어서 작업할 수 있도록 현재 상태와 구현 위치를 명시합니다.

## 현재 상태
- 관리자 통계 화면은 아래 파일에서 렌더링됩니다.
  - `services/django/users/pages/views_vendor.py`
  - `services/django/templates/users/vendor_analytics.html`
- 현재 `개인화 신호`에 보이는 일부 값은 실제 저장 필드가 아니라 통계 화면용 가공 지표입니다.
- 현재 화면에서 사용하는 항목:
  - 추천 반응률
  - 상세 탐색률
  - 장바구니 진입률
  - 구매 전환율
  - 재구매 잠재력
  - 추천 적합도

## 실제 저장 필드로 바로 활용 가능한 신호
아래 필드는 이미 `product` 테이블에 존재합니다.

파일:
- `services/django/products/models.py`

활용 가능 필드:
- `rating`
- `review_count`
- `popularity_score`
- `sentiment_avg`
- `repeat_rate`
- `aspect_palatability`
- `aspect_price_purchase`
- `aspect_delivery_packaging`
- `health_concern_tags`
- `pet_type`
- `category`
- `subcategory`

설명:
- 위 필드는 현재도 관리자 통계/대시보드/상품 상세에서 일부 사용 중입니다.
- 발표 시에는 `리뷰 기반 반응`, `상품 메타`, `추천 점수`를 이미 저장 및 활용 중이라고 설명할 수 있습니다.

## 현재 목업/가공 지표
아래 값은 현재 `views_vendor.py`에서 계산된 통계용 수치입니다.

- 노출
- 클릭
- 상세 진입
- 장바구니
- 구매
- 추천 반응률
- 상세 탐색률
- 장바구니 진입률
- 구매 전환율
- 재구매 잠재력 일부 조합식

주의:
- 이 값들은 실제 프론트/백엔드 이벤트 로그를 집계한 결과가 아닙니다.
- 발표에서는 `현재는 통계 시각화 구조를 먼저 구현했고, 이후 이벤트 수집을 붙여 실제 개인화 신호로 치환 예정`이라고 설명하는 것이 안전합니다.

## 다음 단계 목표
아래 이벤트를 실제로 수집해 `개인화 신호`를 이벤트 기반으로 교체합니다.

### 프론트/웹 이벤트
- 상품 노출
- 추천 슬롯 노출
- 추천 카드 클릭
- 상품 상세 진입
- 장바구니 담기
- 빠른 구매 진입
- 주문 완료
- 검색어 입력
- 필터 선택
- 정렬 변경
- 위시리스트 추가

### 채팅/추천 이벤트
- 추천 응답 생성
- 추천 상품 카드 렌더링
- 추천 상품 카드 클릭
- 추천 후 장바구니 이동
- 추천 후 주문 완료

### 리뷰 기반 확장 신호
- 재구매 리뷰 비율
- 감성 점수 추이
- 속성별 반응 분포
- 연령/체중/품종별 반응 분포

## 권장 데이터 모델
추천:
- 별도 이벤트 테이블 또는 로그 수집 파이프라인 추가
- 예시 컬럼:
  - `event_id`
  - `user_id` 또는 익명 세션 ID
  - `product_id`
  - `session_id`
  - `source`
  - `event_type`
  - `metadata`
  - `created_at`

권장 `event_type` 예시:
- `recommendation_impression`
- `recommendation_click`
- `product_impression`
- `product_click`
- `detail_view`
- `add_to_cart`
- `wishlist_add`
- `checkout_start`
- `purchase_complete`
- `search_submit`
- `filter_apply`

## 백엔드 구현 후보 위치
- Django:
  - `services/django/orders/`
  - `services/django/chat/`
  - `services/django/recommendations/`
  - `services/django/common/`
- FastAPI:
  - 추천/채팅 응답에 이벤트 로깅 훅이 필요하면 `services/fastapi/`

## 프론트 구현 후보 위치
- 추천 카드 클릭/노출:
  - `services/django/templates/chat/index.html`
- 상품 목록/정렬/필터:
  - `services/django/templates/users/vendor_products.html`
  - 사용자 상품 목록 관련 템플릿
- 장바구니/주문:
  - `services/django/templates/orders/` 하위

## 통계 화면 교체 계획
`services/django/users/pages/views_vendor.py`의 `vendor_analytics_view`에서 아래 항목을 순차적으로 교체합니다.

1. 추천 반응률
- 현재: 가공 계산
- 목표: `recommendation_impression` 대비 `recommendation_click`

2. 상세 탐색률
- 현재: 가공 계산
- 목표: `product_click` 또는 `detail_view` 비율

3. 장바구니 진입률
- 현재: 가공 계산
- 목표: `detail_view` 대비 `add_to_cart`

4. 구매 전환율
- 현재: 가공 계산
- 목표: `detail_view` 또는 `checkout_start` 대비 `purchase_complete`

5. 재구매 잠재력
- 현재: `repeat_rate`, `popularity_score` 혼합식
- 목표: 실제 재구매/재방문/재추천 클릭 신호 기반 스코어

## 발표용 메시지
발표에서는 아래처럼 설명합니다.

- 현재 우리는 리뷰 기반 반응 데이터와 상품 메타를 이미 구조화해 저장하고 있다.
- 관리자 통계에서는 이 데이터를 운영 지표와 개인화 신호로 시각화한다.
- 향후에는 클릭, 상세 진입, 장바구니, 구매 같은 이벤트를 추가 수집해 개인화 추천에 직접 반영한다.

## 후속 작업 체크리스트
- [ ] 이벤트 저장 스키마 설계
- [ ] 추천/상품/주문 이벤트 수집 포인트 정의
- [ ] 프론트 이벤트 송신 구현
- [ ] 백엔드 이벤트 적재 API 또는 큐 설계
- [ ] 집계 배치 또는 실시간 집계 방식 결정
- [ ] `vendor_analytics_view`의 가공 지표를 실제 집계 지표로 교체
- [ ] 추천 모델/랭킹 가중치에 개인화 신호 연결
